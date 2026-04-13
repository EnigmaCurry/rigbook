import html
import logging
import re
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
    """Parse QRZ's ampersand-separated name=value response.

    The ADIF field contains raw ADIF data that may include '&' characters,
    so we extract it separately before splitting the rest.
    """
    result = {}
    body = text.strip()

    # ADIF field is always last and can contain '&', so extract it first
    adif_marker = "&ADIF="
    idx = body.find(adif_marker)
    if idx == -1:
        # Also check if response starts with ADIF=
        if body.startswith("ADIF="):
            result["ADIF"] = body[5:]
            return result
    else:
        result["ADIF"] = body[idx + len(adif_marker) :]
        body = body[:idx]

    for pair in body.split("&"):
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
        logger.info("QRZ STATUS request")
        async with httpx.AsyncClient(
            timeout=10, headers={"User-Agent": _user_agent(callsign)}
        ) as client:
            res = await client.post(
                QRZ_LOGBOOK_URL,
                data={"KEY": api_key, "ACTION": "STATUS"},
            )
            parsed = _parse_qrz_response(res.text)
            logger.info("QRZ STATUS response: RESULT=%s", parsed.get("RESULT"))
            if parsed.get("RESULT") == "OK":
                qrz_status = parsed.get("DATA")
    except Exception as e:
        logger.warning("QRZ STATUS failed: %s", e)

    logger.info(
        "QRZ sync status: total=%d, synced=%d, pending=%d, excluded=%d",
        total_count,
        synced_count,
        unsynced_count,
        excluded_count,
    )

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
    logger.info("QRZ upload requested for %d contact IDs", len(body.contact_ids))

    stmt = (
        select(Contact)
        .where(Contact.id.in_(body.contact_ids), _not_excluded)
        .order_by(Contact.timestamp.asc())
    )
    result = await session.execute(stmt)
    contacts = result.scalars().all()

    if not contacts:
        logger.info("QRZ upload: no eligible contacts found")
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

    logger.info("QRZ upload-all: %d contacts", len(contacts))
    return await _upload_contacts(contacts, api_key, callsign, session, replace=True)


@router.get("/fetch")
async def fetch_qrz_logbook(session: AsyncSession = Depends(get_session)):
    """Fetch entire QRZ logbook as ADIF text, paginating with MAX/AFTERLOGID."""
    api_key = await _get_api_key(session)
    if not api_key:
        return {"error": "QRZ API key not set"}

    callsign = await _get_callsign(session)
    all_adif = []
    after_logid = 0
    page_size = 250
    total_records = 0
    page_num = 0

    logger.info("QRZ FETCH: starting logbook download")

    async with httpx.AsyncClient(
        timeout=30, headers={"User-Agent": _user_agent(callsign)}
    ) as client:
        while True:
            page_num += 1
            option = f"TYPE:ADIF,MAX:{page_size},AFTERLOGID:{after_logid}"
            logger.info("QRZ FETCH page %d: OPTION=%s", page_num, option)

            res = await client.post(
                QRZ_LOGBOOK_URL,
                data={
                    "KEY": api_key,
                    "ACTION": "FETCH",
                    "OPTION": option,
                },
            )

            raw_text = res.text
            logger.debug(
                "QRZ FETCH raw response (%d chars): %s",
                len(raw_text),
                raw_text[:500],
            )

            parsed = _parse_qrz_response(raw_text)
            result_code = parsed.get("RESULT", "(missing)")
            count_str = parsed.get("COUNT", "0")
            adif_data = html.unescape(parsed.get("ADIF", ""))

            logger.info(
                "QRZ FETCH page %d: RESULT=%s, COUNT=%s, ADIF length=%d chars",
                page_num,
                result_code,
                count_str,
                len(adif_data),
            )

            if result_code != "OK":
                reason = parsed.get("REASON", "Unknown error")
                logger.warning(
                    "QRZ FETCH page %d failed: %s (all parsed keys: %s)",
                    page_num,
                    reason,
                    list(parsed.keys()),
                )
                if all_adif:
                    break
                return {"error": f"QRZ fetch failed: {reason}"}

            if not adif_data:
                logger.info("QRZ FETCH page %d: empty ADIF, done", page_num)
                break

            logger.info(
                "QRZ FETCH page %d ADIF preview: %s",
                page_num,
                repr(adif_data[:500]),
            )

            # Count <eor> markers to verify record count
            eor_count = len(re.findall(r"<eor>", adif_data, re.IGNORECASE))
            logger.info(
                "QRZ FETCH page %d: %d <eor> markers found in ADIF",
                page_num,
                eor_count,
            )
            if eor_count > 0:
                # Log first record as sample
                first_eor = re.search(r"<eor>", adif_data, re.IGNORECASE)
                if first_eor:
                    logger.debug(
                        "QRZ FETCH sample record: %s",
                        adif_data[: first_eor.end()],
                    )

            all_adif.append(adif_data)
            total_records += eor_count

            count = int(count_str)
            if count < page_size:
                logger.info(
                    "QRZ FETCH: last page (count %d < page_size %d)",
                    count,
                    page_size,
                )
                break

            # Find highest app_qrzlog_logid for pagination
            logids = re.findall(
                r"<app_qrzlog_logid:\d+>(\d+)", adif_data, re.IGNORECASE
            )
            if logids:
                after_logid = max(int(lid) for lid in logids) + 1
                logger.info("QRZ FETCH: next AFTERLOGID=%d", after_logid)
            else:
                logger.info("QRZ FETCH: no app_qrzlog_logid found, stopping")
                break

    adif_text = "\n".join(all_adif)
    logger.info(
        "QRZ FETCH complete: %d pages, %d records, %d chars total ADIF",
        page_num,
        total_records,
        len(adif_text),
    )
    return {"adif": adif_text, "ok": True}


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
    logger.info("QRZ excluded contact %d (%s)", contact_id, contact.call)
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
    logger.info("QRZ included contact %d (%s)", contact_id, contact.call)
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

    logger.info(
        "QRZ INSERT: uploading %d contacts (replace=%s)", len(contacts), replace
    )

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

            use_replace = replace or contact.qrz_logid is not None
            data = {
                "KEY": api_key,
                "ACTION": "INSERT",
                "ADIF": adif_line,
            }
            if use_replace:
                data["OPTION"] = "REPLACE"

            logger.debug(
                "QRZ INSERT %s: ADIF=%s, REPLACE=%s",
                contact.call,
                adif_line[:200],
                use_replace,
            )

            try:
                res = await client.post(QRZ_LOGBOOK_URL, data=data)
                parsed = _parse_qrz_response(res.text)
                result_code = parsed.get("RESULT", "(missing)")

                logger.info(
                    "QRZ INSERT %s: RESULT=%s, LOGID=%s",
                    contact.call,
                    result_code,
                    parsed.get("LOGID", "(none)"),
                )

                if result_code in ("OK", "REPLACE"):
                    logid = parsed.get("LOGID")
                    if logid:
                        contact.qrz_logid = int(logid)
                    contact.qrz_synced_at = now
                    uploaded += 1
                elif result_code == "FAIL":
                    reason = parsed.get("REASON", "Unknown error")
                    errors += 1
                    error_details.append({"call": contact.call, "reason": reason})
                    logger.warning("QRZ INSERT %s failed: %s", contact.call, reason)
                else:
                    errors += 1
                    error_details.append(
                        {"call": contact.call, "reason": res.text[:200]}
                    )
                    logger.warning(
                        "QRZ INSERT %s unexpected response: %s",
                        contact.call,
                        res.text[:200],
                    )
            except Exception as e:
                errors += 1
                error_details.append({"call": contact.call, "reason": str(e)})
                logger.warning("QRZ INSERT %s error: %s", contact.call, e)

    await session.commit()

    logger.info(
        "QRZ INSERT complete: %d uploaded, %d errors, %d total",
        uploaded,
        errors,
        len(contacts),
    )

    return {
        "uploaded": uploaded,
        "errors": errors,
        "total": len(contacts),
        "error_details": error_details[:20],
    }
