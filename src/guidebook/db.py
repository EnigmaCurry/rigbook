import json
import logging
import os
import sys
import time
import uuid as _uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator

from fastapi import HTTPException
from sqlalchemy import String, DateTime, Integer, Float, inspect, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

logger = logging.getLogger("guidebook")

DB_DIR = Path.home() / ".local" / "guidebook"
META_DB_PATH = DB_DIR / "__global.db"
_LAST_OPENED_FILE = DB_DIR / "last_opened.json"

# Settings that can be set globally in __global.db and overridden per-logbook
GLOBAL_DEFAULTABLE_KEYS: set[str] = set()

# Settings that live exclusively in __global.db (not per-logbook)
GLOBAL_ONLY_KEYS = {
    "update_check_enabled",
    "default_pick_mode",
    "default_host",
    "default_port",
    "update_skip_version",
    "shutdown_in_menu",
    "auto_shutdown_on_disconnect",
    "disable_shutdown",
    "welcome_acknowledged",
    "auto_shutdown_delay",
    "default_logbook_name",
    "browser_url_override",
    "open_browser_on_startup",
}


def _read_last_opened() -> dict[str, float]:
    try:
        return json.loads(_LAST_OPENED_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _record_last_opened(name: str) -> None:
    data = _read_last_opened()
    data[name] = time.time()
    _LAST_OPENED_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LAST_OPENED_FILE.write_text(json.dumps(data))


def _lock_exclusive(f) -> None:
    """Acquire a non-blocking exclusive lock on a file (cross-platform)."""
    if sys.platform == "win32":
        import msvcrt

        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(f) -> None:
    """Release a file lock (cross-platform)."""
    if sys.platform == "win32":
        import msvcrt

        try:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
    else:
        import fcntl

        fcntl.flock(f, fcntl.LOCK_UN)


class Base(DeclarativeBase):
    pass


class Record(Base):
    __tablename__ = "records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uuid: Mapped[str | None] = mapped_column(
        String, unique=True, nullable=True, default=lambda: str(_uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[str | None] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


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


# --- Global database models (shared __global.db) ---


class GlobalBase(DeclarativeBase):
    pass


class GlobalSetting(GlobalBase):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    value: Mapped[str | None] = mapped_column(String, nullable=True)


class GlobalCache(GlobalBase):
    __tablename__ = "cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    namespace: Mapped[str] = mapped_column(String, nullable=False)
    key: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str | None] = mapped_column(String, nullable=True)
    expires_at: Mapped[float] = mapped_column(nullable=False)


class GlobalLastOpened(GlobalBase):
    __tablename__ = "last_opened"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    opened_at: Mapped[float] = mapped_column(Float, nullable=False)


class DatabaseLockError(Exception):
    """Raised when the database is already locked by another process."""


class DatabaseTooNewError(Exception):
    """Raised when the database schema is newer than this version supports."""

    pass


# --- Migration framework ---


def _get_schema_version(conn, table="settings") -> int:
    """Read _schema_version from a settings table (sync, inside run_sync)."""
    try:
        row = conn.execute(
            text(f"SELECT value FROM {table} WHERE key = '_schema_version'")
        ).fetchone()
        return int(row[0]) if row and row[0] else 0
    except Exception:
        return 0


def _set_schema_version(conn, table, version_num):
    """Write _schema_version to a settings table (sync, inside run_sync)."""
    existing = conn.execute(
        text(f"SELECT id FROM {table} WHERE key = '_schema_version'")
    ).fetchone()
    if existing:
        conn.execute(
            text(f"UPDATE {table} SET value = :v WHERE key = '_schema_version'"),
            {"v": str(version_num)},
        )
    else:
        conn.execute(
            text(f"INSERT INTO {table} (key, value) VALUES ('_schema_version', :v)"),
            {"v": str(version_num)},
        )


def _set_last_migrated_by(conn, table):
    """Store which guidebook version last migrated this DB."""
    from importlib.metadata import version as pkg_version

    try:
        v = pkg_version("guidebook")
    except Exception:
        v = "unknown"
    existing = conn.execute(
        text(f"SELECT id FROM {table} WHERE key = '_last_migrated_by'")
    ).fetchone()
    if existing:
        conn.execute(
            text(f"UPDATE {table} SET value = :v WHERE key = '_last_migrated_by'"),
            {"v": v},
        )
    else:
        conn.execute(
            text(f"INSERT INTO {table} (key, value) VALUES ('_last_migrated_by', :v)"),
            {"v": v},
        )


def _get_last_migrated_by(conn, table="settings") -> str:
    """Read _last_migrated_by from a settings table."""
    try:
        row = conn.execute(
            text(f"SELECT value FROM {table} WHERE key = '_last_migrated_by'")
        ).fetchone()
        return row[0] if row and row[0] else "unknown"
    except Exception:
        return "unknown"


def _backup_before_migration(db_path: Path, current_version: int, target_version: int):
    """Create a backup of the database before running migrations."""
    import shutil

    backup_dir = db_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%Sz")
    backup_name = f"{db_path.stem}_premigrate_v{current_version}_to_v{target_version}_{ts}{db_path.suffix}"
    backup_path = backup_dir / backup_name
    shutil.copy2(str(db_path), str(backup_path))
    size_kb = backup_path.stat().st_size / 1024
    logger.info("Pre-migration backup: %s (%.1f KB)", backup_name, size_kb)


def _run_migrations(conn, migrations, table="settings") -> bool:
    """Run pending migrations and update schema version. Returns True if any ran."""
    current = _get_schema_version(conn, table)
    expected = len(migrations)
    if current > expected:
        last_by = _get_last_migrated_by(conn, table)
        raise DatabaseTooNewError(
            f"Database was migrated by Guidebook v{last_by} (schema v{current}). "
            f"This version only supports schema up to v{expected}. "
            f"Please upgrade Guidebook."
        )
    if current < expected:
        for migrate_fn in migrations[current:]:
            migrate_fn(conn)
        _set_schema_version(conn, table, expected)
        _set_last_migrated_by(conn, table)
        logger.info("Migrated %s schema: v%d → v%d", table, current, expected)
        return True
    return False


# --- Logbook migrations ---

LOGBOOK_MIGRATIONS: list = []

# --- Global DB migrations ---

GLOBAL_MIGRATIONS: list = []


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
        # Global database (shared __global.db)
        self.global_engine = None
        self._global_session_factory = None

    def configure(self, db_name: str | None = None, picker: bool = False) -> None:
        cli_name = db_name
        env_name = os.environ.get("GUIDEBOOK_DB")
        env_picker = os.environ.get("GUIDEBOOK_PICKER", "").lower() in (
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
        return DB_DIR / "guidebook.db"

    def check_lock(self, db_path: Path) -> None:
        """Raise DatabaseLockError if the database is locked by another process."""
        lock_path = db_path.with_suffix(".lock")
        if not lock_path.exists():
            return
        try:
            with open(lock_path, "r+") as f:
                _lock_exclusive(f)
                _unlock(f)
        except OSError:
            raise DatabaseLockError(
                f"Logbook '{db_path.stem}' is already open in another process"
            )

    def read_lock_info(self, db_path: Path) -> dict | None:
        """Read lock file contents. Returns dict with pid, host, port or None.

        Falls back to .addr file if the .lock file can't be read (Windows
        holds an exclusive byte-range lock that blocks reads).
        """
        for suffix in (".lock", ".addr"):
            path = db_path.with_suffix(suffix)
            if not path.exists():
                continue
            try:
                parts = path.read_text().strip().split()
                info = {"pid": int(parts[0])}
                if len(parts) > 1:
                    host, _, port = parts[1].rpartition(":")
                    info["host"] = host
                    info["port"] = int(port)
                return info
            except (ValueError, OSError, IndexError):
                continue
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
        self._write_addr_file()

    def _write_lock_content(self) -> None:
        """Write current pid and optional host:port to the lock file."""
        if not self._lock_file:
            return
        self._lock_file.seek(0)
        self._lock_file.truncate()
        content = str(os.getpid())
        if self._host is not None and self._port is not None:
            content += f" {self._host}:{self._port}"
        self._lock_file.write(content)
        self._lock_file.flush()

    def _write_addr_file(self) -> None:
        """Write pid and host:port to a separate unlocked file for Windows."""
        if not self._lock_file:
            return
        addr_path = Path(self._lock_file.name).with_suffix(".addr")
        content = str(os.getpid())
        if self._host is not None and self._port is not None:
            content += f" {self._host}:{self._port}"
        addr_path.write_text(content)

    def _acquire_lock(self, db_path: Path) -> None:
        """Acquire an exclusive file lock to prevent concurrent access."""
        lock_path = db_path.with_suffix(".lock")
        self._lock_file = open(lock_path, "w")
        try:
            _lock_exclusive(self._lock_file)
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
                lock_path.with_suffix(".addr").unlink(missing_ok=True)
            except OSError:
                pass
            self._lock_file = None

    async def open(self, db_path: str | Path) -> None:
        await self.close()
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._acquire_lock(db_path)
        self.db_path = db_path
        # Back up before migration if needed
        if db_path.exists() and LOGBOOK_MIGRATIONS:
            import sqlite3

            _conn = sqlite3.connect(str(db_path))
            try:
                row = _conn.execute(
                    "SELECT value FROM settings WHERE key = '_schema_version'"
                ).fetchone()
                current_v = int(row[0]) if row and row[0] else 0
            except Exception:
                current_v = 0
            _conn.close()
            if current_v < len(LOGBOOK_MIGRATIONS):
                _backup_before_migration(db_path, current_v, len(LOGBOOK_MIGRATIONS))
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        self._session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        migrated = [False]
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.run_sync(_add_missing_columns)
            await conn.run_sync(
                lambda c: migrated.__setitem__(
                    0, _run_migrations(c, LOGBOOK_MIGRATIONS, "settings")
                )
            )
            await conn.execute(
                text(
                    "UPDATE records SET updated_at = timestamp WHERE updated_at IS NULL"
                )
            )
            await conn.execute(
                text(
                    "UPDATE records SET uuid = lower(hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' || substr(hex(randomblob(2)),2) || '-' || substr('89ab', abs(random()) % 4 + 1, 1) || substr(hex(randomblob(2)),2) || '-' || hex(randomblob(6))) WHERE uuid IS NULL"
                )
            )
        if migrated[0]:
            async with self.engine.begin() as conn:
                await conn.execute(text("VACUUM"))
                logger.info("Vacuumed logbook database after migration")
        async with self.engine.connect() as conn:
            sv = await conn.run_sync(lambda c: _get_schema_version(c, "settings"))
        await self.record_last_opened(db_path.stem)
        logger.info("Opened logbook: %s (schema v%d)", db_path, sv)

    async def close(self) -> None:
        if self.engine:
            await self.engine.dispose()
        self.engine = None
        self._session_factory = None
        self.db_path = None
        self._release_lock()

    async def open_global(self) -> None:
        """Open the shared __global.db with WAL mode for multi-process safety."""
        if self.global_engine is not None:
            return
        META_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        # Back up before migration if needed
        if META_DB_PATH.exists() and GLOBAL_MIGRATIONS:
            import sqlite3

            _conn = sqlite3.connect(str(META_DB_PATH))
            try:
                row = _conn.execute(
                    "SELECT value FROM settings WHERE key = '_schema_version'"
                ).fetchone()
                current_v = int(row[0]) if row and row[0] else 0
            except Exception:
                current_v = 0
            _conn.close()
            if current_v < len(GLOBAL_MIGRATIONS):
                _backup_before_migration(
                    META_DB_PATH, current_v, len(GLOBAL_MIGRATIONS)
                )
        self.global_engine = create_async_engine(f"sqlite+aiosqlite:///{META_DB_PATH}")
        self._global_session_factory = async_sessionmaker(
            self.global_engine, expire_on_commit=False
        )
        async with self.global_engine.begin() as conn:
            await conn.execute(text("PRAGMA journal_mode=WAL"))
            await conn.execute(text("PRAGMA busy_timeout=5000"))
            await conn.run_sync(GlobalBase.metadata.create_all)
            await conn.run_sync(_add_missing_columns_global)
            await conn.run_sync(
                lambda c: _run_migrations(c, GLOBAL_MIGRATIONS, "settings")
            )
        # Migrate last_opened.json if it exists
        await self._migrate_last_opened()
        async with self.global_engine.connect() as conn:
            gsv = await conn.run_sync(lambda c: _get_schema_version(c, "settings"))
        logger.info("Opened global database: %s (schema v%d)", META_DB_PATH, gsv)

    async def close_global(self) -> None:
        """Dispose of the global database engine."""
        if self.global_engine:
            await self.global_engine.dispose()
        self.global_engine = None
        self._global_session_factory = None

    async def _migrate_last_opened(self) -> None:
        """One-time migration of last_opened.json into GlobalLastOpened table."""
        if not _LAST_OPENED_FILE.exists():
            return
        data = _read_last_opened()
        if not data:
            _LAST_OPENED_FILE.unlink(missing_ok=True)
            return
        async with self._global_session_factory() as session:
            for name, ts in data.items():
                existing = (
                    await session.execute(
                        select(GlobalLastOpened).where(GlobalLastOpened.name == name)
                    )
                ).scalar_one_or_none()
                if existing:
                    if ts > existing.opened_at:
                        existing.opened_at = ts
                else:
                    session.add(GlobalLastOpened(name=name, opened_at=ts))
            await session.commit()
        _LAST_OPENED_FILE.unlink(missing_ok=True)
        logger.info("Migrated last_opened.json to global database")

    async def record_last_opened(self, name: str) -> None:
        """Record when a logbook was last opened (in global DB)."""
        if self._global_session_factory is None:
            return
        async with self._global_session_factory() as session:
            existing = (
                await session.execute(
                    select(GlobalLastOpened).where(GlobalLastOpened.name == name)
                )
            ).scalar_one_or_none()
            if existing:
                existing.opened_at = time.time()
            else:
                session.add(GlobalLastOpened(name=name, opened_at=time.time()))
            await session.commit()

    async def read_last_opened(self) -> dict[str, float]:
        """Read last-opened timestamps from global DB."""
        if self._global_session_factory is None:
            return {}
        async with self._global_session_factory() as session:
            result = await session.execute(select(GlobalLastOpened))
            return {row.name: row.opened_at for row in result.scalars().all()}


db_manager = DatabaseManager()


def async_session():
    if db_manager._session_factory is None:
        raise RuntimeError("No logbook is currently open")
    return db_manager._session_factory()


def global_async_session():
    if db_manager._global_session_factory is None:
        raise RuntimeError("Global database is not open")
    return db_manager._global_session_factory()


async def resolve_setting(key: str, session: AsyncSession, default: str = "") -> str:
    """Read a setting from the logbook DB, falling back to global DB if blank/missing."""
    result = await session.execute(select(Setting).where(Setting.key == key))
    row = result.scalar_one_or_none()
    if row and row.value:
        return row.value
    if key in GLOBAL_DEFAULTABLE_KEYS and db_manager._global_session_factory:
        async with db_manager._global_session_factory() as gdb:
            gdb_result = await gdb.execute(
                select(GlobalSetting).where(GlobalSetting.key == key)
            )
            gdb_row = gdb_result.scalar_one_or_none()
            if gdb_row and gdb_row.value:
                return gdb_row.value
    return default


def cleanup_stale_locks() -> None:
    """Remove .lock and .addr files left behind by dead processes."""
    for lock_path in DB_DIR.glob("*.lock"):
        try:
            with open(lock_path, "r+") as f:
                _lock_exclusive(f)
                _unlock(f)
            # Lock acquired successfully — no live process holds it; remove stale files
            lock_path.unlink(missing_ok=True)
            lock_path.with_suffix(".addr").unlink(missing_ok=True)
            logger.info("Removed stale lock file: %s", lock_path.name)
        except OSError:
            pass  # Genuinely locked by another process


async def init_db() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    cleanup_stale_locks()
    await db_manager.open_global()
    # Check global default_pick_mode if no CLI override or --pick flag
    if (
        not db_manager.picker_mode
        and not db_manager._db_override
        and db_manager._global_session_factory
    ):
        async with db_manager._global_session_factory() as gdb:
            row = (
                await gdb.execute(
                    select(GlobalSetting).where(
                        GlobalSetting.key == "default_pick_mode"
                    )
                )
            ).scalar_one_or_none()
            if not row or row.value != "false":
                db_manager.picker_mode = True
    if db_manager.picker_mode:
        return
    # Check global DB for default logbook name if no CLI override
    if not db_manager._db_override and db_manager._global_session_factory:
        async with db_manager._global_session_factory() as gdb:
            row = (
                await gdb.execute(
                    select(GlobalSetting).where(
                        GlobalSetting.key == "default_logbook_name"
                    )
                )
            ).scalar_one_or_none()
            if row and row.value:
                db_manager._db_override = row.value
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


def _add_missing_columns_global(conn):
    insp = inspect(conn)
    for table_name, table in GlobalBase.metadata.tables.items():
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


async def get_global_session() -> AsyncGenerator[AsyncSession, None]:
    if db_manager._global_session_factory is None:
        raise HTTPException(status_code=503, detail="Global database is not open")
    async with db_manager._global_session_factory() as session:
        yield session
