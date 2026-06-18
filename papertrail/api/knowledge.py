"""PaperTrail — knowledge ingestion and Q&A endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from papertrail.core.models import IngestRequest, QuestionRequest

router = APIRouter(prefix="/api/v1", tags=["knowledge"])


@router.post("/ingest")
def ingest(req: IngestRequest, request: Request):
    engine = request.app.state.knowledge_engine
    ids = engine.ingest(req.title, req.text)
    return {"chunks": len(ids), "ids": ids}


@router.post("/ask")
def ask(req: QuestionRequest, request: Request):
    engine = request.app.state.knowledge_engine
    return engine.answer(req.question)
