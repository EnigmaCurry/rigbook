from __future__ import annotations

from collections import defaultdict
from typing import Optional

import pycountry
from fastapi import APIRouter, Depends, Query
from sqlalchemy import Float, and_, cast, select
from sqlalchemy.ext.asyncio import AsyncSession

from rigbook.db import Contact, get_session
from rigbook.dxcc import DXCC_ENTITIES

router = APIRouter(prefix="/api/achievements", tags=["achievements"])

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


@router.get("/")
async def get_achievements(
    band: Optional[str] = Query(None),
    mode: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    filters: list = []
    if mode:
        filters.append(Contact.mode == mode)
    if band:
        freq_range = BAND_FREQ_MAP.get(band.lower())
        if freq_range:
            lo, hi = freq_range
            filters.append(
                and_(
                    cast(Contact.freq, Float) >= lo,
                    cast(Contact.freq, Float) <= hi,
                )
            )

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

    states: set[str] = set()
    dxcc_codes: set[int] = set()
    grids: set[str] = set()
    all_modes: set[str] = set()
    all_bands: set[str] = set()
    state_band: dict[str, set[str]] = defaultdict(set)
    state_mode: dict[str, set[str]] = defaultdict(set)
    dxcc_band: dict[int, set[str]] = defaultdict(set)
    dxcc_mode: dict[int, set[str]] = defaultdict(set)

    for st, dx, gr, freq, md in rows:
        b = _freq_to_band(freq)
        if md:
            all_modes.add(md)
        if b:
            all_bands.add(b)
        if st and st.strip():
            s = st.strip()
            states.add(s)
            if b:
                state_band[s].add(b)
            if md:
                state_mode[s].add(md)
        if dx is not None:
            dxcc_codes.add(dx)
            if b:
                dxcc_band[dx].add(b)
            if md:
                dxcc_mode[dx].add(md)
        if gr and len(gr) >= 4:
            grids.add(gr[:4].upper())

    return {
        "states": sorted(states),
        "dxcc": sorted(dxcc_codes),
        "grids": sorted(grids),
        "modes": sorted(all_modes),
        "bands_used": sorted(all_bands, key=lambda b: list(BAND_FREQ_MAP).index(b) if b in BAND_FREQ_MAP else 99),
        "matrix": {
            "state_band": {k: sorted(v, key=lambda b: list(BAND_FREQ_MAP).index(b) if b in BAND_FREQ_MAP else 99) for k, v in state_band.items()},
            "state_mode": {k: sorted(v) for k, v in state_mode.items()},
            "dxcc_band": {str(k): sorted(v, key=lambda b: list(BAND_FREQ_MAP).index(b) if b in BAND_FREQ_MAP else 99) for k, v in dxcc_band.items()},
            "dxcc_mode": {str(k): sorted(v) for k, v in dxcc_mode.items()},
        },
    }


@router.get("/reference")
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
