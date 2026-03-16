import json
import logging
import time

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from rigbook.db import (
    PotaLocation,
    PotaPark,
    PotaProgram,
    Setting,
    async_session,
    get_session,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pota", tags=["pota"])

POTA_SPOTS_URL = "https://api.pota.app/v1/spots"
POTA_PROGRAMS_URL = "https://api.pota.app/programs"
POTA_LOCATIONS_URL = "https://api.pota.app/locations"
POTA_LOCATION_PARKS_URL = "https://api.pota.app/location/parks"

TTL = 86400  # 24 hours
SELECTED_KEY = "pota_selected_programs"


@router.get("/spots")
async def get_spots():
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.get(
            POTA_SPOTS_URL,
            headers={"Accept": "application/json"},
        )
        res.raise_for_status()
        return res.json()


async def _fetch_and_cache_programs(session: AsyncSession):
    now = time.time()
    async with httpx.AsyncClient(timeout=30) as client:
        prog_res = await client.get(
            POTA_PROGRAMS_URL, headers={"Accept": "application/json"}
        )
        prog_res.raise_for_status()

        loc_res = await client.get(
            POTA_LOCATIONS_URL, headers={"Accept": "application/json"}
        )
        loc_res.raise_for_status()

    await session.execute(delete(PotaProgram))
    await session.execute(delete(PotaLocation))

    for p in prog_res.json():
        session.add(
            PotaProgram(
                program_id=p.get("programId", 0),
                prefix=p.get("programPrefix", ""),
                name=p.get("programName", ""),
                fetched_at=now,
            )
        )

    for loc in loc_res.json():
        descriptor = loc.get("locationDesc", "")
        prefix = descriptor.split("-")[0] if "-" in descriptor else descriptor
        session.add(
            PotaLocation(
                location_id=loc.get("locationId", 0),
                program_prefix=prefix,
                descriptor=descriptor,
                name=loc.get("locationName", ""),
                latitude=loc.get("latitude"),
                longitude=loc.get("longitude"),
                fetched_at=now,
            )
        )

    await session.commit()


@router.get("/programs")
async def get_programs(session: AsyncSession = Depends(get_session)):
    row = (
        await session.execute(select(func.min(PotaProgram.fetched_at)))
    ).scalar()

    if row is None or time.time() - row > TTL:
        await _fetch_and_cache_programs(session)

    programs = (await session.execute(select(PotaProgram))).scalars().all()

    # Park counts per program prefix
    park_counts = dict(
        (
            await session.execute(
                select(PotaPark.location_desc, func.count()).group_by(
                    PotaPark.location_desc
                )
            )
        ).all()
    )

    # Map location descriptors to program prefixes
    loc_rows = (await session.execute(select(PotaLocation))).scalars().all()
    prefix_park_count: dict[str, int] = {}
    prefix_loc_count: dict[str, int] = {}
    for loc in loc_rows:
        prefix_park_count[loc.program_prefix] = prefix_park_count.get(
            loc.program_prefix, 0
        ) + park_counts.get(loc.descriptor, 0)
        prefix_loc_count[loc.program_prefix] = (
            prefix_loc_count.get(loc.program_prefix, 0) + 1
        )

    # Get selected programs
    selected = await _get_selected(session)

    return [
        {
            "prefix": p.prefix,
            "name": p.name,
            "location_count": prefix_loc_count.get(p.prefix, 0),
            "park_count": prefix_park_count.get(p.prefix, 0),
            "selected": p.prefix in selected,
        }
        for p in programs
    ]


async def _get_selected(session: AsyncSession) -> set[str]:
    row = (
        await session.execute(
            select(Setting.value).where(Setting.key == SELECTED_KEY)
        )
    ).scalar()
    if row:
        return set(json.loads(row))
    return set()


@router.get("/programs/{prefix}/locations")
async def get_locations(
    prefix: str, session: AsyncSession = Depends(get_session)
):
    locations = (
        (
            await session.execute(
                select(PotaLocation).where(PotaLocation.program_prefix == prefix)
            )
        )
        .scalars()
        .all()
    )

    descriptors = [loc.descriptor for loc in locations]
    park_counts = {}
    if descriptors:
        rows = (
            await session.execute(
                select(PotaPark.location_desc, func.count())
                .where(PotaPark.location_desc.in_(descriptors))
                .group_by(PotaPark.location_desc)
            )
        ).all()
        park_counts = dict(rows)

    return [
        {
            "descriptor": loc.descriptor,
            "name": loc.name,
            "park_count": park_counts.get(loc.descriptor, 0),
        }
        for loc in locations
    ]


@router.put("/selected-programs")
async def set_selected_programs(
    body: dict, session: AsyncSession = Depends(get_session)
):
    prefixes = body.get("prefixes", [])
    existing = (
        await session.execute(
            select(Setting).where(Setting.key == SELECTED_KEY)
        )
    ).scalar_one_or_none()
    if existing:
        existing.value = json.dumps(prefixes)
    else:
        session.add(Setting(key=SELECTED_KEY, value=json.dumps(prefixes)))
    await session.commit()
    return {"status": "ok"}


@router.post("/fetch-parks")
async def fetch_parks_for_selected(session: AsyncSession = Depends(get_session)):
    """Stream progress as SSE while fetching parks for all selected programs."""
    selected = await _get_selected(session)
    if not selected:
        return {"status": "none_selected"}

    # Get locations for selected programs
    locations = (
        (
            await session.execute(
                select(PotaLocation).where(
                    PotaLocation.program_prefix.in_(selected)
                )
            )
        )
        .scalars()
        .all()
    )

    # Filter to locations that need fetching (stale or missing)
    now = time.time()
    stale = []
    for loc in locations:
        if loc.parks_fetched_at is None or now - loc.parks_fetched_at > TTL:
            stale.append(loc)

    total = len(stale)
    if total == 0:
        return {"status": "up_to_date", "locations": len(locations)}

    async def stream():
        yield f"data: {json.dumps({'type': 'start', 'total': total})}\n\n"
        done = 0
        for loc in stale:
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    res = await client.get(
                        f"{POTA_LOCATION_PARKS_URL}/{loc.descriptor}",
                        headers={"Accept": "application/json"},
                    )
                    res.raise_for_status()
                    parks_data = res.json()

                async with async_session() as s:
                    await s.execute(
                        delete(PotaPark).where(
                            PotaPark.location_desc == loc.descriptor
                        )
                    )
                    t = time.time()
                    for p in parks_data:
                        s.add(
                            PotaPark(
                                reference=p.get("reference", ""),
                                name=p.get("name", ""),
                                location_desc=loc.descriptor,
                                latitude=p.get("latitude"),
                                longitude=p.get("longitude"),
                                grid=p.get("grid"),
                                attempts=p.get("attempts"),
                                activations=p.get("activations"),
                                qsos=p.get("qsos"),
                                fetched_at=t,
                            )
                        )
                    # Mark location as fetched
                    await s.execute(
                        text("UPDATE pota_locations SET parks_fetched_at = :t WHERE descriptor = :d"),
                        {"t": t, "d": loc.descriptor},
                    )
                    await s.commit()
                done += 1
                yield f"data: {json.dumps({'type': 'progress', 'done': done, 'total': total, 'location': loc.descriptor, 'parks': len(parks_data)})}\n\n"
            except Exception as exc:
                done += 1
                logger.warning("Failed to fetch parks for %s: %s", loc.descriptor, exc)
                yield f"data: {json.dumps({'type': 'error', 'location': loc.descriptor, 'error': str(exc), 'done': done, 'total': total})}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'total': total})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.get("/locations/{descriptor}/parks")
async def get_parks(
    descriptor: str, session: AsyncSession = Depends(get_session)
):
    parks = (
        (
            await session.execute(
                select(PotaPark).where(PotaPark.location_desc == descriptor)
            )
        )
        .scalars()
        .all()
    )

    return [
        {
            "reference": p.reference,
            "name": p.name,
            "latitude": p.latitude,
            "longitude": p.longitude,
            "grid": p.grid,
            "attempts": p.attempts,
            "activations": p.activations,
            "qsos": p.qsos,
        }
        for p in parks
    ]
