from __future__ import annotations

import io
import json
from collections import Counter
from typing import Any

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def export_report_pdf(report: dict) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    writer = _PdfWriter(c, width, height)
    summary = report.get("summary", {}) or {}
    extracted = report.get("extracted", {}) or {}
    risks = report.get("risks", []) or []
    metadata = report.get("metadata", {}) or {}

    writer.heading("Contract Analysis Report", size=18)
    writer.kv("Report ID", report.get("report_id", "N/A"))
    writer.kv("Job ID", report.get("job_id", "N/A"))
    writer.kv("Overall Risk", summary.get("overall_risk", "N/A"))
    writer.kv("Generated", report.get("created_at", ""))
    writer.kv("File Name", metadata.get("filename", "N/A"))
    writer.kv("File Type", metadata.get("mime_type", "N/A"))
    writer.kv("Page Count", str(metadata.get("page_count", "N/A")))
    writer.spacer(12)

    writer.section("Executive Summary")
    writer.paragraph(summary.get("executive_summary", "No executive summary available."))

    writer.section("Most Important Contract Terms")
    important_terms = summary.get("most_important_contract_terms") or summary.get("most_important_terms") or []
    writer.bullets(important_terms, empty_message="No key terms extracted.")

    writer.section("Recommended Actions")
    writer.bullets(summary.get("recommended_actions", []), empty_message="No actions recommended.")

    writer.section("Unusual or Non-Standard Clauses")
    writer.bullets(summary.get("unusual_or_non_standard_clauses", []), empty_message="No unusual clauses detected.")

    writer.section("Key Extracted Fields")
    for label, value in _flatten_extracted_fields(extracted):
        writer.kv(label, value)

    writer.section("Risk Summary")
    risk_levels = [str((r or {}).get("risk_level", "UNKNOWN")).upper() for r in risks]
    counts = Counter(risk_levels)
    writer.kv("Total Risks", str(len(risks)))
    for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]:
        if counts.get(level):
            writer.kv(f"{level.title()} Risks", str(counts[level]))

    if risks:
        writer.section("Risk Details")
        for idx, risk in enumerate(risks, start=1):
            writer.kv(f"Risk #{idx}", f"{risk.get('risk_level', 'UNKNOWN')} - {risk.get('risk_category', 'General')}")
            writer.paragraph(f"Clause Type: {risk.get('clause_type', 'N/A')}")
            writer.paragraph(f"Description: {risk.get('risk_description', 'N/A')}")
            writer.paragraph(f"Recommendation: {risk.get('recommendation', 'N/A')}")
            snippet = risk.get("clause_text_snippet")
            if snippet:
                writer.paragraph(f"Snippet: {snippet}")
            writer.spacer(6)

    errors = report.get("errors", []) or []
    if errors:
        writer.section("Processing Notes")
        writer.bullets([str(e) for e in errors], empty_message="")

    writer.section("Raw Extracted JSON")
    writer.paragraph(json.dumps(extracted, indent=2))

    c.save()
    buffer.seek(0)
    return buffer.read()


class _PdfWriter:
    def __init__(self, c: canvas.Canvas, width: float, height: float):
        self.c = c
        self.width = width
        self.height = height
        self.left = 50
        self.right = width - 50
        self.top = height - 50
        self.bottom = 55
        self.y = self.top

    def _ensure_space(self, needed: float) -> None:
        if self.y - needed < self.bottom:
            self.c.showPage()
            self.y = self.top

    def heading(self, text: str, size: int = 16) -> None:
        self._ensure_space(24)
        self.c.setFont("Helvetica-Bold", size)
        self.c.drawString(self.left, self.y, text)
        self.y -= 24

    def section(self, text: str) -> None:
        self._ensure_space(20)
        self.c.setFont("Helvetica-Bold", 13)
        self.c.drawString(self.left, self.y, text)
        self.y -= 16

    def kv(self, label: str, value: Any) -> None:
        val = "N/A" if value is None else str(value)
        self._ensure_space(14)
        self.c.setFont("Helvetica-Bold", 10)
        self.c.drawString(self.left, self.y, f"{label}:")
        self.c.setFont("Helvetica", 10)
        for line in _wrap(val, 88):
            self._ensure_space(13)
            self.c.drawString(self.left + 115, self.y, line)
            self.y -= 13

    def paragraph(self, text: str) -> None:
        lines = _wrap(text or "", 100)
        self.c.setFont("Helvetica", 10)
        for line in lines:
            self._ensure_space(13)
            self.c.drawString(self.left, self.y, line)
            self.y -= 13

    def bullets(self, items: list[Any], empty_message: str = "No items available.") -> None:
        if not items and empty_message:
            self.paragraph(empty_message)
            return
        self.c.setFont("Helvetica", 10)
        for item in items:
            lines = _wrap(str(item), 96)
            for idx, line in enumerate(lines):
                self._ensure_space(13)
                prefix = "- " if idx == 0 else "  "
                self.c.drawString(self.left, self.y, f"{prefix}{line}")
                self.y -= 13

    def spacer(self, amount: float) -> None:
        self._ensure_space(amount)
        self.y -= amount


def _flatten_extracted_fields(extracted: dict[str, Any]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    priority_keys = [
        "effective_date",
        "expiration_date",
        "contract_value",
        "payment_terms",
        "termination_notice_days",
        "liability_cap",
        "governing_law",
        "auto_renewal",
        "confidentiality_period",
        "ip_ownership",
    ]

    for key in priority_keys:
        if key in extracted:
            pairs.append((key.replace("_", " ").title(), _stringify(extracted.get(key))))

    parties = extracted.get("parties")
    if isinstance(parties, dict):
        client_name = (((parties.get("client") or {}) if isinstance(parties.get("client"), dict) else {}).get("name"))
        provider_name = (((parties.get("provider") or {}) if isinstance(parties.get("provider"), dict) else {}).get("name"))
        if client_name:
            pairs.append(("Client", str(client_name)))
        if provider_name:
            pairs.append(("Provider", str(provider_name)))

    if not pairs:
        pairs.append(("Extracted", "No extracted fields available."))
    return pairs


def _stringify(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=True)
    return str(value)


def _wrap(text: str, width: int) -> list[str]:
    if not text:
        return [""]
    text = text.replace("\r", "")
    raw_lines = text.split("\n")
    output: list[str] = []
    for raw in raw_lines:
        words = raw.split()
        if not words:
            output.append("")
            continue
        current: list[str] = []
        for word in words:
            candidate = " ".join(current + [word])
            if len(candidate) <= width:
                current.append(word)
            else:
                if current:
                    output.append(" ".join(current))
                    current = [word]
                else:
                    output.append(word[:width])
                    remainder = word[width:]
                    while len(remainder) > width:
                        output.append(remainder[:width])
                        remainder = remainder[width:]
                    current = [remainder] if remainder else []
        if current:
            output.append(" ".join(current))
    return output
