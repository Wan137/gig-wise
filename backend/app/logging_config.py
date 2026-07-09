"""Central logging setup, called once at app startup."""
from __future__ import annotations

import logging
import sys

from app.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # Avoid duplicate handlers if this is called more than once (e.g. under
    # uvicorn's --reload, which re-imports the module).
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(handler)

    # These libraries are extremely chatty at INFO (one line per HTTP HEAD
    # request to huggingface.co, etc.) - keep them at WARNING unless we're
    # specifically debugging them.
    for noisy_logger in ("httpx", "httpcore", "urllib3", "chromadb", "sentence_transformers"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
