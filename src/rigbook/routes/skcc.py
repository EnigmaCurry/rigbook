import logging
import time

import httpx
from fastapi import APIRouter

logger = logging.getLogger("rigbook")


router = APIRouter(prefix="/api/skcc", tags=["skcc"])

SKCC_URL = "https://skccgroup.com/search/skcclist.txt"
CACHE_TTL = 86400  # 24 hours

# In-memory: callsign -> skcc number
_skcc_cache: dict[str, str] = {}
_cache_time: float = 0


async def _ensure_cache():
    global _skcc_cache, _cache_time

    if _skcc_cache and (time.time() - _cache_time) < CACHE_TTL:
        logger.debug("SKCC using cached member list (%d entries)", len(_skcc_cache))
        return

    logger.info("SKCC fetching member list from %s", SKCC_URL)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.get(SKCC_URL)
            res.raise_for_status()
            lines = res.text.splitlines()

        new_cache: dict[str, str] = {}
        for line in lines[1:]:  # skip header
            parts = line.split("|")
            if len(parts) >= 2:
                skcc_nr = parts[0].strip()
                callsign = parts[1].strip().upper()
                # Strip /SK, /EX suffixes from callsign
                base_call = callsign.split("/")[0]
                if base_call and skcc_nr:
                    new_cache[base_call] = skcc_nr
                if callsign != base_call and callsign and skcc_nr:
                    new_cache[callsign] = skcc_nr

        _skcc_cache = new_cache
        _cache_time = time.time()
    except Exception:
        pass


@router.get("/lookup/{callsign}")
async def skcc_lookup(callsign: str):
    await _ensure_cache()

    call_upper = callsign.upper().strip()
    skcc_nr = _skcc_cache.get(call_upper)
    if skcc_nr:
        return {"call": call_upper, "skcc": skcc_nr}

    # Try base callsign without suffix
    base = call_upper.split("/")[0]
    skcc_nr = _skcc_cache.get(base)
    if skcc_nr:
        return {"call": call_upper, "skcc": skcc_nr}

    return {"call": call_upper, "skcc": None}


@router.delete("/cache")
async def clear_skcc_cache():
    global _skcc_cache, _cache_time
    _skcc_cache = {}
    _cache_time = 0
    return {"ok": True}
