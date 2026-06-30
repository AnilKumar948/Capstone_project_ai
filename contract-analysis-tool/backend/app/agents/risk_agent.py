from __future__ import annotations

import re

from app.agents.base_agent import BaseAgent


class RiskAgent(BaseAgent):
    async def run(self, chunks: list[str], context: dict) -> list[dict]:
        clauses = context.get("clauses", [])
        text = "\n\n".join(chunks)
        prompt = (
            "You are a contract risk analyst. For each clause provided, identify\n"
            "potential legal or business risks. Be specific about why each clause\n"
            "is risky — reference the clause's actual language. Assign risk_level\n"
            "as CRITICAL only for clauses with direct financial exposure > $1M,\n"
            "unlimited liability, or waived fundamental rights. Respond ONLY\n"
            "with a JSON array of RiskFlag objects. No preamble.\n\n"
            f"Clauses:\n{clauses}"
        )
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "clause_type": {"type": "string"},
                    "clause_text_snippet": {"type": "string"},
                    "risk_level": {"type": "string"},
                    "risk_category": {"type": "string"},
                    "risk_description": {"type": "string"},
                    "recommendation": {"type": "string"},
                },
            },
        }
        try:
            data = await self._call_llm(prompt, schema)
            if isinstance(data, dict):
                data = data.get("risks", [])
            normalized = self._normalize_risks(data if isinstance(data, list) else [])
            if normalized:
                return normalized
            return self._heuristic_risks(text)
        except Exception as e:
            # LLM call failed - log error and return empty result
            import logging
            logging.warning(f"RiskAgent failed: {e}")
            return self._heuristic_risks(text)

    def _normalize_risks(self, risks: list[dict]) -> list[dict]:
        normalized: list[dict] = []
        for risk in risks:
            if not isinstance(risk, dict):
                continue
            level = str(risk.get("risk_level", "MEDIUM")).upper()
            if level not in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}:
                level = "MEDIUM"
            normalized.append(
                {
                    "clause_type": str(risk.get("clause_type", "GENERAL")),
                    "clause_text_snippet": str(risk.get("clause_text_snippet", "Clause text not provided")),
                    "risk_level": level,
                    "risk_category": str(risk.get("risk_category", "Contractual")),
                    "risk_description": str(risk.get("risk_description", "Potential contractual risk identified.")),
                    "recommendation": str(risk.get("recommendation", "Review and clarify this clause.")),
                }
            )
        return normalized

    def _heuristic_risks(self, text: str) -> list[dict]:
        risks: list[dict] = []
        lower_text = text.lower()

        if "unlimited liability" in lower_text:
            risks.append(
                {
                    "clause_type": "LIABILITY",
                    "clause_text_snippet": "Unlimited liability language detected.",
                    "risk_level": "HIGH",
                    "risk_category": "Financial Exposure",
                    "risk_description": "Unlimited liability can create unbounded financial risk.",
                    "recommendation": "Negotiate a clear monetary liability cap.",
                }
            )

        if re.search(r"\bindemnif(y|ication)\b", lower_text):
            risks.append(
                {
                    "clause_type": "INDEMNIFICATION",
                    "clause_text_snippet": "Indemnification obligations detected.",
                    "risk_level": "MEDIUM",
                    "risk_category": "Indemnity",
                    "risk_description": "Indemnity clauses can shift significant legal costs and liabilities.",
                    "recommendation": "Limit scope, carve out exclusions, and add liability boundaries.",
                }
            )

        if "termination" not in lower_text:
            risks.append(
                {
                    "clause_type": "TERMINATION",
                    "clause_text_snippet": "No explicit termination clause identified in extracted text.",
                    "risk_level": "MEDIUM",
                    "risk_category": "Exit Rights",
                    "risk_description": "Missing termination language can create uncertainty for ending the agreement.",
                    "recommendation": "Add termination triggers, cure periods, and notice requirements.",
                }
            )

        if "governing law" not in lower_text:
            risks.append(
                {
                    "clause_type": "GOVERNING_LAW",
                    "clause_text_snippet": "No governing law clause identified in extracted text.",
                    "risk_level": "LOW",
                    "risk_category": "Jurisdiction",
                    "risk_description": "Missing governing law may increase dispute complexity and cost.",
                    "recommendation": "Specify governing law and forum for disputes.",
                }
            )

        return risks
