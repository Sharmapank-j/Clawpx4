"""memory/sqlite_store.py — SQLite-backed chat history and key-value store.

Tables
------
chat_history  – ordered conversation turns per user
kv_store      – arbitrary key/value pairs (JSON values)
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Generator, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = os.getenv("SQLITE_DB_PATH", "data/clawpx4.db")


class SQLiteStore:
    """Lightweight SQLite wrapper for chat history and structured data."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or _DEFAULT_DB_PATH
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self._init_db()

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS chat_history (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id   TEXT    NOT NULL,
                    role      TEXT    NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                    content   TEXT    NOT NULL,
                    timestamp TEXT    NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_chat_user
                    ON chat_history(user_id, id);

                CREATE TABLE IF NOT EXISTS kv_store (
                    key       TEXT PRIMARY KEY,
                    value     TEXT NOT NULL,
                    updated   TEXT NOT NULL
                );
                """
            )

    # ------------------------------------------------------------------
    # Chat history
    # ------------------------------------------------------------------

    def add_message(self, user_id: str, role: str, content: str) -> None:
        """Append a message to the chat history for *user_id*."""
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO chat_history (user_id, role, content, timestamp) "
                "VALUES (?, ?, ?, ?)",
                (str(user_id), role, content, now),
            )

    def get_history(
        self, user_id: str, limit: int = 20
    ) -> List[dict]:
        """Return the last *limit* messages for *user_id*, oldest first."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT role, content FROM chat_history "
                "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (str(user_id), limit),
            ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    def clear_history(self, user_id: str) -> None:
        """Delete all chat history for *user_id*."""
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM chat_history WHERE user_id = ?",
                (str(user_id),),
            )

    # ------------------------------------------------------------------
    # Key-value store
    # ------------------------------------------------------------------

    def set(self, key: str, value: Any) -> None:
        """Persist *value* (JSON-serialisable) under *key*."""
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO kv_store (key, value, updated) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated=excluded.updated",
                (key, json.dumps(value), now),
            )

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve the value stored under *key*, or *default* if absent."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT value FROM kv_store WHERE key = ?", (key,)
            ).fetchone()
        if row is None:
            return default
        return json.loads(row["value"])

    def delete(self, key: str) -> None:
        """Remove *key* from the kv store."""
        with self._conn() as conn:
            conn.execute("DELETE FROM kv_store WHERE key = ?", (key,))


# Module-level singleton
_store: Optional[SQLiteStore] = None


def get_store(db_path: Optional[str] = None) -> SQLiteStore:
    """Return the module-level :class:`SQLiteStore` singleton."""
    global _store
    if _store is None:
        _store = SQLiteStore(db_path)
    return _store
