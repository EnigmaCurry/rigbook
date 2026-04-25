import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, field_serializer, field_validator
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from guidebook.db import Notification, async_session, get_session
from guidebook.sse import broadcast

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationResponse(BaseModel):
    id: int
    title: str
    text: str
    meta: dict | None = None
    read: bool
    done: bool
    timestamp: datetime

    @field_validator("meta", mode="before")
    @classmethod
    def parse_meta(cls, v: str | dict | None) -> dict | None:
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v

    @field_serializer("timestamp")
    def serialize_timestamp(self, v: datetime) -> str:
        return v.strftime("%Y-%m-%dT%H:%M:%SZ")

    model_config = {"from_attributes": True}


async def _broadcast_unread() -> None:
    try:
        async with async_session() as session:
            result = await session.execute(
                select(func.count())
                .select_from(Notification)
                .where(Notification.read == 0, Notification.done == 0)
            )
            count = result.scalar_one()
    except RuntimeError:
        return
    broadcast("unread", {"count": count})


@router.get("/unread-count")
async def unread_count(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(func.count())
        .select_from(Notification)
        .where(Notification.read == 0, Notification.done == 0)
    )
    return {"count": result.scalar_one()}


@router.get("/done", response_model=list[NotificationResponse])
async def list_done(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Notification)
        .where(Notification.done == 1)
        .order_by(Notification.timestamp.desc())
    )
    return result.scalars().all()


@router.put("/read-all", status_code=204)
async def read_all(session: AsyncSession = Depends(get_session)):
    await session.execute(
        update(Notification)
        .where(Notification.done == 0, Notification.read == 0)
        .values(read=1)
    )
    await session.commit()
    await _broadcast_unread()


@router.put("/done-all", status_code=204)
async def done_all(session: AsyncSession = Depends(get_session)):
    await session.execute(
        update(Notification).where(Notification.done == 0).values(read=1, done=1)
    )
    await session.commit()
    await _broadcast_unread()


@router.delete("/done-all", status_code=204)
async def delete_all_done(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Notification).where(Notification.done == 1))
    for notif in result.scalars().all():
        await session.delete(notif)
    await session.commit()


@router.get("/", response_model=list[NotificationResponse])
async def list_inbox(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Notification)
        .where(Notification.done == 0)
        .order_by(Notification.timestamp.desc())
    )
    return result.scalars().all()


@router.put("/{notification_id}/read", status_code=204)
async def mark_read(notification_id: int, session: AsyncSession = Depends(get_session)):
    notif = await session.get(Notification, notification_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.read = 1
    await session.commit()
    await _broadcast_unread()


@router.put("/{notification_id}/done", status_code=204)
async def mark_done(notification_id: int, session: AsyncSession = Depends(get_session)):
    notif = await session.get(Notification, notification_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.read = 1
    notif.done = 1
    await session.commit()
    await _broadcast_unread()


@router.delete("/{notification_id}", status_code=204)
async def delete_notification(
    notification_id: int, session: AsyncSession = Depends(get_session)
):
    notif = await session.get(Notification, notification_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    await session.delete(notif)
    await session.commit()
    await _broadcast_unread()


async def _delayed_test_notification() -> None:
    await asyncio.sleep(5)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    await create_notification(
        "Test Notification", f"This is a test notification sent at {now}."
    )


@router.post("/test", status_code=202)
async def send_test_notification(background_tasks: BackgroundTasks):
    background_tasks.add_task(_delayed_test_notification)
    return {"status": "scheduled"}


async def create_notification(title: str, text: str, meta: dict | None = None) -> None:
    """Create a notification from non-request context (e.g. background feeds)."""
    try:
        session_ctx = async_session()
    except RuntimeError:
        return
    async with session_ctx as session:
        notif = Notification(
            title=title,
            text=text,
            meta=json.dumps(meta) if meta else None,
        )
        session.add(notif)
        await session.commit()
        await session.refresh(notif)
    resp = NotificationResponse.model_validate(notif)
    broadcast("notification", resp.model_dump())
    await _broadcast_unread()
