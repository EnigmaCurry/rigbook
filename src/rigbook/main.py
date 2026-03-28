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
from rigbook.routes.solar import router as solar_router

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
async def log_errors(request: Request, call_next):
    response: Response = await call_next(request)
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


GITHUB_REPO = "EnigmaCurry/rigbook"
UPDATE_CACHE_NS = "update_check"
UPDATE_CACHE_KEY = "latest"
UPDATE_CACHE_TTL = 3600  # 1 hour


@app.get("/api/update-check")
async def check_for_update(session: AsyncSession = Depends(get_session)):
    current = version("rigbook")

    # Check if update checking is disabled
    row = (
        await session.execute(
            select(Setting).where(Setting.key == "update_check_enabled")
        )
    ).scalar_one_or_none()
    if row and row.value == "false":
        return {"current": current, "latest": None, "update_available": False}

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

    if cached and cached.value:
        data = json.loads(cached.value)
        latest = data["latest"]
        url = data["url"]
    else:
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
        except Exception:
            logger.debug("Update check failed")
            return {"current": current, "latest": None, "update_available": False}

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
                value=json.dumps({"latest": latest, "url": url}),
                expires_at=time.time() + UPDATE_CACHE_TTL,
            )
        )
        await session.commit()

    try:
        update_available = Version(latest) > Version(current)
    except Exception:
        update_available = latest != current

    return {
        "current": current,
        "latest": latest,
        "update_available": update_available,
        "url": url if update_available else None,
    }


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
app.include_router(solar_router)
app.include_router(sse_router)

static_dir = _resource_path("static")
if static_dir.is_dir():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


def run() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Rigbook - Ham Radio Logbook")
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

    if not db_manager.picker_mode:
        db_path = db_manager.default_db_path
        if db_path.exists() or not db_manager._db_override:
            try:
                db_manager.check_lock(db_path)
            except DatabaseLockError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)

    log_level = "DEBUG" if args.verbose else "INFO"
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s: %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    host = os.environ.get("RIGBOOK_HOST", "127.0.0.1")
    port = args.port or int(os.environ.get("RIGBOOK_PORT", "8073"))

    db_manager.set_listen_addr(host, port)

    import threading
    import webbrowser

    no_browser = args.no_browser or os.environ.get(
        "RIGBOOK_NO_BROWSER", ""
    ).lower() in ("1", "true", "yes")
    if not no_browser:
        url = f"http://{host}:{port}"

        def open_browser():
            import time

            time.sleep(1)
            webbrowser.open(url)

        threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(app, host=host, port=port, access_log=False)
