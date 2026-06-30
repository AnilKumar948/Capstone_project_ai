from __future__ import annotations

import asyncio
import re
from difflib import SequenceMatcher

from app.agents.base_agent import BaseAgent


CLAUSE_TYPES = [
    "TERMINATION",
    "LIABILITY",
    "CONFIDENTIALITY",
    "PAYMENT",
    "INDEMNIFICATION",
    "INTELLECTUAL_PROPERTY",
    "GOVERNING_LAW",
    "DISPUTE_RESOLUTION",
    "FORCE_MAJEURE",
    "WARRANTY",
    "NON_COMPETE",
    "ASSIGNMENT",
    "RENEWAL",
    "NOTICE",
    "GENERAL",
]

MAX_CLAUSE_CHUNKS = 12
MAX_CLAUSE_CHARS = 1400
MIN_USEFUL_CLAUSES = 4

CLAUSE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "TERMINATION": ("terminate", "termination", "terminated", "notice period"),
    "LIABILITY": ("liability", "liable", "damages", "limitation of liability", "liability cap"),
    "CONFIDENTIALITY": ("confidential", "non-disclosure", "confidentiality"),
    "PAYMENT": ("payment", "invoice", "fees", "net 30", "compensation"),
    "INDEMNIFICATION": ("indemnify", "indemnification", "hold harmless"),
    "INTELLECTUAL_PROPERTY": ("intellectual property", "ip ownership", "ownership of deliverables", "license"),
    "GOVERNING_LAW": ("governing law", "laws of", "state of"),
    "DISPUTE_RESOLUTION": ("dispute", "arbitration", "mediation", "venue", "jurisdiction"),
    "FORCE_MAJEURE": ("force majeure", "acts of god"),
    "WARRANTY": ("warranty", "warrants", "representations"),
    "NON_COMPETE": ("non-compete", "non solicit", "non-solicit", "restrictive covenant"),
    "ASSIGNMENT": ("assign", "assignment", "delegate"),
    "RENEWAL": ("renewal", "renew", "auto-renew"),
    "NOTICE": ("notice", "written notice", "deliver notice"),
}

LABEL_PATTERNS: tuple[tuple[str, str], ...] = (
    ("effective date", "GENERAL"),
    ("expiration date", "GENERAL"),
    ("contract value", "PAYMENT"),
    ("payment terms", "PAYMENT"),
    ("termination notice", "TERMINATION"),
    ("liability cap", "LIABILITY"),
    ("governing law", "GOVERNING_LAW"),
    ("auto-renewal", "RENEWAL"),
    ("confidentiality period", "CONFIDENTIALITY"),
    ("ip ownership", "INTELLECTUAL_PROPERTY"),
    ("arbitration", "DISPUTE_RESOLUTION"),
    ("indemnification", "INDEMNIFICATION"),
    ("notice", "NOTICE"),
)


class ClauseAgent(BaseAgent):
    async def run(self, chunks: list[str], context: dict) -> list[dict]:
        system_prompt = (
            "You are a legal document analysis AI. Given a segment of a contract, "
            "identify and extract every distinct clause. For each clause:\n"
            "- Assign exactly one clause_type from the provided vocabulary.\n"
            "- Copy the clause text verbatim from the input.\n"
            "- Estimate confidence (0.0–1.0) based on how clearly the clause "
            "matches its type.\n"
            "Respond ONLY with a JSON array of clause objects. No preamble."
        )
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "clause_type": {"type": "string", "enum": CLAUSE_TYPES},
                    "text": {"type": "string"},
                    "page_hint": {"type": "integer"},
                    "confidence": {"type": "number"},
                },
                "required": ["clause_type", "text", "page_hint", "confidence"],
            },
        }

        def _select_chunks(items: list[str]) -> list[str]:
            if len(items) <= MAX_CLAUSE_CHUNKS:
                return items
            # Distribute picks across the document to preserve coverage.
            picks: list[str] = []
            step = max(1, len(items) // MAX_CLAUSE_CHUNKS)
            for i in range(0, len(items), step):
                picks.append(items[i])
                if len(picks) >= MAX_CLAUSE_CHUNKS:
                    break
            return picks

        async def process_chunk(idx: int, chunk: str) -> list[dict]:
            clipped = chunk[:MAX_CLAUSE_CHARS]
            prompt = (
                f"{system_prompt}\\n\\n"
                f"Allowed clause types: {', '.join(CLAUSE_TYPES)}\\n"
                f"Chunk index: {idx}\\n"
                f"Contract segment:\n{clipped}"
            )
            try:
                data = await self._call_llm(prompt, schema)
                if isinstance(data, dict):
                    return data.get("clauses", [])
                return data
            except Exception as e:
                # LLM call failed - log error and return empty result
                import logging
                logging.warning(f"ClauseAgent failed for chunk {idx}: {e}")
                return []

        selected_chunks = _select_chunks(chunks)
        outputs = await asyncio.gather(*(process_chunk(i, c) for i, c in enumerate(selected_chunks)))
        flattened = [item for sublist in outputs for item in sublist]
        merged = self._merge_overlaps(flattened)
        if len(merged) >= MIN_USEFUL_CLAUSES:
            return merged

        heuristic_clauses = self._extract_heuristic_clauses(chunks)
        combined = merged + heuristic_clauses
        return self._merge_overlaps(combined)

    def _merge_overlaps(self, clauses: list[dict]) -> list[dict]:
        merged: list[dict] = []
        for clause in clauses:
            text = clause.get("text", "")
            if not text:
                continue
            dup = next(
                (
                    existing
                    for existing in merged
                    if existing.get("clause_type") == clause.get("clause_type")
                    and SequenceMatcher(None, existing.get("text", ""), text).ratio() > 0.9
                ),
                None,
            )
            if dup:
                dup["confidence"] = max(dup.get("confidence", 0), clause.get("confidence", 0))
                continue
            merged.append(clause)
        return merged

    def _extract_heuristic_clauses(self, chunks: list[str]) -> list[dict]:
        candidates: list[dict] = []
        for page_hint, chunk in enumerate(chunks, start=1):
            segments = self._split_chunk_into_segments(chunk)
            for paragraph in segments:
                normalized = " ".join(paragraph.split())
                if len(normalized) < 20:
                    continue
                clause_type = self._infer_clause_type(normalized)
                if not clause_type:
                    continue
                candidates.append(
                    {
                        "clause_type": clause_type,
                        "text": normalized[:1200],
                        "page_hint": page_hint,
                        "confidence": 0.72,
                    }
                )
        return candidates

    def _split_chunk_into_segments(self, chunk: str) -> list[str]:
        paragraphs = [part.strip() for part in re.split(r"\n{2,}|(?<=[.!?])\s{2,}", chunk) if part.strip()]
        segments: list[str] = []
        for paragraph in paragraphs:
            labeled = self._split_labeled_phrases(paragraph)
            if labeled:
                segments.extend(labeled)
            else:
                segments.append(paragraph)
        return segments

    def _split_labeled_phrases(self, text: str) -> list[str]:
        compact = re.sub(r"\s+", " ", text).strip()
        matches: list[tuple[int, str, str]] = []
        for label, clause_type in LABEL_PATTERNS:
            for match in re.finditer(rf"\b{re.escape(label)}\s*:", compact, flags=re.IGNORECASE):
                matches.append((match.start(), label, clause_type))

        if len(matches) < 2:
            return []

        matches.sort(key=lambda item: item[0])
        segments: list[str] = []
        for idx, (start, label, _clause_type) in enumerate(matches):
            end = matches[idx + 1][0] if idx + 1 < len(matches) else len(compact)
            piece = compact[start:end].strip(" .;")
            if len(piece) >= 15:
                segments.append(piece)
        return segments

    def _infer_clause_type(self, text: str) -> str | None:
        lowered = text.lower()
        for clause_type, keywords in CLAUSE_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                return clause_type
        if any(token in lowered for token in ("shall", "agreement", "party", "obligation")):
            return "GENERAL"
        return None
