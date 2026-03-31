import os
import re
import signal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from rigbook.db import DB_DIR, DatabaseLockError, _read_last_opened, db_manager
from rigbook.spots import start_feeds, stop_feeds
from rigbook.sse import notify_shutdown

router = APIRouter(prefix="/api/logbooks", tags=["logbooks"])


class LogbookName(BaseModel):
    name: str


_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def _validate_name(name: str) -> None:
    if not _NAME_RE.match(name):
        raise HTTPException(
            status_code=400,
            detail="Name must contain only letters, digits, hyphens, and underscores",
        )


@router.get("/mode")
async def get_mode():
    return {
        "picker": db_manager.picker_mode,
        "db_override": db_manager._db_override is not None,
    }


def _is_locked(db_path) -> bool:
    """Check if a logbook database is locked by another process."""
    import fcntl

    lock_path = db_path.with_suffix(".lock")
    if not lock_path.exists():
        return False
    try:
        with open(lock_path, "r+") as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(f, fcntl.LOCK_UN)
        return False
    except OSError:
        return True


@router.get("/")
async def list_logbooks():
    last_opened = _read_last_opened()
    dbs = []
    for f in DB_DIR.glob("*.db"):
        dbs.append({
            "name": f.stem,
            "size_bytes": f.stat().st_size,
            "locked": _is_locked(f),
        })
    dbs.sort(key=lambda d: last_opened.get(d["name"], 0), reverse=True)
    return dbs


@router.get("/current")
async def get_current():
    return {
        "name": db_manager.db_name,
        "is_open": db_manager.is_open,
        "pending": db_manager.pending_name,
    }


@router.post("/confirm")
async def confirm_create():
    if not db_manager.pending_name:
        raise HTTPException(status_code=400, detail="No pending logbook to confirm")
    name = db_manager.pending_name
    db_manager.pending_name = None
    db_path = DB_DIR / f"{name}.db"
    try:
        await db_manager.open(db_path)
    except DatabaseLockError as e:
        raise HTTPException(status_code=409, detail=str(e))
    await start_feeds()
    return {"name": name, "is_open": True}


def _deferred_kill(delay: float = 1.0):
    """Send SIGTERM after a delay so SSE can flush the shutdown event."""
    import threading
    import time

    def kill():
        time.sleep(delay)
        os.kill(os.getpid(), signal.SIGKILL)

    threading.Thread(target=kill, daemon=True).start()


@router.post("/decline")
async def decline_create():
    if not db_manager.pending_name:
        raise HTTPException(status_code=400, detail="No pending logbook to decline")
    db_manager.pending_name = None
    notify_shutdown()
    os.kill(os.getpid(), signal.SIGTERM)
    _deferred_kill()
    return {"status": "shutting down"}


@router.post("/shutdown")
async def shutdown_server():
    from rigbook.main import NO_SHUTDOWN

    if NO_SHUTDOWN:
        raise HTTPException(status_code=403, detail="Shutdown is disabled")
    notify_shutdown()
    os.kill(os.getpid(), signal.SIGTERM)
    _deferred_kill()
    return {"status": "shutting down"}


@router.post("/open")
async def open_logbook(body: LogbookName):
    _validate_name(body.name)
    db_path = DB_DIR / f"{body.name}.db"
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Logbook not found")
    try:
        await db_manager.open(db_path)
    except DatabaseLockError as e:
        raise HTTPException(status_code=409, detail=str(e))
    await start_feeds()
    return {"name": body.name, "is_open": True}


@router.post("/close")
async def close_logbook():
    if not db_manager.picker_mode:
        raise HTTPException(
            status_code=400, detail="Close is only available in picker mode"
        )
    await stop_feeds()
    await db_manager.close()
    return {"is_open": False}


@router.delete("/delete")
async def delete_logbook(body: LogbookName):
    _validate_name(body.name)
    if not db_manager.is_open or db_manager.db_name != body.name:
        raise HTTPException(
            status_code=400, detail="Can only delete the currently open logbook"
        )
    db_path = DB_DIR / f"{body.name}.db"
    await stop_feeds()
    await db_manager.close()
    if db_path.exists():
        db_path.unlink()
    if db_manager.picker_mode:
        return {"deleted": True, "shutdown": False}
    notify_shutdown()
    os.kill(os.getpid(), signal.SIGTERM)
    _deferred_kill()
    return {"deleted": True, "shutdown": True}


@router.post("/create")
async def create_logbook(body: LogbookName):
    _validate_name(body.name)
    db_path = DB_DIR / f"{body.name}.db"
    if db_path.exists():
        raise HTTPException(status_code=409, detail="Logbook already exists")
    try:
        await db_manager.open(db_path)
    except DatabaseLockError as e:
        raise HTTPException(status_code=409, detail=str(e))
    await start_feeds()
    return {"name": body.name, "is_open": True}
