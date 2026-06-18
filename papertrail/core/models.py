"""PaperTrail — shared Pydantic models and dataclasses."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field


# ── API request models ─────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    title: str = ""
    text: str = Field(..., min_length=1)


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1)


class ProcessRequest(BaseModel):
    text: str = Field(..., min_length=1)
    source: str = "manual"


# ── API response models ────────────────────────────────────────────────────

class Citation(BaseModel):
    title: str
    excerpt: str


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]


class ExtractedRow(BaseModel):
    date: str = ""
    description: str = ""
    amount: str = ""
    confidence: float = 0.0
    raw: str = ""


class ProcessResponse(BaseModel):
    row_count: int
    rows: list[ExtractedRow]


class UploadResponse(BaseModel):
    id: int
    filename: str
    page_count: int


class SearchHit(BaseModel):
    document_id: int
    domain: str
    filename: str
    page_number: int | None = None
    snippet: str
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchHit]


class DocumentInfo(BaseModel):
    id: int
    domain: str
    title: str
    source: str | None = None
    page_count: int = 0
    created_at: str


class HealthResponse(BaseModel):
    status: str
    documents: int
    domains: dict[str, int]


# ── Internal dataclasses ────────────────────────────────────────────────────

@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    text: str
