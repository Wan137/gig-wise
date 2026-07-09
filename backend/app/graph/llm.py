"""Shared Groq LLM client factory used by every graph node."""
from __future__ import annotations

from functools import lru_cache

from langchain_groq import ChatGroq

from app.config import get_settings

GROQ_MODEL = "llama-3.3-70b-versatile"


@lru_cache
def get_llm(temperature: float = 0.2) -> ChatGroq:
    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Get a free key at https://console.groq.com and set it in backend/.env."
        )
    return ChatGroq(model=GROQ_MODEL, api_key=settings.groq_api_key, temperature=temperature)
