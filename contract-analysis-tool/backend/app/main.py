from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.auth import auth_backend, fastapi_users
from app.db.session import Base, get_engine
from app.routers.auth import router as auth_router
from app.routers.contracts import router as contracts_router
from app.routers.reports import router as reports_router
from app.schemas.user import UserCreate, UserRead


app = FastAPI(title="contract-analysis-tool", version="0.1.0")


async def _ensure_report_columns(conn):
    # Supabase/PostgreSQL: add visible report columns and backfill from JSON payload.
    await conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS extracted_effective_date TEXT"))
    await conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS extracted_expiration_date TEXT"))
    await conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS extracted_contract_value TEXT"))
    await conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS extracted_payment_terms TEXT"))
    await conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS extracted_termination_notice_days INTEGER"))
    await conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS extracted_liability_cap TEXT"))
    await conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS extracted_governing_law TEXT"))
    await conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS extracted_auto_renewal TEXT"))
    await conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS risk_critical INTEGER NOT NULL DEFAULT 0"))
    await conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS risk_high INTEGER NOT NULL DEFAULT 0"))
    await conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS risk_medium INTEGER NOT NULL DEFAULT 0"))
    await conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS risk_low INTEGER NOT NULL DEFAULT 0"))
    await conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS summary_overall_risk VARCHAR(32)"))
    await conn.execute(text("ALTER TABLE reports ADD COLUMN IF NOT EXISTS summary_executive_summary TEXT"))

    await conn.execute(
        text(
            """
            UPDATE reports
            SET
                extracted_effective_date = COALESCE(extracted_effective_date, payload->'extracted'->>'effective_date'),
                extracted_expiration_date = COALESCE(extracted_expiration_date, payload->'extracted'->>'expiration_date'),
                extracted_contract_value = COALESCE(extracted_contract_value, payload->'extracted'->>'contract_value'),
                extracted_payment_terms = COALESCE(extracted_payment_terms, payload->'extracted'->>'payment_terms'),
                extracted_termination_notice_days = COALESCE(
                    extracted_termination_notice_days,
                    NULLIF(regexp_replace(payload->'extracted'->>'termination_notice_days', '\\D', '', 'g'), '')::integer
                ),
                extracted_liability_cap = COALESCE(extracted_liability_cap, payload->'extracted'->>'liability_cap'),
                extracted_governing_law = COALESCE(extracted_governing_law, payload->'extracted'->>'governing_law'),
                extracted_auto_renewal = COALESCE(extracted_auto_renewal, payload->'extracted'->>'auto_renewal'),
                summary_overall_risk = COALESCE(summary_overall_risk, payload->'summary'->>'overall_risk'),
                summary_executive_summary = COALESCE(summary_executive_summary, payload->'summary'->>'executive_summary'),
                risk_critical = COALESCE(risk_critical, 0),
                risk_high = COALESCE(risk_high, 0),
                risk_medium = COALESCE(risk_medium, 0),
                risk_low = COALESCE(risk_low, 0)
            """
        )
    )


@app.on_event("startup")
async def startup_event():
    """Create database tables on startup."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if conn.dialect.name == "postgresql":
            await _ensure_report_columns(conn)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/api/v1/auth/jwt", tags=["auth"])
app.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix="/api/v1/auth", tags=["auth"])
app.include_router(contracts_router)
app.include_router(reports_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
