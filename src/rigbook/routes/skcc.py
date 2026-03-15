import logging
import time

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from rigbook.db import Cache, get_session

logger = logging.getLogger("rigbook")


router = APIRouter(prefix="/api/skcc", tags=["skcc"])

SKCC_URL = "https://skccgroup.com/search/skcclist.txt"
CACHE_TTL = 86400  # 24 hours
NAMESPACE = "skcc"

# In-memory mirror loaded from DB (avoid re-parsing on every request)
_mem_cache: dict[str, str] = {}
_mem_loaded: float = 0


async def _load_from_db(session: AsyncSession) -> bool:
    """Load SKCC data from DB cache into memory. Returns True if valid cache exists."""
    global _mem_cache, _mem_loaded

    if _mem_cache and (time.time() - _mem_loaded) < 60:
        return True

    result = await session.execute(
        select(Cache).where(
            Cache.namespace == NAMESPACE,
            Cache.expires_at > time.time(),
        )
    )
    rows = result.scalars().all()
    if rows:
        _mem_cache = {r.key: r.value for r in rows}
        _mem_loaded = time.time()
        logger.debug("SKCC loaded %d entries from DB cache", len(_mem_cache))
        return True
    return False


async def _fetch_and_store(session: AsyncSession):
    """Fetch SKCC list from upstream and store in DB."""
    global _mem_cache, _mem_loaded

    logger.info("SKCC fetching member list from %s", SKCC_URL)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.get(SKCC_URL)
            res.raise_for_status()
            lines = res.text.splitlines()
    except Exception:
        logger.warning("SKCC fetch failed")
        return

    # Clear old cache
    await session.execute(delete(Cache).where(Cache.namespace == NAMESPACE))

    expires = time.time() + CACHE_TTL
    new_cache: dict[str, str] = {}

    for line in lines[1:]:
        parts = line.split("|")
        if len(parts) >= 2:
            skcc_nr = parts[0].strip()
            callsign = parts[1].strip().upper()
            base_call = callsign.split("/")[0]
            if base_call and skcc_nr:
                new_cache[base_call] = skcc_nr
                session.add(
                    Cache(namespace=NAMESPACE, key=base_call, value=skcc_nr, expires_at=expires)
                )

    await session.commit()
    _mem_cache = new_cache
    _mem_loaded = time.time()
    logger.info("SKCC cached %d entries", len(new_cache))


@router.get("/lookup/{callsign}")
async def skcc_lookup(callsign: str, session: AsyncSession = Depends(get_session)):
    if not await _load_from_db(session):
        await _fetch_and_store(session)

    call_upper = callsign.upper().strip()
    skcc_nr = _mem_cache.get(call_upper)
    if not skcc_nr:
        base = call_upper.split("/")[0]
        skcc_nr = _mem_cache.get(base)

    return {"call": call_upper, "skcc": skcc_nr}


@router.delete("/cache")
async def clear_skcc_cache(session: AsyncSession = Depends(get_session)):
    global _mem_cache, _mem_loaded
    await session.execute(delete(Cache).where(Cache.namespace == NAMESPACE))
    await session.commit()
    _mem_cache = {}
    _mem_loaded = 0
    return {"ok": True}
