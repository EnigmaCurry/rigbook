import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from importlib.metadata import version
from pathlib import Path

import httpx
import uvicorn
from fastapi import Depends, FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from packaging.version import Version
from sqlalchemy import delete, select

from sqlalchemy.ext.asyncio import AsyncSession

from rigbook.db import Cache, DatabaseLockError, Setting, db_manager, get_session, init_db
from rigbook.flrig import router as flrig_router
from rigbook.routes.logbooks import router as logbooks_router
from rigbook.routes.spots import router as spots_router
from rigbook.spots import start_feeds, stop_feeds
from rigbook.routes.adif import router as adif_router
from rigbook.routes.pota import router as pota_router
from rigbook.routes.qrz import router as qrz_router
from rigbook.routes.search import router as search_router
from rigbook.routes.tiles import router as tiles_router
from rigbook.routes.skcc import router as skcc_router
from rigbook.routes.contacts import router as contacts_router
from rigbook.routes.geo import router as geo_router
from rigbook.routes.notifications import router as notifications_router
from rigbook.sse import router as sse_router
from rigbook.routes.settings import (
    router as settings_router,
    start_auto_backup,
    stop_auto_backup,
)
from rigbook.routes.query import router as query_router
from rigbook.routes.solar import router as solar_router
from rigbook.routes.update import router as update_router
from rigbook._build_info import BUILD_ORIGIN_REPO

logger = logging.getLogger("rigbook")



def _resource_path(relative: str) -> Path:
    """Resolve path to bundled resource (works in both dev and PyInstaller)."""
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent
    return base / relative


def _handle_shutdown_signal(sig, frame):
    import signal
    import threading
    import time

    from rigbook.sse import notify_shutdown

    notify_shutdown()
    # Restore default handlers so a second signal force-quits
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.signal(signal.SIGTERM, signal.SIG_DFL)

    # Delay the actual shutdown so the event loop can flush SSE to clients
    def deferred_shutdown():
        time.sleep(0.5)
        os.kill(os.getpid(), signal.SIGINT)

    threading.Thread(target=deferred_shutdown, daemon=True).start()


@asynccontextmanager
async def lifespan(app: FastAPI):
    import signal

    signal.signal(signal.SIGINT, _handle_shutdown_signal)
    signal.signal(signal.SIGTERM, _handle_shutdown_signal)
    if GITHUB_REPO != "EnigmaCurry/rigbook":
        logger.warning(
            "Custom update source: BUILD_ORIGIN_REPO=%s", GITHUB_REPO
        )
    await init_db()
    if db_manager.is_open:
        await start_feeds()
        await start_auto_backup()
    yield
    await stop_auto_backup()
    await stop_feeds()
    await db_manager.close()


app = FastAPI(title="Rigbook", lifespan=lifespan)


@app.middleware("http")
async def http_middleware(request: Request, call_next):
    response: Response = await call_next(request)
    if not request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-cache"
    if response.status_code >= 400:
        logger.warning(
            '%s - "%s %s" %s',
            request.client.host,
            request.method,
            request.url.path,
            response.status_code,
        )
    return response


@app.get("/api/version")
async def get_version():
    return {"version": version("rigbook")}


GITHUB_REPO = BUILD_ORIGIN_REPO or "EnigmaCurry/rigbook"
UPDATE_CACHE_NS = "update_check"
UPDATE_CACHE_KEY = "latest"
UPDATE_CACHE_TTL = 3600  # 1 hour


@app.get("/api/update-check")
async def check_for_update(
    session: AsyncSession = Depends(get_session), bust: bool = False
):
    current = version("rigbook")

    # Check if update checking is disabled (skip when bust=True so settings page can force-check)
    if not bust:
        row = (
            await session.execute(
                select(Setting).where(Setting.key == "update_check_enabled")
            )
        ).scalar_one_or_none()
        if row and row.value == "false":
            return {"current": current, "latest": None, "update_available": False}

    # Bust cache if requested
    if bust:
        await session.execute(
            delete(Cache).where(
                Cache.namespace == UPDATE_CACHE_NS,
                Cache.key == UPDATE_CACHE_KEY,
            )
        )
        await session.commit()

    # Check cache
    cached = (
        await session.execute(
            select(Cache).where(
                Cache.namespace == UPDATE_CACHE_NS,
                Cache.key == UPDATE_CACHE_KEY,
                Cache.expires_at > time.time(),
            )
        )
    ).scalar_one_or_none()

    fresh_fetch = False
    if cached and cached.value:
        data = json.loads(cached.value)
        latest = data["latest"]
        url = data["url"]
        checked_at = data.get("checked_at", time.time())
    else:
        fresh_fetch = True
        # Fetch from GitHub
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
                    headers={"Accept": "application/vnd.github+json"},
                    timeout=10,
                )
                resp.raise_for_status()
                release = resp.json()
                latest = release["tag_name"].lstrip("v")
                url = release["html_url"]
                logger.info("Update check (%s): current=%s, latest=%s", GITHUB_REPO, current, latest)
        except Exception:
            logger.info("Update check failed: could not reach GitHub")
            return {"current": current, "latest": None, "update_available": False}

        checked_at = time.time()

        # Store in cache
        await session.execute(
            delete(Cache).where(
                Cache.namespace == UPDATE_CACHE_NS,
                Cache.key == UPDATE_CACHE_KEY,
            )
        )
        session.add(
            Cache(
                namespace=UPDATE_CACHE_NS,
                key=UPDATE_CACHE_KEY,
                value=json.dumps(
                    {"latest": latest, "url": url, "checked_at": checked_at}
                ),
                expires_at=time.time() + UPDATE_CACHE_TTL,
            )
        )
        await session.commit()

    dev_suffixes = ("-dev", "-alpha", "-beta", "-rc")
    is_dev = any(s in current for s in dev_suffixes)
    is_exact = current == latest

    try:
        update_available = not is_dev and Version(latest) > Version(current)
    except Exception:
        update_available = not is_dev and latest != current

    result = {
        "current": current,
        "latest": latest,
        "update_available": update_available,
        "is_dev": is_dev,
        "is_exact": is_exact,
        "url": url if update_available else None,
        "checked_at": checked_at,
    }

    if fresh_fetch:
        from rigbook.sse import broadcast

        broadcast("update-check", result)

    return result


app.include_router(logbooks_router)
app.include_router(contacts_router)
app.include_router(settings_router)
app.include_router(flrig_router)
app.include_router(geo_router)
app.include_router(adif_router)
app.include_router(pota_router)
app.include_router(qrz_router)
app.include_router(search_router)
app.include_router(skcc_router)
app.include_router(tiles_router)
app.include_router(spots_router)
app.include_router(notifications_router)
app.include_router(query_router)
app.include_router(solar_router)
app.include_router(update_router)
app.include_router(sse_router)

static_dir = _resource_path("static")
if static_dir.is_dir():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


def run() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Rigbook - Ham Radio Logbook")
    parser.add_argument(
        "--version", action="version", version=f"rigbook {version('rigbook')}"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose/debug logging"
    )
    parser.add_argument(
        "name",
        nargs="?",
        default=None,
        help="Logbook name to open (e.g. field-day, default: rigbook)",
    )
    parser.add_argument(
        "--pick",
        action="store_true",
        help="Enable database picker mode",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the browser automatically",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=None,
        help="Port to listen on (default: auto-select starting from 8073)",
    )
    args = parser.parse_args()

    db_manager.configure(db_name=args.name, picker=args.pick)

    import subprocess
    import webbrowser

    def _detect_browser_name() -> str:
        name = webbrowser.get().name
        if name == "xdg-open":
            try:
                result = subprocess.run(
                    ["xdg-settings", "get", "default-web-browser"],
                    capture_output=True, text=True, timeout=5,
                )
                desktop = result.stdout.strip()
                if desktop:
                    return desktop.removesuffix(".desktop")
            except (OSError, subprocess.TimeoutExpired):
                pass
        return name

    if not db_manager.picker_mode:
        db_path = db_manager.default_db_path
        if db_path.exists() or not db_manager._db_override:
            try:
                db_manager.check_lock(db_path)
            except DatabaseLockError as e:
                no_browser = args.no_browser or os.environ.get(
                    "RIGBOOK_NO_BROWSER", ""
                ).lower() in ("1", "true", "yes")
                lock_info = db_manager.read_lock_info(db_path)
                if not no_browser and lock_info and "host" in lock_info:
                    import urllib.request

                    url = f"http://{lock_info['host']}:{lock_info['port']}"
                    # Wait for the server to be ready (it may have just started)
                    for _ in range(10):
                        try:
                            urllib.request.urlopen(f"{url}/api/settings/", timeout=1)
                            break
                        except Exception:
                            time.sleep(0.5)
                    browser_name = _detect_browser_name()
                    print(f"{e} — opening {url} in {browser_name}")
                    webbrowser.open(url)
                else:
                    print(f"Error: {e}", file=sys.stderr)
                sys.exit(0 if not no_browser and lock_info else 1)

    log_level = "DEBUG" if args.verbose else "INFO"

    class ColorFormatter(logging.Formatter):
        COLORS = {
            logging.WARNING: "\033[33m",   # orange/yellow
            logging.ERROR: "\033[31m",     # red
            logging.CRITICAL: "\033[31;1m",  # bold red
        }
        RESET = "\033[0m"
        converter = time.gmtime

        def format(self, record):
            msg = super().format(record)
            color = self.COLORS.get(record.levelno)
            if color and sys.stderr.isatty():
                return f"{color}{msg}{self.RESET}"
            return msg

    handler = logging.StreamHandler()
    handler.setFormatter(
        ColorFormatter(
            fmt="%(asctime)s UTC %(levelname)s: %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logging.basicConfig(level=log_level, handlers=[handler])
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    host = os.environ.get("RIGBOOK_HOST", "127.0.0.1")
    port = args.port or int(os.environ.get("RIGBOOK_PORT", "8073"))

    db_manager.set_listen_addr(host, port)

    import threading

    no_browser = args.no_browser or os.environ.get(
        "RIGBOOK_NO_BROWSER", ""
    ).lower() in ("1", "true", "yes")
    if not no_browser:
        url = f"http://{host}:{port}"

        def open_browser():
            import time

            time.sleep(1)
            browser_name = _detect_browser_name()
            logger.info("Opening %s in %s", url, browser_name)
            webbrowser.open(url)

        threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(app, host=host, port=port, access_log=False, log_config=None)
