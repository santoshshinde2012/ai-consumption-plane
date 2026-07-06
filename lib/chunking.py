"""Pure, dependency-free chunking + PII-redaction logic.

This module has NO Spark/Databricks imports on purpose so it can be unit
tested in CI on a plain Python runtime (see ``tests/test_chunking.py``).

``01_pipeline/silver_docs.py`` inlines the same algorithm (it must stay
self-contained to be guaranteed-runnable inside a Lakeflow pipeline where the
repo root may not be on ``sys.path``). **Keep the two in sync** — the inline
copy carries a comment pointing back here.

The functions operate on the already-JSON-decoded output of
``ai_parse_document``. That output is a versioned (major.minor) structure whose
exact field names can grow over releases, so the walker is deliberately
schema-tolerant: it collects any string under a ``content``/``text`` key and
groups it by whatever page identifier it can find.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

# --- PII redaction -----------------------------------------------------------
# Baseline regex redaction. Redaction happens in Silver, BEFORE anything is
# embedded — once PII is inside an embedding the deletion story gets much
# harder. Swap in ``ai_query`` or a dedicated PII library for production.
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")

_TITLE_TYPES = {"title", "header", "section_header", "sectionheader", "heading"}
_CONTENT_KEYS = ("content", "text")
_PAGE_KEYS = ("page_id", "page_number", "page", "page_no", "pageIndex")


def redact(text: str) -> str:
    """Mask emails and phone numbers. Order matters little; both are disjoint."""
    text = _EMAIL.sub("[EMAIL]", text)
    text = _PHONE.sub("[PHONE]", text)
    return text


def _coerce_page(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def extract_pages(parsed: Any) -> list[dict]:
    """Walk parsed document output into one redacted text blob per page.

    Returns a list of ``{"page": int, "title": str, "text": str}`` sorted by
    page. ``title`` is the first title/header seen on that page (falling back
    to the document title) — these become the citations RAG answers show.
    """
    pages: dict[int, list[str]] = {}
    page_titles: dict[int, str] = {}
    doc_title = ""

    def walk(node: Any, cur_page: int) -> None:
        nonlocal doc_title
        if isinstance(node, dict):
            page = cur_page
            for k in _PAGE_KEYS:
                if k in node:
                    page = _coerce_page(node[k], cur_page)
                    break
            etype = str(node.get("type", "")).strip().lower()
            for ck in _CONTENT_KEYS:
                content = node.get(ck)
                if isinstance(content, str) and content.strip():
                    pages.setdefault(page, []).append(content.strip())
                    if etype in _TITLE_TYPES:
                        page_titles.setdefault(page, content.strip())
                        if not doc_title:
                            doc_title = content.strip()
                    break  # don't double-count content + text on one node
            for v in node.values():
                walk(v, page)
        elif isinstance(node, list):
            for v in node:
                walk(v, cur_page)

    walk(parsed, 0)

    out: list[dict] = []
    for page in sorted(pages):
        text = redact("\n".join(pages[page]))
        out.append({"page": page, "title": page_titles.get(page, doc_title), "text": text})
    return out


def window_text(
    text: str,
    size: int,
    overlap: int,
    min_chars: int,
) -> list[str]:
    """Split ``text`` into overlapping character windows.

    Short text (``<= size``) yields a single chunk when it clears
    ``min_chars``, otherwise nothing (drop noise). Chunk size stays a *quality
    knob* — the retrieval evaluation is what tells you the right value.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text] if len(text) >= min_chars else []

    step = max(size - overlap, 1)
    chunks: list[str] = []
    i = 0
    while i < len(text):
        piece = text[i : i + size].strip()
        if len(piece) >= min_chars:
            chunks.append(piece)
        if i + size >= len(text):
            break
        i += step
    return chunks


def chunk_id(path: str, page: int, seq: int) -> str:
    """Stable, content-addressable id — same (path, page, seq) → same id.

    Deterministic ids make the chunks table (and therefore the synced vector
    index) idempotent across pipeline re-runs.
    """
    return hashlib.sha1(f"{path}::{page}::{seq}".encode()).hexdigest()
