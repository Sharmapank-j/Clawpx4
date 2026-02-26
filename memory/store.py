"""memory/store.py — Unified memory API for Clawpx4.

Provides a single :class:`Store` object that combines:
* :class:`~memory.sqlite_store.SQLiteStore` — ordered chat history
* :class:`~memory.chroma_store.ChromaStore` — semantic / vector search

Most callers only need :func:`get_store`.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from memory.sqlite_store import SQLiteStore, get_store as _get_sqlite
from memory.chroma_store import ChromaStore, get_store as _get_chroma

logger = logging.getLogger(__name__)


class Store:
    """Unified memory façade — chat history + semantic search."""

    def __init__(
        self,
        sqlite: Optional[SQLiteStore] = None,
        chroma: Optional[ChromaStore] = None,
    ) -> None:
        self._sqlite = sqlite or _get_sqlite()
        self._chroma = chroma or _get_chroma()

    # ------------------------------------------------------------------
    # Chat history (SQLite)
    # ------------------------------------------------------------------

    def save_message(self, user_id: str, role: str, content: str) -> None:
        """Persist a conversation turn and index it in vector memory."""
        self._sqlite.add_message(user_id, role, content)
        # Index in vector store for later semantic retrieval
        doc_id = f"{user_id}:{role}:{content[:40]}"
        try:
            self._chroma.add(
                doc_id=doc_id,
                text=content,
                metadata={"user_id": user_id, "role": role},
            )
        except Exception:
            logger.debug("ChromaDB unavailable — skipping vector index", exc_info=True)

    def get_history(self, user_id: str, limit: int = 20) -> List[dict]:
        """Return the last *limit* conversation turns for *user_id*."""
        return self._sqlite.get_history(user_id, limit=limit)

    def clear_history(self, user_id: str) -> None:
        """Delete all stored messages for *user_id*."""
        self._sqlite.clear_history(user_id)

    # ------------------------------------------------------------------
    # Semantic search (ChromaDB)
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        n_results: int = 5,
        user_id: Optional[str] = None,
    ) -> List[dict]:
        """Return semantically similar past messages.

        Args:
            query:     Free-text query.
            n_results: Number of results to return.
            user_id:   If provided, restrict results to this user.

        Returns:
            List of dicts with ``id``, ``text``, ``metadata``, ``distance``.
        """
        where = {"user_id": user_id} if user_id else None
        try:
            return self._chroma.query(query, n_results=n_results, where=where)
        except Exception:
            logger.debug("ChromaDB unavailable — returning empty search", exc_info=True)
            return []

    # ------------------------------------------------------------------
    # Key-value pass-through
    # ------------------------------------------------------------------

    def set(self, key: str, value: Any) -> None:
        self._sqlite.set(key, value)

    def get(self, key: str, default: Any = None) -> Any:
        return self._sqlite.get(key, default)


# Module-level singleton
_store: Optional[Store] = None


def get_store() -> Store:
    """Return the module-level :class:`Store` singleton."""
    global _store
    if _store is None:
        _store = Store()
    return _store
