"""Shared embedding function so ingestion and query time use the identical model.

Chroma's default embedding function is a different (ONNX MiniLM) model than the
sentence-transformers one specified in Settings.embedding_model. Using our own
wrapper guarantees the vectors written at ingest time and the vectors used to
query at request time always come from the same model.
"""
from __future__ import annotations

from chromadb import Documents, EmbeddingFunction, Embeddings

from app.config import get_settings

_model = None
_model_name: str | None = None


def _get_model():
    global _model, _model_name
    settings = get_settings()
    if _model is None or _model_name != settings.embedding_model:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(settings.embedding_model)
        _model_name = settings.embedding_model
    return _model


class LocalEmbeddingFunction(EmbeddingFunction):
    """Wraps a local sentence-transformers model as a Chroma embedding function."""

    def __init__(self) -> None:
        pass

    @staticmethod
    def name() -> str:
        return "gigwise-local-sentence-transformers"

    def __call__(self, input: Documents) -> Embeddings:
        model = _get_model()
        vectors = model.encode(list(input), normalize_embeddings=True, show_progress_bar=False)
        return vectors.tolist()
