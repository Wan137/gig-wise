"""Application configuration, loaded once from environment variables / .env."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BACKEND_DIR / ".env"), extra="ignore")

    groq_api_key: str = ""

    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    database_url: str = "sqlite:///./gigwise.db"

    chroma_persist_dir: str = str(BACKEND_DIR / "chroma_db")

    # Only needed on Windows local dev when Tesseract isn't on PATH; left blank
    # on Linux/Docker deploy targets where `apt-get install tesseract-ocr` puts
    # it on PATH already.
    tesseract_cmd: str = ""

    upload_dir: str = str(BACKEND_DIR / "uploads")
    max_upload_size_bytes: int = 10 * 1024 * 1024  # 10 MB
    chat_history_limit: int = 10  # most recent messages loaded as context per turn

    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()
