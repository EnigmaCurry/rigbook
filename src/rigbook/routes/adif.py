from datetime import datetime, timezone
from io import StringIO

from adif_file import adi
from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from rigbook.db import Contact, Setting, get_session

router = APIRouter(prefix="/api/adif", tags=["adif"])


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
    if c.grid:
        record["GRIDSQUARE"] = c.grid
    if c.pota_park:
        record["POTA_REF"] = c.pota_park
    if c.skcc is not None:
        record["SKCC"] = str(c.skcc)
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
    data["grid"] = record.get("GRIDSQUARE")
    data["pota_park"] = record.get("POTA_REF")
    skcc = record.get("SKCC")
    if skcc:
        data["skcc"] = skcc
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


@router.get("/export")
async def export_adif(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Contact).order_by(Contact.timestamp.asc())
    )
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

    callsign_row = (await session.execute(
        select(Setting).where(Setting.key == "my_callsign")
    )).scalar_one_or_none()
    callsign = callsign_row.value if callsign_row and callsign_row.value else "rigbook"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H%M%Sz")
    filename = f"{callsign} - {ts}.adi"

    return StreamingResponse(
        StringIO(output),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
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
            existing = (await session.execute(
                select(Contact).where(Contact.uuid == record_uuid)
            )).scalar_one_or_none()
            if existing:
                duplicates += 1
                continue
        else:
            # Fall back to call + timestamp dedup (ignore seconds)
            ts = data.get("timestamp")
            if ts:
                check_ts = ts.replace(second=0, tzinfo=None) if ts.tzinfo else ts.replace(second=0)
                minute_start = check_ts
                minute_end = check_ts.replace(second=59)
                existing = (await session.execute(
                    select(Contact).where(and_(
                        Contact.call == data["call"].upper(),
                        Contact.timestamp >= minute_start,
                        Contact.timestamp <= minute_end,
                    ))
                )).scalar_one_or_none()
                if existing:
                    duplicates += 1
                    continue
        contact = Contact(**data)
        session.add(contact)
        imported += 1

    await session.commit()
    return {"imported": imported, "skipped": skipped, "duplicates": duplicates}
