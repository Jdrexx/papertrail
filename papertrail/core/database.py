"""PaperTrail — unified SQLite storage.

Single schema with a ``documents`` table using a ``domain`` discriminator
plus an FTS5 virtual table for full-text search across every domain.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class Database:
    """Lightweight wrapper around a SQLite connection with PaperTrail's schema."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    # ── connection ──────────────────────────────────────────────────────────

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    # ── schema ──────────────────────────────────────────────────────────────

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain        TEXT NOT NULL,
                    parent_id     INTEGER REFERENCES documents(id) ON DELETE CASCADE,
                    title         TEXT NOT NULL DEFAULT '',
                    source        TEXT,
                    storage_path  TEXT,
                    payload       TEXT NOT NULL DEFAULT '{}',
                    text_content  TEXT NOT NULL DEFAULT '',
                    page_number   INTEGER,
                    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_domain ON documents(domain)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_parent ON documents(parent_id)")

            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                    text_content,
                    title       UNINDEXED,
                    domain      UNINDEXED,
                    document_id UNINDEXED,
                    tokenize='unicode61 remove_diacritics 2'
                )
            """)

    # ── CRUD ────────────────────────────────────────────────────────────────

    def insert_document(
        self,
        domain: str,
        title: str = "",
        text_content: str = "",
        payload: str | dict | None = None,
        *,
        source: str | None = None,
        storage_path: str | None = None,
        parent_id: int | None = None,
        page_number: int | None = None,
    ) -> int:
        if isinstance(payload, dict):
            payload = json.dumps(payload)
        with self.connect() as conn:
            cur = conn.execute(
                """INSERT INTO documents(domain, title, source, storage_path, payload,
                                         text_content, page_number, parent_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (domain, title, source, storage_path, payload or "{}",
                 text_content, page_number, parent_id),
            )
            doc_id = int(cur.lastrowid)
            conn.execute(
                "INSERT INTO documents_fts(text_content, title, domain, document_id) VALUES (?, ?, ?, ?)",
                (text_content, title, domain, doc_id),
            )
        return doc_id

    def get_document(self, doc_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        return dict(row) if row else None

    def list_documents(self, domain: str | None = None) -> list[dict[str, Any]]:
        with self.connect() as conn:
            if domain:
                rows = conn.execute(
                    """SELECT d.*, (SELECT COUNT(*) FROM documents c
                       WHERE c.parent_id = d.id) AS child_count
                       FROM documents d
                       WHERE d.domain = ?
                       ORDER BY d.created_at DESC, d.id DESC""",
                    (domain,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT d.*, (SELECT COUNT(*) FROM documents c
                       WHERE c.parent_id = d.id) AS child_count
                       FROM documents d
                       ORDER BY d.created_at DESC, d.id DESC"""
                ).fetchall()
        return [dict(r) for r in rows]

    def count_by_domain(self) -> dict[str, int]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT domain, COUNT(*) AS cnt FROM documents GROUP BY domain"
            ).fetchall()
        return {str(r["domain"]): int(r["cnt"]) for r in rows}

    def total_count(self) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM documents").fetchone()
        return int(row["cnt"]) if row else 0

    def close_all(self) -> None:
        """Close any cached connections. Called on app shutdown."""
        # SQLite connections are created per-call via connect(),
        # so there's nothing persistent to close. This hook exists
        # for cleanup lifecycle compatibility.
        pass
