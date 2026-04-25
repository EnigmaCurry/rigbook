import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from guidebook.db import (
    GLOBAL_DEFAULTABLE_KEYS,
    GLOBAL_ONLY_KEYS,
    GlobalSetting,
    get_global_session,
)

logger = logging.getLogger("guidebook")

router = APIRouter(prefix="/api/global-settings", tags=["global-settings"])

ALLOWED_KEYS = GLOBAL_DEFAULTABLE_KEYS | GLOBAL_ONLY_KEYS
HIDDEN_KEYS: set[str] = set()


class SettingValue(BaseModel):
    value: str


class SettingResponse(BaseModel):
    key: str
    value: str | None

    model_config = {"from_attributes": True}


def _redact(setting: GlobalSetting) -> SettingResponse:
    if setting.key in HIDDEN_KEYS:
        return SettingResponse(key=setting.key, value="***" if setting.value else None)
    return SettingResponse.model_validate(setting)


@router.get("/", response_model=list[SettingResponse])
async def list_global_settings(gdb: AsyncSession = Depends(get_global_session)):
    result = await gdb.execute(select(GlobalSetting))
    return [_redact(s) for s in result.scalars().all()]


@router.get("/{key}", response_model=SettingResponse)
async def get_global_setting(key: str, gdb: AsyncSession = Depends(get_global_session)):
    result = await gdb.execute(select(GlobalSetting).where(GlobalSetting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        return SettingResponse(key=key, value=None)
    return _redact(setting)


@router.put("/{key}", response_model=SettingResponse)
async def upsert_global_setting(
    key: str,
    data: SettingValue,
    gdb: AsyncSession = Depends(get_global_session),
):
    if key not in ALLOWED_KEYS:
        raise HTTPException(
            status_code=400,
            detail=f"Key '{key}' is not a valid global setting",
        )
    result = await gdb.execute(select(GlobalSetting).where(GlobalSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting:
        if setting.value == data.value:
            return _redact(setting)
        setting.value = data.value
    else:
        setting = GlobalSetting(key=key, value=data.value)
        gdb.add(setting)
    await gdb.commit()
    await gdb.refresh(setting)
    log_value = "***" if key in HIDDEN_KEYS else data.value
    logger.info("Global setting changed: %s = %s", key, log_value)

    if key == "disable_shutdown":
        import guidebook.main as _main
        from guidebook.sse import stop_auto_shutdown

        if data.value == "true":
            _main.NO_SHUTDOWN = True
            await stop_auto_shutdown()
        else:
            _main.NO_SHUTDOWN = False

    if key == "auto_shutdown_on_disconnect":
        from guidebook.main import NO_SHUTDOWN
        from guidebook.sse import start_auto_shutdown, stop_auto_shutdown

        if not NO_SHUTDOWN and data.value == "true":
            await start_auto_shutdown()
        else:
            await stop_auto_shutdown()

    return _redact(setting)
