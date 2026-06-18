"""PaperTrail — document upload and management (plans domain)."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from papertrail.core.models import DocumentInfo, UploadResponse

router = APIRouter(prefix="/api/v1", tags=["documents"])


@router.get("/documents", response_model=list[DocumentInfo])
def list_documents(request: Request):
    return request.app.state.search_index.list_documents()


@router.post("/documents", response_model=UploadResponse, status_code=201)
async def upload_document(request: Request, file: UploadFile = File(...)):
    idx = request.app.state.search_index
    settings = request.app.state.settings

    filename = Path(file.filename or "document.pdf").name
    ext = Path(filename).suffix.lower()
    if ext not in settings.SUPPORTED_PLAN_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format {ext}. Supported: {', '.join(sorted(settings.SUPPORTED_PLAN_EXTENSIONS))}",
        )

    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = settings.upload_dir / stored_name
    with stored_path.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    try:
        pages = idx.extract_pages(stored_path)
        document_id = idx.add_pdf_pages(filename, pages, str(stored_path))
    except Exception as exc:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"Could not process document: {exc}") from exc

    return UploadResponse(id=document_id, filename=filename, page_count=len(pages))


@router.get("/documents/{document_id}/pages/{page_number}")
def get_page(request: Request, document_id: int, page_number: int):
    text = request.app.state.search_index.get_page_text(document_id, page_number)
    if text is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return {"document_id": document_id, "page_number": page_number, "text": text}
