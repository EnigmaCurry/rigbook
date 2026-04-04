import json
import logging
import time

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from rigbook.db import (
    Contact,
    GlobalPotaLocation,
    GlobalPotaPark,
    GlobalPotaProgram,
    GlobalSetting,
    get_global_session,
    get_session,
    global_async_session,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pota", tags=["pota"])

POTA_SPOTS_URL = "https://api.pota.app/v1/spots"
POTA_PROGRAMS_URL = "https://api.pota.app/programs"
POTA_LOCATIONS_URL = "https://api.pota.app/locations"
POTA_LOCATION_PARKS_URL = "https://api.pota.app/location/parks"

TTL = 86400  # 24 hours
SPOTS_TTL = 30  # seconds
SELECTED_KEY = "pota_selected_programs"

_spots_cache: list | None = None
_spots_fetched_at: float = 0

PROGRAM_NAME_OVERRIDES: dict[int, str] = {
    30: "Taiwan",
    160: "Vietnam",
    175: "Korea",
}

# Built at import time from the ID map; populated after first fetch
_program_name_cache: dict[str, str] = {}


def _build_name_cache(programs):
    """Build a prefix->override lookup from program objects."""
    _program_name_cache.clear()
    for p in programs:
        pid = p.program_id if hasattr(p, "program_id") else p.get("program_id", 0)
        prefix = p.prefix if hasattr(p, "prefix") else p.get("prefix", "")
        if pid in PROGRAM_NAME_OVERRIDES:
            _program_name_cache[prefix] = PROGRAM_NAME_OVERRIDES[pid]


def _fix_program_name(name: str, prefix: str = "") -> str:
    if prefix and prefix in _program_name_cache:
        return _program_name_cache[prefix]
    return name


_spots_lock = None


def _get_spots_lock():
    global _spots_lock
    import asyncio

    if _spots_lock is None:
        _spots_lock = asyncio.Lock()
    return _spots_lock


@router.get("/spots")
async def get_spots():
    global _spots_cache, _spots_fetched_at
    now = time.time()
    if _spots_cache is not None and now - _spots_fetched_at < SPOTS_TTL:
        return _spots_cache
    async with _get_spots_lock():
        # Re-check after acquiring lock
        now = time.time()
        if _spots_cache is not None and now - _spots_fetched_at < SPOTS_TTL:
            return _spots_cache
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                res = await client.get(
                    POTA_SPOTS_URL,
                    headers={"Accept": "application/json"},
                )
                res.raise_for_status()
                _spots_cache = res.json()
                _spots_fetched_at = time.time()
                return _spots_cache
        except (httpx.HTTPError, OSError) as e:
            logger.warning("POTA spots fetch failed: %s", e)
            if _spots_cache is not None:
                return _spots_cache
            return []


async def _fetch_and_cache_programs(session: AsyncSession):
    now = time.time()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            prog_res = await client.get(
                POTA_PROGRAMS_URL, headers={"Accept": "application/json"}
            )
            prog_res.raise_for_status()

            loc_res = await client.get(
                POTA_LOCATIONS_URL, headers={"Accept": "application/json"}
            )
            loc_res.raise_for_status()
    except (httpx.HTTPError, OSError) as e:
        logger.warning("POTA programs/locations fetch failed: %s", e)
        return

    await session.execute(delete(GlobalPotaProgram))
    await session.execute(delete(GlobalPotaLocation))

    for p in prog_res.json():
        session.add(
            GlobalPotaProgram(
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
            GlobalPotaLocation(
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
async def get_programs(
    gdb: AsyncSession = Depends(get_global_session),
):
    row = (await gdb.execute(select(func.min(GlobalPotaProgram.fetched_at)))).scalar()

    if row is None or time.time() - row > TTL:
        await _fetch_and_cache_programs(gdb)

    programs = (await gdb.execute(select(GlobalPotaProgram))).scalars().all()
    _build_name_cache(programs)

    # Park counts per program prefix
    park_counts = dict(
        (
            await gdb.execute(
                select(GlobalPotaPark.location_desc, func.count()).group_by(
                    GlobalPotaPark.location_desc
                )
            )
        ).all()
    )

    # Map location descriptors to program prefixes
    loc_rows = (await gdb.execute(select(GlobalPotaLocation))).scalars().all()
    prefix_park_count: dict[str, int] = {}
    prefix_loc_count: dict[str, int] = {}
    for loc in loc_rows:
        prefix_park_count[loc.program_prefix] = prefix_park_count.get(
            loc.program_prefix, 0
        ) + park_counts.get(loc.descriptor, 0)
        prefix_loc_count[loc.program_prefix] = (
            prefix_loc_count.get(loc.program_prefix, 0) + 1
        )

    # Get selected programs (global setting)
    selected = await _get_selected(gdb)

    return [
        {
            "prefix": p.prefix,
            "name": _fix_program_name(p.name, p.prefix),
            "location_count": prefix_loc_count.get(p.prefix, 0),
            "park_count": prefix_park_count.get(p.prefix, 0),
            "selected": p.prefix in selected,
        }
        for p in programs
    ]


async def _get_selected(gdb: AsyncSession) -> set[str]:
    row = (
        await gdb.execute(
            select(GlobalSetting.value).where(GlobalSetting.key == SELECTED_KEY)
        )
    ).scalar()
    if row:
        return set(json.loads(row))
    return set()


@router.get("/programs/{prefix}/locations")
async def get_locations(prefix: str, gdb: AsyncSession = Depends(get_global_session)):
    locations = (
        (
            await gdb.execute(
                select(GlobalPotaLocation).where(
                    GlobalPotaLocation.program_prefix == prefix
                )
            )
        )
        .scalars()
        .all()
    )

    descriptors = [loc.descriptor for loc in locations]
    park_counts = {}
    if descriptors:
        rows = (
            await gdb.execute(
                select(GlobalPotaPark.location_desc, func.count())
                .where(GlobalPotaPark.location_desc.in_(descriptors))
                .group_by(GlobalPotaPark.location_desc)
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
    body: dict, gdb: AsyncSession = Depends(get_global_session)
):
    prefixes = body.get("prefixes", [])
    existing = (
        await gdb.execute(
            select(GlobalSetting).where(GlobalSetting.key == SELECTED_KEY)
        )
    ).scalar_one_or_none()
    if existing:
        existing.value = json.dumps(prefixes)
    else:
        gdb.add(GlobalSetting(key=SELECTED_KEY, value=json.dumps(prefixes)))
    await gdb.commit()
    return {"status": "ok"}


@router.post("/fetch-parks")
async def fetch_parks_for_selected(
    gdb: AsyncSession = Depends(get_global_session),
):
    """Stream progress as SSE while fetching parks for all selected programs."""
    selected = await _get_selected(gdb)
    if not selected:
        return {"status": "none_selected"}

    # Get locations for selected programs
    locations = (
        (
            await gdb.execute(
                select(GlobalPotaLocation).where(
                    GlobalPotaLocation.program_prefix.in_(selected)
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

                try:
                    session_ctx = global_async_session()
                except RuntimeError:
                    continue
                async with session_ctx as s:
                    await s.execute(
                        delete(GlobalPotaPark).where(
                            GlobalPotaPark.location_desc == loc.descriptor
                        )
                    )
                    t = time.time()
                    for p in parks_data:
                        s.add(
                            GlobalPotaPark(
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
                        text(
                            "UPDATE pota_locations SET parks_fetched_at = :t WHERE descriptor = :d"
                        ),
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


@router.get("/parks/search")
async def search_parks(q: str = "", gdb: AsyncSession = Depends(get_global_session)):
    if len(q) < 2:
        return []
    # Insert hyphen if query looks like a reference missing one (e.g. "US1024" -> "US-1024")
    import re

    pattern = f"%{q}%"
    m = re.match(r"^([A-Za-z]{1,2})(\d.*)$", q)
    ref_pattern = f"%{m.group(1)}-{m.group(2)}%" if m else pattern
    # Subquery to count locations per reference
    loc_count_sub = (
        select(
            GlobalPotaPark.reference.label("ref"),
            func.count().label("loc_count"),
        )
        .group_by(GlobalPotaPark.reference)
        .subquery()
    )
    rows = (
        await gdb.execute(
            select(
                GlobalPotaPark,
                GlobalPotaLocation.name.label("location_name"),
                GlobalPotaProgram.name.label("program_name"),
                loc_count_sub.c.loc_count,
            )
            .outerjoin(
                GlobalPotaLocation,
                GlobalPotaPark.location_desc == GlobalPotaLocation.descriptor,
            )
            .outerjoin(
                GlobalPotaProgram,
                GlobalPotaLocation.program_prefix == GlobalPotaProgram.prefix,
            )
            .outerjoin(
                loc_count_sub,
                GlobalPotaPark.reference == loc_count_sub.c.ref,
            )
            .where(
                GlobalPotaPark.reference.ilike(ref_pattern)
                | GlobalPotaPark.name.ilike(pattern)
                | GlobalPotaPark.location_desc.ilike(pattern)
                | GlobalPotaPark.grid.ilike(pattern)
            )
            .group_by(GlobalPotaPark.reference)
            .limit(20)
        )
    ).all()
    return [
        {
            "reference": p.reference,
            "name": p.name,
            "location_desc": p.location_desc,
            "grid": p.grid,
            "location_name": loc_name if loc_count == 1 else "",
            "program_name": _fix_program_name(
                prog_name, p.reference.split("-")[0] if p.reference else ""
            ),
            "location_count": loc_count or 1,
        }
        for p, loc_name, prog_name, loc_count in rows
    ]


@router.get("/my-parks")
async def get_my_parks(
    session: AsyncSession = Depends(get_session),
    gdb: AsyncSession = Depends(get_global_session),
):
    """Return parks where the user has logged at least one QSO, ordered by most recent."""
    rows = (
        await session.execute(
            select(
                Contact.pota_park,
                func.count().label("qso_count"),
                func.max(Contact.timestamp).label("last_contact"),
            )
            .where(Contact.pota_park.isnot(None), Contact.pota_park != "")
            .group_by(Contact.pota_park)
            .order_by(func.max(Contact.timestamp).desc())
        )
    ).all()

    results = []
    for pota_park, qso_count, last_contact in rows:
        park = (
            (
                await gdb.execute(
                    select(GlobalPotaPark).where(GlobalPotaPark.reference == pota_park)
                )
            )
            .scalars()
            .first()
        )
        results.append(
            {
                "reference": pota_park,
                "name": park.name if park else None,
                "latitude": park.latitude if park else None,
                "longitude": park.longitude if park else None,
                "grid": park.grid if park else None,
                "location_desc": park.location_desc if park else None,
                "qso_count": qso_count,
                "last_contact": last_contact.isoformat() if last_contact else None,
            }
        )
    return results


@router.get("/park/{reference}")
async def get_park(
    reference: str,
    session: AsyncSession = Depends(get_session),
    gdb: AsyncSession = Depends(get_global_session),
):
    ref = reference.upper()
    park = (
        await gdb.execute(
            select(
                GlobalPotaPark,
                GlobalPotaLocation.name.label("location_name"),
                GlobalPotaProgram.name.label("program_name"),
            )
            .outerjoin(
                GlobalPotaLocation,
                GlobalPotaPark.location_desc == GlobalPotaLocation.descriptor,
            )
            .outerjoin(
                GlobalPotaProgram,
                GlobalPotaLocation.program_prefix == GlobalPotaProgram.prefix,
            )
            .where(GlobalPotaPark.reference == ref)
        )
    ).first()
    if not park:
        return {"error": "Park not found"}
    p, loc_name, prog_name = park

    # All locations for this park (multi-state parks have multiple rows)
    all_locs = (
        await gdb.execute(
            select(GlobalPotaPark.location_desc, GlobalPotaLocation.name)
            .outerjoin(
                GlobalPotaLocation,
                GlobalPotaPark.location_desc == GlobalPotaLocation.descriptor,
            )
            .where(GlobalPotaPark.reference == ref)
        )
    ).all()
    locations = [{"descriptor": d, "name": n or ""} for d, n in all_locs]

    my_qsos_rows = (
        (
            await session.execute(
                select(Contact)
                .where(Contact.pota_park == ref)
                .order_by(Contact.timestamp.desc())
            )
        )
        .scalars()
        .all()
    )

    contacts = [
        {
            "id": c.id,
            "call": c.call,
            "name": c.name,
            "freq": c.freq,
            "mode": c.mode,
            "rst_sent": c.rst_sent,
            "rst_recv": c.rst_recv,
            "timestamp": c.timestamp.isoformat() if c.timestamp else None,
        }
        for c in my_qsos_rows
    ]

    return {
        "reference": p.reference,
        "name": p.name,
        "location_desc": p.location_desc,
        "latitude": p.latitude,
        "longitude": p.longitude,
        "grid": p.grid,
        "attempts": p.attempts,
        "activations": p.activations,
        "qsos": p.qsos,
        "my_qsos": len(contacts),
        "contacts": contacts,
        "location_name": loc_name,
        "program_name": _fix_program_name(
            prog_name, p.reference.split("-")[0] if p.reference else ""
        ),
        "locations": locations,
    }


@router.get("/locations/{descriptor}/parks")
async def get_parks(descriptor: str, gdb: AsyncSession = Depends(get_global_session)):
    parks = (
        (
            await gdb.execute(
                select(GlobalPotaPark).where(GlobalPotaPark.location_desc == descriptor)
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
