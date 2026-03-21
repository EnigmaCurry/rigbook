"""API routes for querying RBN and HamAlert spot data."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rigbook.db import Setting, get_session
from rigbook.spots import hamalert_feed, rbn_feed, refresh_feeds, spot_cache

router = APIRouter(prefix="/api/spots", tags=["spots"])


@router.get("/")
async def query_spots(
    source: str | None = None,
    callsign: str | None = None,
    mode: str | None = None,
    band: str | None = None,
    min_freq: float | None = None,
    max_freq: float | None = None,
    limit: int = 200,
):
    return await spot_cache.query(
        source=source,
        callsign=callsign,
        mode=mode,
        band=band,
        min_freq=min_freq,
        max_freq=max_freq,
        limit=limit,
    )


@router.get("/status")
async def feed_status(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Setting).where(Setting.key.in_(["rbn_enabled", "hamalert_enabled"]))
    )
    settings = {s.key: s.value for s in result.scalars().all()}
    rbn_enabled = settings.get("rbn_enabled", "false").lower() == "true"
    ha_enabled = settings.get("hamalert_enabled", "false").lower() == "true"

    return {
        "rbn": {
            "connected": rbn_feed.connected,
            "enabled": rbn_enabled,
        },
        "hamalert": {
            "connected": hamalert_feed.connected,
            "enabled": ha_enabled,
        },
        "total_spots": await spot_cache.count(),
        "last_spot_time": await spot_cache.last_spot_time(),
    }


@router.get("/bands")
async def band_summary():
    return await spot_cache.band_summary()


@router.post("/restart")
async def restart_feeds():
    await refresh_feeds()
    return {"ok": True}
