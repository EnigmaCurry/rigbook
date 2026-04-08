from __future__ import annotations

from collections import defaultdict
from typing import Optional

import pycountry
from fastapi import APIRouter, Depends, Query
from sqlalchemy import Float, and_, cast, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from rigbook.db import Contact, get_session
from rigbook.dxcc import DXCC_ENTITIES

router = APIRouter(prefix="/api", tags=["achievements"])

BAND_FREQ_MAP = {
    "160m": (1800, 2000),
    "80m": (3500, 4000),
    "60m": (5330, 5410),
    "40m": (7000, 7300),
    "30m": (10100, 10150),
    "20m": (14000, 14350),
    "17m": (18068, 18168),
    "15m": (21000, 21450),
    "12m": (24890, 24990),
    "10m": (28000, 29700),
    "6m": (50000, 54000),
    "2m": (144000, 148000),
}

_BAND_ORDER = list(BAND_FREQ_MAP)


def _freq_to_band(freq_str: str | None) -> str:
    if not freq_str:
        return ""
    try:
        f = float(freq_str)
    except (ValueError, TypeError):
        return ""
    for band, (lo, hi) in BAND_FREQ_MAP.items():
        if lo <= f <= hi:
            return band
    return ""


def _band_sort_key(b: str) -> int:
    try:
        return _BAND_ORDER.index(b)
    except ValueError:
        return 99


def _band_filter(band: str | None) -> list:
    """Build SQLAlchemy filter conditions for comma-separated band string."""
    if not band:
        return []
    conditions = []
    for b in band.split(","):
        freq_range = BAND_FREQ_MAP.get(b.strip().lower())
        if freq_range:
            lo, hi = freq_range
            conditions.append(
                and_(
                    cast(Contact.freq, Float) >= lo,
                    cast(Contact.freq, Float) <= hi,
                )
            )
    if conditions:
        return [or_(*conditions)]
    return []


@router.get("/achievements")
async def get_achievements(
    band: Optional[str] = Query(None),
    mode: Optional[str] = Query(None),
    pota: Optional[bool] = Query(None),
    skcc: Optional[bool] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    filters: list = []
    if mode:
        filters.append(Contact.mode == mode)
    filters.extend(_band_filter(band))
    if pota:
        filters.append(Contact.pota_park.isnot(None))
        filters.append(Contact.pota_park != "")
    if skcc:
        filters.append(Contact.skcc_exch.isnot(None))
        filters.append(Contact.skcc_exch != 0)

    # Fetch all contacts with relevant fields in one query
    rows = (
        await session.execute(
            select(
                Contact.state,
                Contact.dxcc,
                Contact.grid,
                Contact.freq,
                Contact.mode,
            ).where(*filters)
        )
    ).all()

    # Also fetch all modes/bands from entire logbook (unfiltered) for filter options
    all_rows = (
        await session.execute(select(Contact.freq, Contact.mode))
    ).all()

    all_modes: set[str] = set()
    all_bands: set[str] = set()
    for freq, md in all_rows:
        if md:
            all_modes.add(md)
        b = _freq_to_band(freq)
        if b:
            all_bands.add(b)

    states: set[str] = set()
    dxcc_codes: set[int] = set()
    grids: set[str] = set()
    # Counts: entity -> band/mode -> count
    state_band: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    state_mode: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    dxcc_band: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    dxcc_mode: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for st, dx, gr, freq, md in rows:
        b = _freq_to_band(freq)
        if st and st.strip():
            s = st.strip()
            states.add(s)
            if b:
                state_band[s][b] += 1
            if md:
                state_mode[s][md] += 1
        if dx is not None:
            dxcc_codes.add(dx)
            if b:
                dxcc_band[dx][b] += 1
            if md:
                dxcc_mode[dx][md] += 1
        if gr and len(gr) >= 4:
            grids.add(gr[:4].upper())

    return {
        "states": sorted(states),
        "dxcc": sorted(dxcc_codes),
        "grids": sorted(grids),
        "modes": sorted(all_modes),
        "bands_used": sorted(all_bands, key=_band_sort_key),
        "matrix": {
            "state_band": dict(state_band),
            "state_mode": dict(state_mode),
            "dxcc_band": {str(k): dict(v) for k, v in dxcc_band.items()},
            "dxcc_mode": {str(k): dict(v) for k, v in dxcc_mode.items()},
        },
    }


@router.get("/achievements/qsos")
async def get_achievement_qsos(
    state: Optional[str] = Query(None),
    dxcc: Optional[int] = Query(None),
    grid: Optional[str] = Query(None),
    band: Optional[str] = Query(None),
    mode: Optional[str] = Query(None),
    pota: Optional[bool] = Query(None),
    skcc: Optional[bool] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    filters: list = []
    if state:
        filters.append(Contact.state == state)
    if dxcc is not None:
        filters.append(Contact.dxcc == dxcc)
    if grid:
        filters.append(Contact.grid.ilike(f"{grid}%"))
    if mode:
        filters.append(Contact.mode == mode)
    filters.extend(_band_filter(band))
    if pota:
        filters.append(Contact.pota_park.isnot(None))
        filters.append(Contact.pota_park != "")
    if skcc:
        filters.append(Contact.skcc_exch.isnot(None))
        filters.append(Contact.skcc_exch != 0)

    rows = (
        await session.execute(
            select(Contact).where(*filters).order_by(Contact.timestamp.desc())
        )
    ).scalars().all()

    return [
        {
            "id": r.id,
            "call": r.call,
            "freq": r.freq,
            "mode": r.mode,
            "state": r.state,
            "country": r.country,
            "grid": r.grid,
            "pota_park": r.pota_park,
            "name": r.name,
            "rst_sent": r.rst_sent,
            "rst_recv": r.rst_recv,
            "timestamp": r.timestamp.strftime("%Y-%m-%d %H:%M"),
        }
        for r in rows
    ]


@router.get("/achievements/reference")
async def get_reference():
    subs = pycountry.subdivisions.get(country_code="US")
    us_states = [
        {"code": s.code, "short": s.code.split("-", 1)[-1], "name": s.name}
        for s in sorted(subs, key=lambda s: s.name)
        if s.type == "State"
    ]
    return {
        "us_states": us_states,
        "dxcc_entities": {str(k): v for k, v in DXCC_ENTITIES.items() if k != 0},
    }
