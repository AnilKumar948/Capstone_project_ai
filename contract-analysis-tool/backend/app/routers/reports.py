from __future__ import annotations

import json
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import current_active_user, get_db
from app.models.contract import Report
from app.utils.pdf_exporter import export_report_pdf


router = APIRouter(
    prefix="/api/v1/reports",
    tags=["reports"],
    dependencies=[Depends(current_active_user)],
)


@router.get("/{report_id}")
async def get_report(report_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    payload = dict(report.payload or {})
    payload["report_id"] = report.id
    return payload


@router.get("/{report_id}/export")
async def export_report(
    report_id: str,
    format: str = Query(pattern="^(pdf|json)$"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    payload = dict(report.payload or {})
    payload.setdefault("report_id", report.id)

    if format == "json":
        body = json.dumps(payload, indent=2).encode("utf-8")
        return StreamingResponse(
            BytesIO(body),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="report-{report_id}.json"'},
        )

    pdf_bytes = export_report_pdf(payload)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report-{report_id}.pdf"'},
    )
