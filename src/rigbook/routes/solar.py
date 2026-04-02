import asyncio
import time
import xml.etree.ElementTree as ET

import httpx
from fastapi import APIRouter

router = APIRouter(prefix="/api/solar", tags=["solar"])

HAMQSL_URL = "https://www.hamqsl.com/solarxml.php"
CACHE_TTL = 600  # 10 minutes

_cache: dict | None = None
_fetched_at: float = 0
_lock: asyncio.Lock | None = None


def _get_lock():
    global _lock
    if _lock is None:
        _lock = asyncio.Lock()
    return _lock


def _parse_solar_xml(xml_text: str) -> dict:
    root = ET.fromstring(xml_text)
    sd = root.find("solardata")
    if sd is None:
        return {}

    def text(tag: str) -> str:
        el = sd.find(tag)
        return (el.text or "").strip() if el is not None else ""

    bands = []
    cc = sd.find("calculatedconditions")
    if cc is not None:
        for b in cc.findall("band"):
            bands.append({
                "name": b.get("name", ""),
                "time": b.get("time", ""),
                "condition": (b.text or "").strip(),
            })

    vhf = []
    vc = sd.find("calculatedvhfconditions")
    if vc is not None:
        for p in vc.findall("phenomenon"):
            vhf.append({
                "name": p.get("name", ""),
                "location": p.get("location", ""),
                "condition": (p.text or "").strip(),
            })

    return {
        "updated": text("updated"),
        "solarflux": text("solarflux"),
        "aindex": text("aindex"),
        "kindex": text("kindex"),
        "xray": text("xray"),
        "sunspots": text("sunspots"),
        "heliumline": text("heliumline"),
        "protonflux": text("protonflux"),
        "electronflux": text("electonflux"),
        "aurora": text("aurora"),
        "solarwind": text("solarwind"),
        "magneticfield": text("magneticfield"),
        "geomagfield": text("geomagfield"),
        "signalnoise": text("signalnoise"),
        "muf": text("muf"),
        "bands": bands,
        "vhf": vhf,
    }


@router.get("/conditions")
async def get_conditions():
    global _cache, _fetched_at
    now = time.time()
    if _cache is not None and now - _fetched_at < CACHE_TTL:
        return _cache
    async with _get_lock():
        now = time.time()
        if _cache is not None and now - _fetched_at < CACHE_TTL:
            return _cache
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                res = await client.get(HAMQSL_URL)
                res.raise_for_status()
                _cache = _parse_solar_xml(res.text)
                _fetched_at = time.time()
                return _cache
        except Exception as e:
            if _cache is not None:
                return _cache
            return {"error": str(e)}


@router.delete("/cache")
async def clear_solar_cache():
    global _cache, _fetched_at
    _cache = None
    _fetched_at = 0
    return {"ok": True}


@router.get("/cache/stats")
async def solar_cache_stats():
    """Return solar cache statistics."""
    now = time.time()
    cached = _cache is not None
    age = round(now - _fetched_at) if cached and _fetched_at else None
    return {
        "cached": cached,
        "age_seconds": age,
        "ttl_seconds": CACHE_TTL,
    }
