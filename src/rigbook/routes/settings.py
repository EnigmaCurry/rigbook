from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rigbook.db import Setting, get_session

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingValue(BaseModel):
    value: str


class SettingResponse(BaseModel):
    key: str
    value: str | None

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[SettingResponse])
async def list_settings(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Setting))
    return result.scalars().all()


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(key: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        return SettingResponse(key=key, value=None)
    return setting


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
