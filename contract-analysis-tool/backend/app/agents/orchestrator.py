from __future__ import annotations

import asyncio
import json
import operator
from typing import Annotated, Awaitable, Callable, TypedDict

from langgraph.graph import END, START, StateGraph
from redis.asyncio import Redis

from app.agents.clause_agent import ClauseAgent
from app.agents.extractor_agent import ExtractorAgent
from app.agents.risk_agent import RiskAgent
from app.agents.summary_agent import SummaryAgent
from app.services.parser import DocumentParser
from app.services.report_compiler import ReportCompiler


class ContractState(TypedDict):
    job_id: str
    chunks: list[str]
    raw_text: str
    metadata: dict
    file_path: str
    clauses: list[dict]
    risks: list[dict]
    extracted: dict
    summary: dict
    report: dict
    errors: Annotated[list[str], operator.add]
    status: str


class ContractOrchestrator:
    # LangGraph is used for explicit state and easy parallel branches.
    def __init__(
        self,
        redis_client: Redis | None = None,
        progress_updater: Callable[[str, str, int], Awaitable[None]] | None = None,
    ):
        self.redis = redis_client
        self.progress_updater = progress_updater
        self.parser = DocumentParser()
        self.clause_agent = ClauseAgent()
        self.risk_agent = RiskAgent()
        self.extractor_agent = ExtractorAgent()
        self.summary_agent = SummaryAgent()
        self.compiler = ReportCompiler()
        self.graph = self._build_graph()

    async def progress_callback(self, job_id: str, step: str, pct: int) -> None:
        if self.progress_updater:
            await self.progress_updater(job_id, step, pct)
        if not self.redis:
            return
        channel = f"jobs:{job_id}"
        await self.redis.publish(channel, json.dumps({"step": step, "pct": pct}))

    def _build_graph(self):
        graph = StateGraph(ContractState)
        graph.add_node("parse_node", self.parse_node)
        graph.add_node("clause_node", self.clause_node)
        graph.add_node("extractor_node", self.extractor_node)
        graph.add_node("risk_node", self.risk_node)
        graph.add_node("summary_node", self.summary_node)
        graph.add_node("compile_node", self.compile_node)

        graph.add_edge(START, "parse_node")
        graph.add_edge("parse_node", "clause_node")
        graph.add_edge("parse_node", "extractor_node")
        graph.add_edge("clause_node", "risk_node")
        graph.add_edge("risk_node", "summary_node")
        graph.add_edge("extractor_node", "summary_node")
        graph.add_edge("summary_node", "compile_node")
        graph.add_edge("compile_node", END)
        return graph.compile()

    async def _safe(self, state: ContractState, step: str, pct: int, fn: Awaitable[dict]) -> dict:
        try:
            updates = await fn
            try:
                await self.progress_callback(state["job_id"], step, pct)
            except Exception:
                # Progress notifications are best-effort and must not fail analysis.
                pass
            return updates
        except Exception as exc:
            return {"errors": [f"{step}: {exc}"]}

    async def parse_node(self, state: ContractState) -> dict:
        async def run_parse():
            result = await asyncio.to_thread(
                self.parser.parse,
                state["file_path"],
                state["metadata"].get("filename"),
                state["metadata"].get("mime_type"),
            )
            merged_metadata = dict(state.get("metadata", {}))
            merged_metadata.update(result.metadata)
            return {
                "raw_text": result.raw_text,
                "chunks": result.chunks,
                "metadata": merged_metadata,
            }

        return await self._safe(state, "Parsing", 20, run_parse())

    async def clause_node(self, state: ContractState) -> dict:
        return await self._safe(
            state,
            "Identifying clauses",
            40,
            self._run_assign(self.clause_agent.run(state["chunks"], state), "clauses"),
        )

    async def extractor_node(self, state: ContractState) -> dict:
        return await self._safe(
            state,
            "Extracting fields",
            50,
            self._run_assign(self.extractor_agent.run(state["chunks"], state), "extracted"),
        )

    async def risk_node(self, state: ContractState) -> dict:
        return await self._safe(
            state,
            "Analyzing risks",
            70,
            self._run_assign(self.risk_agent.run(state["chunks"], state), "risks"),
        )

    async def summary_node(self, state: ContractState) -> dict:
        return await self._safe(
            state,
            "Summarizing",
            85,
            self._run_assign(self.summary_agent.run(state["chunks"], state), "summary"),
        )

    async def compile_node(self, state: ContractState) -> dict:
        async def run_compile():
            report = self.compiler.compile(
                job_id=state["job_id"],
                metadata=state.get("metadata", {}),
                clauses=state.get("clauses", []),
                risks=state.get("risks", []),
                extracted=state.get("extracted", {}),
                summary=state.get("summary", {}),
                errors=state.get("errors", []),
            )
            return {
                "report": report,
                "status": "COMPLETE" if not state.get("errors") else "FAILED",
            }

        return await self._safe(state, "Compiling report", 100, run_compile())

    async def _run_assign(self, coro: Awaitable, key: str) -> dict:
        result = await asyncio.gather(coro)
        return {key: result[0]}

    async def run(self, state: ContractState) -> ContractState:
        state.setdefault("errors", [])
        state.setdefault("clauses", [])
        state.setdefault("risks", [])
        state.setdefault("extracted", {})
        state.setdefault("summary", {})
        state.setdefault("report", {})
        state["status"] = "RUNNING"
        final_state = await self.graph.ainvoke(state)
        if final_state.get("errors"):
            final_state["report"]["partial"] = True
        return final_state
