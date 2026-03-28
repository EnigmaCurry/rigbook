import logging
import os
import sys
import uuid as _uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator

from fastapi import HTTPException
from sqlalchemy import Float, String, DateTime, Integer, inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

logger = logging.getLogger("rigbook")

_WIN = sys.platform == "win32"

DB_DIR = Path.home() / ".local" / "rigbook"


class Base(DeclarativeBase):
    pass


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uuid: Mapped[str | None] = mapped_column(
        String, unique=True, nullable=True, default=lambda: str(_uuid.uuid4())
    )
    call: Mapped[str] = mapped_column(String, nullable=False)
    freq: Mapped[str | None] = mapped_column(String, nullable=True)
    mode: Mapped[str | None] = mapped_column(String, nullable=True)
    rst_sent: Mapped[str | None] = mapped_column(String, nullable=True)
    rst_recv: Mapped[str | None] = mapped_column(String, nullable=True)
    pota_park: Mapped[str | None] = mapped_column(String, nullable=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    qth: Mapped[str | None] = mapped_column(String, nullable=True)
    state: Mapped[str | None] = mapped_column(String, nullable=True)
    country: Mapped[str | None] = mapped_column(String, nullable=True)
    dxcc: Mapped[int | None] = mapped_column(Integer, nullable=True)
    grid: Mapped[str | None] = mapped_column(String, nullable=True)
    skcc: Mapped[str | None] = mapped_column(String, nullable=True)
    skcc_exch: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    comments: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Cache(Base):
    __tablename__ = "cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    namespace: Mapped[str] = mapped_column(String, nullable=False)
    key: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str | None] = mapped_column(String, nullable=True)
    expires_at: Mapped[float] = mapped_column(nullable=False)


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    value: Mapped[str | None] = mapped_column(String, nullable=True)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    meta: Mapped[str | None] = mapped_column(String, nullable=True)
    read: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    done: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class PotaProgram(Base):
    __tablename__ = "pota_programs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(Integer, nullable=False)
    prefix: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    fetched_at: Mapped[float] = mapped_column(Float, nullable=False)


class PotaLocation(Base):
    __tablename__ = "pota_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    location_id: Mapped[int] = mapped_column(Integer, nullable=False)
    program_prefix: Mapped[str] = mapped_column(String, nullable=False)
    descriptor: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    fetched_at: Mapped[float] = mapped_column(Float, nullable=False)
    parks_fetched_at: Mapped[float | None] = mapped_column(Float, nullable=True)


class PotaPark(Base):
    __tablename__ = "pota_parks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    location_desc: Mapped[str] = mapped_column(String, nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    grid: Mapped[str | None] = mapped_column(String, nullable=True)
    attempts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    activations: Mapped[int | None] = mapped_column(Integer, nullable=True)
    qsos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fetched_at: Mapped[float] = mapped_column(Float, nullable=False)


def _try_lock(f) -> None:
    """Acquire a non-blocking exclusive lock on an open file."""
    if _WIN:
        import msvcrt

        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(f) -> None:
    """Release a file lock."""
    if _WIN:
        import msvcrt

        try:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
    else:
        import fcntl

        fcntl.flock(f, fcntl.LOCK_UN)


class DatabaseLockError(Exception):
    """Raised when the database is already locked by another process."""

    pass


class DatabaseManager:
    def __init__(self):
        self.engine = None
        self._session_factory = None
        self.db_path: Path | None = None
        self.picker_mode: bool = False
        self._db_override: str | None = None
        self.pending_name: str | None = None
        self._lock_file = None
        self._host: str | None = None
        self._port: int | None = None

    def configure(self, db_name: str | None = None, picker: bool = False) -> None:
        cli_name = db_name
        env_name = os.environ.get("RIGBOOK_DB")
        env_picker = os.environ.get("RIGBOOK_PICKER", "").lower() in (
            "1",
            "true",
            "yes",
        )
        if cli_name:
            self._db_override = cli_name
            self.picker_mode = False
        elif env_name:
            self._db_override = env_name
            self.picker_mode = False
        elif picker or env_picker:
            self._db_override = None
            self.picker_mode = True
        else:
            self._db_override = None
            self.picker_mode = False

    @property
    def db_name(self) -> str | None:
        if self.db_path:
            return self.db_path.stem
        return None

    @property
    def is_open(self) -> bool:
        return self.engine is not None

    @property
    def default_db_path(self) -> Path:
        if self._db_override:
            return DB_DIR / f"{self._db_override}.db"
        return DB_DIR / "rigbook.db"

    def check_lock(self, db_path: Path) -> None:
        """Raise DatabaseLockError if the database is locked by another process."""
        lock_path = db_path.with_suffix(".lock")
        if not lock_path.exists():
            return
        try:
            with open(lock_path, "r+") as f:
                _try_lock(f)
                _unlock(f)
        except OSError:
            raise DatabaseLockError(
                f"Logbook '{db_path.stem}' is already open in another process"
            )

    def read_lock_info(self, db_path: Path) -> dict | None:
        """Read lock file contents. Returns dict with pid, host, port or None."""
        lock_path = db_path.with_suffix(".lock")
        if not lock_path.exists():
            return None
        try:
            parts = lock_path.read_text().strip().split()
            info = {"pid": int(parts[0])}
            if len(parts) > 1:
                host, _, port = parts[1].rpartition(":")
                info["host"] = host
                info["port"] = int(port)
            if len(parts) > 2:
                info["version"] = parts[2]
            return info
        except (ValueError, OSError, IndexError):
            return None

    def read_lock_pid(self, db_path: Path) -> int | None:
        """Read the PID from a lock file, or None if not locked."""
        info = self.read_lock_info(db_path)
        return info["pid"] if info else None

    def set_listen_addr(self, host: str, port: int) -> None:
        """Store and write host:port to the lock file."""
        self._host = host
        self._port = port
        self._write_lock_content()

    def _write_lock_content(self) -> None:
        """Write current pid, optional host:port, and version to the lock file."""
        if not self._lock_file:
            return
        from importlib.metadata import version

        self._lock_file.seek(0)
        self._lock_file.truncate()
        content = str(os.getpid())
        if self._host is not None and self._port is not None:
            content += f" {self._host}:{self._port}"
        try:
            content += f" {version('rigbook')}"
        except Exception:
            pass
        self._lock_file.write(content)
        self._lock_file.flush()

    def _acquire_lock(self, db_path: Path) -> None:
        """Acquire an exclusive file lock to prevent concurrent access."""
        lock_path = db_path.with_suffix(".lock")
        self._lock_file = open(lock_path, "w")
        try:
            _try_lock(self._lock_file)
            self._write_lock_content()
        except OSError:
            self._lock_file.close()
            self._lock_file = None
            raise DatabaseLockError(
                f"Logbook '{db_path.stem}' is already open in another process"
            )

    def _release_lock(self) -> None:
        """Release the file lock."""
        if self._lock_file:
            try:
                _unlock(self._lock_file)
                lock_path = Path(self._lock_file.name)
                self._lock_file.close()
                lock_path.unlink(missing_ok=True)
            except OSError:
                pass
            self._lock_file = None

    async def open(self, db_path: str | Path) -> None:
        await self.close()
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._acquire_lock(db_path)
        self.db_path = db_path
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        self._session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(_add_missing_columns)
            await conn.execute(
                text(
                    "UPDATE contacts SET updated_at = timestamp WHERE updated_at IS NULL"
                )
            )
            await conn.execute(
                text(
                    "UPDATE contacts SET uuid = lower(hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' || substr(hex(randomblob(2)),2) || '-' || substr('89ab', abs(random()) % 4 + 1, 1) || substr(hex(randomblob(2)),2) || '-' || hex(randomblob(6))) WHERE uuid IS NULL"
                )
            )
        logger.info("Opened logbook: %s", db_path)

    async def close(self) -> None:
        if self.engine:
            await self.engine.dispose()
        self.engine = None
        self._session_factory = None
        self.db_path = None
        self._release_lock()


db_manager = DatabaseManager()


def async_session():
    if db_manager._session_factory is None:
        raise RuntimeError("No logbook is currently open")
    return db_manager._session_factory()


async def init_db() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    if db_manager.picker_mode:
        return
    db_path = db_manager.default_db_path
    if not db_path.exists() and db_manager._db_override:
        db_manager.pending_name = db_path.stem
        return
    await db_manager.open(db_path)


def _add_missing_columns(conn):
    insp = inspect(conn)
    for table_name, table in Base.metadata.tables.items():
        if not insp.has_table(table_name):
            continue
        existing = {c["name"] for c in insp.get_columns(table_name)}
        for col in table.columns:
            if col.name not in existing:
                col_type = col.type.compile(conn.dialect)
                conn.execute(
                    text(f"ALTER TABLE {table_name} ADD COLUMN {col.name} {col_type}")
                )


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if db_manager._session_factory is None:
        raise HTTPException(status_code=503, detail="No logbook is currently open")
    async with db_manager._session_factory() as session:
        yield session
