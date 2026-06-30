import pytest

from app.agents.base_agent import AgentError
from app.agents.clause_agent import ClauseAgent
from app.agents.extractor_agent import ExtractorAgent
from app.agents.risk_agent import RiskAgent
from app.agents.summary_agent import SummaryAgent


@pytest.mark.asyncio
async def test_clause_agent_returns_valid_schema(monkeypatch):
    agent = ClauseAgent()
    async def fake_call(prompt, schema):
        return [{"clause_type": "LIABILITY", "text": "X", "page_hint": 1, "confidence": 0.9}]

    monkeypatch.setattr(
        agent,
        "_call_llm",
        fake_call,
    )
    result = await agent.run(["sample"], {})
    assert result[0]["clause_type"] == "LIABILITY"


@pytest.mark.asyncio
async def test_clause_agent_falls_back_to_heuristics_when_llm_empty(monkeypatch):
    agent = ClauseAgent()

    async def fake_call(prompt, schema):
        return []

    monkeypatch.setattr(agent, "_call_llm", fake_call)
    chunks = [
        (
            "Payment Terms: Customer shall pay all invoices within Net 30 days of receipt. "
            "Termination Notice: Either party may terminate this agreement with 30 days written notice. "
            "Governing Law: State of New York. "
            "Liability Cap: Liability shall not exceed USD 500,000."
        ),
    ]

    result = await agent.run(chunks, {})
    types = {item["clause_type"] for item in result}
    assert "PAYMENT" in types
    assert "TERMINATION" in types
    assert "GOVERNING_LAW" in types
    assert len(result) >= 3


@pytest.mark.asyncio
async def test_risk_agent_scores_liability_high(monkeypatch):
    agent = RiskAgent()
    async def fake_call(prompt, schema):
        return [{"clause_type": "LIABILITY", "clause_text_snippet": "Unlimited liability", "risk_level": "HIGH", "risk_category": "LIABILITY", "risk_description": "Too broad", "recommendation": "Add cap"}]

    monkeypatch.setattr(
        agent,
        "_call_llm",
        fake_call,
    )
    result = await agent.run([], {"clauses": [{"clause_type": "LIABILITY"}]})
    assert result[0]["risk_level"] in {"HIGH", "CRITICAL"}


@pytest.mark.asyncio
async def test_extractor_agent_finds_parties(monkeypatch):
    agent = ExtractorAgent()
    async def fake_call(prompt, schema):
        return {"parties": {"client": {"name": "A", "jurisdiction": "US"}, "provider": {"name": "B", "jurisdiction": "US"}, "others": []}}

    monkeypatch.setattr(agent, "_call_llm", fake_call)
    result = await agent.run(["Agreement between A and B"], {})
    assert result["parties"]["client"]["name"] == "A"


@pytest.mark.asyncio
async def test_summary_agent_returns_executive_summary(monkeypatch):
    agent = SummaryAgent()

    async def fake_call(prompt, schema):
        if "Partial summaries" in prompt:
            return {"executive_summary": "Summary", "key_terms": [], "unusual_clauses": [], "overall_risk": "LOW", "recommended_actions": []}
        return {"summary": "chunk summary"}

    monkeypatch.setattr(agent, "_call_llm", fake_call)
    result = await agent.run(["chunk"], {"extracted": {}, "risks": []})
    assert "executive_summary" in result


@pytest.mark.asyncio
async def test_agent_fallback_to_claude_on_openai_error(monkeypatch):
    class Dummy:
        async def ainvoke(self, prompt):
            class Msg:
                content = '{"ok":true}'

            return Msg()

    class Failing:
        async def ainvoke(self, prompt):
            raise RuntimeError("openai down")

    agent = ExtractorAgent()
    agent.primary = Failing()
    agent.fallback = Dummy()
    result = await agent._call_llm("prompt", {"type": "object"})
    assert result["ok"] is True
