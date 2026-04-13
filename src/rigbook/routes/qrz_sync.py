import logging
from datetime import datetime, timezone
from importlib.metadata import version as pkg_version

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from rigbook.db import Contact, get_session, resolve_setting
from rigbook.routes.adif import (
    _fetch_comment_settings,
    contact_to_adif_record,
    record_to_adif_line,
)
from rigbook.routes.contacts import ContactResponse
from rigbook.spots import freq_to_band

logger = logging.getLogger("rigbook")

router = APIRouter(prefix="/api/qrz-sync", tags=["qrz-sync"])

QRZ_LOGBOOK_URL = "https://logbook.qrz.com/api"

# Common filter: not excluded from QRZ
_not_excluded = or_(Contact.qrz_excluded.is_(None), Contact.qrz_excluded == 0)

# Common filter: needs sync (new or updated since last sync) and not excluded
_needs_sync = (
    _not_excluded,
    or_(
        Contact.qrz_logid.is_(None),
        Contact.updated_at > Contact.qrz_synced_at,
    ),
)


async def _get_api_key(session: AsyncSession) -> str | None:
    return await resolve_setting("qrz_api_key", session)


async def _get_callsign(session: AsyncSession) -> str | None:
    return await resolve_setting("my_callsign", session)


def _user_agent(callsign: str | None) -> str:
    ver = pkg_version("rigbook")
    if callsign:
        return f"Rigbook/{ver} ({callsign})"
    return f"Rigbook/{ver}"


def _parse_qrz_response(text: str) -> dict[str, str]:
    """Parse QRZ's ampersand-separated name=value response."""
    result = {}
    for pair in text.strip().split("&"):
        if "=" in pair:
            key, _, value = pair.partition("=")
            result[key] = value
    return result


def _add_required_fields(
    record: dict, callsign: str | None, freq_khz: str | None
) -> dict:
    """Add STATION_CALLSIGN and BAND fields required by QRZ."""
    if callsign and "STATION_CALLSIGN" not in record:
        record["STATION_CALLSIGN"] = callsign
    if freq_khz and "BAND" not in record:
        try:
            band = freq_to_band(float(freq_khz))
            if band:
                record["BAND"] = band
        except (ValueError, TypeError):
            pass
    return record


@router.get("/status")
async def sync_status(session: AsyncSession = Depends(get_session)):
    """Return count of unsynced contacts and QRZ logbook stats."""
    api_key = await _get_api_key(session)
    if not api_key:
        return {"configured": False, "error": "QRZ API key not set"}

    unsynced_count = (
        await session.execute(select(func.count(Contact.id)).where(*_needs_sync))
    ).scalar() or 0

    total_count = (await session.execute(select(func.count(Contact.id)))).scalar() or 0

    excluded_count = (
        await session.execute(
            select(func.count(Contact.id)).where(Contact.qrz_excluded == 1)
        )
    ).scalar() or 0

    synced_stmt = select(func.count(Contact.id)).where(
        _not_excluded,
        Contact.qrz_logid.isnot(None),
        or_(
            Contact.qrz_synced_at.is_(None),
            Contact.updated_at <= Contact.qrz_synced_at,
        ),
    )
    synced_count = (await session.execute(synced_stmt)).scalar() or 0

    # Try to get QRZ logbook status
    callsign = await _get_callsign(session)
    qrz_status = None
    try:
        async with httpx.AsyncClient(
            timeout=10, headers={"User-Agent": _user_agent(callsign)}
        ) as client:
            res = await client.post(
                QRZ_LOGBOOK_URL,
                data={"KEY": api_key, "ACTION": "STATUS"},
            )
            parsed = _parse_qrz_response(res.text)
            if parsed.get("RESULT") == "OK":
                qrz_status = parsed.get("DATA")
    except Exception as e:
        logger.warning("QRZ status check failed: %s", e)

    return {
        "configured": True,
        "total": total_count,
        "synced": synced_count,
        "pending": unsynced_count,
        "excluded": excluded_count,
        "qrz_status": qrz_status,
    }


@router.get("/preview")
async def sync_preview(session: AsyncSession = Depends(get_session)):
    """Return contacts pending upload to QRZ."""
    api_key = await _get_api_key(session)
    if not api_key:
        return {"configured": False, "contacts": [], "pending": 0, "total": 0}

    total_count = (await session.execute(select(func.count(Contact.id)))).scalar() or 0

    stmt = select(Contact).where(*_needs_sync).order_by(Contact.timestamp.desc())
    result = await session.execute(stmt)
    contacts = result.scalars().all()

    previews = []
    for c in contacts:
        data = ContactResponse.model_validate(c).model_dump()
        previews.append(data)

    excluded_stmt = (
        select(Contact)
        .where(Contact.qrz_excluded == 1)
        .order_by(Contact.timestamp.desc())
    )
    excluded_result = await session.execute(excluded_stmt)
    excluded_contacts = excluded_result.scalars().all()

    excluded_previews = []
    for c in excluded_contacts:
        data = ContactResponse.model_validate(c).model_dump()
        excluded_previews.append(data)

    return {
        "configured": True,
        "contacts": previews,
        "excluded": excluded_previews,
        "pending": len(previews),
        "total": total_count,
    }


class UploadRequest(BaseModel):
    contact_ids: list[int]


@router.post("/upload")
async def upload_selected(
    body: UploadRequest, session: AsyncSession = Depends(get_session)
):
    """Upload selected contacts to QRZ."""
    api_key = await _get_api_key(session)
    if not api_key:
        return {"error": "QRZ API key not set"}

    callsign = await _get_callsign(session)

    stmt = (
        select(Contact)
        .where(Contact.id.in_(body.contact_ids), _not_excluded)
        .order_by(Contact.timestamp.asc())
    )
    result = await session.execute(stmt)
    contacts = result.scalars().all()

    if not contacts:
        return {"uploaded": 0, "errors": 0, "message": "No contacts to upload"}

    return await _upload_contacts(contacts, api_key, callsign, session, replace=False)


@router.post("/upload-all")
async def upload_all(session: AsyncSession = Depends(get_session)):
    """Re-upload all contacts to QRZ with REPLACE option."""
    api_key = await _get_api_key(session)
    if not api_key:
        return {"error": "QRZ API key not set"}

    callsign = await _get_callsign(session)

    stmt = select(Contact).where(_not_excluded).order_by(Contact.timestamp.asc())
    result = await session.execute(stmt)
    contacts = result.scalars().all()

    if not contacts:
        return {"uploaded": 0, "errors": 0, "message": "No contacts to upload"}

    return await _upload_contacts(contacts, api_key, callsign, session, replace=True)


@router.post("/exclude/{contact_id}")
async def exclude_contact(
    contact_id: int, session: AsyncSession = Depends(get_session)
):
    """Mark a contact as excluded from QRZ uploads."""
    contact = (
        await session.execute(select(Contact).where(Contact.id == contact_id))
    ).scalar_one_or_none()
    if not contact:
        return {"error": "Contact not found"}
    contact.qrz_excluded = 1
    await session.commit()
    return {"ok": True, "id": contact_id}


@router.post("/include/{contact_id}")
async def include_contact(
    contact_id: int, session: AsyncSession = Depends(get_session)
):
    """Remove exclusion flag from a contact."""
    contact = (
        await session.execute(select(Contact).where(Contact.id == contact_id))
    ).scalar_one_or_none()
    if not contact:
        return {"error": "Contact not found"}
    contact.qrz_excluded = 0
    await session.commit()
    return {"ok": True, "id": contact_id}


async def _upload_contacts(
    contacts: list[Contact],
    api_key: str,
    callsign: str | None,
    session: AsyncSession,
    replace: bool = False,
) -> dict:
    """Upload a list of contacts to QRZ one at a time."""
    uploaded = 0
    errors = 0
    error_details = []
    now = datetime.now(timezone.utc)

    comment_template, comment_separator = await _fetch_comment_settings(session)

    async with httpx.AsyncClient(
        timeout=15, headers={"User-Agent": _user_agent(callsign)}
    ) as client:
        for contact in contacts:
            record = contact_to_adif_record(
                contact,
                comment_template=comment_template or None,
                comment_separator=comment_separator,
            )
            record = _add_required_fields(record, callsign, contact.freq)
            adif_line = record_to_adif_line(record)

            data = {
                "KEY": api_key,
                "ACTION": "INSERT",
                "ADIF": adif_line,
            }
            if replace or contact.qrz_logid is not None:
                data["OPTION"] = "REPLACE"

            try:
                res = await client.post(QRZ_LOGBOOK_URL, data=data)
                parsed = _parse_qrz_response(res.text)

                if parsed.get("RESULT") == "OK" or parsed.get("RESULT") == "REPLACE":
                    logid = parsed.get("LOGID")
                    if logid:
                        contact.qrz_logid = int(logid)
                    contact.qrz_synced_at = now
                    uploaded += 1
                elif parsed.get("RESULT") == "FAIL":
                    reason = parsed.get("REASON", "Unknown error")
                    errors += 1
                    error_details.append({"call": contact.call, "reason": reason})
                    logger.warning("QRZ upload failed for %s: %s", contact.call, reason)
                else:
                    errors += 1
                    error_details.append(
                        {"call": contact.call, "reason": res.text[:200]}
                    )
            except Exception as e:
                errors += 1
                error_details.append({"call": contact.call, "reason": str(e)})
                logger.warning("QRZ upload error for %s: %s", contact.call, e)

    await session.commit()

    return {
        "uploaded": uploaded,
        "errors": errors,
        "total": len(contacts),
        "error_details": error_details[:20],
    }
