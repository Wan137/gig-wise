"""Shared embedding function so ingestion and query time use the identical model.

Uses Chroma's bundled ONNX export of all-MiniLM-L6-v2 (same weights as the
sentence-transformers checkpoint, same 384-dim vector space) rather than
loading the model through the full sentence-transformers/torch stack - torch
alone pushes runtime memory well past the 512MB free-tier ceiling on hosts
like Render, while onnxruntime (already a chromadb dependency) needs a
fraction of that. Still wrapped in our own class rather than passed as
`chromadb`'s literal `DefaultEmbeddingFunction` so the model is loaded once
and reused, instead of re-initializing an ONNX session on every call.
"""
from __future__ import annotations

from chromadb import Documents, EmbeddingFunction, Embeddings
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

_model: ONNXMiniLM_L6_V2 | None = None


def _get_model() -> ONNXMiniLM_L6_V2:
    global _model
    if _model is None:
        _model = ONNXMiniLM_L6_V2()
    return _model


class LocalEmbeddingFunction(EmbeddingFunction):
    """Wraps Chroma's local ONNX MiniLM model as a reusable embedding function."""

    def __init__(self) -> None:
        pass

    @staticmethod
    def name() -> str:
        return "gigwise-local-onnx-minilm"

    def __call__(self, input: Documents) -> Embeddings:
        model = _get_model()
        return model(input)
