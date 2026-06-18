"""PaperTrail — unified full-text search endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from papertrail.core.models import SearchResponse

router = APIRouter(prefix="/api/v1", tags=["search"])


@router.get("/search", response_model=SearchResponse)
def search(request: Request, q: str = Query(..., min_length=1), limit: int = Query(20, ge=1, le=100)):
    results = request.app.state.search_index.search(q, limit=limit)
    return SearchResponse(query=q, results=results)
