"""API routes for querying RBN and HamAlert spot data."""

import time

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rigbook.db import Cache, Setting, get_session
from rigbook.spots import (
    hamalert_feed,
    rbn_feed,
    refresh_feeds,
    spot_cache,
    spotter_grids,
)

router = APIRouter(prefix="/api/spots", tags=["spots"])


async def _batch_skcc_lookup(
    callsigns: list[str], session: AsyncSession
) -> dict[str, str]:
    """Look up SKCC numbers for a batch of callsigns. Returns {call: skcc_nr}."""
    if not callsigns:
        return {}
    result = await session.execute(
        select(Cache.key, Cache.value).where(
            Cache.namespace == "skcc",
            Cache.key.in_(callsigns),
            Cache.expires_at > time.time(),
        )
    )
    return dict(result.all())


@router.get("/")
async def query_spots(
    source: str | None = None,
    callsign: str | None = None,
    mode: str | None = None,
    band: str | None = None,
    min_freq: float | None = None,
    max_freq: float | None = None,
    skcc: str | None = None,
    limit: int = 200,
    session: AsyncSession = Depends(get_session),
):
    spots = await spot_cache.query(
        source=source,
        callsign=callsign,
        mode=mode,
        band=band,
        min_freq=min_freq,
        max_freq=max_freq,
        limit=limit,
    )

    # Enrich with SKCC numbers for CW spots
    cw_calls = list({s["callsign"].upper() for s in spots if s["mode"] == "CW"})
    skcc_map = await _batch_skcc_lookup(cw_calls, session) if cw_calls else {}

    for s in spots:
        s["skcc"] = skcc_map.get(s["callsign"].upper())

    # Filter by SKCC if requested
    if skcc == "required":
        spots = [s for s in spots if s.get("skcc")]

    # Enrich with closest spotter distance
    result = await session.execute(
        select(Setting.value).where(Setting.key == "my_grid")
    )
    my_grid = (result.scalar_one_or_none() or "").strip()
    if my_grid:
        await spotter_grids.ensure_loaded()
        # Collect all spotters and refetch if any are unknown
        all_spotters = []
        for s in spots:
            all_spotters.extend(s.get("spotters", []))
        if all_spotters:
            await spotter_grids.ensure_spotters(all_spotters)
        for s in spots:
            dist, snr = spotter_grids.closest_spotter(
                my_grid, s.pop("spotter_snrs", {})
            )
            s["distance_mi"] = dist
            s["closest_snr"] = snr
    else:
        for s in spots:
            s.pop("spotter_snrs", None)
            s["distance_mi"] = None
            s["closest_snr"] = None

    return spots


@router.get("/status")
async def feed_status(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Setting).where(Setting.key.in_(["rbn_enabled", "hamalert_enabled"]))
    )
    settings = {s.key: s.value for s in result.scalars().all()}
    rbn_enabled = settings.get("rbn_enabled", "false").lower() == "true"
    ha_enabled = settings.get("hamalert_enabled", "false").lower() == "true"

    cache_stats = await spot_cache.stats()

    return {
        "rbn": {
            "connected": rbn_feed.connected,
            "enabled": rbn_enabled,
        },
        "hamalert": {
            "connected": hamalert_feed.connected,
            "enabled": ha_enabled,
        },
        **cache_stats,
    }


@router.get("/modes")
async def list_modes():
    return await spot_cache.modes()


@router.get("/bands")
async def band_summary():
    return await spot_cache.band_summary()


@router.post("/restart")
async def restart_feeds():
    await refresh_feeds()
    return {"ok": True}
