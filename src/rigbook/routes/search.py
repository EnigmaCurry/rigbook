from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from rigbook.db import Contact, get_session
from rigbook.routes.contacts import ContactResponse

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/", response_model=list[ContactResponse])
async def search_contacts(q: str = "", session: AsyncSession = Depends(get_session)):
    if len(q) < 2:
        return []
    pattern = f"%{q}%"
    columns = [
        Contact.call,
        Contact.name,
        Contact.qth,
        Contact.state,
        Contact.country,
        Contact.pota_park,
        Contact.grid,
        Contact.comments,
        Contact.skcc,
    ]
    result = await session.execute(
        select(Contact)
        .where(or_(*[col.ilike(pattern) for col in columns]))
        .order_by(Contact.timestamp.desc())
        .limit(20)
    )
    return result.scalars().all()
