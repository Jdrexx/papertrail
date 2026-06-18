"""PaperTrail — Full-text search index and document text extraction.

Merged from the ArchPlanReview ``SearchIndex``, PyMuPDF extractors,
and Tesseract OCR fallback. Uses the unified ``Database`` for storage.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from papertrail.core.config import Settings
from papertrail.core.database import Database
from papertrail.core.models import ExtractedPage

TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-']*")


class SearchIndex:
    """Unified FTS5 search across all PaperTrail document domains."""

    def __init__(self, db: Database, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or Settings()

    # ── document lifecycle ──────────────────────────────────────────────────

    def add_pdf_pages(
        self,
        filename: str,
        pages: list[ExtractedPage],
        stored_path: str | None = None,
    ) -> int:
        """Ingest a PDF document — insert parent + one child per page."""
        parent_id = self.db.insert_document(
            domain="plan",
            title=filename,
            payload={"page_count": len(pages)},
            source=filename,
            storage_path=stored_path,
        )
        for page in pages:
            self.db.insert_document(
                domain="plan_page",
                title=f"{filename} — p.{page.page_number}",
                text_content=page.text,
                parent_id=parent_id,
                page_number=page.page_number,
            )
        return parent_id

    def list_documents(self) -> list[dict[str, Any]]:
        return self.db.list_documents(domain="plan")

    def get_page_text(self, document_id: int, page_number: int) -> str | None:
        with self.db.connect() as conn:
            row = conn.execute(
                "SELECT text_content FROM documents WHERE parent_id = ? AND page_number = ?",
                (document_id, page_number),
            ).fetchone()
        return str(row["text_content"]) if row else None

    # ── Search ──────────────────────────────────────────────────────────────

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        query = query.strip()
        if not query:
            return []
        fts_query = self._build_fts_query(query)
        with self.db.connect() as conn:
            rows = conn.execute(
                """SELECT document_id, domain, title AS filename,
                          snippet(documents_fts, 0, '[', ']', ' … ', 18) AS snippet,
                          bm25(documents_fts) AS score
                   FROM documents_fts
                   WHERE documents_fts MATCH ?
                   ORDER BY bm25(documents_fts)
                   LIMIT ?""",
                (fts_query, int(limit)),
            ).fetchall()
        return [
            {
                "document_id": int(r["document_id"]),
                "domain": str(r["domain"]),
                "filename": str(r["filename"]),
                "snippet": _clean_snippet(str(r["snippet"])),
                "score": float(r["score"]),
            }
            for r in rows
        ]

    def _build_fts_query(self, query: str) -> str:
        tokens = TOKEN_RE.findall(query)
        if not tokens:
            return '""'
        return " OR ".join(f'"{t}"*' for t in tokens[: self.settings.MAX_SEARCH_TOKENS])

    # ── file extraction helpers ─────────────────────────────────────────────

    def extract_pages(self, path: str | Path) -> list[ExtractedPage]:
        """Auto-detect format and extract text pages from a file."""
        path = Path(path)
        ext = path.suffix.lower()
        if ext == ".pdf":
            return self._extract_pdf(path)
        if ext in self.settings.SUPPORTED_PLAN_EXTENSIONS:
            text = self._ocr_image(path)
            return [ExtractedPage(page_number=1, text=text)]
        raise ValueError(f"Unsupported format: {ext}")

    def _extract_pdf(self, path: Path) -> list[ExtractedPage]:
        import fitz  # PyMuPDF

        pages: list[ExtractedPage] = []
        with fitz.open(path) as doc:
            for idx, page in enumerate(doc, start=1):
                text = (page.get_text("text") or "").strip()
                if text:
                    pages.append(ExtractedPage(page_number=idx, text=text))
        return pages

    def _ocr_image(self, path: Path) -> str:
        try:
            import pytesseract
            from PIL import Image
        except ImportError:
            return "[OCR not installed. Run: pip install pytesseract and install Tesseract binary]"
        try:
            return pytesseract.image_to_string(Image.open(path)).strip()
        except Exception as exc:
            return f"[OCR failed: {exc}]"


def _clean_snippet(snippet: str) -> str:
    return " ".join(snippet.replace("\n", " ").split())
