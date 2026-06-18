# PaperTrail — Local Document Intelligence

**Upload, extract, search, and analyze documents — all local, no cloud.**

PaperTrail merges three existing tools into one unified platform:

| Source | Domain | Core Capability |
|--------|--------|----------------|
| **ArchPlanReview** | Plans & PDFs | Upload PDFs/images, extract text (PyMuPDF/OCR), FTS5 search |
| **Knowledge Assistant** | Notes & Docs | Ingest text, chunk, keyword-retrieval Q&A with citations |
| **ScanExcel** | Receipts & Invoices | Parse unstructured text into structured rows, CSV export |

**What they share:** FastAPI backend, SQLite storage, no cloud, no API keys.

---

## Quick Start

```bash
# Install
cd papertrail
pip install -e .

# Run
uvicorn papertrail:app --host 127.0.0.1 --port 8000 --reload
```

Open **http://127.0.0.1:8000/docs** for the interactive API browser.

### Optional extras

```bash
# For PDF/image plan processing
pip install -e ".[plans]"

# For OCR (requires Tesseract binary installed system-wide)
pip install -e ".[ocr]"

# For development
pip install -e ".[dev]"
```

---

## API

All endpoints under `/api/v1/`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Health check with document counts by domain |
| `POST` | `/api/v1/documents` | Upload PDF/image for text extraction |
| `GET` | `/api/v1/documents` | List uploaded plan documents |
| `GET` | `/api/v1/documents/{id}/pages/{n}` | Get extracted page text |
| `POST` | `/api/v1/ingest` | Ingest text as knowledge chunks |
| `POST` | `/api/v1/ask` | Ask a question against ingested chunks |
| `POST` | `/api/v1/process` | Parse unstructured text into structured rows |
| `POST` | `/api/v1/upload` | Upload a text file for row extraction |
| `GET` | `/api/v1/export.csv` | Export all receipt rows as CSV |
| `GET` | `/api/v1/search` | Full-text search across all domains |

---

## Architecture

```
papertrail/
├── papertrail/
│   ├── __init__.py          # create_app() factory + module-level app
│   ├── core/
│   │   ├── config.py        # Settings (paths, tunables)
│   │   ├── database.py      # Unified SQLite + FTS5 schema
│   │   └── models.py        # Pydantic models + dataclasses
│   ├── adapters/
│   │   ├── search.py        # FTS5 SearchIndex + PyMuPDF/OCR extractors
│   │   ├── knowledge.py     # Chunking, keyword scoring, Q&A
│   │   └── scan.py          # Receipt/invoice regex parsing, CSV export
│   └── api/
│       ├── health.py        # GET /api/v1/health
│       ├── documents.py     # Upload, list, get page
│       ├── knowledge.py     # POST /api/v1/ingest, /ask
│       ├── scan.py          # POST /api/v1/process, /upload, GET /export.csv
│       └── search.py        # GET /api/v1/search
├── tests/
├── pyproject.toml
└── README.md
```

---

## Storage

Single SQLite database with a `documents` table using a `domain` discriminator:

| Domain | What It Stores |
|--------|---------------|
| `plan` | A parent document (PDF/image upload) |
| `plan_page` | One page of extracted plan text |
| `knowledge_chunk` | A text chunk from ingested notes |
| `receipt` | A parsed receipt/invoice with structured rows |

A unified FTS5 index (`documents_fts`) enables cross-domain search via BM25 ranking. All data stays on your machine.
