import logging
from datetime import datetime, timezone
from importlib.metadata import version as pkg_version
import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from rigbook.db import Contact, get_session, resolve_setting
from rigbook.routes.adif import contact_to_adif_record, record_to_adif_line
from rigbook.spots import freq_to_band

logger = logging.getLogger("rigbook")

router = APIRouter(prefix="/api/qrz-sync", tags=["qrz-sync"])

QRZ_LOGBOOK_URL = "https://logbook.qrz.com/api"


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


def _needs_sync(contact: Contact) -> bool:
    """Check if a contact needs syncing to QRZ."""
    if contact.qrz_logid is None:
        return True
    if contact.updated_at and contact.qrz_synced_at:
        return contact.updated_at > contact.qrz_synced_at
    return False


@router.get("/status")
async def sync_status(session: AsyncSession = Depends(get_session)):
    """Return count of unsynced contacts and QRZ logbook stats."""
    api_key = await _get_api_key(session)
    if not api_key:
        return {"configured": False, "error": "QRZ API key not set"}

    # Count contacts needing sync
    unsynced_stmt = select(func.count(Contact.id)).where(
        or_(
            Contact.qrz_logid.is_(None),
            Contact.updated_at > Contact.qrz_synced_at,
        )
    )
    unsynced_count = (await session.execute(unsynced_stmt)).scalar() or 0

    total_stmt = select(func.count(Contact.id))
    total_count = (await session.execute(total_stmt)).scalar() or 0

    synced_stmt = select(func.count(Contact.id)).where(
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
        "qrz_status": qrz_status,
    }


@router.post("/upload")
async def upload_unsynced(session: AsyncSession = Depends(get_session)):
    """Upload contacts that haven't been synced to QRZ yet."""
    api_key = await _get_api_key(session)
    if not api_key:
        return {"error": "QRZ API key not set"}

    callsign = await _get_callsign(session)

    # Find contacts needing sync
    stmt = (
        select(Contact)
        .where(
            or_(
                Contact.qrz_logid.is_(None),
                Contact.updated_at > Contact.qrz_synced_at,
            )
        )
        .order_by(Contact.timestamp.asc())
    )
    result = await session.execute(stmt)
    contacts = result.scalars().all()

    if not contacts:
        return {"uploaded": 0, "errors": 0, "message": "All contacts already synced"}

    return await _upload_contacts(contacts, api_key, callsign, session, replace=False)


@router.post("/upload-all")
async def upload_all(session: AsyncSession = Depends(get_session)):
    """Re-upload all contacts to QRZ with REPLACE option."""
    api_key = await _get_api_key(session)
    if not api_key:
        return {"error": "QRZ API key not set"}

    callsign = await _get_callsign(session)

    stmt = select(Contact).order_by(Contact.timestamp.asc())
    result = await session.execute(stmt)
    contacts = result.scalars().all()

    if not contacts:
        return {"uploaded": 0, "errors": 0, "message": "No contacts to upload"}

    return await _upload_contacts(contacts, api_key, callsign, session, replace=True)


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

    async with httpx.AsyncClient(
        timeout=15, headers={"User-Agent": _user_agent(callsign)}
    ) as client:
        for contact in contacts:
            record = contact_to_adif_record(contact)
            record = _add_required_fields(record, callsign, contact.freq)
            adif_line = record_to_adif_line(record)

            data = {
                "KEY": api_key,
                "ACTION": "INSERT",
                "ADIF": adif_line,
            }
            if replace:
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
