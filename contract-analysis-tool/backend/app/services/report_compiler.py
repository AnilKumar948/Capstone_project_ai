from datetime import datetime, timezone


class ReportCompiler:
    def compile(self, job_id: str, metadata: dict, clauses: list[dict], risks: list[dict], extracted: dict, summary: dict, errors: list[str]) -> dict:
        return {
            "job_id": job_id,
            "clauses": clauses,
            "risks": risks,
            "extracted": extracted,
            "summary": summary,
            "metadata": metadata,
            "partial": len(errors) > 0,
            "errors": errors,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
