FROM python:3.12-slim AS base

# Tesseract is a system binary, not a Python package - required by
# pytesseract for the Expense Tracker's OCR step. libgl1/libglib2.0-0 are
# runtime deps of opencv-python-headless.
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Bake the Chroma index into the image at build time: the source documents
# are static and already committed, so there's no reason to redo this work
# (network fetch of the embedding model + PDF parsing) on every container
# start. The free hosting tier this targets has no persistent disk anyway -
# app data lives in Postgres (DATABASE_URL) instead of local files.
RUN python scripts/ingest_documents.py

RUN chmod +x start.sh

EXPOSE 8000

CMD ["./start.sh"]
