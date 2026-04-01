import asyncio
import xmlrpc.client

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from rigbook.db import get_session, resolve_setting

router = APIRouter(prefix="/api/flrig", tags=["flrig"])

DEFAULT_FLRIG_HOST = "127.0.0.1"
DEFAULT_FLRIG_PORT = "12345"

SIMULATED_MODES = ["CW", "USB", "LSB", "RTTY", "FT8"]


# --- Simulated radio state ---
_sim_freq: str = "14074000"
_sim_mode: str = "CW"


async def is_simulate(session: AsyncSession) -> bool:
    val = await resolve_setting("flrig_simulate", session)
    return val == "true"


async def get_flrig_url(session: AsyncSession = Depends(get_session)) -> str:
    host = await resolve_setting("flrig_host", session, DEFAULT_FLRIG_HOST)
    port = await resolve_setting("flrig_port", session, DEFAULT_FLRIG_PORT)
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
async def flrig_status(
    url: str = Depends(get_flrig_url),
    session: AsyncSession = Depends(get_session),
):
    if await is_simulate(session):
        return FlrigStatus(freq=_sim_freq, mode=_sim_mode, connected=True)
    loop = asyncio.get_event_loop()
    client = FlrigClient(url)
    freq = await loop.run_in_executor(None, client.get_frequency)
    mode = await loop.run_in_executor(None, client.get_mode)
    connected = freq is not None
    return FlrigStatus(freq=freq, mode=mode, connected=connected)


@router.get("/modes")
async def flrig_modes(
    url: str = Depends(get_flrig_url),
    session: AsyncSession = Depends(get_session),
):
    if await is_simulate(session):
        return SIMULATED_MODES
    loop = asyncio.get_event_loop()
    client = FlrigClient(url)
    return await loop.run_in_executor(None, client.get_modes)


@router.put("/vfo")
async def flrig_set_vfo(
    data: FlrigSet,
    url: str = Depends(get_flrig_url),
    session: AsyncSession = Depends(get_session),
):
    global _sim_freq, _sim_mode
    if await is_simulate(session):
        if data.freq is not None:
            _sim_freq = data.freq
        if data.mode is not None:
            _sim_mode = data.mode
        return {"ok": True}
    loop = asyncio.get_event_loop()
    client = FlrigClient(url)
    if data.freq is not None:
        await loop.run_in_executor(None, client.set_frequency, data.freq)
    if data.mode is not None:
        await loop.run_in_executor(None, client.set_mode, data.mode)
    return {"ok": True}
