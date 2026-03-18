import asyncio
import logging
import time

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from rigbook.db import Cache, get_session

logger = logging.getLogger("rigbook")

_fetch_lock = asyncio.Lock()


router = APIRouter(prefix="/api/skcc", tags=["skcc"])

SKCC_URL = "https://skccgroup.com/search/skcclist.txt"
CACHE_TTL = 86400  # 24 hours
NAMESPACE = "skcc"


async def _has_valid_cache(session: AsyncSession) -> bool:
    result = await session.execute(
        select(Cache.id)
        .where(
            Cache.namespace == NAMESPACE,
            Cache.expires_at > time.time(),
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def _fetch_and_store(session: AsyncSession):
    logger.info("SKCC fetching member list from %s", SKCC_URL)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.get(SKCC_URL)
            res.raise_for_status()
            lines = res.text.splitlines()
    except Exception:
        logger.warning("SKCC fetch failed")
        return

    await session.execute(delete(Cache).where(Cache.namespace == NAMESPACE))

    expires = time.time() + CACHE_TTL
    count = 0
    for line in lines[1:]:
        parts = line.split("|")
        if len(parts) >= 2:
            skcc_nr = parts[0].strip()
            callsign = parts[1].strip().upper()
            base_call = callsign.split("/")[0]
            if base_call and skcc_nr:
                session.add(
                    Cache(
                        namespace=NAMESPACE,
                        key=base_call,
                        value=skcc_nr,
                        expires_at=expires,
                    )
                )
                count += 1

    await session.commit()
    logger.info("SKCC cached %d entries", count)


async def _ensure_cache(session: AsyncSession):
    """Populate cache if expired, serializing concurrent callers."""
    if await _has_valid_cache(session):
        return
    async with _fetch_lock:
        # Re-check after acquiring lock — another caller may have filled it
        if not await _has_valid_cache(session):
            await _fetch_and_store(session)


async def _lookup_db(call: str, session: AsyncSession) -> str | None:
    result = await session.execute(
        select(Cache.value).where(
            Cache.namespace == NAMESPACE,
            Cache.key == call,
            Cache.expires_at > time.time(),
        )
    )
    row = result.scalar_one_or_none()
    return row


@router.get("/lookup/{callsign}")
async def skcc_lookup(callsign: str, session: AsyncSession = Depends(get_session)):
    await _ensure_cache(session)

    call_upper = callsign.upper().strip()
    skcc_nr = await _lookup_db(call_upper, session)
    if not skcc_nr:
        base = call_upper.split("/")[0]
        if base != call_upper:
            skcc_nr = await _lookup_db(base, session)

    return {"call": call_upper, "skcc": skcc_nr}


@router.get("/search")
async def skcc_search(q: str = "", session: AsyncSession = Depends(get_session)):
    if len(q) < 2:
        return []
    await _ensure_cache(session)

    pattern = f"%{q}%"
    result = await session.execute(
        select(Cache.key, Cache.value)
        .where(
            Cache.namespace == NAMESPACE,
            Cache.expires_at > time.time(),
            (Cache.value.ilike(pattern) | Cache.key.ilike(pattern)),
        )
        .limit(5)
    )
    return [{"call": row.key, "skcc": row.value} for row in result.all()]


@router.delete("/cache")
async def clear_skcc_cache(session: AsyncSession = Depends(get_session)):
    await session.execute(delete(Cache).where(Cache.namespace == NAMESPACE))
    await session.commit()
    return {"ok": True}
