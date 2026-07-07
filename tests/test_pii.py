"""Tests for lib/pii.py — redaction is the deletion story's first line."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.pii import PII_LABELS, ai_mask_expr, redact_regex  # noqa: E402


def test_regex_masks_email_and_phone():
    out = redact_regex("reach jane.doe@example.com or +1 415 555 0182")
    assert "jane.doe@example.com" not in out
    assert "415 555 0182" not in out
    assert "[EMAIL]" in out and "[PHONE]" in out


def test_regex_is_idempotent():
    once = redact_regex("mail a@b.com")
    assert redact_regex(once) == once


def test_regex_handles_none():
    assert redact_regex(None) == ""


def test_ai_mask_expr_is_well_formed_sql():
    expr = ai_mask_expr("chunk_content")
    assert expr.startswith("ai_mask(chunk_content, array(")
    assert expr.endswith("))")
    for label in PII_LABELS:
        assert f"'{label}'" in expr


def test_ai_mask_expr_sanitizes_quotes():
    expr = ai_mask_expr("col", labels=["o'brien"])
    assert "''" not in expr and "obrien" in expr  # single quote stripped, SQL stays valid
