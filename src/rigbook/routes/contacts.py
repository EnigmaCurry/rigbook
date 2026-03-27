import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_serializer, field_validator, model_validator
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from rigbook.db import Contact, get_session

logger = logging.getLogger("rigbook")

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


class ContactCreate(BaseModel):
    call: str
    freq: str
    mode: str
    rst_sent: str | None = None
    rst_recv: str | None = None
    pota_park: str | None = None
    name: str | None = None
    qth: str | None = None
    state: str | None = None
    country: str | None = None
    dxcc: int | None = None
    grid: str | None = None
    skcc: str | None = None
    skcc_exch: bool = False
    comments: str | None = None
    notes: str | None = None
    timestamp: datetime | None = None

    @field_validator("call")
    @classmethod
    def validate_call(cls, v: str) -> str:
        v = v.strip()
        if not v or " " in v or len(v) > 10:
            raise ValueError(
                "callsign must be non-whitespace and at most 10 characters"
            )
        return v.upper()

    @field_validator("pota_park")
    @classmethod
    def validate_pota_park(cls, v: str | None) -> str | None:
        if not v:
            return None
        v = v.strip()
        if not all(c.isalnum() or c == "-" for c in v):
            raise ValueError("POTA park must be alphanumeric (hyphens allowed)")
        return v.upper()

    @field_validator("grid")
    @classmethod
    def validate_grid(cls, v: str | None) -> str | None:
        if not v:
            return None
        v = v.strip()
        if not v.isalnum():
            raise ValueError("grid must be alphanumeric with no spaces")
        return v.upper()

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        if v.tzinfo is not None:
            v = v.astimezone(timezone.utc).replace(tzinfo=None)
        return v


class ContactUpdate(BaseModel):
    call: str | None = None
    freq: str | None = None
    mode: str | None = None
    rst_sent: str | None = None
    rst_recv: str | None = None
    pota_park: str | None = None
    name: str | None = None
    qth: str | None = None
    state: str | None = None
    country: str | None = None
    dxcc: int | None = None
    grid: str | None = None
    skcc: str | None = None
    skcc_exch: bool | None = None
    comments: str | None = None
    notes: str | None = None
    timestamp: datetime | None = None

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        if v.tzinfo is not None:
            v = v.astimezone(timezone.utc).replace(tzinfo=None)
        return v


class ContactResponse(BaseModel):
    id: int
    uuid: str | None
    call: str
    freq: str | None
    mode: str | None
    rst_sent: str | None
    rst_recv: str | None
    pota_park: str | None
    name: str | None
    qth: str | None
    state: str | None
    country: str | None
    dxcc: int | None = None
    grid: str | None
    skcc: str | None
    skcc_exch: bool = False
    comments: str | None
    notes: str | None
    timestamp: datetime
    updated_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def coerce_skcc_exch(cls, data):
        if hasattr(data, "__dict__"):
            val = getattr(data, "skcc_exch", None)
            if val is None:
                object.__setattr__(data, "skcc_exch", 0)
        elif isinstance(data, dict) and data.get("skcc_exch") is None:
            data["skcc_exch"] = False
        return data

    @field_serializer("timestamp")
    def serialize_timestamp(self, v: datetime) -> str:
        return v.strftime("%Y-%m-%dT%H:%M:%SZ")

    @field_serializer("updated_at")
    def serialize_updated_at(self, v: datetime | None) -> str | None:
        if v is None:
            return None
        return v.strftime("%Y-%m-%dT%H:%M:%SZ")

    model_config = {"from_attributes": True}


@router.get("/today-pota")
async def today_pota_contacts(session: AsyncSession = Depends(get_session)):
    today_start = (
        datetime.now(timezone.utc)
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .replace(tzinfo=None)
    )
    rows = (
        await session.execute(
            select(Contact.call, Contact.freq, Contact.mode, Contact.pota_park)
            .where(Contact.pota_park.isnot(None))
            .where(Contact.pota_park != "")
            .where(Contact.timestamp >= today_start)
        )
    ).all()
    return [
        {"call": call, "freq": freq, "mode": mode, "pota_park": park}
        for call, freq, mode, park in rows
    ]


@router.get("/today-cw")
async def today_cw_contacts(session: AsyncSession = Depends(get_session)):
    today_start = (
        datetime.now(timezone.utc)
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .replace(tzinfo=None)
    )
    rows = (
        await session.execute(
            select(Contact.call, Contact.freq, Contact.mode)
            .where(Contact.mode == "CW")
            .where(Contact.timestamp >= today_start)
        )
    ).all()
    return [
        {"call": call, "freq": freq, "mode": mode}
        for call, freq, mode in rows
    ]


@router.get("/today")
async def today_contacts(session: AsyncSession = Depends(get_session)):
    today_start = (
        datetime.now(timezone.utc)
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .replace(tzinfo=None)
    )
    rows = (
        await session.execute(
            select(Contact.call, Contact.freq, Contact.mode)
            .where(Contact.timestamp >= today_start)
        )
    ).all()
    return [
        {"call": call, "freq": freq, "mode": mode}
        for call, freq, mode in rows
    ]


@router.get("/callsign-counts")
async def callsign_counts(session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(
            select(
                Contact.call,
                func.count(),
                func.max(Contact.timestamp),
            ).group_by(Contact.call)
        )
    ).all()
    return {
        call: {
            "count": count,
            "last": last.isoformat() if last else None,
        }
        for call, count, last in rows
    }


@router.get("/", response_model=list[ContactResponse])
async def list_contacts(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Contact).order_by(Contact.timestamp.desc()))
    return result.scalars().all()


@router.post("/", response_model=ContactResponse, status_code=201)
async def create_contact(
    data: ContactCreate, session: AsyncSession = Depends(get_session)
):
    fields = data.model_dump(exclude_unset=True)
    fields["updated_at"] = fields.get("timestamp") or datetime.now(timezone.utc)
    contact = Contact(**fields)
    session.add(contact)
    await session.commit()
    await session.refresh(contact)
    return contact


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(contact_id: int, session: AsyncSession = Depends(get_session)):
    contact = await session.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.put("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: int,
    data: ContactUpdate,
    session: AsyncSession = Depends(get_session),
):
    contact = await session.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(contact, key, value)
    contact.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(contact)
    return contact


@router.delete("/all")
async def delete_all_contacts(session: AsyncSession = Depends(get_session)):
    result = await session.execute(delete(Contact))
    await session.commit()
    logger.info("Deleted all contacts: %d removed", result.rowcount)
    return {"deleted": result.rowcount}


@router.delete("/{contact_id}", status_code=204)
async def delete_contact(contact_id: int, session: AsyncSession = Depends(get_session)):
    contact = await session.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    await session.delete(contact)
    await session.commit()
