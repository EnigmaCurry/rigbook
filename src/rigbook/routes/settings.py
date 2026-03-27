import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rigbook.db import Setting, db_manager, get_session

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingValue(BaseModel):
    value: str


class SettingResponse(BaseModel):
    key: str
    value: str | None

    model_config = {"from_attributes": True}


HIDDEN_KEYS = {"qrz_password", "hamalert_password"}


def _redact(setting: Setting) -> SettingResponse:
    if setting.key in HIDDEN_KEYS:
        return SettingResponse(key=setting.key, value="***" if setting.value else None)
    return SettingResponse.model_validate(setting)


@router.get("/", response_model=list[SettingResponse])
async def list_settings(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Setting))
    return [_redact(s) for s in result.scalars().all()]


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(key: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        return SettingResponse(key=key, value=None)
    return _redact(setting)


@router.put("/{key}", response_model=SettingResponse)
async def upsert_setting(
    key: str, data: SettingValue, session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = data.value
    else:
        setting = Setting(key=key, value=data.value)
        session.add(setting)
    await session.commit()
    await session.refresh(setting)
    return setting


class BackupRequest(BaseModel):
    directory: str


@router.post("/backup")
async def backup_database(data: BackupRequest):
    db_path = db_manager.db_path
    if not db_path or not db_path.exists():
        raise HTTPException(status_code=400, detail="No database is open")

    backup_dir = Path(data.directory).expanduser().resolve()
    if not backup_dir.is_dir():
        raise HTTPException(
            status_code=400, detail=f"Directory does not exist: {backup_dir}"
        )

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%Sz")
    backup_name = f"{db_path.stem}_backup_{ts}{db_path.suffix}"
    backup_path = backup_dir / backup_name

    try:
        shutil.copy2(str(db_path), str(backup_path))
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Backup failed: {e}") from e

    return {"path": str(backup_path), "size": backup_path.stat().st_size}


@router.get("/backup/db-info")
async def get_db_info():
    db_path = db_manager.db_path
    if not db_path or not db_path.exists():
        return {"path": None, "size": None, "directory": None}
    return {
        "path": str(db_path),
        "size": db_path.stat().st_size,
        "directory": str(db_path.parent),
    }
