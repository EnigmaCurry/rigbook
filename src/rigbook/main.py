import base64
import logging
import os
import sys
from contextlib import asynccontextmanager
from importlib.metadata import version
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles

from rigbook.db import db_manager, init_db
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
    get_auth_settings,
    _verify_password,
)
from rigbook.routes.solar import router as solar_router

logger = logging.getLogger("rigbook")

_no_auth = False


def _resource_path(relative: str) -> Path:
    """Resolve path to bundled resource (works in both dev and PyInstaller)."""
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent
    return base / relative


def _handle_sigint(sig, frame):
    import signal
    import threading
    import time

    from rigbook.sse import notify_shutdown

    notify_shutdown()
    # Restore default handler so a second Ctrl-C force-quits
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Delay the actual shutdown so the event loop can flush SSE to clients
    def deferred_shutdown():
        time.sleep(0.5)
        os.kill(os.getpid(), signal.SIGINT)

    threading.Thread(target=deferred_shutdown, daemon=True).start()


@asynccontextmanager
async def lifespan(app: FastAPI):
    import signal

    signal.signal(signal.SIGINT, _handle_sigint)
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
async def auth_middleware(request: Request, call_next):
    if _no_auth:
        return await call_next(request)
    try:
        auth = await get_auth_settings()
    except Exception:
        return await call_next(request)
    if not auth.get("enabled"):
        return await call_next(request)

    realm = db_manager.db_name or "rigbook"
    header = request.headers.get("authorization", "")
    if header.startswith("Basic "):
        try:
            decoded = base64.b64decode(header[6:]).decode("utf-8")
            username, _, password = decoded.partition(":")
            if (
                username.upper() == (auth.get("callsign") or "").upper()
                and _verify_password(password, auth.get("password", ""), auth.get("salt", ""))
            ):
                return await call_next(request)
        except Exception:
            pass

    return Response(
        status_code=401,
        headers={"WWW-Authenticate": f'Basic realm="{realm}"'},
    )


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
        "--no-auth",
        action="store_true",
        help="Disable authentication even if configured",
    )
    args = parser.parse_args()

    global _no_auth
    _no_auth = args.no_auth

    db_manager.configure(db_name=args.name, picker=args.pick)

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
    port = int(os.environ.get("RIGBOOK_PORT", "8073"))

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
