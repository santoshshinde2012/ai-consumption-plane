"""PII redaction — baseline regex and production-grade native ``ai_mask``.

Redaction happens in Silver, BEFORE anything is embedded: once personal data is
inside a vector, deletion is much harder. Two engines, chosen by config.PII_ENGINE:

  * ``regex``  — fast, deterministic, zero cost, no external calls. Catches emails
    and phone numbers. The safe default; runs anywhere.
  * ``ai_mask`` — the Databricks-native AI function ``ai_mask(content, labels)``,
    which masks named entity types (person, address, etc.) an LLM can recognize
    but a regex cannot. Costs AI_FUNCTIONS tokens; recommended for production.

This module is pure (no Spark imports) so the regex engine and the SQL-expression
builder are unit-testable in CI. The pipeline applies whichever engine is active.
"""
from __future__ import annotations

import re

# Entity types masked by the ai_mask engine. Keep short, model-recognizable labels.
PII_LABELS = [
    "email",
    "phone number",
    "person name",
    "street address",
    "credit card number",
    "national id",
]

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")


def redact_regex(text: str) -> str:
    """Mask emails and phone numbers (baseline). Idempotent."""
    text = _EMAIL.sub("[EMAIL]", text or "")
    text = _PHONE.sub("[PHONE]", text)
    return text


def ai_mask_expr(column: str, labels: list[str] | None = None) -> str:
    """Build the ``ai_mask`` SQL expression for a column.

    Returns e.g. ``ai_mask(chunk_content, array('email', 'phone number', ...))``.
    Labels are sanitized (single quotes stripped) to keep the SQL well-formed.
    """
    labels = labels or PII_LABELS
    quoted = ", ".join("'" + label.replace("'", "") + "'" for label in labels)
    return f"ai_mask({column}, array({quoted}))"
