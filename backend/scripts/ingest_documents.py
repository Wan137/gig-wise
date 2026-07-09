#!/usr/bin/env python
"""CLI entry point: rebuilds the Chroma vector index from source documents.

Usage (from the backend/ directory, with the venv active):
    python scripts/ingest_documents.py
"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

# Allow `import app...` when this script is invoked directly rather than as a
# module, regardless of the caller's current working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.rag.ingest import build_index  # noqa: E402


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    start = time.time()
    count = build_index()
    elapsed = time.time() - start
    print(f"Indexed {count} chunks in {elapsed:.1f}s.")


if __name__ == "__main__":
    main()
