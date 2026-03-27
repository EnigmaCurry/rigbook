from datetime import datetime, timezone
import json
import re
from io import StringIO
from typing import Optional

from adif_file import adi
from fastapi import APIRouter, Depends, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, cast, Float, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from rigbook.db import Contact, Setting, get_session
from rigbook.dxcc import dxcc_country
from rigbook.routes.contacts import ContactResponse

router = APIRouter(prefix="/api/adif", tags=["adif"])

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


def _build_filtered_query(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    comment: Optional[str] = None,
    skcc_validated: bool = False,
    country: Optional[str] = None,
    mode: Optional[str] = None,
    band: Optional[str] = None,
):
    stmt = select(Contact)
    if date_from:
        try:
            dt = datetime.strptime(date_from, "%Y-%m-%d")
            stmt = stmt.where(Contact.timestamp >= dt)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59
            )
            stmt = stmt.where(Contact.timestamp <= dt)
        except ValueError:
            pass
    if comment:
        pattern = f"%{comment}%"
        stmt = stmt.where(
            or_(
                Contact.comments.ilike(pattern),
                Contact.notes.ilike(pattern),
            )
        )
    if skcc_validated:
        stmt = stmt.where(Contact.skcc_exch == 1)
    if country:
        stmt = stmt.where(Contact.country.ilike(country))
    if mode:
        stmt = stmt.where(Contact.mode.ilike(mode))
    if band:
        freq_range = BAND_FREQ_MAP.get(band.lower())
        if freq_range:
            lo, hi = freq_range
            stmt = stmt.where(
                and_(
                    cast(Contact.freq, Float) >= lo,
                    cast(Contact.freq, Float) <= hi,
                )
            )
    return stmt


def render_comment_with_template(
    template_fields: list[dict], c: Contact, separator: str = "|"
) -> str:
    """Render comment from template fields + user comments."""
    field_map = {
        "call": c.call,
        "freq": c.freq,
        "mode": c.mode,
        "rst_sent": c.rst_sent,
        "rst_recv": c.rst_recv,
        "name": c.name,
        "qth": c.qth,
        "state": c.state,
        "country": c.country,
        "grid": c.grid,
        "pota_park": c.pota_park,
        "skcc": c.skcc,
    }
    parts = []
    for entry in template_fields:
        val = field_map.get(entry.get("field"))
        if val:
            label = entry.get("label", entry["field"])
            parts.append(f"{label}: {val}")
    if (c.comments or "").strip():
        parts.append((c.comments or "").strip())
    sep = f" {separator.strip()} "
    return sep.join(parts)


def contact_to_adif_record(
    c: Contact,
    comment_template: list | None = None,
    comment_separator: str = "|",
) -> dict:
    ts = c.timestamp or datetime.now(timezone.utc)
    record = {
        "QSO_DATE": ts.strftime("%Y%m%d"),
        "TIME_ON": ts.strftime("%H%M%S"),
        "CALL": c.call or "",
        "FREQ": str(float(c.freq) / 1000) if c.freq else "",
        "MODE": c.mode or "",
    }
    if c.rst_sent:
        record["RST_SENT"] = c.rst_sent
    if c.rst_recv:
        record["RST_RCVD"] = c.rst_recv
    if c.name:
        record["NAME"] = c.name
    if c.qth:
        record["QTH"] = c.qth
    if c.state:
        record["STATE"] = c.state
    if c.dxcc is not None:
        record["DXCC"] = str(c.dxcc)
        adif_name = dxcc_country(c.dxcc)
        if adif_name:
            record["COUNTRY"] = adif_name
    elif c.country:
        record["COUNTRY"] = c.country
    if c.grid:
        record["GRIDSQUARE"] = c.grid
    if c.pota_park:
        record["POTA_REF"] = c.pota_park
    if c.skcc is not None:
        record["SKCC"] = str(c.skcc)
    if c.skcc_exch:
        record["APP_RIGBOOK_SKCC_EXCH"] = "Y"
    if comment_template:
        comment = render_comment_with_template(
            comment_template, c, comment_separator
        )
        if comment:
            record["COMMENT"] = comment
        record["APP_RIGBOOK_COMMENT_FMT"] = comment_separator.strip()
    elif c.comments:
        record["COMMENT"] = c.comments
    if c.notes:
        record["NOTES"] = c.notes
    if c.uuid:
        record["APP_RIGBOOK_UUID"] = c.uuid
    return record


def strip_comment_prefix(
    comment: str,
    record: dict,
    template_fields: list[dict],
    default_separator: str,
) -> str:
    """Strip template-generated prefix from COMMENT, return user's original text."""
    if not comment:
        return comment
    fmt_sep = record.get("APP_RIGBOOK_COMMENT_FMT")
    separator = (fmt_sep or default_separator or "|").strip()
    padded = f" {separator} "

    if not template_fields or padded not in comment:
        return comment

    parts = comment.split(padded)
    if len(parts) <= 1:
        return comment

    # Build expected prefix segments from the ADIF record's own normalized fields
    field_values = {
        "call": record.get("CALL", ""),
        "freq": record.get("FREQ", ""),
        "mode": record.get("MODE", ""),
        "rst_sent": record.get("RST_SENT", ""),
        "rst_recv": record.get("RST_RCVD", ""),
        "name": record.get("NAME", ""),
        "qth": record.get("QTH", ""),
        "state": record.get("STATE", ""),
        "country": record.get("COUNTRY", ""),
        "grid": record.get("GRIDSQUARE", ""),
        "pota_park": record.get("POTA_REF", ""),
        "skcc": record.get("SKCC", ""),
    }
    expected = []
    for entry in template_fields:
        val = field_values.get(entry.get("field"), "")
        if val:
            expected.append(f"{entry.get('label', entry['field'])}: {val}")

    # Strip matching leading segments
    strip_count = 0
    for i, seg in enumerate(parts):
        if i < len(expected) and seg.strip() == expected[i].strip():
            strip_count += 1
        else:
            break

    if strip_count > 0:
        return padded.join(parts[strip_count:])
    return comment


def record_to_adif_line(record: dict) -> str:
    """Render an ADIF record dict as a single ADIF line string."""
    parts = []
    for key, val in record.items():
        if val is not None and val != "":
            s = str(val)
            parts.append(f"<{key}:{len(s)}>{s}")
    parts.append("<eor>")
    return " ".join(parts)


def adif_record_to_contact_dict(record: dict) -> dict:
    data = {}
    data["call"] = record.get("CALL", "")
    freq_mhz = record.get("FREQ", "")
    if freq_mhz:
        try:
            data["freq"] = str(float(freq_mhz) * 1000)
        except ValueError:
            data["freq"] = freq_mhz
    data["mode"] = record.get("MODE", "")
    data["rst_sent"] = record.get("RST_SENT")
    data["rst_recv"] = record.get("RST_RCVD")
    data["name"] = record.get("NAME")
    data["qth"] = record.get("QTH")
    data["state"] = record.get("STATE")
    data["country"] = record.get("COUNTRY")
    dxcc_val = record.get("DXCC")
    if dxcc_val:
        try:
            data["dxcc"] = int(dxcc_val)
        except (ValueError, TypeError):
            pass
    data["grid"] = record.get("GRIDSQUARE")
    data["pota_park"] = record.get("POTA_REF")
    skcc = record.get("SKCC")
    if skcc:
        data["skcc"] = skcc
    if record.get("APP_RIGBOOK_SKCC_EXCH", "").upper() == "Y":
        data["skcc_exch"] = 1
    data["comments"] = record.get("COMMENT")
    data["notes"] = record.get("NOTES")
    app_uuid = record.get("APP_RIGBOOK_UUID")
    if app_uuid:
        data["uuid"] = app_uuid

    qso_date = record.get("QSO_DATE", "")
    time_on = record.get("TIME_ON", "")
    if qso_date:
        time_str = time_on.ljust(6, "0") if time_on else "000000"
        try:
            data["timestamp"] = datetime.strptime(
                f"{qso_date}{time_str}", "%Y%m%d%H%M%S"
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    return {k: v for k, v in data.items() if v is not None and v != ""}


@router.get("/preview")
async def preview_adif(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    comment: Optional[str] = Query(None),
    skcc_validated: bool = Query(False),
    country: Optional[str] = Query(None),
    mode: Optional[str] = Query(None),
    band: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    total_result = await session.execute(select(Contact))
    total = len(total_result.scalars().all())

    stmt = _build_filtered_query(
        date_from, date_to, comment, skcc_validated, country, mode, band
    ).order_by(Contact.timestamp.desc())
    result = await session.execute(stmt)
    contacts = result.scalars().all()
    included = len(contacts)

    comment_template, comment_separator = await _fetch_comment_settings(session)

    previews = []
    for c in contacts:
        data = ContactResponse.model_validate(c).model_dump()
        adif_rec = contact_to_adif_record(
            c,
            comment_template=comment_template or None,
            comment_separator=comment_separator,
        )
        data["adif_line"] = record_to_adif_line(adif_rec)
        previews.append(data)

    header = {
        "ADIF_VER": "3.1.4",
        "PROGRAMID": "Rigbook",
        "PROGRAMVERSION": "0.1.0",
    }

    return {
        "contacts": previews,
        "total": total,
        "included": included,
        "excluded": total - included,
        "header": header,
        "header_adif": record_to_adif_line(header).replace("<eor>", "<eoh>"),
    }


@router.get("/export")
async def export_adif(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    comment: Optional[str] = Query(None),
    skcc_validated: bool = Query(False),
    country: Optional[str] = Query(None),
    mode: Optional[str] = Query(None),
    band: Optional[str] = Query(None),
    title: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    stmt = _build_filtered_query(
        date_from, date_to, comment, skcc_validated, country, mode, band
    ).order_by(Contact.timestamp.asc())
    result = await session.execute(stmt)
    contacts = result.scalars().all()

    comment_template, comment_separator = await _fetch_comment_settings(session)

    doc = {
        "HEADER": {
            "ADIF_VER": "3.1.4",
            "PROGRAMID": "Rigbook",
            "PROGRAMVERSION": "0.1.0",
        },
        "RECORDS": [
            contact_to_adif_record(
                c,
                comment_template=comment_template or None,
                comment_separator=comment_separator,
            )
            for c in contacts
        ],
    }

    output = adi.dumps(doc)

    callsign_row = (
        await session.execute(select(Setting).where(Setting.key == "my_callsign"))
    ).scalar_one_or_none()
    callsign = callsign_row.value if callsign_row and callsign_row.value else "rigbook"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H%M%Sz")
    safe_title = ""
    if title:
        safe_title = "".join(
            c for c in title.strip() if c.isalnum() or c in " -_"
        ).strip()
    if safe_title:
        filename = f"{callsign} - {safe_title} - {ts}.adi"
    else:
        filename = f"{callsign} - {ts}.adi"

    return StreamingResponse(
        StringIO(output),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _fetch_comment_settings(session: AsyncSession):
    template = []
    separator = "|"
    tpl_row = (
        await session.execute(
            select(Setting).where(Setting.key == "comment_template")
        )
    ).scalar_one_or_none()
    if tpl_row and tpl_row.value:
        try:
            template = json.loads(tpl_row.value)
        except (json.JSONDecodeError, TypeError):
            template = []
    sep_row = (
        await session.execute(
            select(Setting).where(Setting.key == "comment_separator")
        )
    ).scalar_one_or_none()
    if sep_row and sep_row.value:
        separator = sep_row.value
    return template, separator


async def _classify_import_records(
    records: list[dict],
    session: AsyncSession,
    template: list[dict],
    separator: str,
):
    """Classify ADIF records into new, duplicate, and skipped without committing.

    Returns (new_records, duplicates, skipped) where new_records is a list
    of (contact_dict, raw_adif_record) tuples.
    """
    new_records = []
    skipped = 0
    duplicates = 0
    for record in records:
        data = adif_record_to_contact_dict(record)
        if data.get("comments") and template:
            data["comments"] = strip_comment_prefix(
                data["comments"], record, template, separator
            )
            if not data["comments"]:
                del data["comments"]
        if not data.get("call"):
            skipped += 1
            continue
        record_uuid = data.get("uuid")
        is_dup = False
        if record_uuid:
            existing = (
                await session.execute(
                    select(Contact).where(Contact.uuid == record_uuid)
                )
            ).scalar_one_or_none()
            if existing:
                is_dup = True
        else:
            ts = data.get("timestamp")
            if ts:
                check_ts = (
                    ts.replace(second=0, tzinfo=None)
                    if ts.tzinfo
                    else ts.replace(second=0)
                )
                minute_start = check_ts
                minute_end = check_ts.replace(second=59)
                existing = (
                    await session.execute(
                        select(Contact).where(
                            and_(
                                Contact.call == data["call"].upper(),
                                Contact.timestamp >= minute_start,
                                Contact.timestamp <= minute_end,
                            )
                        )
                    )
                ).scalar_one_or_none()
                if existing:
                    is_dup = True
        if is_dup:
            duplicates += 1
        else:
            new_records.append((data, record))
    return new_records, duplicates, skipped


def _extract_raw_header(content: str) -> str:
    """Extract everything before <eoh> (case-insensitive) as raw header text."""
    match = re.search(r"<eoh>", content, re.IGNORECASE)
    if match:
        return content[: match.start()].strip()
    return ""


async def _parse_adif_upload(file: UploadFile):
    content = (await file.read()).decode("utf-8", errors="replace")
    raw_header = _extract_raw_header(content)
    doc = adi.loads(content)
    return doc.get("RECORDS", []), doc.get("HEADER", {}), raw_header


@router.post("/import/preview")
async def preview_import_adif(
    file: UploadFile, session: AsyncSession = Depends(get_session)
):
    records, file_header, raw_header = await _parse_adif_upload(file)
    template, separator = await _fetch_comment_settings(session)
    new_records, duplicate_count, skipped_count = await _classify_import_records(
        records, session, template, separator
    )

    contacts = []
    for data, raw_record in new_records:
        contact_data = {
            "id": 0,
            "uuid": data.get("uuid"),
            "call": data.get("call", ""),
            "freq": data.get("freq"),
            "mode": data.get("mode"),
            "rst_sent": data.get("rst_sent"),
            "rst_recv": data.get("rst_recv"),
            "pota_park": data.get("pota_park"),
            "name": data.get("name"),
            "qth": data.get("qth"),
            "state": data.get("state"),
            "country": data.get("country"),
            "dxcc": data.get("dxcc"),
            "grid": data.get("grid"),
            "skcc": data.get("skcc"),
            "skcc_exch": bool(data.get("skcc_exch")),
            "comments": data.get("comments"),
            "notes": data.get("notes"),
            "timestamp": data.get("timestamp", datetime.now(timezone.utc)).isoformat()
            if data.get("timestamp")
            else None,
            "updated_at": None,
            "adif_line": record_to_adif_line(raw_record),
        }
        contacts.append(contact_data)

    return {
        "contacts": contacts,
        "total": len(records),
        "new_count": len(new_records),
        "duplicate_count": duplicate_count,
        "skipped_count": skipped_count,
        "header": file_header,
        "header_raw": raw_header,
    }


@router.post("/import")
async def import_adif(file: UploadFile, session: AsyncSession = Depends(get_session)):
    records, _header, _raw = await _parse_adif_upload(file)
    template, separator = await _fetch_comment_settings(session)
    new_records, duplicates, skipped = await _classify_import_records(
        records, session, template, separator
    )

    for data, _raw in new_records:
        contact = Contact(**data)
        session.add(contact)

    await session.commit()
    return {"imported": len(new_records), "skipped": skipped, "duplicates": duplicates}
