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
    return ChatGroq(
        model=GROQ_MODEL,
        api_key=settings.groq_api_key,
        temperature=temperature,
        # The underlying Groq SDK retries on 429 using the server's suggested
        # Retry-After delay by default, which can be tens of seconds when the
        # daily quota is nearly exhausted - fine for a background job, bad for
        # a synchronous request a user is waiting on. Fail fast instead: every
        # call site already has a try/except that degrades gracefully (a
        # fallback message or a regex-based extraction), so a quick failure
        # reaches that fallback in seconds rather than leaving the user
        # staring at a spinner for half a minute.
        max_retries=0,
        timeout=20.0,
    )
