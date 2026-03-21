"""API routes for querying RBN and HamAlert spot data."""

import json
import time

import pycountry
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rigbook.db import Cache, Setting, get_session
from rigbook.routes.qrz import qrz_lookup
from rigbook.routes.skcc import _ensure_cache as ensure_skcc_cache
from rigbook.spots import (
    hamalert_feed,
    rbn_feed,
    refresh_feeds,
    spot_cache,
    spotter_grids,
)

# Build country name -> ISO code lookup (cached at import time)
_COUNTRY_NAME_TO_CODE: dict[str, str] = {}
for _c in pycountry.countries:
    _COUNTRY_NAME_TO_CODE[_c.name.lower()] = _c.alpha_2
    if hasattr(_c, "common_name"):
        _COUNTRY_NAME_TO_CODE[_c.common_name.lower()] = _c.alpha_2
    if hasattr(_c, "official_name"):
        _COUNTRY_NAME_TO_CODE[_c.official_name.lower()] = _c.alpha_2
# Common aliases QRZ uses
_COUNTRY_NAME_TO_CODE.update(
    {
        "usa": "US",
        "united states": "US",
        "russia": "RU",
        "south korea": "KR",
        "north korea": "KP",
        "taiwan": "TW",
        "england": "GB",
        "scotland": "GB",
        "wales": "GB",
    }
)

router = APIRouter(prefix="/api/spots", tags=["spots"])


async def _batch_cache_lookup(
    namespace: str, callsigns: list[str], session: AsyncSession
) -> dict[str, str]:
    """Look up cached values for a batch of callsigns. Returns {call: value}."""
    if not callsigns:
        return {}
    result = await session.execute(
        select(Cache.key, Cache.value).where(
            Cache.namespace == namespace,
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
    max_distance: int | None = None,
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

    all_calls = list({s["callsign"].upper() for s in spots})

    # Enrich with SKCC numbers for CW spots
    cw_calls = [
        c
        for c in all_calls
        if any(s["callsign"].upper() == c and s["mode"] == "CW" for s in spots)
    ]
    if cw_calls:
        await ensure_skcc_cache(session)
    skcc_map = await _batch_cache_lookup("skcc", cw_calls, session) if cw_calls else {}

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

    # Filter by max distance if requested
    if max_distance is not None:
        spots = [
            s
            for s in spots
            if s.get("distance_mi") is not None and s["distance_mi"] <= max_distance
        ]

    # Enrich with country/state from QRZ cache (after all filters to minimize lookups)
    filtered_calls = list({s["callsign"].upper() for s in spots})
    qrz_map = await _batch_cache_lookup("qrz", filtered_calls, session)
    for s in spots:
        qrz_json = qrz_map.get(s["callsign"].upper())
        if qrz_json:
            try:
                qrz_data = json.loads(qrz_json)
                country_name = qrz_data.get("country") or ""
                s["country"] = country_name
                s["country_code"] = _COUNTRY_NAME_TO_CODE.get(country_name.lower(), "")
                s["qrz_state"] = qrz_data.get("state") or ""
            except (json.JSONDecodeError, TypeError):
                s["country"] = ""
                s["country_code"] = ""
                s["qrz_state"] = ""
        else:
            s["country"] = ""
            s["country_code"] = ""
            s["qrz_state"] = ""

    return spots


@router.get("/skcc")
async def skcc_skimmer(
    band: str | None = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
):
    """Pre-filtered SKCC skimmer view: CW + SKCC members + distance limit from settings."""
    # Read distance setting
    result = await session.execute(
        select(Setting.value).where(Setting.key == "skcc_skimmer_distance")
    )
    dist_str = result.scalar_one_or_none()
    max_dist = int(dist_str) if dist_str and dist_str.isdigit() else 500

    spots = await query_spots(
        source=None,
        callsign=None,
        mode="CW",
        band=band,
        min_freq=None,
        max_freq=None,
        skcc="required",
        max_distance=max_dist if max_dist > 0 else None,
        limit=limit,
        session=session,
    )

    # Prefetch QRZ data for spots missing location (small set, safe to fetch live)
    missing = [s for s in spots if not s.get("country")]
    for s in missing:
        data = await qrz_lookup(s["callsign"], session)
        if isinstance(data, dict) and not data.get("error"):
            country_name = data.get("country") or ""
            s["country"] = country_name
            s["country_code"] = _COUNTRY_NAME_TO_CODE.get(country_name.lower(), "")
            s["qrz_state"] = data.get("state") or ""

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
