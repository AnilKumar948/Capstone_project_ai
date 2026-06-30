from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path

from celery import Celery
from redis import Redis
from sqlalchemy import select

from app.agents.orchestrator import ContractOrchestrator
from app.config import get_settings
from app.db.session import get_session_maker
from app.models.contract import Contract, Job, Report
from app.services.embedder import EmbedderService
from app.services.parser import DocumentParser
from app.services.storage import StorageService


settings = get_settings()


def _env_or_default(name: str, default_value: str) -> str | None:
    value = os.getenv(name)
    if value is not None:
        value = value.strip()
        return value or None
    return default_value or None


broker_url = _env_or_default("CELERY_BROKER_URL", settings.celery_broker_url)
result_backend_url = _env_or_default("CELERY_RESULT_BACKEND", settings.celery_result_backend)

celery_app = Celery(
    "contract-analysis",
    broker=broker_url,
    backend=result_backend_url,
)
celery_app.conf.update(task_serializer="json", worker_concurrency=4, task_time_limit=300)


def _to_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _to_int(value) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    raw = str(value).strip()
    if not raw:
        return None
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        return None
    return int(digits)


def _risk_counts(report_payload: dict) -> tuple[int, int, int, int]:
    summary = report_payload.get("risk_summary") if isinstance(report_payload, dict) else None
    if isinstance(summary, dict):
        critical = _to_int(summary.get("critical")) or 0
        high = _to_int(summary.get("high")) or 0
        medium = _to_int(summary.get("medium")) or 0
        low = _to_int(summary.get("low")) or 0
        return critical, high, medium, low

    critical = high = medium = low = 0
    for item in report_payload.get("risks", []) if isinstance(report_payload, dict) else []:
        if not isinstance(item, dict):
            continue
        level = str(item.get("severity", "")).upper()
        if level == "CRITICAL":
            critical += 1
        elif level == "HIGH":
            high += 1
        elif level == "MEDIUM":
            medium += 1
        elif level == "LOW":
            low += 1
    return critical, high, medium, low


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def analyze_contract(self, job_id: str, s3_key: str):
    """
    Celery task that:
    1. Downloads file from S3/MinIO
    2. Calls DocumentParser.parse()
    3. Embeds chunks into vector store (for future RAG queries)
    4. Runs ContractOrchestrator.run(state) via asyncio.run()
    5. Saves final report to PostgreSQL
    6. Updates job status to COMPLETE or FAILED
    7. Publishes completion event to Redis pub/sub channel
    """

    try:
        asyncio.run(run_analysis_async(job_id, s3_key))
    except Exception as exc:
        raise self.retry(exc=exc)


async def run_analysis_async(job_id: str, s3_key: str):
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Starting analysis for job {job_id}, s3_key: {s3_key}")

    session_maker = get_session_maker()

    async def persist_progress(current_job_id: str, step: str, pct: int) -> None:
        try:
            async with session_maker() as db:
                job_result = await db.execute(select(Job).where(Job.id == current_job_id))
                job = job_result.scalar_one_or_none()
                if not job:
                    return
                job.status = "RUNNING"
                # Keep progress monotonic in case callbacks arrive out of order.
                job.progress_pct = max(int(job.progress_pct or 0), int(pct))
                await db.commit()
        except Exception:
            # Progress updates are best-effort and should not fail analysis.
            pass
    
    # Guard: only connect to Redis if a URL is configured
    redis_sync = None
    if settings.redis_url:
        try:
            redis_sync = Redis.from_url(settings.redis_url, decode_responses=True)
        except Exception:
            redis_sync = None
    storage = StorageService()
    parser = DocumentParser()
    embedder = EmbedderService()
    final_state = None
    try:
        await persist_progress(job_id, "Starting", 5)
        logger.info("Downloading file from storage...")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / Path(s3_key).name
            file_bytes = storage.get_bytes(s3_key)
            logger.info(f"Got {len(file_bytes) if file_bytes else 0} bytes from storage")
            path.write_bytes(file_bytes)

            logger.info("Parsing document...")
            parse_result = parser.parse(path)
            logger.info(f"Parsed document with {len(parse_result.chunks)} chunks")
            
            logger.info("Embedding chunks...")
            await embedder.embed_chunks(job_id, parse_result.chunks)
            logger.info("Embedding complete")

            from redis.asyncio import Redis as AsyncRedis

            redis_client = None
            if settings.redis_url:
                try:
                    redis_client = AsyncRedis.from_url(settings.redis_url, decode_responses=True)
                except Exception:
                    redis_client = None

            logger.info("Running orchestrator...")
            orchestrator = ContractOrchestrator(redis_client=redis_client, progress_updater=persist_progress)
            final_state = await orchestrator.run(
                {
                    "job_id": job_id,
                    "file_path": str(path),
                    "raw_text": parse_result.raw_text,
                    "chunks": parse_result.chunks,
                    "metadata": parse_result.metadata,
                    "clauses": [],
                    "risks": [],
                    "extracted": {},
                    "summary": {},
                    "report": {},
                    "errors": [],
                    "status": "RUNNING",
                }
            )
            logger.info("Orchestrator completed successfully")
    except Exception as exc:
        logger.error(f"Analysis failed with exception: {exc}", exc_info=True)
        final_state = {
            "report": {"partial": True, "errors": [str(exc)]},
            "errors": [str(exc)],
            "status": "FAILED",
        }

    async with session_maker() as db:
        job_result = await db.execute(select(Job).where(Job.id == job_id))
        job = job_result.scalar_one_or_none()
        if not job:
            return

        job.status = "COMPLETE" if final_state and not final_state.get("errors") else "FAILED"
        job.progress_pct = 100
        
        # Save error message if analysis failed
        if final_state and final_state.get("errors"):
            job.error_message = "; ".join(final_state.get("errors", []))

        report_id = final_state.get("report", {}).get("report_id") if final_state else None
        if not report_id:
            from uuid import uuid4

            report_id = str(uuid4())

        payload = (final_state or {}).get("report", {"partial": True})
        extracted = payload.get("extracted", {}) if isinstance(payload, dict) else {}
        summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
        critical, high, medium, low = _risk_counts(payload if isinstance(payload, dict) else {})

        report = Report(
            id=report_id,
            job_id=job_id,
            payload=payload,
            extracted_effective_date=_to_text(extracted.get("effective_date")),
            extracted_expiration_date=_to_text(extracted.get("expiration_date")),
            extracted_contract_value=_to_text(extracted.get("contract_value")),
            extracted_payment_terms=_to_text(extracted.get("payment_terms")),
            extracted_termination_notice_days=_to_int(extracted.get("termination_notice_days")),
            extracted_liability_cap=_to_text(extracted.get("liability_cap")),
            extracted_governing_law=_to_text(extracted.get("governing_law")),
            extracted_auto_renewal=_to_text(extracted.get("auto_renewal")),
            risk_critical=critical,
            risk_high=high,
            risk_medium=medium,
            risk_low=low,
            summary_overall_risk=_to_text(summary.get("overall_risk")),
            summary_executive_summary=_to_text(summary.get("executive_summary")),
        )
        db.add(report)
        await db.commit()

    if redis_sync:
        try:
            redis_sync.publish(f"jobs:{job_id}", json.dumps({"status": "COMPLETE", "report_id": report_id}))
        except Exception:
            pass
