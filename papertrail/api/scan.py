"""PaperTrail — receipt/invoice scanning and CSV export."""

from __future__ import annotations

from fastapi import APIRouter, File, Request, UploadFile
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
    content = (await file.read()).decode("utf-8", errors="ignore")
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
