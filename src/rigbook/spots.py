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
import math
import re
import time as _time
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field

import httpx
from rigbook.db import async_session, resolve_setting

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
# Maidenhead grid utilities
# ---------------------------------------------------------------------------

_GRID_RE = re.compile(r"^[A-R]{2}\d{2}([A-X]{2})?$", re.IGNORECASE)


def grid_to_latlon(grid: str) -> tuple[float, float] | None:
    """Convert a 4 or 6 character Maidenhead grid to (lat, lon) degrees."""
    grid = grid.upper()
    if not _GRID_RE.match(grid):
        return None

    lon = (ord(grid[0]) - ord("A")) * 20 - 180 + (ord(grid[2]) - ord("0")) * 2
    lat = (ord(grid[1]) - ord("A")) * 10 - 90 + (ord(grid[3]) - ord("0"))

    if len(grid) >= 6:
        lon += (ord(grid[4]) - ord("A")) * (2 / 24) + (1 / 24)
        lat += (ord(grid[5]) - ord("A")) * (1 / 24) + (0.5 / 24)
    else:
        lon += 1
        lat += 0.5

    return lat, lon


def grid_distance_km(grid1: str, grid2: str) -> float | None:
    """Great-circle distance in km between two Maidenhead grid squares."""
    c1 = grid_to_latlon(grid1)
    c2 = grid_to_latlon(grid2)
    if not c1 or not c2:
        return None

    lat1, lon1 = math.radians(c1[0]), math.radians(c1[1])
    lat2, lon2 = math.radians(c2[0]), math.radians(c2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return 2 * 6371 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def grid_distance_mi(grid1: str, grid2: str) -> int | None:
    """Great-circle distance in miles between two Maidenhead grid squares."""
    km = grid_distance_km(grid1, grid2)
    if km is None:
        return None
    return round(km * 0.621371)


# ---------------------------------------------------------------------------
# Spotter grid cache (fetched from RBN status page)
# ---------------------------------------------------------------------------

RBN_STATUS_URL = "https://reversebeacon.net/cont_includes/status.php?t=skt"


class SpotterGrids:
    """Cache of spotter callsign -> grid square, fetched from RBN status page."""

    REFETCH_COOLDOWN = 60  # minimum seconds between refetches on miss

    def __init__(self) -> None:
        self._grids: dict[str, str] = {}  # spotter -> grid
        self._no_grid: set[str] = set()  # spotters confirmed to have no grid
        self._fetched_at: float = 0
        self._ttl: float = 3600  # full refresh hourly
        self._lock = asyncio.Lock()

    async def ensure_loaded(self) -> None:
        if _time.time() - self._fetched_at < self._ttl:
            return
        async with self._lock:
            if _time.time() - self._fetched_at < self._ttl:
                return
            self._no_grid.clear()
            await self._fetch("TTL expired")

    def _is_known(self, spotter: str) -> bool:
        return spotter in self._grids or spotter in self._no_grid

    async def ensure_spotters(self, spotters: list[str]) -> None:
        """Refetch if any spotter is unknown, respecting a cooldown."""
        unknown = sorted({s for s in spotters if not self._is_known(s)})
        if not unknown:
            return
        if _time.time() - self._fetched_at < self.REFETCH_COOLDOWN:
            return
        async with self._lock:
            unknown = sorted({s for s in spotters if not self._is_known(s)})
            if not unknown:
                return
            if _time.time() - self._fetched_at < self.REFETCH_COOLDOWN:
                return
            sample = ", ".join(unknown[:3])
            suffix = f" and {len(unknown) - 3} more" if len(unknown) > 3 else ""
            reason = f"{len(unknown)} unknown spotter(s): {sample}{suffix}"
            await self._fetch(reason)
            # Mark still-unknown spotters so we don't refetch for them again
            for s in unknown:
                if s not in self._grids:
                    self._no_grid.add(s)

    async def _fetch(self, reason: str = "") -> None:
        logger.info("Fetching spotter grids (%s)...", reason)
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(RBN_STATUS_URL)
                if response.status_code != 200:
                    logger.warning("RBN status page returned %d", response.status_code)
                    return
                html = response.text

            # Parse HTML table rows for spotter callsign and grid
            # Format: <td><a href="...">SPOTTER</a></td> ... <td>GRID</td>
            grids: dict[str, str] = {}
            row_re = re.compile(
                r'<tr.*?online24h online7d total">(.*?)</tr>', re.DOTALL
            )
            col_re = re.compile(
                r'<td.*?><a href="/dxsd1\.php\?f=.*?>\s*(.*?)\s*</a>.*?</td>\s*'
                r"<td.*?>\s*(.*?)</a></td>\s*<td.*?>(.*?)</td>",
                re.DOTALL,
            )
            for row in row_re.findall(html):
                for spotter, _, grid in col_re.findall(row):
                    grid = grid.strip()
                    if grid and _GRID_RE.match(grid) and grid != "XX88LL":
                        grids[spotter.strip()] = grid.upper()

            self._grids = grids
            self._fetched_at = _time.time()
            logger.info("Loaded %d spotter grids", len(grids))
        except Exception as e:
            logger.warning("Failed to fetch spotter grids: %s", e)

    def get(self, spotter: str) -> str | None:
        return self._grids.get(spotter)

    def closest_spotter(
        self,
        my_grid: str,
        spotter_snrs: dict[str, int | None],
    ) -> tuple[str | None, int | None, int | None]:
        """Find closest spotter and return (callsign, distance_mi, snr_db).

        Args:
            my_grid: User's Maidenhead grid square.
            spotter_snrs: Mapping of spotter callsign -> SNR (or None).

        Returns:
            (callsign, distance in miles, SNR dB) for the closest spotter,
            or (None, None, None).
        """
        best_call: str | None = None
        best_dist: int | None = None
        best_snr: int | None = None
        for spotter, snr in spotter_snrs.items():
            grid = self._grids.get(spotter)
            if grid:
                dist = grid_distance_mi(my_grid, grid)
                if dist is not None and (best_dist is None or dist < best_dist):
                    best_call = spotter
                    best_dist = dist
                    best_snr = snr
        return best_call, best_dist, best_snr


spotter_grids = SpotterGrids()


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
    spotters: dict[str, tuple[float, int | None]] = field(
        default_factory=dict
    )  # spotter -> (timestamp, snr)
    best_snr: int | None = None
    wpm: int | None = None
    time: str = ""  # most recent spot time
    received_at: float = field(default_factory=_time.time)
    state: str = ""
    comment: str = ""
    wwff_ref: str = ""

    def prune_spotters(self, cutoff: float) -> None:
        """Remove spotters older than cutoff timestamp."""
        self.spotters = {k: v for k, v in self.spotters.items() if v[0] > cutoff}

    def to_dict(self) -> dict:
        spotters_sorted = sorted(self.spotters.keys())
        best_snr = max(
            (snr for _, snr in self.spotters.values() if snr is not None),
            default=self.best_snr,
        )
        return {
            "callsign": self.callsign,
            "frequency": self.frequency,
            "mode": self.mode,
            "band": self.band,
            "spotter_count": len(self.spotters),
            "spotters": spotters_sorted,
            "best_snr": best_snr,
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
        self._entries: dict[tuple[str, str], AggregateSpot] = {}
        self._lock = asyncio.Lock()

    async def add(self, spot: ParsedSpot) -> None:
        key = (spot.callsign, spot.mode)
        freq = round(spot.frequency, 1)
        now = _time.time()
        async with self._lock:
            entry = self._entries.get(key)
            if entry:
                # Update existing aggregate with latest data
                entry.frequency = freq
                entry.band = spot.band or entry.band
                if spot.spotter:
                    entry.spotters[spot.spotter] = (now, spot.snr)
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
                    frequency=freq,
                    mode=spot.mode,
                    band=spot.band,
                    source=spot.source,
                    spotters={spot.spotter: (now, spot.snr)} if spot.spotter else {},
                    wpm=spot.wpm,
                    time=spot.time,
                    received_at=now,
                    state=spot.state,
                    comment=spot.comment,
                    wwff_ref=spot.wwff_ref,
                )

    async def purge_source(self, source: str) -> None:
        async with self._lock:
            to_remove = [k for k, e in self._entries.items() if e.source == source]
            for key in to_remove:
                del self._entries[key]

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
            live_count = sum(1 for ts, _ in entry.spotters.values() if ts > cutoff)
            if live_count > 0:
                results.append(entry)
        return results

    async def query(
        self,
        *,
        source: str | None = None,
        callsign: str | None = None,
        mode: str | None = None,
        bands: set[str] | None = None,
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
        if bands:
            live = [e for e in live if e.band in bands]
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
            live_spotter_snrs = {
                k: snr for k, (ts, snr) in e.spotters.items() if ts > cutoff
            }
            d["spotters"] = sorted(live_spotter_snrs.keys())
            d["spotter_count"] = len(live_spotter_snrs)
            d["spotter_snrs"] = live_spotter_snrs
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

    async def modes(self) -> dict[str, int]:
        """Return mode -> count of live entries."""
        cutoff = _time.time() - SPOT_TTL
        async with self._lock:
            counts: dict[str, int] = {}
            for e in self._live_entries(cutoff):
                if e.mode:
                    counts[e.mode] = counts.get(e.mode, 0) + 1
            return counts

    async def stats(self) -> dict:
        """Cache statistics: callsigns, total spots, average spots per callsign."""
        cutoff = _time.time() - SPOT_TTL
        async with self._lock:
            live = self._live_entries(cutoff)
            total_entries = len(live)
            total_spots = sum(
                sum(1 for ts, _ in e.spotters.values() if ts > cutoff) for e in live
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
                msg = str(e) or type(e).__name__
                logger.warning("%s connection error: %s", self.__class__.__name__, msg)
                self._connected = False
            if self._should_run:
                await asyncio.sleep(10)

    async def _connect_and_read(self, **kwargs: object) -> None:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# RBN feed
# ---------------------------------------------------------------------------


class RBNFeed:
    """Connects to RBN feeds. CW and digital are on separate ports."""

    # RBN serves different modes on different ports
    AVAILABLE_FEEDS: dict[str, int] = {"cw": 7000, "digital": 7001}

    def __init__(self, cache: SpotCache) -> None:
        self.cache = cache
        self._tasks: dict[str, asyncio.Task] = {}
        self._connected: dict[str, bool] = {}
        self._should_run = False

    @property
    def connected(self) -> bool:
        return any(self._connected.values())

    async def start(self, **kwargs: object) -> None:
        await self.stop()
        self._should_run = True
        host = str(kwargs.get("host", "telnet.reversebeacon.net"))
        callsign = str(kwargs.get("callsign", ""))
        # feeds is a comma-separated string like "cw"
        feeds_str = str(kwargs.get("feeds", "cw"))
        enabled_feeds = {f.strip().lower() for f in feeds_str.split(",") if f.strip()}

        for name, port in self.AVAILABLE_FEEDS.items():
            if name in enabled_feeds:
                self._connected[name] = False
                self._tasks[name] = asyncio.create_task(
                    self._run_loop(name=name, host=host, port=port, callsign=callsign)
                )

    async def stop(self) -> None:
        self._should_run = False
        for name, task in list(self._tasks.items()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()
        self._connected.clear()

    async def _run_loop(self, **kwargs: object) -> None:
        name = str(kwargs.get("name", ""))
        while self._should_run:
            try:
                await self._connect_and_read(**kwargs)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning("RBN/%s connection error: %s", name, e)
                self._connected[name] = False
            if self._should_run:
                await asyncio.sleep(10)

    async def _connect_and_read(self, **kwargs: object) -> None:
        name = str(kwargs.get("name", ""))
        host = str(kwargs.get("host", "telnet.reversebeacon.net"))
        port = int(kwargs.get("port", 7000))  # type: ignore[arg-type]
        callsign = str(kwargs.get("callsign", ""))

        if not callsign:
            logger.warning("RBN feed: no callsign configured, cannot connect")
            await asyncio.sleep(30)
            return

        logger.info("RBN/%s: connecting to %s:%d as %s", name, host, port, callsign)
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=15
        )

        try:
            await asyncio.wait_for(reader.readuntil(b"call: "), timeout=15)
            writer.write(f"{callsign}\r\n".encode("ascii"))
            await writer.drain()
            await asyncio.wait_for(reader.readuntil(b">\r\n"), timeout=15)

            self._connected[name] = True
            logger.info("RBN/%s: connected", name)

            while self._should_run:
                line_bytes = await asyncio.wait_for(reader.readline(), timeout=3600)
                if not line_bytes:
                    logger.info("RBN/%s: connection closed by server", name)
                    break

                line = line_bytes.rstrip().decode("ascii", errors="replace")
                parsed = self._parse_line(line)
                if parsed:
                    await self.cache.add(parsed)
        finally:
            self._connected[name] = False
            writer.close()
            try:
                await asyncio.wait_for(writer.wait_closed(), timeout=2)
            except Exception:
                pass

    # RBN spot formats vary by mode:
    # CW:      DX de SPOTTER-#:  FREQ  CALL  CW    26 dB  31 WPM  CQ      1832Z
    # Digital: DX de SPOTTER-#:  FREQ  CALL  FT8  -21 dB          CQ      1831Z
    # Digital: DX de SPOTTER-#:  FREQ  CALL  FT8    1 dB  IM99    CQ      1831Z
    # Common prefix up to dB, then variable tail
    _RBN_PREFIX_RE = re.compile(
        r"^DX de\s+(\S+)-#:\s+"  # spotter
        r"(\d+\.\d+)\s+"  # frequency kHz
        r"(\S+)\s+"  # callsign
        r"(\S+)\s+"  # mode
        r"(-?\d+)\s+dB\s+"  # snr (can be negative)
    )

    @staticmethod
    def _parse_line(line: str) -> ParsedSpot | None:
        """Parse an RBN spot line into a ParsedSpot."""
        if not line.startswith("DX de "):
            return None

        m = RBNFeed._RBN_PREFIX_RE.match(line)
        if not m:
            return None

        spotter, freq_str, callsign, mode, snr_str = m.groups()

        # Parse the tail after "NN dB  " — variable fields then HHMMZ
        tail = line[m.end() :].strip()

        # Time is always the last token (HHMMZ)
        if not tail or not tail.endswith("Z"):
            return None
        tokens = tail.split()
        if not tokens:
            return None
        zulu = tokens[-1]
        if not re.match(r"^\d{4}Z$", zulu):
            return None

        # Look for spot type (CQ, BEACON, NCDXF, etc.) — second to last
        # and optional WPM/grid before that
        wpm: int | None = None
        spot_type = ""
        remaining = tokens[:-1]  # everything except time

        # Look for "NN WPM" or "NN BPS" anywhere in remaining tokens
        if remaining:
            for i, tok in enumerate(remaining):
                if tok in ("WPM", "BPS") and i > 0 and remaining[i - 1].isdigit():
                    if tok == "WPM":
                        wpm = int(remaining[i - 1])
                    break

            # spot_type is the last token that isn't part of WPM/BPS/grid
            spot_type = remaining[-1]
            if spot_type in ("WPM", "BPS"):
                # "31 WPM" was the last thing — no explicit type
                spot_type = "CQ"

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
            wpm=wpm,
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
    async def _maybe_notify(self, spot: ParsedSpot) -> None:
        """Create a notification for a HamAlert spot."""
        from rigbook.routes.notifications import create_notification

        freq_mhz = f"{spot.frequency / 1000:.3f}" if spot.frequency else "?"
        title = f"HamAlert: {spot.callsign}"
        parts = [f"{spot.callsign} on {freq_mhz} MHz {spot.mode}"]
        if spot.comment:
            parts.append(spot.comment)
        if spot.wwff_ref:
            parts.append(f"WWFF: {spot.wwff_ref}")
        meta = {
            "callsign": spot.callsign,
            "frequency": str(spot.frequency),
            "mode": spot.mode,
        }
        try:
            await create_notification(title, " — ".join(parts), meta=meta)
        except Exception:
            logger.exception("Failed to create notification for HamAlert spot")

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
            banner = raw.decode("ascii", errors="replace").strip()
            logger.debug("HamAlert banner: %s", banner)

            writer.write(f"{username}\r\n".encode("ascii"))
            await writer.drain()
            await asyncio.sleep(1)

            raw = await asyncio.wait_for(reader.read(4096), timeout=10)
            raw = _strip_iac(raw)
            prompt = raw.decode("ascii", errors="replace").strip()
            logger.debug("HamAlert after username: %s", prompt)

            writer.write(f"{password}\r\n".encode("ascii"))
            await writer.drain()
            await asyncio.sleep(1)

            raw = await asyncio.wait_for(reader.read(4096), timeout=10)
            raw = _strip_iac(raw)
            auth_response = raw.decode("ascii", errors="replace").strip()
            logger.debug("HamAlert after password: %s", auth_response)

            if "invalid" in auth_response.lower() or "denied" in auth_response.lower():
                logger.warning("HamAlert: authentication failed: %s", auth_response)
                return

            # Switch to JSON mode
            writer.write(b"set/json\r\n")
            await writer.drain()

            self._connected = True
            logger.info("HamAlert: connected and authenticated as %s", username)

            buffer = b""
            while self._should_run:
                data = await asyncio.wait_for(reader.read(32768), timeout=3600)
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
                        await self._maybe_notify(parsed)
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
_idle_disconnect_task: asyncio.Task | None = None
_rbn_stopped_for_idle: bool = False


async def _read_feed_settings() -> dict[str, str]:
    """Read all feed-related settings from the database."""
    keys = [
        "rbn_enabled",
        "rbn_host",
        "rbn_feeds",
        "hamalert_enabled",
        "hamalert_username",
        "hamalert_password",
        "my_callsign",
        "rbn_idle_timeout_minutes",
    ]
    settings: dict[str, str] = {}
    try:
        async with async_session() as session:
            for key in keys:
                settings[key] = await resolve_setting(key, session)
    except RuntimeError:
        pass
    return settings


async def _prune_loop() -> None:
    """Periodically prune expired spots from the cache."""
    while True:
        await asyncio.sleep(60)
        await spot_cache.prune()


def rbn_idle_stopped() -> bool:
    """Return True if RBN was stopped due to idle timeout."""
    return _rbn_stopped_for_idle


async def _idle_disconnect_after(timeout_minutes: int) -> None:
    """Sleep for exactly the timeout duration, then disconnect RBN."""
    global _rbn_stopped_for_idle
    disconnect_at = datetime.now(timezone.utc) + timedelta(minutes=timeout_minutes)
    logger.debug(
        "RBN: no web clients, will disconnect at %s UTC (%dm)",
        disconnect_at.strftime("%Y-%m-%d %H:%M:%S"),
        timeout_minutes,
    )
    await asyncio.sleep(timeout_minutes * 60)
    await rbn_feed.stop()
    _rbn_stopped_for_idle = True
    logger.info(
        "RBN idle timeout: no web clients for %d minutes, disconnected."
        " Will reconnect automatically when a client connects.",
        timeout_minutes,
    )


def _schedule_idle_disconnect() -> None:
    """Schedule an idle disconnect task if conditions are met."""
    global _idle_disconnect_task
    if _idle_disconnect_task and not _idle_disconnect_task.done():
        return
    if _rbn_stopped_for_idle or not rbn_feed.connected:
        return
    asyncio.create_task(_maybe_schedule_idle_disconnect())


async def _maybe_schedule_idle_disconnect() -> None:
    global _idle_disconnect_task
    settings = await _read_feed_settings()
    rbn_enabled = settings.get("rbn_enabled", "false").lower() == "true"
    if not rbn_enabled:
        return
    try:
        timeout_minutes = int(settings.get("rbn_idle_timeout_minutes", "720") or "720")
    except (ValueError, TypeError):
        return
    if timeout_minutes <= 0:
        return
    _idle_disconnect_task = asyncio.create_task(_idle_disconnect_after(timeout_minutes))


def _cancel_idle_disconnect() -> None:
    """Cancel any pending idle disconnect task."""
    global _idle_disconnect_task
    if _idle_disconnect_task and not _idle_disconnect_task.done():
        _idle_disconnect_task.cancel()
        _idle_disconnect_task = None
        logger.debug("RBN: idle disconnect cancelled, client connected")


def _on_last_client_disconnect() -> None:
    """Called when an SSE client disconnects. If none remain, schedule idle disconnect."""
    from rigbook.sse import subscriber_count

    if subscriber_count() > 0:
        return
    _schedule_idle_disconnect()


def _on_client_connect() -> None:
    """Called when an SSE client connects. Cancel idle disconnect or restart if stopped."""
    global _rbn_stopped_for_idle
    _cancel_idle_disconnect()
    if not _rbn_stopped_for_idle:
        return
    _rbn_stopped_for_idle = False
    asyncio.create_task(_restart_rbn_from_idle())


async def _restart_rbn_from_idle() -> None:
    """Re-read settings and restart RBN after idle stop."""
    settings = await _read_feed_settings()
    rbn_enabled = settings.get("rbn_enabled", "false").lower() == "true"
    if not rbn_enabled:
        return
    callsign = settings.get("my_callsign", "")
    if not callsign:
        return
    logger.info("RBN: web client connected, restarting idle-stopped feed")
    await rbn_feed.start(
        host=settings.get("rbn_host", "telnet.reversebeacon.net"),
        feeds=settings.get("rbn_feeds", "cw"),
        callsign=callsign,
    )


async def _apply_settings(settings: dict[str, str]) -> None:
    """Start or stop feeds based on current settings."""
    # RBN
    rbn_enabled = settings.get("rbn_enabled", "false").lower() == "true"
    if rbn_enabled:
        callsign = settings.get("my_callsign", "")
        if callsign:
            await rbn_feed.start(
                host=settings.get("rbn_host") or "telnet.reversebeacon.net",
                feeds=settings.get("rbn_feeds") or "cw",
                callsign=callsign,
            )
        else:
            logger.warning("RBN enabled but no callsign configured")
            await rbn_feed.stop()
    else:
        await rbn_feed.stop()
        await spot_cache.purge_source("rbn")
        _rbn_stopped_for_idle = False

    # HamAlert
    ha_enabled = settings.get("hamalert_enabled", "false").lower() == "true"
    if ha_enabled:
        username = settings.get("hamalert_username", "")
        password = settings.get("hamalert_password", "")
        if username and password:
            await hamalert_feed.start(
                host="hamalert.org",
                port=7300,
                username=username,
                password=password,
            )
        else:
            logger.warning("HamAlert enabled but credentials not configured")
            await hamalert_feed.stop()
    else:
        await hamalert_feed.stop()
        await spot_cache.purge_source("hamalert")


async def start_feeds() -> None:
    """Start enabled feeds on app startup."""
    global _prune_task
    _prune_task = asyncio.create_task(_prune_loop())
    from rigbook.sse import register_connect_callback, register_disconnect_callback

    register_connect_callback(_on_client_connect)
    register_disconnect_callback(_on_last_client_disconnect)
    settings = await _read_feed_settings()
    await _apply_settings(settings)


async def stop_feeds() -> None:
    """Stop all feeds on app shutdown."""
    _cancel_idle_disconnect()
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
    global _rbn_stopped_for_idle
    _cancel_idle_disconnect()
    _rbn_stopped_for_idle = False
    settings = await _read_feed_settings()
    await _apply_settings(settings)
