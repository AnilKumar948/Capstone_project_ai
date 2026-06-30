from __future__ import annotations

import re
from datetime import datetime

from app.agents.base_agent import BaseAgent


class ExtractorAgent(BaseAgent):
    async def run(self, chunks: list[str], context: dict) -> dict:
        text = "\n\n".join(chunks)[:32000]
        prompt = (
            "You are a contract data extraction specialist. Extract all named\n"
            "fields from the contract text. For dates, output ISO 8601 format\n"
            "(YYYY-MM-DD). For monetary values, preserve the original currency\n"
            "and amount exactly as written. If a field is genuinely absent from\n"
            "the document, return null — do not guess. Respond ONLY with the\n"
            "JSON object matching the provided schema. No preamble.\n\n"
            f"Contract text:\n{text}"
        )

        schema = {
            "type": "object",
            "properties": {
                "parties": {"type": "object"},
                "effective_date": {"type": ["string", "null"]},
                "expiration_date": {"type": ["string", "null"]},
                "auto_renewal": {"type": ["boolean", "null"]},
                "renewal_notice_days": {"type": ["integer", "null"]},
                "contract_value": {"type": ["string", "null"]},
                "payment_terms": {"type": ["string", "null"]},
                "termination_notice_days": {"type": ["integer", "null"]},
                "liability_cap": {"type": ["string", "null"]},
                "governing_law": {"type": ["string", "null"]},
                "confidentiality_period": {"type": ["string", "null"]},
                "ip_ownership": {"type": ["string", "null"]},
                "arbitration_required": {"type": ["boolean", "null"]},
            },
        }
        try:
            data = await self._call_llm(prompt, schema)
            if isinstance(data, list):
                data = {}
            return self._normalize_extracted(data if isinstance(data, dict) else {}, text)
        except Exception as e:
            # LLM call failed - log error and return empty result
            import logging
            logging.warning(f"ExtractorAgent failed: {e}")
            return self._normalize_extracted({}, text)

    def _normalize_extracted(self, raw: dict, text: str) -> dict:
        extracted = {
            "parties": {
                "client": {"name": None, "jurisdiction": None},
                "provider": {"name": None, "jurisdiction": None},
                "others": [],
            },
            "effective_date": None,
            "expiration_date": None,
            "auto_renewal": None,
            "renewal_notice_days": None,
            "contract_value": None,
            "payment_terms": None,
            "termination_notice_days": None,
            "liability_cap": None,
            "governing_law": None,
            "confidentiality_period": None,
            "ip_ownership": None,
            "arbitration_required": None,
        }

        # Copy known keys from LLM output.
        for key in extracted:
            if key in raw:
                extracted[key] = raw.get(key)

        # Backward compatibility for legacy extractor keys seen in existing reports.
        if not extracted["payment_terms"] and raw.get("payment"):
            extracted["payment_terms"] = raw.get("payment")

        if not extracted["parties"]["provider"]["name"] and raw.get("company_a"):
            extracted["parties"]["provider"]["name"] = raw.get("company_a")
        if not extracted["parties"]["client"]["name"] and raw.get("company_b"):
            extracted["parties"]["client"]["name"] = raw.get("company_b")

        # Heuristic extraction from raw text for critical fields.
        extracted["effective_date"] = extracted["effective_date"] or self._extract_date(
            text,
            [r"effective\s+date\s*[:\-]\s*([^\n\.]+)", r"effective\s+as\s+of\s*[:\-]\s*([^\n\.]+)"],
        )
        extracted["expiration_date"] = extracted["expiration_date"] or self._extract_date(
            text,
            [r"expiration\s+date\s*[:\-]\s*([^\n\.]+)", r"expires?\s+on\s*[:\-]?\s*([^\n\.]+)"],
        )
        extracted["contract_value"] = extracted["contract_value"] or self._extract_first(
            text,
            [r"contract\s+value\s*[:\-]\s*([^\n\.]+)", r"\$\s?[\d,]+(?:\.\d+)?", r"USD\s?[\d,]+(?:\.\d+)?"],
        )
        extracted["payment_terms"] = extracted["payment_terms"] or self._extract_first(
            text,
            [r"payment\s+terms?\s*[:\-]\s*([^\n\.]+)", r"payment\s*[:\-]\s*([^\n\.]+)"],
        )
        extracted["termination_notice_days"] = extracted["termination_notice_days"] or self._extract_int(
            text,
            [r"termination\s+notice\s*[:\-]?\s*(\d{1,3})\s*days", r"(\d{1,3})\s*days\s+notice"],
        )
        extracted["liability_cap"] = extracted["liability_cap"] or self._extract_first(
            text,
            [r"liability\s+cap\s*[:\-]\s*([^\n\.]+)", r"liability\s+shall\s+not\s+exceed\s*([^\n\.]+)"],
        )
        extracted["governing_law"] = extracted["governing_law"] or self._extract_first(
            text,
            [r"governing\s+law\s*[:\-]\s*([^\n\.]+)", r"laws\s+of\s+([^\n\.,]+)"],
        )

        if extracted["auto_renewal"] is None:
            lower_text = text.lower()
            if "auto-renew" in lower_text or "automatically renew" in lower_text:
                extracted["auto_renewal"] = True
            elif "no auto-renew" in lower_text or "will not renew automatically" in lower_text:
                extracted["auto_renewal"] = False

        if not extracted["parties"]["provider"]["name"] or not extracted["parties"]["client"]["name"]:
            match = re.search(r"between\s+(.+?)\s+and\s+(.+?)(?:\.|\n|$)", text, flags=re.IGNORECASE)
            if match:
                extracted["parties"]["provider"]["name"] = extracted["parties"]["provider"]["name"] or match.group(1).strip()
                extracted["parties"]["client"]["name"] = extracted["parties"]["client"]["name"] or match.group(2).strip()

        return extracted

    def _extract_first(self, text: str, patterns: list[str]) -> str | None:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip() if match.groups() else match.group(0).strip()
        return None

    def _extract_int(self, text: str, patterns: list[str]) -> int | None:
        value = self._extract_first(text, patterns)
        if not value:
            return None
        digits = re.search(r"\d+", value)
        return int(digits.group(0)) if digits else None

    def _extract_date(self, text: str, patterns: list[str]) -> str | None:
        raw = self._extract_first(text, patterns)
        if not raw:
            return None

        candidate = raw.strip().rstrip(".,")
        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %B %Y",
            "%d %b %Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(candidate, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return candidate
