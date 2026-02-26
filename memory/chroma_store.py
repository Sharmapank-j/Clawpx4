"""memory/chroma_store.py — ChromaDB vector memory for semantic recall.

ChromaDB stores embedded text chunks so Clawpx4 can retrieve relevant context
from past conversations or documents using semantic similarity search.

Environment variables:
    CHROMA_DB_PATH – directory for ChromaDB persistence (default: data/chroma_db)
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_CHROMA_PATH = os.getenv("CHROMA_DB_PATH", "data/chroma_db")
_COLLECTION_NAME = "clawpx4_memory"


class ChromaStore:
    """Semantic memory store backed by ChromaDB with local persistence."""

    def __init__(self, persist_directory: Optional[str] = None) -> None:
        self.persist_directory = persist_directory or _DEFAULT_CHROMA_PATH
        os.makedirs(self.persist_directory, exist_ok=True)
        self._client = None
        self._collection = None

    # ------------------------------------------------------------------
    # Lazy initialisation (avoids importing chromadb at module load time,
    # keeping startup fast on low-RAM devices)
    # ------------------------------------------------------------------

    def _get_collection(self):
        if self._collection is None:
            try:
                import chromadb
                from chromadb.config import Settings
            except ImportError as exc:
                raise ImportError(
                    "chromadb is not installed. "
                    "Run: pip install chromadb"
                ) from exc

            self._client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Add or update a document in the vector store.

        Args:
            doc_id:   Unique identifier for the document.
            text:     The text to embed and store.
            metadata: Optional dict of filterable metadata.
        """
        collection = self._get_collection()
        collection.upsert(
            ids=[doc_id],
            documents=[text],
            metadatas=[metadata or {}],
        )
        logger.debug("ChromaStore: upserted doc_id=%s", doc_id)

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        where: Optional[dict] = None,
    ) -> List[dict]:
        """Retrieve the *n_results* most semantically similar documents.

        Args:
            query_text: The query string.
            n_results:  Number of results to return.
            where:      Optional ChromaDB metadata filter.

        Returns:
            List of dicts with keys ``id``, ``text``, ``metadata``,
            and ``distance``.
        """
        collection = self._get_collection()
        kwargs: dict = {"query_texts": [query_text], "n_results": n_results}
        if where:
            kwargs["where"] = where

        results = collection.query(**kwargs)

        output: List[dict] = []
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc_id, doc, meta, dist in zip(ids, documents, metadatas, distances):
            output.append(
                {
                    "id": doc_id,
                    "text": doc,
                    "metadata": meta,
                    "distance": dist,
                }
            )
        return output

    def delete(self, doc_id: str) -> None:
        """Remove a document by its ID."""
        collection = self._get_collection()
        collection.delete(ids=[doc_id])
        logger.debug("ChromaStore: deleted doc_id=%s", doc_id)

    def count(self) -> int:
        """Return the number of documents in the collection."""
        return self._get_collection().count()


# Module-level singleton
_store: Optional[ChromaStore] = None


def get_store(persist_directory: Optional[str] = None) -> ChromaStore:
    """Return the module-level :class:`ChromaStore` singleton."""
    global _store
    if _store is None:
        _store = ChromaStore(persist_directory)
    return _store
