import asyncio
import xmlrpc.client

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rigbook.db import Setting, get_session

router = APIRouter(prefix="/api/flrig", tags=["flrig"])

DEFAULT_FLRIG_HOST = "localhost"
DEFAULT_FLRIG_PORT = "12345"


async def get_flrig_url(session: AsyncSession = Depends(get_session)) -> str:
    host = DEFAULT_FLRIG_HOST
    port = DEFAULT_FLRIG_PORT
    result = await session.execute(
        select(Setting).where(Setting.key.in_(["flrig_host", "flrig_port"]))
    )
    for s in result.scalars():
        if s.key == "flrig_host" and s.value:
            host = s.value
        if s.key == "flrig_port" and s.value:
            port = s.value
    return f"http://{host}:{port}"


class FlrigStatus(BaseModel):
    freq: str | None = None
    mode: str | None = None
    connected: bool = False


class FlrigClient:
    def __init__(self, url: str):
        self.url = url

    def get_frequency(self) -> str | None:
        try:
            server = xmlrpc.client.ServerProxy(self.url)
            return server.rig.get_vfo()
        except Exception:
            return None

    def get_mode(self) -> str | None:
        try:
            server = xmlrpc.client.ServerProxy(self.url)
            return server.rig.get_mode()
        except Exception:
            return None

    def set_frequency(self, freq: str) -> bool:
        try:
            server = xmlrpc.client.ServerProxy(self.url)
            server.rig.set_frequency(float(freq))
            return True
        except Exception:
            return False

    def get_modes(self) -> list[str]:
        try:
            server = xmlrpc.client.ServerProxy(self.url)
            modes = server.rig.get_modes()
            if isinstance(modes, str):
                return [m.strip() for m in modes.split("|") if m.strip()]
            return list(modes)
        except Exception:
            return []

    def set_mode(self, mode: str) -> bool:
        try:
            server = xmlrpc.client.ServerProxy(self.url)
            server.rig.set_mode(mode)
            return True
        except Exception:
            return False


class FlrigSet(BaseModel):
    freq: str | None = None
    mode: str | None = None


@router.get("/status", response_model=FlrigStatus)
async def flrig_status(url: str = Depends(get_flrig_url)):
    loop = asyncio.get_event_loop()
    client = FlrigClient(url)
    freq = await loop.run_in_executor(None, client.get_frequency)
    mode = await loop.run_in_executor(None, client.get_mode)
    connected = freq is not None
    return FlrigStatus(freq=freq, mode=mode, connected=connected)


@router.get("/modes")
async def flrig_modes(url: str = Depends(get_flrig_url)):
    loop = asyncio.get_event_loop()
    client = FlrigClient(url)
    return await loop.run_in_executor(None, client.get_modes)


@router.put("/vfo")
async def flrig_set_vfo(data: FlrigSet, url: str = Depends(get_flrig_url)):
    loop = asyncio.get_event_loop()
    client = FlrigClient(url)
    if data.freq is not None:
        await loop.run_in_executor(None, client.set_frequency, data.freq)
    if data.mode is not None:
        await loop.run_in_executor(None, client.set_mode, data.mode)
    return {"ok": True}
