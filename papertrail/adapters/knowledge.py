"""PaperTrail — Knowledge Engine (keyword-based RAG).

Merged from the original ``knowledgeassistant``: text chunking,
keyword overlap scoring, and answer assembly with citations.
"""

from __future__ import annotations

import re
from typing import Any

from papertrail.core.config import Settings
from papertrail.core.database import Database
from papertrail.core.models import Citation


class KnowledgeEngine:
    """Keyword-based retrieval and Q&A over ingested text chunks."""

    def __init__(self, db: Database, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or Settings()

    def ingest(self, title: str, text: str) -> list[int]:
        """Chunk *text* and store each chunk as a ``knowledge_chunk`` document."""
        ids: list[int] = []
        for i, chunk in enumerate(self._chunk(text), start=1):
            doc_id = self.db.insert_document(
                domain="knowledge_chunk",
                title=f"{title} #{i}",
                text_content=chunk,
                payload={"index": i, "parent_title": title},
                source=title,
            )
            ids.append(doc_id)
        return ids

    def answer(self, question: str) -> dict[str, Any]:
        """Score chunks against *question*, return top-3 citations and an answer."""
        chunks = self.db.list_documents(domain="knowledge_chunk")
        ranked = sorted(chunks, key=lambda r: self._score(question, str(r.get("text_content", ""))), reverse=True)
        top = ranked[:3]

        citations: list[Citation] = []
        for r in top:
            text = str(r.get("text_content", ""))
            score = self._score(question, text)
            if score > 0:
                citations.append(Citation(title=str(r.get("title", "")), excerpt=text[:280]))

        answer = (
            "I found relevant notes: " + " ".join(c.excerpt for c in citations[:2])
            if citations
            else "No strong matching document chunk found. Ingest more source material."
        )
        return {"answer": answer, "citations": [c.model_dump() for c in citations]}

    def _chunk(self, text: str, size: int | None = None) -> list[str]:
        size = size or self.settings.MAX_CHUNK_SIZE
        words = text.split()
        return [" ".join(words[i : i + size]) for i in range(0, len(words), size)] or [text]

    @staticmethod
    def _score(query: str, chunk: str) -> int:
        q_words = set(re.findall(r"[a-z0-9]+", query.lower()))
        c_words = set(re.findall(r"[a-z0-9]+", chunk.lower()))
        return len(q_words & c_words)
