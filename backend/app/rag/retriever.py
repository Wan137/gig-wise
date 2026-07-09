"""Query-time interface to the Chroma vector store built by ingest.py."""
from __future__ import annotations

import logging
from dataclasses import dataclass

import chromadb

from app.config import get_settings
from app.rag.embeddings import LocalEmbeddingFunction
from app.rag.ingest import COLLECTION_NAME

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    content: str
    source_document: str
    section: str
    source_url: str
    score: float


class RagIndexNotBuiltError(RuntimeError):
    """Raised when the Chroma collection hasn't been built yet."""


class TaxKnowledgeRetriever:
    """Wraps Chroma similarity search over the LHDN/EPF/SOCSO knowledge base."""

    def __init__(self, persist_dir: str | None = None):
        settings = get_settings()
        self._persist_dir = persist_dir or settings.chroma_persist_dir
        self._client = chromadb.PersistentClient(path=self._persist_dir)
        self._embedding_fn = LocalEmbeddingFunction()
        try:
            self._collection = self._client.get_collection(
                COLLECTION_NAME, embedding_function=self._embedding_fn
            )
        except Exception as exc:
            raise RagIndexNotBuiltError(
                f"RAG collection '{COLLECTION_NAME}' not found at {self._persist_dir}. "
                "Run `python scripts/ingest_documents.py` first."
            ) from exc

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        if not query or not query.strip():
            return []

        results = self._collection.query(query_texts=[query], n_results=top_k)

        docs = (results.get("documents") or [[]])[0]
        metadatas = (results.get("metadatas") or [[]])[0]
        distances = (results.get("distances") or [[]])[0]

        chunks: list[RetrievedChunk] = []
        for doc, meta, distance in zip(docs, metadatas, distances):
            chunks.append(
                RetrievedChunk(
                    content=doc,
                    source_document=meta.get("source_document", "Unknown source"),
                    section=meta.get("section", ""),
                    source_url=meta.get("source_url", ""),
                    score=1.0 - distance,  # cosine distance -> similarity
                )
            )
        return chunks
