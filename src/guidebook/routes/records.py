import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_serializer, field_validator
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from guidebook.db import Record, get_session

logger = logging.getLogger("guidebook")

router = APIRouter(prefix="/api/records", tags=["records"])


class RecordCreate(BaseModel):
    title: str
    content: str | None = None
    tags: str | None = None
    timestamp: datetime | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("title must not be empty")
        return v

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        if v.tzinfo is not None:
            v = v.astimezone(timezone.utc).replace(tzinfo=None)
        return v


class RecordUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    tags: str | None = None
    timestamp: datetime | None = None

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return v
        if v.tzinfo is not None:
            v = v.astimezone(timezone.utc).replace(tzinfo=None)
        return v


class RecordResponse(BaseModel):
    id: int
    uuid: str | None
    title: str
    content: str | None
    tags: str | None
    timestamp: datetime
    updated_at: datetime | None = None

    @field_serializer("timestamp")
    def serialize_timestamp(self, v: datetime) -> str:
        return v.strftime("%Y-%m-%dT%H:%M:%SZ")

    @field_serializer("updated_at")
    def serialize_updated_at(self, v: datetime | None) -> str | None:
        if v is None:
            return None
        return v.strftime("%Y-%m-%dT%H:%M:%SZ")

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[RecordResponse])
async def list_records(
    q: str | None = Query(None, description="Search query"),
    limit: int = Query(100, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Record)
    if q and len(q) >= 2:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                Record.title.ilike(pattern),
                Record.content.ilike(pattern),
                Record.tags.ilike(pattern),
            )
        )
    stmt = stmt.order_by(Record.timestamp.desc()).offset(offset).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.post("/", response_model=RecordResponse, status_code=201)
async def create_record(
    data: RecordCreate, session: AsyncSession = Depends(get_session)
):
    fields = data.model_dump(exclude_unset=True)
    fields["updated_at"] = fields.get("timestamp") or datetime.now(timezone.utc)
    record = Record(**fields)
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


@router.get("/{record_id}", response_model=RecordResponse)
async def get_record(record_id: int, session: AsyncSession = Depends(get_session)):
    record = await session.get(Record, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@router.put("/{record_id}", response_model=RecordResponse)
async def update_record(
    record_id: int,
    data: RecordUpdate,
    session: AsyncSession = Depends(get_session),
):
    record = await session.get(Record, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    record.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(record)
    return record


@router.delete("/all")
async def delete_all_records(session: AsyncSession = Depends(get_session)):
    result = await session.execute(delete(Record))
    await session.commit()
    logger.info("Deleted all records: %d removed", result.rowcount)
    return {"deleted": result.rowcount}


@router.delete("/{record_id}", status_code=204)
async def delete_record(record_id: int, session: AsyncSession = Depends(get_session)):
    record = await session.get(Record, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    await session.delete(record)
    await session.commit()
