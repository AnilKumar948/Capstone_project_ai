from __future__ import annotations

import json
import asyncio
import os
from uuid import uuid4

import fitz
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dependencies import current_active_user, get_db, get_redis
from app.models.contract import Contract, Job, Report
from app.models.user import User
from app.schemas.contract import JobStatusResponse, UploadResponse
from app.services.embedder import EmbedderService
from app.services.storage import StorageService
from app.tasks.celery_tasks import analyze_contract, run_analysis_async


router = APIRouter(
    prefix="/api/v1/contracts",
    tags=["contracts"],
    dependencies=[Depends(current_active_user)],
)
settings = get_settings()
ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-excel": ".xls",
}
ALLOWED_EXTENSIONS = set(ALLOWED_TYPES.values())
MAX_FILE_SIZE = 50 * 1024 * 1024
embedder = EmbedderService()
storage = StorageService()


def _use_inline_analysis() -> bool:
    broker_env = os.getenv("CELERY_BROKER_URL")
    if broker_env is not None and not broker_env.strip():
        return True
    return not bool(settings.celery_broker_url)


@router.post("/upload", response_model=UploadResponse)
async def upload_contract(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
):
    _ = user
    file_name = (file.filename or "uploaded").strip()
    file_ext = os.path.splitext(file_name)[1].lower()
    mime_allowed = file.content_type in ALLOWED_TYPES
    ext_allowed = file_ext in ALLOWED_EXTENSIONS

    if not mime_allowed and not ext_allowed:
        raise HTTPException(status_code=422, detail="Only PDF, DOCX, XLSX, and XLS are allowed")

    body = await file.read()
    if not body:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")

    is_pdf = file.content_type == "application/pdf" or file_ext == ".pdf"
    if is_pdf:
        try:
            probe_doc = fitz.open(stream=body, filetype="pdf")
            probe_doc.close()
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid or corrupted PDF file")

    if len(body) > MAX_FILE_SIZE:
        raise HTTPException(status_code=422, detail="File exceeds 50 MB limit")

    contract_id = str(uuid4())
    job_id = str(uuid4())
    storage_key = storage.put_bytes(f"contracts/{contract_id}/{file_name}", body, file.content_type)

    contract = Contract(id=contract_id, file_name=file_name or "uploaded", s3_key=storage_key)
    job = Job(id=job_id, contract_id=contract_id, status="PENDING", progress_pct=0)
    db.add(contract)
    db.add(job)
    await db.commit()

    # In local/dev without a configured broker, run analysis in-process.
    if not _use_inline_analysis():
        try:
            analyze_contract.delay(job_id, storage_key)
        except Exception:
            asyncio.create_task(run_analysis_async(job_id, storage_key))
    else:
        asyncio.create_task(run_analysis_async(job_id, storage_key))
    return UploadResponse(job_id=job_id, status="PENDING")


@router.get("/job/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    report_result = await db.execute(select(Report.id).where(Report.job_id == job.id))
    report_id = report_result.scalar_one_or_none()
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        progress_pct=job.progress_pct,
        created_at=job.created_at,
        report_id=report_id,
    )


@router.get("/job/{job_id}/stream")
async def stream_job(job_id: str, redis: Redis = Depends(get_redis)):

    async def event_generator():
        pubsub = None
        try:
            pubsub = redis.pubsub()
            await pubsub.subscribe(f"jobs:{job_id}")
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30)
                if not message:
                    continue
                data = message.get("data")
                payload = json.loads(data) if isinstance(data, str) else data
                if isinstance(payload, dict):
                    yield f"data: {json.dumps(payload)}\\n\\n"
                    if payload.get("status") == "COMPLETE":
                        break
        except Exception:
            # Local dev fallback when Redis is unavailable.
            yield f"data: {json.dumps({'step': 'Processing', 'pct': 10, 'status': 'RUNNING'})}\\n\\n"
        finally:
            if pubsub is not None:
                try:
                    await pubsub.unsubscribe(f"jobs:{job_id}")
                    await pubsub.close()
                except Exception:
                    pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/search")
async def search_contract_clauses(q: str):
    if not q.strip():
        raise HTTPException(status_code=422, detail="Query cannot be empty")
    matches = await embedder.search_clauses(q, top_k=5)
    return {"query": q, "matches": matches}
