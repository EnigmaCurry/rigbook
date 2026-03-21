"""RBN and HamAlert spot feed integration.

Manages persistent telnet connections to the Reverse Beacon Network and
HamAlert, caching received spots in memory with a configurable TTL.

RBN line parsing based on skcc_skimmer.py by Mark J Glenn (mark@k7mjg.com),
licensed under the MIT License. Original source:
https://github.com/k7mjg/skcc_skimmer
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time as _time
from dataclasses import dataclass, field

from sqlalchemy import select

from rigbook.db import Setting, async_session

logger = logging.getLogger("rigbook.spots")

# ---------------------------------------------------------------------------
# Band mapping
# ---------------------------------------------------------------------------

_BAND_RANGES: list[tuple[str, float, float]] = [
    ("160m", 1800.0, 2000.0),
    ("80m", 3500.0, 4000.0),
    ("60m", 5330.0, 5410.0),
    ("40m", 7000.0, 7300.0),
    ("30m", 10100.0, 10150.0),
    ("20m", 14000.0, 14350.0),
    ("17m", 18068.0, 18168.0),
    ("15m", 21000.0, 21450.0),
    ("12m", 24890.0, 24990.0),
    ("10m", 28000.0, 29700.0),
    ("6m", 50000.0, 54000.0),
    ("2m", 144000.0, 148000.0),
]


def freq_to_band(freq_khz: float) -> str:
    """Map a frequency in kHz to a band string like '20m'."""
    for band, lo, hi in _BAND_RANGES:
        if lo <= freq_khz <= hi:
            return band
    return ""


# ---------------------------------------------------------------------------
# Parsed spot (transient — used only to pass data from parser to cache)
# ---------------------------------------------------------------------------


@dataclass
class ParsedSpot:
    callsign: str = ""
    frequency: float = 0.0  # kHz
    mode: str = ""
    source: str = ""  # "rbn" or "hamalert"
    spotter: str = ""
    snr: int | None = None
    wpm: int | None = None
    time: str = ""  # UTC time string from spot data
    band: str = ""
    state: str = ""
    comment: str = ""
    wwff_ref: str = ""


# ---------------------------------------------------------------------------
# Aggregate spot entry (what the cache actually stores)
# ---------------------------------------------------------------------------


@dataclass
class AggregateSpot:
    callsign: str
    frequency: float  # kHz
    mode: str
    band: str
    source: str  # source of most recent spot
    spotters: dict[str, float] = field(default_factory=dict)  # spotter -> timestamp
    best_snr: int | None = None
    wpm: int | None = None
    time: str = ""  # most recent spot time
    received_at: float = field(default_factory=_time.time)
    state: str = ""
    comment: str = ""
    wwff_ref: str = ""

    def prune_spotters(self, cutoff: float) -> None:
        """Remove spotters older than cutoff timestamp."""
        self.spotters = {k: v for k, v in self.spotters.items() if v > cutoff}

    def to_dict(self) -> dict:
        spotters_sorted = sorted(self.spotters.keys())
        return {
            "callsign": self.callsign,
            "frequency": self.frequency,
            "mode": self.mode,
            "band": self.band,
            "spotter_count": len(self.spotters),
            "spotters": spotters_sorted,
            "best_snr": self.best_snr,
            "wpm": self.wpm,
            "time": self.time,
            "received_at": self.received_at,
            "source": self.source,
            "state": self.state,
            "comment": self.comment,
            "wwff_ref": self.wwff_ref,
        }


# ---------------------------------------------------------------------------
# In-memory spot cache (aggregate only)
# ---------------------------------------------------------------------------

SPOT_TTL = 600  # 10 minutes


class SpotCache:
    """Stores one AggregateSpot per (callsign, frequency, mode) key."""

    def __init__(self) -> None:
        self._entries: dict[tuple[str, float, str], AggregateSpot] = {}
        self._lock = asyncio.Lock()

    async def add(self, spot: ParsedSpot) -> None:
        key = (spot.callsign, spot.frequency, spot.mode)
        now = _time.time()
        async with self._lock:
            entry = self._entries.get(key)
            if entry:
                # Update existing aggregate
                if spot.spotter:
                    entry.spotters[spot.spotter] = now
                if spot.snr is not None and (
                    entry.best_snr is None or spot.snr > entry.best_snr
                ):
                    entry.best_snr = spot.snr
                entry.received_at = now
                entry.time = spot.time or entry.time
                entry.wpm = spot.wpm or entry.wpm
                entry.source = spot.source
                entry.state = spot.state or entry.state
                entry.comment = spot.comment or entry.comment
                entry.wwff_ref = spot.wwff_ref or entry.wwff_ref
            else:
                # Create new aggregate
                self._entries[key] = AggregateSpot(
                    callsign=spot.callsign,
                    frequency=spot.frequency,
                    mode=spot.mode,
                    band=spot.band,
                    source=spot.source,
                    spotters={spot.spotter: now} if spot.spotter else {},
                    best_snr=spot.snr,
                    wpm=spot.wpm,
                    time=spot.time,
                    received_at=now,
                    state=spot.state,
                    comment=spot.comment,
                    wwff_ref=spot.wwff_ref,
                )

    async def prune(self) -> None:
        cutoff = _time.time() - SPOT_TTL
        async with self._lock:
            # Prune stale spotters from each entry, then remove empty entries
            to_remove = []
            for key, entry in self._entries.items():
                entry.prune_spotters(cutoff)
                if not entry.spotters:
                    to_remove.append(key)
            for key in to_remove:
                del self._entries[key]

    def _live_entries(self, cutoff: float) -> list[AggregateSpot]:
        """Return entries that have at least one non-expired spotter.

        Must be called with self._lock held.
        """
        results = []
        for entry in self._entries.values():
            live_count = sum(1 for t in entry.spotters.values() if t > cutoff)
            if live_count > 0:
                results.append(entry)
        return results

    async def query(
        self,
        *,
        source: str | None = None,
        callsign: str | None = None,
        mode: str | None = None,
        band: str | None = None,
        min_freq: float | None = None,
        max_freq: float | None = None,
        limit: int = 200,
    ) -> list[dict]:
        cutoff = _time.time() - SPOT_TTL
        async with self._lock:
            live = self._live_entries(cutoff)

        if source:
            live = [e for e in live if e.source == source]
        if callsign:
            q = callsign.upper()
            live = [e for e in live if q in e.callsign.upper()]
        if mode:
            live = [e for e in live if e.mode.upper() == mode.upper()]
        if band:
            live = [e for e in live if e.band == band.lower()]
        if min_freq is not None:
            live = [e for e in live if e.frequency >= min_freq]
        if max_freq is not None:
            live = [e for e in live if e.frequency <= max_freq]

        live.sort(key=lambda e: e.received_at, reverse=True)

        # Build dicts with only live spotter counts
        results = []
        for e in live[:limit]:
            d = e.to_dict()
            # Override spotters/count with only non-expired ones
            live_spotters = sorted(k for k, t in e.spotters.items() if t > cutoff)
            d["spotters"] = live_spotters
            d["spotter_count"] = len(live_spotters)
            results.append(d)
        return results

    async def band_summary(self) -> dict[str, int]:
        cutoff = _time.time() - SPOT_TTL
        async with self._lock:
            counts: dict[str, int] = {}
            for e in self._live_entries(cutoff):
                if e.band:
                    counts[e.band] = counts.get(e.band, 0) + 1
            return counts

    async def count(self) -> int:
        cutoff = _time.time() - SPOT_TTL
        async with self._lock:
            return len(self._live_entries(cutoff))

    async def modes(self) -> list[str]:
        """Return sorted list of distinct modes in live entries."""
        cutoff = _time.time() - SPOT_TTL
        async with self._lock:
            return sorted({e.mode for e in self._live_entries(cutoff) if e.mode})

    async def stats(self) -> dict:
        """Cache statistics: callsigns, total spots, average spots per callsign."""
        cutoff = _time.time() - SPOT_TTL
        async with self._lock:
            live = self._live_entries(cutoff)
            total_entries = len(live)
            total_spots = sum(
                sum(1 for t in e.spotters.values() if t > cutoff) for e in live
            )
            callsigns = len({e.callsign for e in live})
            avg_spots = round(total_spots / callsigns, 1) if callsigns else 0
            last_time = max((e.received_at for e in live), default=None)
            return {
                "callsigns": callsigns,
                "entries": total_entries,
                "total_spots": total_spots,
                "avg_spots_per_callsign": avg_spots,
                "last_spot_time": last_time,
            }


# ---------------------------------------------------------------------------
# Feed base class
# ---------------------------------------------------------------------------


class BaseFeed:
    def __init__(self, cache: SpotCache) -> None:
        self.cache = cache
        self._task: asyncio.Task | None = None
        self._connected = False
        self._should_run = False

    @property
    def connected(self) -> bool:
        return self._connected

    async def start(self, **kwargs: object) -> None:
        if self._task and not self._task.done():
            await self.stop()
        self._should_run = True
        self._task = asyncio.create_task(self._run_loop(**kwargs))

    async def stop(self) -> None:
        self._should_run = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._connected = False

    async def _run_loop(self, **kwargs: object) -> None:
        while self._should_run:
            try:
                await self._connect_and_read(**kwargs)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning("%s connection error: %s", self.__class__.__name__, e)
                self._connected = False
            if self._should_run:
                await asyncio.sleep(10)

    async def _connect_and_read(self, **kwargs: object) -> None:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# RBN feed
# ---------------------------------------------------------------------------


class RBNFeed(BaseFeed):
    async def _connect_and_read(self, **kwargs: object) -> None:
        host = str(kwargs.get("host", "telnet.reversebeacon.net"))
        port = int(kwargs.get("port", 7000))  # type: ignore[arg-type]
        callsign = str(kwargs.get("callsign", ""))

        if not callsign:
            logger.warning("RBN feed: no callsign configured, cannot connect")
            await asyncio.sleep(30)
            return

        logger.info("RBN: connecting to %s:%d as %s", host, port, callsign)
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=15
        )

        try:
            # Read login prompt and authenticate
            await asyncio.wait_for(reader.readuntil(b"call: "), timeout=15)
            writer.write(f"{callsign}\r\n".encode("ascii"))
            await writer.drain()
            # Read welcome message
            await asyncio.wait_for(reader.readuntil(b">\r\n"), timeout=15)

            self._connected = True
            logger.info("RBN: connected")

            while self._should_run:
                line_bytes = await asyncio.wait_for(reader.readline(), timeout=120)
                if not line_bytes:
                    logger.info("RBN: connection closed by server")
                    break

                line = line_bytes.rstrip().decode("ascii", errors="replace")
                parsed = self._parse_line(line)
                if parsed:
                    await self.cache.add(parsed)
        finally:
            self._connected = False
            writer.close()
            try:
                await asyncio.wait_for(writer.wait_closed(), timeout=2)
            except Exception:
                pass

    # Regex to parse RBN spot lines:
    # DX de SPOTTER-#:  FREQ  CALLSIGN  MODE  dB  WPM  TYPE  HHMMZ
    _RBN_LINE_RE = re.compile(
        r"^DX de\s+(\S+)-#:\s+"  # spotter
        r"(\d+\.\d+)\s+"  # frequency kHz
        r"(\S+)\s+"  # callsign
        r"(\w+)\s+"  # mode (CW, RTTY, etc.)
        r"(\d+)\s+dB\s+"  # snr
        r"(\d+)\s+WPM\s+"  # wpm
        r"(\S+)\s+"  # type (CQ, BEACON, etc.)
        r"(\d{4}Z)\s*$"  # time
    )

    @staticmethod
    def _parse_line(line: str) -> ParsedSpot | None:
        """Parse an RBN spot line into a Spot object."""
        if not line.startswith("DX de "):
            return None

        m = RBNFeed._RBN_LINE_RE.match(line)
        if not m:
            return None

        spotter, freq_str, callsign, mode, snr_str, wpm_str, spot_type, zulu = (
            m.groups()
        )

        if spot_type == "BEACON":
            return None

        frequency = float(freq_str)
        band = freq_to_band(frequency)

        return ParsedSpot(
            callsign=callsign,
            frequency=frequency,
            mode=mode,
            source="rbn",
            spotter=spotter,
            snr=int(snr_str),
            wpm=int(wpm_str),
            time=zulu,
            band=band,
        )


# ---------------------------------------------------------------------------
# HamAlert feed
# ---------------------------------------------------------------------------


def _strip_iac(data: bytes) -> bytes:
    """Strip telnet IAC sequences (0xFF followed by 2 bytes)."""
    result = bytearray()
    i = 0
    while i < len(data):
        if data[i] == 0xFF and i + 2 < len(data):
            i += 3  # skip IAC + command + option
        else:
            result.append(data[i])
            i += 1
    return bytes(result)


class HamAlertFeed(BaseFeed):
    async def _connect_and_read(self, **kwargs: object) -> None:
        host = str(kwargs.get("host", "hamalert.org"))
        port = int(kwargs.get("port", 7300))  # type: ignore[arg-type]
        username = str(kwargs.get("username", ""))
        password = str(kwargs.get("password", ""))

        if not username or not password:
            logger.warning("HamAlert: no credentials configured, cannot connect")
            await asyncio.sleep(30)
            return

        logger.info("HamAlert: connecting to %s:%d", host, port)
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=15
        )

        try:
            # Login sequence — read prompts, send credentials
            await asyncio.sleep(1)
            raw = await asyncio.wait_for(reader.read(4096), timeout=10)
            raw = _strip_iac(raw)
            logger.debug("HamAlert server: %s", raw.decode("ascii", errors="replace"))

            writer.write(f"{username}\r\n".encode("ascii"))
            await writer.drain()
            await asyncio.sleep(1)

            raw = await asyncio.wait_for(reader.read(4096), timeout=10)
            raw = _strip_iac(raw)
            logger.debug("HamAlert server: %s", raw.decode("ascii", errors="replace"))

            writer.write(f"{password}\r\n".encode("ascii"))
            await writer.drain()
            await asyncio.sleep(1)

            # Switch to JSON mode
            writer.write(b"set/json\r\n")
            await writer.drain()

            self._connected = True
            logger.info("HamAlert: connected")

            buffer = b""
            while self._should_run:
                data = await asyncio.wait_for(reader.read(32768), timeout=120)
                if not data:
                    logger.info("HamAlert: connection closed by server")
                    break

                data = _strip_iac(data)
                buffer += data

                while b"\n" in buffer:
                    line_bytes, buffer = buffer.split(b"\n", 1)
                    line = line_bytes.strip().decode("utf-8", errors="replace")
                    if not line:
                        continue

                    parsed = self._parse_json(line)
                    if parsed:
                        await self.cache.add(parsed)
        finally:
            self._connected = False
            writer.close()
            try:
                await asyncio.wait_for(writer.wait_closed(), timeout=2)
            except Exception:
                pass

    @staticmethod
    def _parse_json(line: str) -> ParsedSpot | None:
        """Parse a HamAlert JSON line into a Spot object."""
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return None

        callsign = data.get("callsign", "").strip()
        if not callsign:
            return None

        freq_str = data.get("frequency", "")
        try:
            frequency = float(freq_str) * 1000  # MHz to kHz
        except (ValueError, TypeError):
            frequency = 0.0

        mode = data.get("mode", "").upper()
        spotter = data.get("spotter", "")
        spot_time = data.get("time", "")

        state = data.get("state", "")
        if isinstance(state, list):
            state = state[0] if state else ""

        comment = ""
        trigger = data.get("triggerComment", "")
        if isinstance(trigger, list):
            comment = trigger[0] if trigger else ""
        elif isinstance(trigger, str):
            comment = trigger

        wwff_ref = data.get("wwffRef", "")

        band = freq_to_band(frequency) if frequency else ""

        return ParsedSpot(
            callsign=callsign,
            frequency=frequency,
            mode=mode,
            source="hamalert",
            spotter=spotter,
            time=spot_time,
            band=band,
            state=state,
            comment=comment,
            wwff_ref=wwff_ref,
        )


# ---------------------------------------------------------------------------
# Module-level singletons and lifecycle
# ---------------------------------------------------------------------------

spot_cache = SpotCache()
rbn_feed = RBNFeed(spot_cache)
hamalert_feed = HamAlertFeed(spot_cache)

_prune_task: asyncio.Task | None = None


async def _read_feed_settings() -> dict[str, str]:
    """Read all feed-related settings from the database."""
    keys = [
        "rbn_enabled",
        "rbn_host",
        "rbn_port",
        "hamalert_enabled",
        "hamalert_host",
        "hamalert_port",
        "hamalert_username",
        "hamalert_password",
        "my_callsign",
    ]
    settings: dict[str, str] = {}
    async with async_session() as session:
        result = await session.execute(select(Setting).where(Setting.key.in_(keys)))
        for s in result.scalars().all():
            settings[s.key] = s.value or ""
    return settings


async def _prune_loop() -> None:
    """Periodically prune expired spots from the cache."""
    while True:
        await asyncio.sleep(60)
        await spot_cache.prune()


async def _apply_settings(settings: dict[str, str]) -> None:
    """Start or stop feeds based on current settings."""
    # RBN
    rbn_enabled = settings.get("rbn_enabled", "false").lower() == "true"
    if rbn_enabled:
        callsign = settings.get("my_callsign", "")
        if callsign:
            await rbn_feed.start(
                host=settings.get("rbn_host", "telnet.reversebeacon.net"),
                port=int(settings.get("rbn_port", "7000")),
                callsign=callsign,
            )
        else:
            logger.warning("RBN enabled but no callsign configured")
            await rbn_feed.stop()
    else:
        await rbn_feed.stop()

    # HamAlert
    ha_enabled = settings.get("hamalert_enabled", "false").lower() == "true"
    if ha_enabled:
        username = settings.get("hamalert_username", "")
        password = settings.get("hamalert_password", "")
        if username and password:
            await hamalert_feed.start(
                host=settings.get("hamalert_host", "hamalert.org"),
                port=int(settings.get("hamalert_port", "7300")),
                username=username,
                password=password,
            )
        else:
            logger.warning("HamAlert enabled but credentials not configured")
            await hamalert_feed.stop()
    else:
        await hamalert_feed.stop()


async def start_feeds() -> None:
    """Start enabled feeds on app startup."""
    global _prune_task
    _prune_task = asyncio.create_task(_prune_loop())
    settings = await _read_feed_settings()
    await _apply_settings(settings)


async def stop_feeds() -> None:
    """Stop all feeds on app shutdown."""
    await rbn_feed.stop()
    await hamalert_feed.stop()
    if _prune_task:
        _prune_task.cancel()
        try:
            await _prune_task
        except asyncio.CancelledError:
            pass


async def refresh_feeds() -> None:
    """Re-read settings and restart feeds as needed."""
    settings = await _read_feed_settings()
    await _apply_settings(settings)
