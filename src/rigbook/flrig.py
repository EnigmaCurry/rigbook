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
    client = FlrigClient()
    freq = client.get_frequency()
    mode = client.get_mode()
    connected = freq is not None
    return FlrigStatus(freq=freq, mode=mode, connected=connected)


@router.put("/vfo")
async def flrig_set_vfo(data: FlrigSet):
    client = FlrigClient()
    if data.freq is not None:
        client.set_frequency(data.freq)
    if data.mode is not None:
        client.set_mode(data.mode)
    return {"ok": True}
