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

from guidebook.db import META_DB_PATH, Setting, db_manager, get_session

logger = logging.getLogger("guidebook")

router = APIRouter(prefix="/api/query", tags=["query"])


async def _download_filename(session: AsyncSession, ext: str) -> str:
    from datetime import datetime, timezone

    db_name = db_manager.db_name or "guidebook"
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    return f"{db_name}_query_{ts}.{ext}"


async def _check_enabled(session: AsyncSession) -> None:
    row = (
        await session.execute(select(Setting).where(Setting.key == "sql_query_enabled"))
    ).scalar_one_or_none()
    if not row or row.value != "true":
        raise HTTPException(status_code=403, detail="SQL query is disabled")


ALLOWED_TABLES = {"records", "notifications"}
META_ALLOWED_TABLES = {"cache"}
MAX_ROWS = 10000
QUERY_TIMEOUT_OPS = 1_000_000  # SQLite VM operations before abort


def _authorizer(action, arg1, arg2, db_name, trigger):
    """SQLite authorizer: allows reading logbook tables and attached meta tables."""
    if action == sqlite3.SQLITE_SELECT:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_READ:
        if db_name == "meta" and arg1 in META_ALLOWED_TABLES:
            return sqlite3.SQLITE_OK
        if (db_name == "main" or db_name is None) and arg1 in ALLOWED_TABLES:
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_FUNCTION:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_ATTACH:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def _execute_query(
    db_path: str, sql: str, limit: int | None = MAX_ROWS
) -> tuple[list[str], list[list]]:
    """Execute a read-only query against logbook + attached global DB."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        conn.set_authorizer(_authorizer)
        # Attach global database for cross-DB queries
        if META_DB_PATH.exists():
            conn.execute(f"ATTACH DATABASE 'file:{META_DB_PATH}?mode=ro' AS meta")
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


@router.get("/schema")
async def get_schema(session: AsyncSession = Depends(get_session)):
    """Return schema for all allowed tables (logbook + meta)."""
    await _check_enabled(session)
    if not db_manager.db_path:
        raise HTTPException(status_code=503, detail="No logbook is currently open")

    tables = {}
    conn = sqlite3.connect(f"file:{db_manager.db_path}?mode=ro", uri=True)
    try:
        for table in sorted(ALLOWED_TABLES):
            cursor = conn.execute(f"PRAGMA table_info('{table}')")
            cols = []
            for row in cursor.fetchall():
                cols.append(
                    {
                        "name": row[1],
                        "type": row[2],
                        "notnull": bool(row[3]),
                        "pk": bool(row[5]),
                    }
                )
            tables[table] = cols
    finally:
        conn.close()

    # Add global database tables
    if META_DB_PATH.exists():
        meta_conn = sqlite3.connect(f"file:{META_DB_PATH}?mode=ro", uri=True)
        try:
            for table in sorted(META_ALLOWED_TABLES):
                cursor = meta_conn.execute(f"PRAGMA table_info('{table}')")
                cols = []
                for row in cursor.fetchall():
                    cols.append(
                        {
                            "name": row[1],
                            "type": row[2],
                            "notnull": bool(row[3]),
                            "pk": bool(row[5]),
                        }
                    )
                if cols:
                    tables[f"meta.{table}"] = cols
        finally:
            meta_conn.close()

    return {"tables": tables}


@router.get("/")
async def run_query(
    sql: str = Query(..., description="SQL SELECT statement"),
    session: AsyncSession = Depends(get_session),
):
    """Execute a read-only SQL query against the records table."""
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
                detail="Access denied: query references a table that is not allowed",
            )
        if "interrupted" in str(e).lower():
            raise HTTPException(status_code=408, detail="Query timed out")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    truncated = len(rows) == MAX_ROWS
    return {
        "columns": columns,
        "rows": rows,
        "count": len(rows),
        "truncated": truncated,
    }


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
                detail="Access denied: query references a table that is not allowed",
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
        headers={
            "Content-Disposition": f"attachment; filename={await _download_filename(session, 'csv')}"
        },
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
                detail="Access denied: query references a table that is not allowed",
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
        headers={
            "Content-Disposition": f"inline; filename={await _download_filename(session, 'json')}"
        },
    )
