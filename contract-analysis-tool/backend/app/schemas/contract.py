from datetime import datetime

from pydantic import BaseModel


class UploadResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress_pct: int
    created_at: datetime
    report_id: str | None = None
