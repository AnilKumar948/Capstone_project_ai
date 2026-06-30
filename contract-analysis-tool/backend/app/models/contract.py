from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    jobs: Mapped[list["Job"]] = relationship(back_populates="contract")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    progress_pct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    contract: Mapped[Contract] = relationship(back_populates="jobs")
    report: Mapped["Report | None"] = relationship(back_populates="job", uselist=False)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), unique=True, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    extracted_effective_date: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_expiration_date: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_contract_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_payment_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_termination_notice_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extracted_liability_cap: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_governing_law: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_auto_renewal: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_critical: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    risk_high: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    risk_medium: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    risk_low: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary_overall_risk: Mapped[str | None] = mapped_column(String(32), nullable=True)
    summary_executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    job: Mapped[Job] = relationship(back_populates="report")
