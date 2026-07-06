"""Unit tests for lib/chunking.py — the retrieval product's quality contract
starts here (deterministic chunking + PII redaction), runnable in CI without
Spark or a Databricks workspace.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root on path

from lib.chunking import chunk_id, extract_pages, redact, window_text  # noqa: E402


# --- redact -----------------------------------------------------------------
def test_redact_masks_email_and_phone():
    out = redact("reach jane.doe@example.com or +1 415 555 0182 anytime")
    assert "jane.doe@example.com" not in out
    assert "415 555 0182" not in out
    assert "[EMAIL]" in out and "[PHONE]" in out


def test_redact_leaves_clean_text_untouched():
    clean = "Electronics must be returned within 30 days of delivery."
    assert redact(clean) == clean


# --- window_text ------------------------------------------------------------
def test_short_text_is_single_chunk():
    assert window_text("a short policy line that clears the floor", 1000, 150, 10) == [
        "a short policy line that clears the floor"
    ]


def test_text_below_min_is_dropped():
    assert window_text("tiny", 1000, 150, 50) == []


def test_long_text_windows_with_overlap():
    text = "".join(str(i % 10) for i in range(2500))  # 2500 chars
    chunks = window_text(text, 1000, 150, 50)
    assert len(chunks) >= 3
    assert all(len(c) <= 1000 for c in chunks)
    # Overlap: end of chunk 0 reappears at the start of chunk 1.
    assert chunks[0][-150:] == chunks[1][:150]
    # Coverage: the final characters of the source survive into the last chunk.
    assert text[-50:] in chunks[-1]


# --- extract_pages ----------------------------------------------------------
_PARSED = {
    "document": {
        "elements": [
            {"type": "title", "content": "E-Shop Return Policy", "page_id": 0},
            {"type": "text", "content": "Electronics: 30 days.", "page_id": 0},
            {"type": "text", "content": "Contact jane.doe@example.com.", "page_id": 1},
        ]
    }
}


def test_extract_pages_groups_by_page_and_redacts():
    pages = extract_pages(_PARSED)
    assert [p["page"] for p in pages] == [0, 1]
    assert pages[0]["title"] == "E-Shop Return Policy"
    assert "30 days" in pages[0]["text"]
    # PII on page 1 is redacted before it can ever be embedded.
    assert "[EMAIL]" in pages[1]["text"]
    # Untitled pages fall back to the document title for citation.
    assert pages[1]["title"] == "E-Shop Return Policy"


def test_extract_pages_tolerates_junk():
    assert extract_pages({}) == []
    assert extract_pages([1, "x", None]) == []


# --- chunk_id ---------------------------------------------------------------
def test_chunk_id_is_deterministic_and_unique():
    a = chunk_id("/Volumes/x/doc.pdf", 0, 0)
    assert a == chunk_id("/Volumes/x/doc.pdf", 0, 0)  # stable → idempotent sync
    assert a != chunk_id("/Volumes/x/doc.pdf", 0, 1)  # seq varies
    assert a != chunk_id("/Volumes/x/doc.pdf", 1, 0)  # page varies
