"""PaperTrail — health endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/api/v1/health")
def health(request: Request):
    db = request.app.state.db
    return {
        "status": "ok",
        "app": "PaperTrail",
        "documents": db.total_count(),
        "domains": db.count_by_domain(),
    }
