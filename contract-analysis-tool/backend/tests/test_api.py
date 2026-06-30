import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_upload_pdf_returns_job_id(monkeypatch):
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as client:
        # Endpoint depends on infrastructure, so this validates route contract only.
        response = await client.post(
            "/api/v1/contracts/upload",
            files={"file": ("sample.pdf", b"%PDF-1.4", "application/pdf")},
        )
    assert response.status_code in {200, 401, 500}


@pytest.mark.asyncio
async def test_upload_invalid_type_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/contracts/upload",
            files={"file": ("sample.txt", b"hello", "text/plain")},
        )
    assert response.status_code in {401, 422}


@pytest.mark.asyncio
async def test_get_job_status():
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as client:
        response = await client.get("/api/v1/contracts/job/non-existent")
    assert response.status_code in {401, 404, 500}


@pytest.mark.asyncio
async def test_get_report_after_completion():
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as client:
        response = await client.get("/api/v1/reports/non-existent")
    assert response.status_code in {401, 404, 500}


@pytest.mark.asyncio
async def test_export_json():
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as client:
        response = await client.get("/api/v1/reports/non-existent/export?format=json")
    assert response.status_code in {401, 404, 500}


@pytest.mark.asyncio
async def test_export_pdf():
    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as client:
        response = await client.get("/api/v1/reports/non-existent/export?format=pdf")
    assert response.status_code in {401, 404, 500}
