import asyncio
import xmlrpc.client

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/flrig", tags=["flrig"])

FLRIG_URL = "http://localhost:12345"


class FlrigStatus(BaseModel):
    freq: str | None = None
    mode: str | None = None
    connected: bool = False


class FlrigClient:
    def __init__(self, url: str = FLRIG_URL):
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
async def flrig_status():
    loop = asyncio.get_event_loop()
    client = FlrigClient()
    freq = await loop.run_in_executor(None, client.get_frequency)
    mode = await loop.run_in_executor(None, client.get_mode)
    connected = freq is not None
    return FlrigStatus(freq=freq, mode=mode, connected=connected)


@router.get("/modes")
async def flrig_modes():
    loop = asyncio.get_event_loop()
    client = FlrigClient()
    return await loop.run_in_executor(None, client.get_modes)


@router.put("/vfo")
async def flrig_set_vfo(data: FlrigSet):
    loop = asyncio.get_event_loop()
    client = FlrigClient()
    if data.freq is not None:
        await loop.run_in_executor(None, client.set_frequency, data.freq)
    if data.mode is not None:
        await loop.run_in_executor(None, client.set_mode, data.mode)
    return {"ok": True}
