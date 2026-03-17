import asyncio
import json
import logging
import time
import xml.etree.ElementTree as ET

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from rigbook.db import Cache, Setting, get_session

logger = logging.getLogger("rigbook")

_call_locks: dict[str, asyncio.Lock] = {}

router = APIRouter(prefix="/api/qrz", tags=["qrz"])

QRZ_URL = "https://xmldata.qrz.com/xml/current/"
CACHE_TTL = 86400  # 24 hours
NAMESPACE = "qrz"

_session_key: str | None = None


async def _get_credentials(session: AsyncSession) -> tuple[str, str]:
    """Return (username, api_key) from settings. Username defaults to my_callsign."""
    result = await session.execute(
        select(Setting).where(
            Setting.key.in_(["qrz_password", "qrz_username", "my_callsign"])
        )
    )
    api_key = ""
    username = ""
    callsign = ""
    for s in result.scalars():
        if s.key == "qrz_password" and s.value:
            api_key = s.value
        if s.key == "qrz_username" and s.value:
            username = s.value
        if s.key == "my_callsign" and s.value:
            callsign = s.value
    # Use explicit QRZ username, fall back to my_callsign
    return username or callsign, api_key


async def _get_cached(call: str, session: AsyncSession) -> dict | None:
    result = await session.execute(
        select(Cache).where(
            Cache.namespace == NAMESPACE,
            Cache.key == call,
            Cache.expires_at > time.time(),
        )
    )
    row = result.scalar_one_or_none()
    if row and row.value:
        logger.debug("QRZ cache hit: %s", call)
        return json.loads(row.value)
    return None


async def _store_cached(call: str, data: dict, session: AsyncSession):
    # Remove old entry
    await session.execute(
        delete(Cache).where(Cache.namespace == NAMESPACE, Cache.key == call)
    )
    session.add(
        Cache(
            namespace=NAMESPACE,
            key=call,
            value=json.dumps(data),
            expires_at=time.time() + CACHE_TTL,
        )
    )
    await session.commit()


async def _login(username: str, api_key: str) -> str | None:
    global _session_key
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(
                QRZ_URL,
                params={
                    "username": username,
                    "password": api_key,
                    "agent": "Rigbook/0.1",
                },
            )
            root = ET.fromstring(res.text)
            ns = {"q": "http://xmldata.qrz.com"}
            key_el = root.find(".//q:Session/q:Key", ns)
            if key_el is not None and key_el.text:
                _session_key = key_el.text
                logger.info("QRZ login successful for %s", username)
                return _session_key
            error_el = root.find(".//q:Session/q:Error", ns)
            if error_el is not None:
                logger.warning("QRZ login failed: %s", error_el.text)
    except Exception as e:
        logger.warning("QRZ login error: %s", e)
    return None


# Sentinel: QRZ responded successfully but callsign doesn't exist (cacheable)
_NOT_FOUND = "NOT_FOUND"
# Sentinel: request failed due to HTTP/network error (not cacheable, should retry)
_FETCH_ERROR = "FETCH_ERROR"


async def _fetch_callsign(
    callsign: str, username: str, api_key: str
) -> dict | str:
    """Return a dict on success, _NOT_FOUND if QRZ says unknown, _FETCH_ERROR on failure."""
    global _session_key
    logger.info("QRZ fetching: %s", callsign)

    if not _session_key:
        await _login(username, api_key)
    if not _session_key:
        return _FETCH_ERROR

    for _attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                res = await client.get(
                    QRZ_URL,
                    params={"s": _session_key, "callsign": callsign},
                )
                res.raise_for_status()
                root = ET.fromstring(res.text)
                ns = {"q": "http://xmldata.qrz.com"}

                error_el = root.find(".//q:Session/q:Error", ns)
                if error_el is not None:
                    err = error_el.text or ""
                    if "session" in err.lower() or "invalid" in err.lower():
                        _session_key = None
                        await _login(username, api_key)
                        if not _session_key:
                            return _FETCH_ERROR
                        continue
                    # QRZ responded but callsign not found
                    logger.debug("QRZ lookup error for %s: %s", callsign, err)
                    return _NOT_FOUND

                cs = root.find(".//q:Callsign", ns)
                if cs is None:
                    return _NOT_FOUND

                def get(tag):
                    el = cs.find(f"q:{tag}", ns)
                    return el.text if el is not None else None

                fname = get("fname") or ""
                lname = get("name") or ""

                return {
                    "call": get("call"),
                    "name": f"{fname} {lname}".strip(),
                    "qth": get("addr2"),
                    "state": get("state"),
                    "country": get("country"),
                    "country_code": get("ccode"),
                    "grid": get("grid"),
                }
        except Exception as e:
            logger.warning("QRZ fetch error for %s: %s", callsign, e)
            return _FETCH_ERROR

    return _FETCH_ERROR


@router.get("/lookup/{callsign}")
async def qrz_lookup(callsign: str, session: AsyncSession = Depends(get_session)):
    call_upper = callsign.upper().strip()

    # Check DB cache (fast path, no lock needed)
    cached = await _get_cached(call_upper, session)
    if cached:
        return cached

    # Serialize concurrent fetches for the same callsign
    if call_upper not in _call_locks:
        _call_locks[call_upper] = asyncio.Lock()
    async with _call_locks[call_upper]:
        # Re-check cache after acquiring lock
        cached = await _get_cached(call_upper, session)
        if cached:
            return cached

        username, api_key = await _get_credentials(session)
        if not username:
            return {"error": "Set My Callsign in Settings (used as QRZ username)"}
        if not api_key:
            return {"error": "Set QRZ Password in Settings"}

        result = await _fetch_callsign(call_upper, username, api_key)
        if result == _FETCH_ERROR:
            # Don't cache — allow retry on next request
            return {"error": "QRZ lookup failed"}
        if result == _NOT_FOUND:
            not_found = {"error": "Callsign not found"}
            await _store_cached(call_upper, not_found, session)
            return not_found

        await _store_cached(call_upper, result, session)
        return result


@router.get("/status")
async def qrz_status(session: AsyncSession = Depends(get_session)):
    global _session_key
    username, api_key = await _get_credentials(session)
    if not username:
        return {"ok": False, "error": "No callsign configured"}
    if not api_key:
        return {"ok": False, "error": "No QRZ password configured"}
    # Force a fresh login to verify credentials
    _session_key = None
    key = await _login(username, api_key)
    if key:
        return {"ok": True, "username": username}
    return {"ok": False, "error": "Login failed — check password"}


@router.delete("/cache")
async def clear_cache(session: AsyncSession = Depends(get_session)):
    await session.execute(delete(Cache).where(Cache.namespace == NAMESPACE))
    await session.commit()
    return {"ok": True}
