from datetime import datetime
from pydantic import BaseModel


class ReportResponse(BaseModel):
    report_id: str
    job_id: str
    clauses: list[dict]
    risks: list[dict]
    extracted: dict
    summary: dict
    metadata: dict
    partial: bool
    created_at: datetime
