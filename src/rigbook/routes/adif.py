from datetime import datetime, timezone
from io import StringIO
from typing import Optional

from adif_file import adi
from fastapi import APIRouter, Depends, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, cast, Float, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from rigbook.db import Contact, Setting, get_session
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


def contact_to_adif_record(c: Contact) -> dict:
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
    if c.country:
        record["COUNTRY"] = c.country
    if c.dxcc is not None:
        record["DXCC"] = str(c.dxcc)
    if c.grid:
        record["GRIDSQUARE"] = c.grid
    if c.pota_park:
        record["POTA_REF"] = c.pota_park
    if c.skcc is not None:
        record["SKCC"] = str(c.skcc)
    if c.skcc_exch:
        record["APP_RIGBOOK_SKCC_EXCH"] = "Y"
    if c.comments:
        record["COMMENT"] = c.comments
    if c.notes:
        record["NOTES"] = c.notes
    if c.uuid:
        record["APP_RIGBOOK_UUID"] = c.uuid
    return record


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

    return {
        "contacts": [ContactResponse.model_validate(c).model_dump() for c in contacts],
        "total": total,
        "included": included,
        "excluded": total - included,
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

    doc = {
        "HEADER": {
            "ADIF_VER": "3.1.4",
            "PROGRAMID": "Rigbook",
            "PROGRAMVERSION": "0.1.0",
        },
        "RECORDS": [contact_to_adif_record(c) for c in contacts],
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


@router.post("/import")
async def import_adif(file: UploadFile, session: AsyncSession = Depends(get_session)):
    content = (await file.read()).decode("utf-8", errors="replace")
    doc = adi.loads(content)
    records = doc.get("RECORDS", [])

    imported = 0
    skipped = 0
    duplicates = 0
    for record in records:
        data = adif_record_to_contact_dict(record)
        if not data.get("call"):
            skipped += 1
            continue
        # Dedup by UUID first
        record_uuid = data.get("uuid")
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
                    duplicates += 1
                    continue
        contact = Contact(**data)
        session.add(contact)
        imported += 1

    await session.commit()
    return {"imported": imported, "skipped": skipped, "duplicates": duplicates}
