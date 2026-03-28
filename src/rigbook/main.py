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

from rigbook.db import DatabaseLockError, db_manager, init_db
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


def _list_logbooks(quiet_if_empty: bool = False) -> None:
    """List all running rigbook processes."""
    from rigbook.db import DB_DIR

    rows = []
    for lock_path in sorted(DB_DIR.glob("*.lock")):
        db_path = lock_path.with_suffix(".db")
        info = db_manager.read_lock_info(db_path)
        if info is None:
            continue
        pid = info["pid"]
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            lock_path.unlink(missing_ok=True)
            continue
        except PermissionError:
            pass
        name = db_path.stem
        addr = f"{info.get('host', '?')}:{info.get('port', '?')}" if "port" in info else "?"
        rows.append((name, str(pid), addr))
    if rows:
        widths = [max(len(r[i]) for r in rows) for i in range(3)]
        print("Running logbooks:")
        for name, pid, addr in rows:
            print(f"  {name:<{widths[0]}}  {pid:>{widths[1]}}  {addr}")
    elif not quiet_if_empty:
        print("No running rigbook processes")


def _open_logbook(name: str | None, port: int | None = None) -> None:
    """Open a logbook in the browser, starting a background server if needed."""
    import signal
    import subprocess
    import time
    import webbrowser

    from importlib.metadata import version

    from rigbook.db import DB_DIR

    db_name = name or "rigbook"
    db_path = DB_DIR / f"{db_name}.db"
    my_version = version("rigbook")
    info = db_manager.read_lock_info(db_path)
    if info and "port" in info:
        pid = info["pid"]
        try:
            os.kill(pid, 0)
            running_version = info.get("version")
            if running_version and running_version != my_version:
                print(f"Logbook '{db_name}' is running v{running_version}, current is v{my_version}. Restarting ...")
                os.kill(pid, signal.SIGTERM)
                time.sleep(1)
            else:
                url = f"http://{info['host']}:{info['port']}"
                ver = f" v{running_version}" if running_version else ""
                print(f"Logbook '{db_name}'{ver} already running at {url}")
                print("Opening in browser ...")
                print(f"To stop: {Path(sys.argv[0]).name} --quit{'' if db_name == 'rigbook' else ' ' + db_name}")
                webbrowser.open(url)
                return
        except ProcessLookupError:
            db_path.with_suffix(".lock").unlink(missing_ok=True)

    print(f"Starting logbook '{db_name}' ...")
    cmd = [sys.argv[0], "--server"]
    if name:
        cmd.append(name)
    if port:
        cmd.extend(["--port", str(port)])
    log_path = db_path.with_suffix(".log")
    log_fh = open(log_path, "w")
    proc = subprocess.Popen(
        cmd,
        start_new_session=True,
        stdout=log_fh,
        stderr=log_fh,
    )
    time.sleep(1)
    log_fh.close()

    if proc.poll() is not None:
        log_output = log_path.read_text().strip()
        print(f"Error: logbook '{db_name}' failed to start", file=sys.stderr)
        if log_output:
            print(log_output, file=sys.stderr)
        log_path.unlink(missing_ok=True)
        sys.exit(1)

    log_path.unlink(missing_ok=True)
    info = db_manager.read_lock_info(db_path)
    if info and "port" in info:
        url = f"http://{info['host']}:{info['port']}"
        print(f"Logbook '{db_name}' running at {url}")
        print("Opening in browser ...")
        print(f"To stop: {Path(sys.argv[0]).name} --quit{'' if db_name == 'rigbook' else ' ' + db_name}")
        webbrowser.open(url)
    else:
        print(f"Error: logbook '{db_name}' did not start", file=sys.stderr)
        sys.exit(1)


def _close_logbook(name: str) -> None:
    """Send SIGTERM to the process holding the named logbook."""
    import signal

    from rigbook.db import DB_DIR

    db_path = DB_DIR / f"{name}.db"
    pid = db_manager.read_lock_pid(db_path)
    if pid is None:
        print(f"Logbook '{name}' is not running")
        _list_logbooks(quiet_if_empty=True)
        return
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Sent SIGTERM to logbook '{name}' (pid {pid})")
    except ProcessLookupError:
        print(f"Logbook '{name}' lock is stale (pid {pid} not found), removing lock")
        db_path.with_suffix(".lock").unlink(missing_ok=True)
    except PermissionError:
        print(f"Error: no permission to signal pid {pid}", file=sys.stderr)
        sys.exit(1)


def _close_all_logbooks() -> None:
    """Send SIGTERM to all running rigbook processes."""
    import signal

    from rigbook.db import DB_DIR

    found = False
    for lock_path in sorted(DB_DIR.glob("*.lock")):
        db_path = lock_path.with_suffix(".db")
        info = db_manager.read_lock_info(db_path)
        if info is None:
            continue
        pid = info["pid"]
        name = db_path.stem
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"Sent SIGTERM to logbook '{name}' (pid {pid})")
            found = True
        except ProcessLookupError:
            lock_path.unlink(missing_ok=True)
        except PermissionError:
            print(f"Error: no permission to signal '{name}' (pid {pid})", file=sys.stderr)
    if not found:
        print("No running rigbook processes")



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
        "name",
        nargs="?",
        default=None,
        help="Logbook name (e.g. field-day, default: rigbook)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose/debug logging"
    )
    parser.add_argument(
        "--server",
        action="store_true",
        help="Run the server in the foreground",
    )
    parser.add_argument(
        "--pick",
        action="store_true",
        help="Enable database picker mode (implies --server)",
    )
    parser.add_argument(
        "--no-auth",
        action="store_true",
        help="Disable authentication even if configured",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=None,
        help="Port to listen on (default: auto-select starting from 8073)",
    )
    parser.add_argument(
        "--quit",
        nargs="?",
        const="rigbook",
        metavar="NAME",
        help="Send SIGTERM to the process holding logbook NAME and exit (default: rigbook)",
    )
    parser.add_argument(
        "--quit-all",
        action="store_true",
        help="Send SIGTERM to all running rigbook processes and exit",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="List running rigbook processes and exit",
    )
    args = parser.parse_args()

    if args.list:
        _list_logbooks()
        return

    if args.quit_all:
        _close_all_logbooks()
        return

    if args.quit:
        _close_logbook(args.quit)
        return

    if not args.server and not args.pick:
        _open_logbook(args.name, port=args.port)
        return

    # --- foreground server mode ---
    global _no_auth
    _no_auth = args.no_auth

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

    uvicorn.run(app, host=host, port=port, access_log=False)
