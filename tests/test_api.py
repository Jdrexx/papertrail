"""PaperTrail test utilities and fixtures."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from papertrail import create_app


@pytest.fixture
def tmp_data_dir():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        yield Path(d)


@pytest.fixture
def client(tmp_data_dir):
    app = create_app(data_dir=tmp_data_dir)
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["app"] == "PaperTrail"


@pytest.mark.asyncio
async def test_ingest_and_ask(client):
    resp = await client.post(
        "/api/v1/ingest",
        json={"title": "test", "text": "FastAPI is a modern web framework for building APIs with Python."},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["chunks"] >= 1

    resp = await client.post("/api/v1/ask", json={"question": "What is FastAPI?"})
    assert resp.status_code == 200
    answer = resp.json()
    assert "answer" in answer
    assert "citations" in answer


@pytest.mark.asyncio
async def test_process_scan(client):
    resp = await client.post(
        "/api/v1/process",
        json={"text": "1/15 Office Depot $42.18\n1/16 GitHub Pro $4.00", "source": "test_receipt"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["row_count"] >= 1
    assert len(data["rows"]) >= 1


@pytest.mark.asyncio
async def test_export_csv(client):
    await client.post("/api/v1/process", json={"text": "1/15 Office Depot $42.18", "source": "csv_test"})
    resp = await client.get("/api/v1/export.csv")
    assert resp.status_code == 200
    assert "csv" in resp.headers.get("content-type", "")
    body = resp.text
    assert "date" in body


@pytest.mark.asyncio
async def test_search(client):
    await client.post("/api/v1/ingest", json={"title": "search_test", "text": "Python is a programming language."})
    resp = await client.get("/api/v1/search", params={"q": "python"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == "python"
    assert isinstance(data["results"], list)


@pytest.mark.asyncio
async def test_404(client):
    resp = await client.get("/api/v1/documents/999/pages/1")
    assert resp.status_code == 404
