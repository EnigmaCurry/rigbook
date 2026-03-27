from datetime import datetime, timezone
import json
import logging
import re
from importlib.metadata import version as pkg_version
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

logger = logging.getLogger("rigbook")

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


def _normalize_freq(khz_val: str, mhz_val: str) -> bool:
    """Check if a KHz value and MHz value represent the same frequency."""
    try:
        return abs(float(khz_val) - float(mhz_val) * 1000) < 0.1
    except (ValueError, TypeError):
        return False


def _segment_matches(segment: str, label: str, value: str, field: str = "") -> bool:
    """Check if a comment segment matches 'Label: value' or 'Label value'."""
    s = segment.strip()
    for fmt in (f"{label}: ", f"{label} "):
        if s.startswith(fmt):
            seg_val = s[len(fmt):]
            if seg_val == value:
                return True
            # Frequency: comment has KHz, ADIF field has MHz
            if field == "freq" and _normalize_freq(seg_val, value):
                return True
    return False


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

    if not template_fields:
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
        f = entry.get("field", "")
        val = field_values.get(f, "")
        if val:
            label = entry.get("label", entry["field"])
            expected.append({"label": label, "val": val, "field": f})

    # Check if entire comment matches a single expected segment (no separator)
    if expected and any(
        _segment_matches(comment, e["label"], e["val"], e["field"])
        for e in expected
    ):
        return ""

    if padded not in comment:
        return comment

    parts = comment.split(padded)
    if len(parts) <= 1:
        return comment

    # Strip matching leading segments
    strip_count = 0
    for i, seg in enumerate(parts):
        if i < len(expected) and _segment_matches(
            seg, expected[i]["label"], expected[i]["val"], expected[i]["field"]
        ):
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
    template_matches = 0
    field_map_keys = {
        "call", "freq", "mode", "rst_sent", "rst_recv", "name",
        "qth", "state", "country", "grid", "pota_park", "skcc",
    }
    for c in contacts:
        data = ContactResponse.model_validate(c).model_dump()
        adif_rec = contact_to_adif_record(
            c,
            comment_template=comment_template or None,
            comment_separator=comment_separator,
        )
        data["adif_line"] = record_to_adif_line(adif_rec)
        previews.append(data)
        if comment_template:
            for entry in comment_template:
                f = entry.get("field")
                if f in field_map_keys and getattr(c, f, None):
                    template_matches += 1
                    break

    header = {
        "ADIF_VER": "3.1.4",
        "PROGRAMID": "Rigbook",
        "PROGRAMVERSION": pkg_version("rigbook"),
    }

    return {
        "contacts": previews,
        "total": total,
        "included": included,
        "excluded": total - included,
        "template_matches": template_matches,
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
            "PROGRAMVERSION": pkg_version("rigbook"),
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


def _validate_import_record(
    record: dict, template_fields: list[dict], separator: str
) -> list[dict]:
    """Check for mismatches between comment-parsed values and normalized fields.

    Only validates the leading prefix segments that match the template pattern
    (Label: value). Free-form text after the prefix is ignored.

    Returns list of warning dicts with keys:
    - field: contact field name (e.g. "skcc")
    - label: display label (e.g. "SKCC")
    - comment_val: value parsed from comment
    - field_val: value from normalized ADIF field (may be empty)
    - message: human-readable warning text
    """
    comment = record.get("COMMENT", "")
    if not comment or not template_fields:
        return []

    field_to_adif = {
        "call": "CALL",
        "freq": "FREQ",
        "mode": "MODE",
        "rst_sent": "RST_SENT",
        "rst_recv": "RST_RCVD",
        "name": "NAME",
        "qth": "QTH",
        "state": "STATE",
        "country": "COUNTRY",
        "grid": "GRIDSQUARE",
        "pota_park": "POTA_REF",
        "skcc": "SKCC",
    }

    fmt_sep = record.get("APP_RIGBOOK_COMMENT_FMT")
    sep = (fmt_sep or separator or "|").strip()
    padded = f" {sep} "

    # Build expected "Label: value" for each template field from normalized fields
    expected = []
    for entry in template_fields:
        f = entry.get("field", "")
        adif_key = field_to_adif.get(f, "")
        val = record.get(adif_key, "") if adif_key else ""
        label = entry.get("label", f)
        if val:
            expected.append({"label": label, "field": f, "val": val})

    # Parse comment into segments (same way strip does)
    if padded in comment:
        parts = comment.split(padded)
    else:
        parts = [comment]

    # Walk through parts in parallel with expected entries.
    # Only validate segments that align with expected prefix positions.
    prefix_values = {}
    for i, exp in enumerate(expected):
        if i >= len(parts):
            break
        part = parts[i].strip()
        # Parse "Label: value" or "Label value"
        if ": " in part:
            lbl, _, val = part.partition(": ")
        elif part.startswith(exp["label"] + " "):
            lbl = exp["label"]
            val = part[len(exp["label"]) + 1:]
        else:
            break
        if lbl.strip() != exp["label"]:
            break
        # This segment aligns with expected position — check if value matches
        if _segment_matches(part, exp["label"], exp["val"], exp["field"]):
            continue  # clean match
        if val.strip() != exp["val"]:
            prefix_values[exp["label"]] = {
                "field": exp["field"],
                "comment_val": val.strip(),
                "field_val": exp["val"],
            }

    warnings = []
    for label, info in prefix_values.items():
        warnings.append({
            "field": info["field"],
            "label": label,
            "comment_val": info["comment_val"],
            "field_val": info["field_val"],
            "message": f"{label}: comment has '{info['comment_val']}'"
            f" but field has '{info['field_val']}'",
        })

    # Also check for single-segment comments (no separator) that match a template
    if not warnings and len(parts) == 1:
        lbl = None
        val = None
        if ": " in comment:
            lbl, _, val = comment.partition(": ")
        for entry in template_fields:
            label = entry.get("label", entry.get("field", ""))
            field = entry.get("field", "")
            # Try "Label: value" or "Label value"
            if lbl and lbl.strip() == label:
                val = val.strip() if val else ""
            elif comment.strip().startswith(label + " "):
                val = comment.strip()[len(label) + 1:]
            else:
                continue
            adif_key = field_to_adif.get(field, "")
            adif_val = record.get(adif_key, "") if adif_key else ""
            vals_match = val == adif_val
            if not vals_match and field == "freq":
                vals_match = _normalize_freq(val, adif_val)
            if adif_val and not vals_match:
                warnings.append({
                    "field": field,
                    "label": label,
                    "comment_val": val,
                    "field_val": adif_val,
                    "message": f"{label}: comment has '{val}'"
                    f" but field has '{adif_val}'",
                })
            elif not adif_val and val:
                warnings.append({
                    "field": field,
                    "label": label,
                    "comment_val": val,
                    "field_val": "",
                    "message": f"{label}: '{val}' found in comment"
                    " but no normalized field",
                })
    # Field-specific validations
    skcc_val = record.get("SKCC", "")
    if skcc_val:
        if " " in skcc_val.strip():
            warnings.append({
                "field": "skcc",
                "label": "SKCC",
                "comment_val": "",
                "field_val": skcc_val,
                "message": f"SKCC: '{skcc_val}' contains spaces"
                " — should be a single value like '2240S'",
            })
        elif not skcc_val.strip()[0].isdigit():
            warnings.append({
                "field": "skcc",
                "label": "SKCC",
                "comment_val": "",
                "field_val": skcc_val,
                "message": f"SKCC: '{skcc_val}' does not start with a digit"
                " — should be a number like '2240S'",
            })

    return warnings


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
    template_matches = 0
    for record in records:
        data = adif_record_to_contact_dict(record)
        data["_original_comment"] = data.get("comments")
        data["_comment_stripped"] = False
        if data.get("comments") and template:
            original = data["comments"]
            data["comments"] = strip_comment_prefix(
                data["comments"], record, template, separator
            )
            if data["comments"] != original:
                data["_comment_stripped"] = True
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
            if data.get("_comment_stripped"):
                template_matches += 1
            new_records.append((data, record))
    return new_records, duplicates, skipped, template_matches


def _extract_raw_header(content: str) -> str:
    """Extract everything before <eoh> (case-insensitive) as raw header text."""
    match = re.search(r"<eoh>", content, re.IGNORECASE)
    if match:
        return content[: match.start()].strip()
    return ""


ADIF_FIELD_MAP = {
    "CALL": "call",
    "FREQ": "freq",
    "MODE": "mode",
    "RST_SENT": "rst_sent",
    "RST_RCVD": "rst_recv",
    "NAME": "name",
    "QTH": "qth",
    "STATE": "state",
    "COUNTRY": "country",
    "GRIDSQUARE": "grid",
    "POTA_REF": "pota_park",
    "SKCC": "skcc",
}

DEFAULT_LABELS = {
    "call": "Call",
    "freq": "Freq",
    "mode": "Mode",
    "rst_sent": "RST Sent",
    "rst_recv": "RST Recv",
    "name": "Name",
    "qth": "QTH",
    "state": "State",
    "country": "Country",
    "grid": "Grid",
    "pota_park": "POTA",
    "skcc": "SKCC",
}


def _suggest_comment_template(records: list[dict]) -> dict:
    """Analyze comments across records to detect a plausible template and separator."""
    comments = [r.get("COMMENT", "") for r in records if r.get("COMMENT")]
    if not comments:
        return {"separator": "|", "fields": []}

    # Try candidate separators, score each by how well they explain the data
    candidates = ["|", "-", "/", ",", ";", "~"]
    best_sep = "|"
    best_score = -1
    best_fields = []

    for sep in candidates:
        padded = f" {sep} "
        # Count how many comments contain this separator
        matching = [c for c in comments if padded in c]
        if not matching:
            continue

        # For each comment, split and look for "Label: value" patterns
        # that match known ADIF fields in the same record
        label_to_field = {}  # maps detected label -> (contact_field, match_count)
        for record in records:
            comment = record.get("COMMENT", "")
            if padded not in comment:
                continue
            parts = comment.split(padded)
            for part in parts:
                part = part.strip()
                if ": " in part:
                    label, _, val = part.partition(": ")
                else:
                    continue
                label = label.strip()
                val = val.strip()
                if not val:
                    continue
                # Check if this value matches any ADIF field in the record
                for adif_key, contact_field in ADIF_FIELD_MAP.items():
                    record_val = record.get(adif_key, "")
                    if not record_val:
                        continue
                    matched = record_val == val
                    # Freq: comment may have KHz, ADIF has MHz
                    if not matched and contact_field == "freq":
                        matched = _normalize_freq(val, record_val)
                    if matched:
                        key = (label, contact_field)
                        label_to_field[key] = label_to_field.get(key, 0) + 1

        # Score: number of field matches
        score = sum(label_to_field.values())
        if score > best_score:
            best_score = score
            best_sep = sep
            # Deduplicate: pick the best label for each field
            field_labels = {}
            for (label, field), count in label_to_field.items():
                if field not in field_labels or count > field_labels[field][1]:
                    field_labels[field] = (label, count)
            best_fields = [
                {"field": field, "label": label}
                for field, (label, _count) in sorted(
                    field_labels.items(), key=lambda x: -x[1][1]
                )
            ]

    return {"separator": best_sep, "fields": best_fields}


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
    new_records, duplicate_count, skipped_count, tpl_matches = (
        await _classify_import_records(records, session, template, separator)
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
            "original_comment": data.get("_original_comment"),
            "notes": data.get("notes"),
            "timestamp": data.get("timestamp", datetime.now(timezone.utc)).isoformat()
            if data.get("timestamp")
            else None,
            "updated_at": None,
            "adif_line": record_to_adif_line(raw_record),
            "warnings": _validate_import_record(raw_record, template, separator),
        }
        contacts.append(contact_data)

    return {
        "contacts": contacts,
        "total": len(records),
        "new_count": len(new_records),
        "duplicate_count": duplicate_count,
        "skipped_count": skipped_count,
        "template_matches": tpl_matches,
        "header": file_header,
        "header_raw": raw_header,
    }


@router.post("/import/suggest-template")
async def suggest_template(file: UploadFile):
    records, _header, _raw = await _parse_adif_upload(file)
    return _suggest_comment_template(records)


@router.post("/import")
async def import_adif(file: UploadFile, session: AsyncSession = Depends(get_session)):
    records, _header, _raw = await _parse_adif_upload(file)
    template, separator = await _fetch_comment_settings(session)
    new_records, duplicates, skipped, _tpl = await _classify_import_records(
        records, session, template, separator
    )

    for data, _raw_rec in new_records:
        data = {k: v for k, v in data.items() if not k.startswith("_")}
        contact = Contact(**data)
        session.add(contact)

    await session.commit()
    logger.info(
        "ADIF import: %d imported, %d duplicates, %d skipped",
        len(new_records), duplicates, skipped,
    )
    return {"imported": len(new_records), "skipped": skipped, "duplicates": duplicates}


IMPORT_FIELDS = {
    "uuid", "call", "freq", "mode", "rst_sent", "rst_recv", "name", "qth",
    "state", "country", "dxcc", "grid", "pota_park", "skcc", "skcc_exch",
    "comments", "notes",
}


@router.post("/import/confirmed")
async def import_confirmed(
    contacts: list[dict], session: AsyncSession = Depends(get_session)
):
    """Import pre-validated contacts with user corrections applied."""
    imported = 0
    duplicates = 0
    for c in contacts:
        data = {}
        for key in IMPORT_FIELDS:
            if key in c and c[key] is not None and c[key] != "":
                data[key] = c[key]
        if not data.get("call"):
            continue
        if c.get("timestamp"):
            try:
                ts = c["timestamp"]
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if ts.tzinfo is not None:
                    ts = ts.replace(tzinfo=None)
                data["timestamp"] = ts
            except (ValueError, TypeError):
                pass
        # Dedup by UUID
        record_uuid = c.get("uuid")
        if record_uuid:
            existing = (
                await session.execute(
                    select(Contact).where(Contact.uuid == record_uuid)
                )
            ).scalar_one_or_none()
            if existing:
                duplicates += 1
                continue
        else:
            # Fall back to call + timestamp dedup (ignore seconds)
            ts = data.get("timestamp")
            if ts:
                check_ts = (
                    ts.replace(second=0, tzinfo=None)
                    if ts.tzinfo
                    else ts.replace(second=0)
                )
                existing = (
                    await session.execute(
                        select(Contact).where(
                            and_(
                                Contact.call == data["call"].upper(),
                                Contact.timestamp >= check_ts,
                                Contact.timestamp <= check_ts.replace(second=59),
                            )
                        )
                    )
                ).scalar_one_or_none()
                if existing:
                    duplicates += 1
                    continue
        contact = Contact(**data)
        session.add(contact)
        imported += 1

    await session.commit()
    logger.info(
        "ADIF confirmed import: %d imported, %d duplicates",
        imported, duplicates,
    )
    return {"imported": imported, "duplicates": duplicates}
