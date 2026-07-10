#!/bin/sh
# Migrations must run against the live DB at container start (not baked into
# the image like the Chroma index), since DATABASE_URL/credentials are only
# known at runtime.
set -e

alembic upgrade head

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
