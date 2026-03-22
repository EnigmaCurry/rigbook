from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_serializer
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from rigbook.db import Notification, async_session, get_session

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationResponse(BaseModel):
    id: int
    title: str
    text: str
    read: bool
    done: bool
    timestamp: datetime

    @field_serializer("timestamp")
    def serialize_timestamp(self, v: datetime) -> str:
        return v.strftime("%Y-%m-%dT%H:%M:%SZ")

    model_config = {"from_attributes": True}


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


@router.put("/{notification_id}/done", status_code=204)
async def mark_done(notification_id: int, session: AsyncSession = Depends(get_session)):
    notif = await session.get(Notification, notification_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.read = 1
    notif.done = 1
    await session.commit()


@router.delete("/{notification_id}", status_code=204)
async def delete_notification(
    notification_id: int, session: AsyncSession = Depends(get_session)
):
    notif = await session.get(Notification, notification_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    await session.delete(notif)
    await session.commit()


async def create_notification(title: str, text: str) -> None:
    """Create a notification from non-request context (e.g. background feeds)."""
    async with async_session() as session:
        session.add(Notification(title=title, text=text))
        await session.commit()
