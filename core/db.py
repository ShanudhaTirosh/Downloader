"""
ShanuFx Downloader — SQLite history + settings persistence.
Thread-safe database with dedicated writer thread.
"""

import json
import queue
import sqlite3
import threading
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from config import DB_PATH, get_default_settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Thread-safe SQLite database manager with a dedicated writer queue."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._db_path = db_path
        self._write_queue: queue.Queue[tuple[str, tuple, Optional[threading.Event]]] = queue.Queue()
        self._running = True
        self._lock = threading.Lock()

        self._init_db()

        self._writer_thread = threading.Thread(target=self._writer_loop, daemon=True, name="DB-Writer")
        self._writer_thread.start()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a new SQLite connection for the current thread."""
        conn = sqlite3.connect(str(self._db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        """Create all tables if they don't exist."""
        conn = self._get_connection()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS downloads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    filepath TEXT,
                    size_bytes INTEGER DEFAULT 0,
                    downloaded_bytes INTEGER DEFAULT 0,
                    speed_avg REAL DEFAULT 0,
                    source_type TEXT DEFAULT 'http',
                    platform TEXT DEFAULT '',
                    status TEXT DEFAULT 'queued',
                    format TEXT DEFAULT '',
                    quality TEXT DEFAULT '',
                    error_message TEXT DEFAULT '',
                    segments INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    metadata_json TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS torrent_state (
                    info_hash TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    save_path TEXT NOT NULL,
                    total_size INTEGER DEFAULT 0,
                    downloaded INTEGER DEFAULT 0,
                    uploaded INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'paused',
                    added_at TEXT NOT NULL,
                    completed_at TEXT,
                    resume_data BLOB,
                    file_priorities TEXT DEFAULT '[]',
                    metadata_json TEXT DEFAULT '{}'
                );

                CREATE INDEX IF NOT EXISTS idx_downloads_status ON downloads(status);
                CREATE INDEX IF NOT EXISTS idx_downloads_created ON downloads(created_at);
                CREATE INDEX IF NOT EXISTS idx_downloads_source ON downloads(source_type);
                CREATE INDEX IF NOT EXISTS idx_downloads_platform ON downloads(platform);
                CREATE INDEX IF NOT EXISTS idx_torrent_state_added ON torrent_state(added_at);
                CREATE INDEX IF NOT EXISTS idx_torrent_state_status ON torrent_state(status);
            """)
            conn.commit()
            self._init_default_settings(conn)
            logger.info("Database initialized at %s", self._db_path)
        finally:
            conn.close()

    def _init_default_settings(self, conn: sqlite3.Connection) -> None:
        """Insert default settings if they don't exist yet."""
        defaults = get_default_settings()
        for key, value in defaults.items():
            existing = conn.execute("SELECT key FROM settings WHERE key = ?", (key,)).fetchone()
            if existing is None:
                conn.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?)",
                    (key, json.dumps(value)),
                )
        conn.commit()

    def _writer_loop(self) -> None:
        """Dedicated writer thread — consumes write queue sequentially."""
        conn = self._get_connection()
        try:
            while self._running:
                try:
                    sql, params, event = self._write_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                try:
                    conn.execute(sql, params)
                    conn.commit()
                except sqlite3.Error as e:
                    logger.error("DB write error: %s | SQL: %s", e, sql)
                    try:
                        conn.rollback()
                    except sqlite3.Error:
                        pass
                finally:
                    if event is not None:
                        event.set()
                    self._write_queue.task_done()
        finally:
            conn.close()

    def _enqueue_write(self, sql: str, params: tuple = (), wait: bool = False) -> None:
        """Enqueue a write operation for the writer thread."""
        event = threading.Event() if wait else None
        self._write_queue.put((sql, params, event))
        if event is not None:
            event.wait(timeout=5.0)

    def _read(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Execute a read query on a per-call connection (thread-safe)."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(sql, params)
            return cursor.fetchall()
        finally:
            conn.close()

    def _read_one(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        """Read a single row."""
        rows = self._read(sql, params)
        return rows[0] if rows else None

    # ── Downloads CRUD ────────────────────────────────────────────────────────

    def add_download(
        self,
        url: str,
        filename: str,
        filepath: str = "",
        size_bytes: int = 0,
        source_type: str = "http",
        platform: str = "",
        status: str = "queued",
        fmt: str = "",
        quality: str = "",
        segments: int = 1,
        metadata: Optional[dict] = None,
    ) -> int:
        """Add a new download record and return its ID."""
        now = datetime.now().isoformat()
        meta_json = json.dumps(metadata or {})

        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """INSERT INTO downloads
                   (url, filename, filepath, size_bytes, source_type, platform,
                    status, format, quality, segments, created_at, metadata_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (url, filename, filepath, size_bytes, source_type, platform,
                 status, fmt, quality, segments, now, meta_json),
            )
            conn.commit()
            return cursor.lastrowid or 0
        finally:
            conn.close()

    def update_download(self, download_id: int, **kwargs: Any) -> None:
        """Update download fields by ID."""
        if not kwargs:
            return
        set_clauses = ", ".join(f"{k} = ?" for k in kwargs)
        values = tuple(kwargs.values()) + (download_id,)
        self._enqueue_write(
            f"UPDATE downloads SET {set_clauses} WHERE id = ?",
            values,
        )

    def complete_download(self, download_id: int, filepath: str, size_bytes: int, speed_avg: float) -> None:
        """Mark a download as complete."""
        now = datetime.now().isoformat()
        self._enqueue_write(
            """UPDATE downloads SET status = 'complete', filepath = ?, size_bytes = ?,
               speed_avg = ?, downloaded_bytes = ?, completed_at = ? WHERE id = ?""",
            (filepath, size_bytes, speed_avg, size_bytes, now, download_id),
        )

    def fail_download(self, download_id: int, error_message: str) -> None:
        """Mark a download as failed."""
        self._enqueue_write(
            "UPDATE downloads SET status = 'failed', error_message = ? WHERE id = ?",
            (error_message, download_id),
        )

    def get_download(self, download_id: int) -> Optional[dict]:
        """Get a download record by ID."""
        row = self._read_one("SELECT * FROM downloads WHERE id = ?", (download_id,))
        return dict(row) if row else None

    def get_downloads(
        self,
        status: Optional[str] = None,
        source_type: Optional[str] = None,
        platform: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Get downloads with optional filters."""
        conditions = []
        params: list[Any] = []

        if status:
            conditions.append("status = ?")
            params.append(status)
        if source_type:
            conditions.append("source_type = ?")
            params.append(source_type)
        if platform:
            conditions.append("platform = ?")
            params.append(platform)
        if search:
            conditions.append("(filename LIKE ? OR url LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.extend([limit, offset])

        sql = f"""
            SELECT * FROM (
                SELECT id, url, filename, filepath, size_bytes, downloaded_bytes, speed_avg, source_type, platform, status, format, quality, error_message, segments, created_at, completed_at, metadata_json 
                FROM downloads
                UNION ALL
                SELECT info_hash as id, 'magnet:?xt=urn:btih:' || info_hash as url, name as filename, save_path as filepath, total_size as size_bytes, downloaded as downloaded_bytes, 0 as speed_avg, 'torrent' as source_type, '' as platform, status, '' as format, '' as quality, '' as error_message, 1 as segments, added_at as created_at, completed_at, metadata_json 
                FROM torrent_state
            ) AS combined
            {where} 
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
        """
        rows = self._read(sql, tuple(params))
        return [dict(r) for r in rows]

    def get_active_downloads(self) -> list[dict]:
        """Get all non-complete downloads."""
        rows = self._read(
            "SELECT * FROM downloads WHERE status IN ('downloading', 'queued', 'paused') ORDER BY created_at DESC"
        )
        return [dict(r) for r in rows]

    def delete_download(self, download_id: Any) -> None:
        """Delete a download record (from downloads or torrent_state)."""
        if isinstance(download_id, str) and len(download_id) >= 32:
            self._enqueue_write("DELETE FROM torrent_state WHERE info_hash = ?", (download_id,))
        else:
            self._enqueue_write("DELETE FROM downloads WHERE id = ?", (download_id,))

    def clear_history(self) -> None:
        """Clear all history (downloads and completed torrents)."""
        self._enqueue_write("DELETE FROM downloads")
        self._enqueue_write("DELETE FROM torrent_state WHERE status IN ('complete', 'finished', 'seeding')")

    def get_download_stats(self) -> dict[str, Any]:
        """Get aggregate download statistics."""
        conn = self._get_connection()
        try:
            total_dl = conn.execute("SELECT COALESCE(SUM(size_bytes), 0) FROM downloads WHERE status = 'complete'").fetchone()
            total_torrent = conn.execute("SELECT COALESCE(SUM(total_size), 0) FROM torrent_state WHERE status IN ('complete', 'finished', 'seeding')").fetchone()
            total_bytes = (total_dl[0] if total_dl else 0) + (total_torrent[0] if total_torrent else 0)

            count_dl = conn.execute("SELECT COUNT(*) FROM downloads WHERE status = 'complete'").fetchone()
            count_torrent = conn.execute("SELECT COUNT(*) FROM torrent_state WHERE status IN ('complete', 'finished', 'seeding')").fetchone()
            total_count = (count_dl[0] if count_dl else 0) + (count_torrent[0] if count_torrent else 0)

            avg_speed = conn.execute("SELECT COALESCE(AVG(speed_avg), 0) FROM downloads WHERE status = 'complete' AND speed_avg > 0").fetchone()
            active = conn.execute("SELECT COUNT(*) FROM downloads WHERE status = 'downloading'").fetchone()
            queued = conn.execute("SELECT COUNT(*) FROM downloads WHERE status = 'queued'").fetchone()
            failed = conn.execute("SELECT COUNT(*) FROM downloads WHERE status = 'failed'").fetchone()

            daily_stats = conn.execute("""
                SELECT day, SUM(count) as count, SUM(total_bytes) as total_bytes FROM (
                    SELECT DATE(completed_at) as day, COUNT(*) as count, SUM(size_bytes) as total_bytes
                    FROM downloads
                    WHERE status = 'complete' AND completed_at IS NOT NULL
                      AND completed_at >= DATE('now', '-30 days')
                    GROUP BY DATE(completed_at)
                    UNION ALL
                    SELECT DATE(completed_at) as day, COUNT(*) as count, SUM(total_size) as total_bytes
                    FROM torrent_state
                    WHERE status IN ('complete', 'finished', 'seeding') AND completed_at IS NOT NULL
                      AND completed_at >= DATE('now', '-30 days')
                    GROUP BY DATE(completed_at)
                ) GROUP BY day ORDER BY day
            """).fetchall()

            return {
                "total_bytes": total_bytes,
                "total_count": total_count,
                "avg_speed": avg_speed[0] if avg_speed else 0,
                "active_count": active[0] if active else 0,
                "queued_count": queued[0] if queued else 0,
                "failed_count": failed[0] if failed else 0,
                "daily_stats": [dict(d) for d in daily_stats],
            }
        finally:
            conn.close()

    # ── Settings CRUD ─────────────────────────────────────────────────────────

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value by key."""
        row = self._read_one("SELECT value FROM settings WHERE key = ?", (key,))
        if row is None:
            return default
        try:
            return json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            return row["value"]

    def set_setting(self, key: str, value: Any) -> None:
        """Set a setting value (upsert)."""
        self._enqueue_write(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, json.dumps(value)),
        )

    def get_all_settings(self) -> dict[str, Any]:
        """Get all settings as a dictionary."""
        rows = self._read("SELECT key, value FROM settings")
        result: dict[str, Any] = {}
        for row in rows:
            try:
                result[row["key"]] = json.loads(row["value"])
            except (json.JSONDecodeError, TypeError):
                result[row["key"]] = row["value"]
        return result

    def reset_settings(self) -> None:
        """Reset all settings to defaults."""
        defaults = get_default_settings()
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM settings")
            for key, value in defaults.items():
                conn.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?)",
                    (key, json.dumps(value)),
                )
            conn.commit()
        finally:
            conn.close()

    # ── Torrent State CRUD ────────────────────────────────────────────────────

    def save_torrent_state(
        self,
        info_hash: str,
        name: str,
        save_path: str,
        total_size: int = 0,
        status: str = "paused",
        resume_data: Optional[bytes] = None,
        file_priorities: Optional[list[int]] = None,
    ) -> None:
        """Save or update torrent state."""
        now = datetime.now().isoformat()
        priorities_json = json.dumps(file_priorities or [])

        conn = self._get_connection()
        try:
            existing = conn.execute("SELECT info_hash FROM torrent_state WHERE info_hash = ?", (info_hash,)).fetchone()
            if existing:
                conn.execute(
                    """UPDATE torrent_state SET name = ?, save_path = ?, total_size = ?,
                       status = ?, resume_data = ?, file_priorities = ? WHERE info_hash = ?""",
                    (name, save_path, total_size, status, resume_data, priorities_json, info_hash),
                )
            else:
                conn.execute(
                    """INSERT INTO torrent_state
                       (info_hash, name, save_path, total_size, status, added_at, resume_data, file_priorities)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (info_hash, name, save_path, total_size, status, now, resume_data, priorities_json),
                )
            conn.commit()
        finally:
            conn.close()

    def get_torrent_states(self) -> list[dict]:
        """Get all saved torrent states."""
        rows = self._read("SELECT * FROM torrent_state ORDER BY added_at DESC")
        return [dict(r) for r in rows]

    def delete_torrent_state(self, info_hash: str) -> None:
        """Delete a torrent state record."""
        self._enqueue_write("DELETE FROM torrent_state WHERE info_hash = ?", (info_hash,))

    def update_torrent_resume_data(self, info_hash: str, resume_data: bytes) -> None:
        """Update resume data for a torrent."""
        self._enqueue_write(
            "UPDATE torrent_state SET resume_data = ? WHERE info_hash = ?",
            (resume_data, info_hash),
        )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def shutdown(self) -> None:
        """Gracefully shut down the writer thread."""
        self._running = False
        self._write_queue.join()
        if self._writer_thread.is_alive():
            self._writer_thread.join(timeout=3.0)
        logger.info("Database manager shut down.")
