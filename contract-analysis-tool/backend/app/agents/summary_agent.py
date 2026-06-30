from __future__ import annotations

import asyncio

from app.agents.base_agent import BaseAgent


MAX_SUMMARY_CHUNKS = 8
MAX_CHUNK_CHARS = 1200


class SummaryAgent(BaseAgent):
    async def run(self, chunks: list[str], context: dict) -> dict:
        map_prompt = (
            "Summarize the following contract segment in 2–3 sentences. Focus on\n"
            "obligations, rights, and notable terms. Be concise and factual."
        )

        def _select_representative_chunks(items: list[str]) -> list[str]:
            if len(items) <= MAX_SUMMARY_CHUNKS:
                return items
            # Keep early, middle, and tail segments for broad coverage with fewer calls.
            picks: list[str] = []
            step = max(1, len(items) // MAX_SUMMARY_CHUNKS)
            for idx in range(0, len(items), step):
                picks.append(items[idx])
                if len(picks) >= MAX_SUMMARY_CHUNKS:
                    break
            return picks

        async def summarize_chunk(chunk: str) -> str:
            schema = {"type": "object", "properties": {"summary": {"type": "string"}}}
            try:
                clipped = chunk[:MAX_CHUNK_CHARS]
                data = await self._call_llm(f"{map_prompt}\\n\\n{clipped}", schema)
                if isinstance(data, dict):
                    return data.get("summary", "")
                return ""
            except Exception as e:
                # LLM call failed - log error and return empty string
                import logging
                logging.warning(f"SummaryAgent chunk summarization failed: {e}")
                return ""

        selected_chunks = _select_representative_chunks(chunks)
        partials = await asyncio.gather(*(summarize_chunk(c) for c in selected_chunks))

        reduce_prompt = (
            "You are a senior contract attorney. Given the following partial\n"
            "summaries and extracted contract data, write an executive summary\n"
            "a business executive could read in under 30 seconds. Then list the\n"
            "8 most important contract terms, any unusual or non-standard clauses,\n"
            "and the top 3 recommended actions for the reviewing party.\n"
            "Respond ONLY with the JSON object. No preamble.\n\n"
            f"Partial summaries:\n{partials}\n\n"
            f"Extracted data:\n{context.get('extracted', {})}\n\n"
            f"Risk flags:\n{context.get('risks', [])}"
        )
        schema = {
            "type": "object",
            "properties": {
                "executive_summary": {"type": "string"},
                "key_terms": {"type": "array", "items": {"type": "string"}},
                "unusual_clauses": {"type": "array", "items": {"type": "string"}},
                "overall_risk": {"type": "string"},
                "recommended_actions": {"type": "array", "items": {"type": "string"}},
            },
        }
        try:
            data = await self._call_llm(reduce_prompt, schema)
            if isinstance(data, list):
                return {}
            return data
        except Exception as e:
            # LLM call failed - log error and return empty result
            import logging
            logging.warning(f"SummaryAgent final summarization failed: {e}")
            return {}
