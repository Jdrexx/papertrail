"""PaperTrail — receipt/invoice scanning and CSV export."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from papertrail.core.models import ProcessRequest, ProcessResponse

router = APIRouter(prefix="/api/v1", tags=["scan"])


@router.post("/process", response_model=ProcessResponse)
def process(req: ProcessRequest, request: Request):
    parser = request.app.state.receipt_parser
    rows = parser.process_and_store(req.text, req.source)
    return ProcessResponse(row_count=len(rows), rows=rows)


@router.post("/upload", response_model=ProcessResponse)
async def upload_scan(request: Request, file: UploadFile = File(...)):
    settings = request.app.state.settings
    content = (await file.read(settings.MAX_UPLOAD_BYTES + 1)).decode(
        "utf-8", errors="ignore"
    )
    if len(content.encode("utf-8")) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {settings.MAX_UPLOAD_BYTES // (1024 * 1024)} MB upload limit",
        )
    parser = request.app.state.receipt_parser
    rows = parser.process_and_store(content, file.filename or "upload")
    return ProcessResponse(row_count=len(rows), rows=rows)


@router.get("/export.csv")
def export_csv(request: Request):
    csv_content = request.app.state.receipt_parser.to_csv()
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=papertrail_export.csv"},
    )