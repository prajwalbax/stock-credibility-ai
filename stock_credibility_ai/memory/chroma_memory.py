from __future__ import annotations

import logging
import math
from typing import Any

from stock_credibility_ai.utils.config import get_settings

logger = logging.getLogger(__name__)


class ChromaMemory:
    """Optional ChromaDB-backed memory for analyst notes."""

    def __init__(self, collection_name: str = "stock_credibility_memory") -> None:
        self.collection_name = collection_name
        self._collection: Any | None = None

    def connect(self) -> None:
        if self._collection is not None:
            return
        try:
            import chromadb

            settings = get_settings()
            client = chromadb.PersistentClient(path=settings.chroma_path)
            self._collection = client.get_or_create_collection(
                self.collection_name,
                embedding_function=None,
            )
        except Exception as exc:
            logger.warning("ChromaDB unavailable; memory will be in-state only: %s", exc)
            self._collection = None

    def add_note(self, ticker: str, note: str) -> None:
        self.connect()
        if self._collection is None:
            return
        doc_id = f"{ticker}:{abs(hash(note))}"
        self._collection.upsert(
            ids=[doc_id],
            documents=[note],
            metadatas=[{"ticker": ticker}],
            embeddings=[_hash_embedding(note)],
        )

    def query(self, ticker: str, query_text: str, limit: int = 5) -> list[str]:
        self.connect()
        if self._collection is None:
            return []
        result = self._collection.query(
            query_embeddings=[_hash_embedding(query_text)],
            n_results=limit,
            where={"ticker": ticker},
        )
        return list(result.get("documents", [[]])[0])


def _hash_embedding(text: str, dimensions: int = 64) -> list[float]:
    vector = [0.0] * dimensions
    for token in text.lower().split():
        index = abs(hash(token)) % dimensions
        vector[index] += 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]
