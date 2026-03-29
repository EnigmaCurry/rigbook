import csv
import io
import logging
import sqlite3

import json as json_mod

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from rigbook.db import Setting, db_manager, get_session

logger = logging.getLogger("rigbook")

router = APIRouter(prefix="/api/query", tags=["query"])


async def _download_filename(session: AsyncSession, ext: str) -> str:
    from datetime import datetime, timezone

    row = (
        await session.execute(
            select(Setting).where(Setting.key == "my_callsign")
        )
    ).scalar_one_or_none()
    callsign = (row.value or "").strip().upper().replace("/", "-") if row else ""
    db_name = db_manager.db_name or "rigbook"
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    parts = [p for p in [callsign, db_name, "query", ts] if p]
    return "_".join(parts) + f".{ext}"


async def _check_enabled(session: AsyncSession) -> None:
    row = (
        await session.execute(
            select(Setting).where(Setting.key == "sql_query_enabled")
        )
    ).scalar_one_or_none()
    if not row or row.value != "true":
        raise HTTPException(status_code=403, detail="SQL query is disabled")

ALLOWED_TABLES = {"contacts", "notifications", "pota_programs", "pota_locations", "pota_parks"}
MAX_ROWS = 10000
QUERY_TIMEOUT_OPS = 1_000_000  # SQLite VM operations before abort


def _authorizer(action, arg1, arg2, db_name, trigger):
    """SQLite authorizer that only allows reading the contacts table."""
    # Allow SELECT statements
    if action == sqlite3.SQLITE_SELECT:
        return sqlite3.SQLITE_OK
    # Allow reading from contacts table only
    if action == sqlite3.SQLITE_READ:
        if arg1 in ALLOWED_TABLES:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY
    # Allow function calls (count, sum, etc.)
    if action == sqlite3.SQLITE_FUNCTION:
        return sqlite3.SQLITE_OK
    # Deny everything else
    return sqlite3.SQLITE_DENY


def _execute_query(
    db_path: str, sql: str, limit: int | None = MAX_ROWS
) -> tuple[list[str], list[list]]:
    """Execute a read-only query against contacts table, returns (columns, rows)."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        conn.set_authorizer(_authorizer)
        ops = [0]

        def progress():
            ops[0] += 1
            if ops[0] > QUERY_TIMEOUT_OPS:
                return 1  # non-zero aborts
            return 0

        conn.set_progress_handler(progress, 1000)
        cursor = conn.execute(sql)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchmany(limit) if limit else cursor.fetchall()
        return columns, [list(row) for row in rows]
    finally:
        conn.close()


@router.get("/")
async def run_query(
    sql: str = Query(..., description="SQL SELECT statement"),
    session: AsyncSession = Depends(get_session),
):
    """Execute a read-only SQL query against the contacts table."""
    await _check_enabled(session)
    if not db_manager.db_path:
        raise HTTPException(status_code=503, detail="No logbook is currently open")

    sql = sql.strip()
    if not sql:
        raise HTTPException(status_code=400, detail="Empty query")

    try:
        columns, rows = _execute_query(str(db_manager.db_path), sql)
    except sqlite3.OperationalError as e:
        if "not authorized" in str(e).lower():
            raise HTTPException(
                status_code=403,
                detail="Access denied: only the contacts table may be queried",
            )
        if "interrupted" in str(e).lower():
            raise HTTPException(status_code=408, detail="Query timed out")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    truncated = len(rows) == MAX_ROWS
    return {"columns": columns, "rows": rows, "count": len(rows), "truncated": truncated}


@router.get("/csv")
async def run_query_csv(
    sql: str = Query(..., description="SQL SELECT statement"),
    session: AsyncSession = Depends(get_session),
):
    """Execute a read-only SQL query and return results as CSV."""
    await _check_enabled(session)
    if not db_manager.db_path:
        raise HTTPException(status_code=503, detail="No logbook is currently open")

    sql = sql.strip()
    if not sql:
        raise HTTPException(status_code=400, detail="Empty query")

    try:
        columns, rows = _execute_query(str(db_manager.db_path), sql, limit=None)
    except sqlite3.OperationalError as e:
        if "not authorized" in str(e).lower():
            raise HTTPException(
                status_code=403,
                detail="Access denied: only the contacts table may be queried",
            )
        if "interrupted" in str(e).lower():
            raise HTTPException(status_code=408, detail="Query timed out")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(columns)
    writer.writerows(rows)
    buf.seek(0)

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={await _download_filename(session, 'csv')}"},
    )


@router.get("/json")
async def run_query_json(
    sql: str = Query(..., description="SQL SELECT statement"),
    session: AsyncSession = Depends(get_session),
):
    """Execute a read-only SQL query and return results as a JSON file download."""
    await _check_enabled(session)
    if not db_manager.db_path:
        raise HTTPException(status_code=503, detail="No logbook is currently open")

    sql = sql.strip()
    if not sql:
        raise HTTPException(status_code=400, detail="Empty query")

    try:
        columns, rows = _execute_query(str(db_manager.db_path), sql, limit=None)
    except sqlite3.OperationalError as e:
        if "not authorized" in str(e).lower():
            raise HTTPException(
                status_code=403,
                detail="Access denied: only the contacts table may be queried",
            )
        if "interrupted" in str(e).lower():
            raise HTTPException(status_code=408, detail="Query timed out")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    data = [dict(zip(columns, row)) for row in rows]
    content = json_mod.dumps(data, indent=2)

    return StreamingResponse(
        iter([content]),
        media_type="application/json",
        headers={"Content-Disposition": f"inline; filename={await _download_filename(session, 'json')}"},
    )
