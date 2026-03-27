"""API routes for querying RBN and HamAlert spot data."""

import json
import logging
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
    bands = {b.strip().lower() for b in band.split(",") if b.strip()} if band else None
    spots = await spot_cache.query(
        source=source,
        callsign=callsign,
        mode=mode,
        bands=bands,
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
            call, dist, snr = spotter_grids.closest_spotter(
                my_grid, s.pop("spotter_snrs", {})
            )
            s["closest_call"] = call
            s["distance_mi"] = dist
            s["closest_snr"] = snr
            s["closest_grid"] = spotter_grids.get(call) if call else None
            # Include grids for all spotters so the frontend can draw them
            sg = {}
            for sp in s.get("spotters", []):
                g = spotter_grids.get(sp)
                if g:
                    sg[sp] = g
            s["spotter_grids"] = sg
    else:
        for s in spots:
            s.pop("spotter_snrs", None)
            s["closest_call"] = None
            s["distance_mi"] = None
            s["closest_snr"] = None
            s["closest_grid"] = None

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
                s["qrz_grid"] = qrz_data.get("grid") or ""
            except (json.JSONDecodeError, TypeError):
                s["country"] = ""
                s["country_code"] = ""
                s["qrz_state"] = ""
                s["qrz_grid"] = ""
        else:
            s["country"] = ""
            s["country_code"] = ""
            s["qrz_state"] = ""
            s["qrz_grid"] = ""

    return {"my_grid": my_grid, "spots": spots}


# Server-side SKCC skimmer snapshot cache
# Spots that qualify are kept for the full TTL even if distance fluctuates
_skcc_cache: dict[str, tuple[dict, float]] = {}  # callsign -> (spot_dict, first_seen)
_SKCC_TTL = 600  # 10 minutes


@router.get("/skcc")
async def skcc_skimmer(
    band: str | None = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
):
    """Pre-filtered SKCC skimmer view with stable TTL.

    Once a spot qualifies, it stays in the snapshot for the full 10-minute
    TTL regardless of distance fluctuations between polls.
    """
    # Read distance setting
    result = await session.execute(
        select(Setting.value).where(Setting.key == "skcc_skimmer_distance")
    )
    dist_str = result.scalar_one_or_none()
    max_dist = int(dist_str) if dist_str and dist_str.isdigit() else 500

    # Get current qualifying spots from the live cache
    fresh = (
        await query_spots(
            source=None,
            callsign=None,
            mode="CW",
            band=None,  # don't filter by band here — filter the snapshot below
            min_freq=None,
            max_freq=None,
            skcc="required",
            max_distance=max_dist if max_dist > 0 else None,
            limit=200,
            session=session,
        )
    )["spots"]

    now = time.time()
    logger = logging.getLogger("rigbook.spots")
    logger.debug(
        "SKCC skimmer: %d fresh from query, %d in snapshot cache",
        len(fresh),
        len(_skcc_cache),
    )

    # Merge fresh spots into snapshot cache
    for s in fresh:
        call = s["callsign"]
        if call in _skcc_cache:
            # Spot already in snapshot — update data but keep first_seen
            # This refreshes distance/snr/spotter data while preserving TTL
            _skcc_cache[call] = (s, _skcc_cache[call][1])
        else:
            # New spot — add to snapshot
            _skcc_cache[call] = (s, now)

    # Expire entries past TTL (based on first_seen, not last update)
    expired = [
        k for k, (_, first_seen) in _skcc_cache.items() if now - first_seen > _SKCC_TTL
    ]
    if expired:
        logger.debug("SKCC skimmer: expiring %d entries: %s", len(expired), expired)
    for k in expired:
        del _skcc_cache[k]

    logger.debug("SKCC skimmer: returning %d from snapshot", len(_skcc_cache))

    # Build result from snapshot, applying band filter
    bands = {b.strip().lower() for b in band.split(",") if b.strip()} if band else None
    results = []
    for call, (s, _) in _skcc_cache.items():
        if bands and s.get("band") not in bands:
            continue
        results.append(s)

    results.sort(key=lambda s: s.get("received_at", 0), reverse=True)
    results = results[:limit]

    # Prefetch QRZ data for spots missing location
    for s in results:
        if not s.get("country"):
            data = await qrz_lookup(s["callsign"], session)
            if isinstance(data, dict) and not data.get("error"):
                country_name = data.get("country") or ""
                s["country"] = country_name
                s["country_code"] = _COUNTRY_NAME_TO_CODE.get(country_name.lower(), "")
                s["qrz_state"] = data.get("state") or ""

    return results


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
