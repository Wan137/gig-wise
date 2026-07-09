"""Builds the Chroma vector index from the public LHDN/EPF/SOCSO source documents.

Chunking keeps page numbers (for PDFs) and section headers (for the curated
.txt extracts) as metadata, because the Tax Advisor agent must cite the
specific document and section behind every claim it makes - a chunk with no
traceable location can't be verified against its source later by the
guardrails layer.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

logger = logging.getLogger(__name__)

DOCUMENTS_DIR = Path(__file__).resolve().parent / "documents"
COLLECTION_NAME = "gigwise_tax_knowledge"

# Human-readable titles + origin URLs for each source file, kept in sync with
# documents/SOURCES.md. PDFs don't carry this metadata inline, so it lives here.
DOCUMENT_METADATA: dict[str, dict[str, str]] = {
    "lhdn_individual_business_income_guide.pdf": {
        "title": "LHDN: Individual Business Income (official leaflet)",
        "url": "https://phl.hasil.gov.my/pdf/pdfam/003a.pdf",
    },
    "lhdn_allowable_disallowed_expenses.pdf": {
        "title": "LHDN: Allowable & Disallowed Expenses",
        "url": "https://phl.hasil.gov.my/pdf/pdfam/Allowable_And_Disallowed_Expenses_Slide.pdf",
    },
    "lhdn_form_b_explanatory_notes_2024.pdf": {
        "title": "LHDN: Form B (Business Income) Explanatory Notes, YA2024",
        "url": "https://www.hasil.gov.my/media/eaglbe10/explanatory_notes_b2024_2.pdf",
    },
    "lhdn_taxation_individual_business_income_article.pdf": {
        "title": "LHDN: Taxation on Individual Business Income (The Star, 19 Jun 2023)",
        "url": "https://www.hasil.gov.my/media/i3pfxazp/taxation-on-individual-business-income_the-star_19062023.pdf",
    },
    "lhdn_tax_relief_ya2025.pdf": {
        "title": "LHDN: Tax Relief Table, YA2025",
        "url": "https://www.hasil.gov.my/media/muob0jyz/tax-relief-ya-2025.pdf",
    },
    "lhdn_tax_rate_schedule.txt": {
        "title": "LHDN: Resident Individual Tax Rate Schedule",
        "url": "https://www.hasil.gov.my/en/individual/individual-life-cycle/income-declaration/tax-rate/",
    },
    "kwsp_i_saraan.txt": {
        "title": "KWSP: i-Saraan Voluntary Contributions for the Self-Employed",
        "url": "https://www.kwsp.gov.my/en/member/savings/i-saraan",
    },
    "kwsp_i_saraan_plus.txt": {
        "title": "KWSP: i-Saraan Plus for e-Hailing & p-Hailing Drivers",
        "url": "https://www.kwsp.gov.my/en/member/savings/i-saraan-plus",
    },
    "perkeso_sksps_self_employed.txt": {
        "title": "PERKESO: Self-Employment Social Security Scheme (SKSPS)",
        "url": "https://www.perkeso.gov.my/en/our-services/protection/self-employed.html",
    },
    "socso_sksps_flyer_2022.pdf": {
        "title": "PERKESO: SKSPS Flyer (2022)",
        "url": "https://www.perkeso.gov.my/images/sps/risalah/FLYERS_SKSPS_2022_EN_compressed.pdf",
    },
}

_SECTION_HEADER_RE = re.compile(r"^==\s*(.+?)\s*==$")
_MIN_CHUNK_CHARS = 40


@dataclass
class SourceChunk:
    content: str
    source_document: str   # human-readable title, shown in citations
    source_file: str        # filename, for internal tracing/debugging
    section: str              # "Page N" for PDFs, or a section heading for .txt
    source_url: str


def _new_splitter() -> RecursiveCharacterTextSplitter:
    # ~800 chars stays comfortably under the 256-token window of
    # all-MiniLM-L6-v2 for English text, with enough overlap that a fact
    # split across a chunk boundary is still findable in the neighboring chunk.
    return RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=120,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def _extract_pdf_chunks(path: Path, splitter: RecursiveCharacterTextSplitter) -> list[SourceChunk]:
    meta = DOCUMENT_METADATA.get(path.name, {"title": path.stem, "url": ""})
    reader = PdfReader(str(path))
    chunks: list[SourceChunk] = []
    for page_num, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            continue
        for piece in splitter.split_text(text):
            piece = piece.strip()
            if len(piece) < _MIN_CHUNK_CHARS:
                continue
            chunks.append(
                SourceChunk(
                    content=piece,
                    source_document=meta["title"],
                    source_file=path.name,
                    section=f"Page {page_num}",
                    source_url=meta["url"],
                )
            )
    return chunks


def _extract_txt_chunks(path: Path, splitter: RecursiveCharacterTextSplitter) -> list[SourceChunk]:
    meta = DOCUMENT_METADATA.get(path.name, {"title": path.stem, "url": ""})
    raw = path.read_text(encoding="utf-8")

    # Split into (section_title, section_body) using "== Heading ==" markers.
    # Everything before the first heading (the SOURCE/TITLE/URL/NOTE preamble)
    # becomes an "Overview" section.
    sections: list[tuple[str, list[str]]] = [("Overview", [])]
    for line in raw.splitlines():
        match = _SECTION_HEADER_RE.match(line.strip())
        if match:
            sections.append((match.group(1), []))
        else:
            sections[-1][1].append(line)

    chunks: list[SourceChunk] = []
    for section_title, lines in sections:
        body = "\n".join(lines).strip()
        if not body:
            continue
        for piece in splitter.split_text(body):
            piece = piece.strip()
            if len(piece) < _MIN_CHUNK_CHARS:
                continue
            chunks.append(
                SourceChunk(
                    content=piece,
                    source_document=meta["title"],
                    source_file=path.name,
                    section=section_title,
                    source_url=meta["url"],
                )
            )
    return chunks


def load_all_chunks(documents_dir: Path = DOCUMENTS_DIR) -> list[SourceChunk]:
    """Loads and chunks every PDF/.txt source document in documents_dir."""
    splitter = _new_splitter()
    chunks: list[SourceChunk] = []
    for path in sorted(documents_dir.iterdir()):
        if path.suffix.lower() == ".pdf":
            file_chunks = _extract_pdf_chunks(path, splitter)
        elif path.suffix.lower() == ".txt":
            file_chunks = _extract_txt_chunks(path, splitter)
        else:
            continue
        logger.info("Loaded %d chunks from %s", len(file_chunks), path.name)
        chunks.extend(file_chunks)
    return chunks


def build_index(persist_dir: str | None = None, documents_dir: Path = DOCUMENTS_DIR) -> int:
    """Rebuilds the Chroma collection from scratch and returns the chunk count."""
    import chromadb

    from app.config import get_settings
    from app.rag.embeddings import LocalEmbeddingFunction

    settings = get_settings()
    target_dir = persist_dir or settings.chroma_persist_dir

    chunks = load_all_chunks(documents_dir)
    if not chunks:
        raise RuntimeError(f"No source documents found in {documents_dir}")

    client = chromadb.PersistentClient(path=target_dir)

    # Rebuild from scratch each run so stale chunks never linger after a
    # source document is edited, replaced, or removed.
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        COLLECTION_NAME,
        embedding_function=LocalEmbeddingFunction(),
        metadata={"hnsw:space": "cosine"},
    )

    ids = [f"{c.source_file}::{i}" for i, c in enumerate(chunks)]
    documents = [c.content for c in chunks]
    metadatas = [
        {
            "source_document": c.source_document,
            "source_file": c.source_file,
            "section": c.section,
            "source_url": c.source_url,
        }
        for c in chunks
    ]

    batch_size = 128
    for start in range(0, len(chunks), batch_size):
        end = start + batch_size
        collection.add(ids=ids[start:end], documents=documents[start:end], metadatas=metadatas[start:end])

    logger.info("Indexed %d chunks into collection '%s' at %s", len(chunks), COLLECTION_NAME, target_dir)
    return len(chunks)
