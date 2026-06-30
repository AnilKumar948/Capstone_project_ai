import pytest

from app.agents.orchestrator import ContractOrchestrator


@pytest.mark.asyncio
async def test_full_pipeline_completes(monkeypatch, tmp_path, redis_mock):
    file_path = tmp_path / "dummy.docx"
    file_path.write_text("dummy")

    orchestrator = ContractOrchestrator(redis_client=redis_mock)

    monkeypatch.setattr(orchestrator.parser, "parse", lambda *args, **kwargs: type("R", (), {"raw_text": "x", "chunks": ["x"], "metadata": {"filename": "x"}})())
    async def clause_ok(chunks, ctx):
        return [{"clause_type": "GENERAL", "text": "x", "page_hint": 1, "confidence": 0.8}]

    async def extractor_ok(chunks, ctx):
        return {"parties": {}}

    async def risk_ok(chunks, ctx):
        return []

    async def summary_ok(chunks, ctx):
        return {"executive_summary": "ok"}

    monkeypatch.setattr(orchestrator.clause_agent, "run", clause_ok)
    monkeypatch.setattr(orchestrator.extractor_agent, "run", extractor_ok)
    monkeypatch.setattr(orchestrator.risk_agent, "run", risk_ok)
    monkeypatch.setattr(orchestrator.summary_agent, "run", summary_ok)

    state = {
        "job_id": "job-1",
        "file_path": str(file_path),
        "chunks": [],
        "raw_text": "",
        "metadata": {"filename": "x"},
        "clauses": [],
        "risks": [],
        "extracted": {},
        "summary": {},
        "report": {},
        "errors": [],
        "status": "PENDING",
    }
    result = await orchestrator.run(state)
    assert "report" in result


@pytest.mark.asyncio
async def test_partial_result_on_agent_failure(monkeypatch, tmp_path, redis_mock):
    file_path = tmp_path / "dummy.docx"
    file_path.write_text("dummy")
    orchestrator = ContractOrchestrator(redis_client=redis_mock)

    monkeypatch.setattr(orchestrator.parser, "parse", lambda *args, **kwargs: type("R", (), {"raw_text": "x", "chunks": ["x"], "metadata": {}})())

    async def fail_agent(chunks, ctx):
        raise RuntimeError("boom")

    monkeypatch.setattr(orchestrator.clause_agent, "run", fail_agent)
    async def extractor_ok(chunks, ctx):
        return {}

    async def risk_ok(chunks, ctx):
        return []

    async def summary_ok(chunks, ctx):
        return {"executive_summary": "ok"}

    monkeypatch.setattr(orchestrator.extractor_agent, "run", extractor_ok)
    monkeypatch.setattr(orchestrator.risk_agent, "run", risk_ok)
    monkeypatch.setattr(orchestrator.summary_agent, "run", summary_ok)

    state = {
        "job_id": "job-2",
        "file_path": str(file_path),
        "chunks": [],
        "raw_text": "",
        "metadata": {"filename": "x"},
        "clauses": [],
        "risks": [],
        "extracted": {},
        "summary": {},
        "report": {},
        "errors": [],
        "status": "PENDING",
    }
    result = await orchestrator.run(state)
    assert result["report"].get("partial") is True


@pytest.mark.asyncio
async def test_progress_events_published_to_redis(monkeypatch, tmp_path, redis_mock):
    file_path = tmp_path / "dummy.docx"
    file_path.write_text("dummy")
    orchestrator = ContractOrchestrator(redis_client=redis_mock)

    monkeypatch.setattr(orchestrator.parser, "parse", lambda *args, **kwargs: type("R", (), {"raw_text": "x", "chunks": ["x"], "metadata": {}})())
    async def clause_ok(chunks, ctx):
        return []

    async def extractor_ok(chunks, ctx):
        return {}

    async def risk_ok(chunks, ctx):
        return []

    async def summary_ok(chunks, ctx):
        return {"executive_summary": "ok"}

    monkeypatch.setattr(orchestrator.clause_agent, "run", clause_ok)
    monkeypatch.setattr(orchestrator.extractor_agent, "run", extractor_ok)
    monkeypatch.setattr(orchestrator.risk_agent, "run", risk_ok)
    monkeypatch.setattr(orchestrator.summary_agent, "run", summary_ok)

    state = {
        "job_id": "job-3",
        "file_path": str(file_path),
        "chunks": [],
        "raw_text": "",
        "metadata": {"filename": "x"},
        "clauses": [],
        "risks": [],
        "extracted": {},
        "summary": {},
        "report": {},
        "errors": [],
        "status": "PENDING",
    }
    await orchestrator.run(state)
    assert len(redis_mock.messages) > 0
