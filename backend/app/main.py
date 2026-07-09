"""FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth.router import router as auth_router
from app.config import get_settings
from app.logging_config import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is managed exclusively through Alembic migrations
    # (app/db/migrations/) - run `alembic upgrade head` before starting the
    # server. No create_all() fallback here, so there's only one path that
    # can create or change tables, and it always leaves alembic_version in
    # sync with the actual schema.
    logger.info("Gig-Wise API starting up (environment=%s)", settings.environment)
    yield
    logger.info("Gig-Wise API shutting down")


app = FastAPI(
    title="Gig-Wise API",
    description="Multi-agent financial copilot for Malaysian gig economy workers.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # exc.errors() can include a `ctx` field holding the raw exception object
    # from a custom validator (e.g. our password-strength check) - that's not
    # JSON-serializable on its own, so it must go through jsonable_encoder
    # before it can be returned as a response body.
    errors = jsonable_encoder(exc.errors())
    logger.warning("Validation error on %s %s: %s", request.method, request.url.path, errors)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": "Request could not be validated.", "errors": errors},
    )


@app.exception_handler(HTTPException)
async def http_exception_logging_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if exc.status_code >= 500:
        logger.error("HTTP %s on %s %s: %s", exc.status_code, request.method, request.url.path, exc.detail)
    return await http_exception_handler(request, exc)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Last-resort safety net: a bug in one agent/tool must never crash the
    # whole request or leak a stack trace to the client - the frontend should
    # always get a clear, user-safe message to display instead of a blank
    # failure or a raw 500 page.
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Something went wrong on our end. Please try again in a moment."},
    )


@app.get("/health", tags=["meta"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth_router)
