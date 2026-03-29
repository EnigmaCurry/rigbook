from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Float, and_, cast, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from rigbook.db import Contact, get_session
from rigbook.routes.contacts import ContactResponse

router = APIRouter(prefix="/api/search", tags=["search"])

ALL_TEXT_COLUMNS = [
    Contact.call,
    Contact.name,
    Contact.qth,
    Contact.state,
    Contact.country,
    Contact.pota_park,
    Contact.grid,
    Contact.comments,
    Contact.notes,
    Contact.skcc,
    Contact.freq,
    Contact.mode,
    Contact.rst_sent,
    Contact.rst_recv,
]

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


@router.get("/", response_model=list[ContactResponse])
async def search_contacts(
    q: str = "",
    limit: int = Query(default=20, ge=0),
    session: AsyncSession = Depends(get_session),
):
    if len(q) < 2:
        return []
    pattern = f"%{q}%"
    stmt = (
        select(Contact)
        .where(or_(*[col.ilike(pattern) for col in ALL_TEXT_COLUMNS]))
        .order_by(Contact.timestamp.desc())
    )
    if limit > 0:
        stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/advanced", response_model=list[ContactResponse])
async def search_contacts_advanced(
    q: Optional[str] = None,
    call: Optional[str] = None,
    mode: Optional[str] = None,
    band: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    country: Optional[str] = None,
    state: Optional[str] = None,
    grid: Optional[str] = None,
    pota_park: Optional[str] = None,
    comments: Optional[str] = None,
    skcc: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Contact)
    filters = []

    if q and len(q) >= 2:
        pattern = f"%{q}%"
        filters.append(or_(*[col.ilike(pattern) for col in ALL_TEXT_COLUMNS]))

    if call:
        filters.append(Contact.call.ilike(f"%{call}%"))
    if mode:
        filters.append(Contact.mode.ilike(mode))
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
    if date_from:
        try:
            dt = datetime.strptime(date_from, "%Y-%m-%d")
            filters.append(Contact.timestamp >= dt)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
            filters.append(Contact.timestamp <= dt)
        except ValueError:
            pass
    if country:
        filters.append(Contact.country.ilike(f"%{country}%"))
    if state:
        filters.append(Contact.state.ilike(f"%{state}%"))
    if grid:
        filters.append(Contact.grid.ilike(f"{grid}%"))
    if pota_park:
        filters.append(Contact.pota_park.ilike(f"%{pota_park}%"))
    if comments:
        pattern = f"%{comments}%"
        filters.append(
            or_(
                Contact.comments.ilike(pattern),
                Contact.notes.ilike(pattern),
            )
        )
    if skcc:
        filters.append(Contact.skcc.ilike(f"%{skcc}%"))

    if filters:
        stmt = stmt.where(and_(*filters))

    stmt = stmt.order_by(Contact.timestamp.desc())
    result = await session.execute(stmt)
    return result.scalars().all()
