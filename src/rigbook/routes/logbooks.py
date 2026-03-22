import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from rigbook.db import DB_DIR, db_manager
from rigbook.spots import start_feeds, stop_feeds

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


@router.get("/")
async def list_logbooks():
    dbs = []
    for f in sorted(DB_DIR.glob("*.db")):
        dbs.append({"name": f.stem, "size_bytes": f.stat().st_size})
    return dbs


@router.get("/current")
async def get_current():
    return {"name": db_manager.db_name, "is_open": db_manager.is_open}


@router.post("/open")
async def open_logbook(body: LogbookName):
    _validate_name(body.name)
    db_path = DB_DIR / f"{body.name}.db"
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Logbook not found")
    await db_manager.open(db_path)
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


@router.post("/create")
async def create_logbook(body: LogbookName):
    _validate_name(body.name)
    db_path = DB_DIR / f"{body.name}.db"
    if db_path.exists():
        raise HTTPException(status_code=409, detail="Logbook already exists")
    await db_manager.open(db_path)
    await start_feeds()
    return {"name": body.name, "is_open": True}
