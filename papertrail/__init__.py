"""PaperTrail — Unified Document Intelligence Platform."""

from __future__ import annotations

__version__ = "0.2.0"

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI

from papertrail.core.config import Settings
from papertrail.core.database import Database
from papertrail.adapters.search import SearchIndex
from papertrail.adapters.knowledge import KnowledgeEngine
from papertrail.adapters.scan import ReceiptParser


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — clean up resources on shutdown."""
    yield
    if hasattr(app.state, "db"):
        app.state.db.close_all()


def create_app(data_dir: str | Path | None = None) -> FastAPI:
    """Factory: build a configured PaperTrail FastAPI application."""
    settings = Settings()
    if data_dir is not None:
        settings.DATA_DIR = Path(data_dir)

    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)

    db = Database(settings.db_path)
    db.init_schema()

    app = FastAPI(
        title="PaperTrail",
        description="Local-first document intelligence: upload, extract, search, and analyze documents.",
        version=__version__,
        lifespan=lifespan,
    )

    app.state.settings = settings
    app.state.db = db
    app.state.search_index = SearchIndex(db)
    app.state.knowledge_engine = KnowledgeEngine(db)
    app.state.receipt_parser = ReceiptParser(db)

    from papertrail.api import health, documents, knowledge, scan, search

    app.include_router(health.router)
    app.include_router(documents.router)
    app.include_router(knowledge.router)
    app.include_router(scan.router)
    app.include_router(search.router)

    return app


app = create_app()
