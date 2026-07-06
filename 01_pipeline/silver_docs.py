"""Silver (unstructured) · parse → enrich → chunk.

Parsing, enrichment, and chunking are Silver-class transformations — to
documents what deduplication and normalization are to rows. They run inside
the same declarative pipeline as the structured path.

Tables declared here (all streaming — @dp.table):
  1. support_docs_parsed   — ai_parse_document(content, map('version','2.0')) → VARIANT
     (document{pages,elements}, error_status, metadata; each element carries
     type/content/confidence/bbox).
  2. support_docs_enriched — ai_classify + ai_extract (v2 signatures accept the
     parsed VARIANT directly) → ONE structured row per document. "One document
     in, two data shapes out." Gated by ENABLE_ENRICHMENT.
  3. support_chunks        — retrieval-ready chunks; Change Data Feed ON (required
     by a Delta Sync index on a standard endpoint).

Two chunking paths, chosen by USE_AI_PREP_SEARCH — BOTH emit the same columns so
the vector index config is identical either way:
    chunk_id · chunk_content · chunk_to_embed · chunk_position · source_uri · path
  * False (default): deterministic manual chunker. Any supported runtime.
  * True:  platform-native ai_prep_search (Beta, DBR 18.2+). Output shape is
    document.contents[] with chunk_id / chunk_position / chunk_content /
    chunk_to_embed. Re-check the docs before shipping:
    https://docs.databricks.com/aws/en/sql/language-manual/functions/ai_prep_search

The pure chunking logic below mirrors lib/chunking.py so this file is
self-contained and guaranteed-runnable inside Lakeflow (where the repo root may
not be on sys.path). lib/chunking.py is unit-tested in CI — KEEP THE TWO IN SYNC.
"""
import hashlib
import json
import re

from pyspark import pipelines as dp
from pyspark.sql import functions as F
from pyspark.sql import types as T

# --- Config (keep in sync with config.py — pipeline files run standalone) -----
USE_AI_PREP_SEARCH = False
ENABLE_ENRICHMENT = True
CHUNK_SIZE_CHARS = 1000
CHUNK_OVERLAP_CHARS = 150
MIN_CHUNK_CHARS = 50

# ---------------------------------------------------------------------------
# 1) Parse — one expression, binary document → structured VARIANT.
# ---------------------------------------------------------------------------
@dp.table(
    comment="CONTRACT: structured parse of every Bronze document; elements + confidence + layout."
)
def support_docs_parsed():
    return spark.readStream.table("support_docs_bronze").selectExpr(
        "path",
        "ingest_time",
        "ai_parse_document(content, map('version', '2.0')) AS parsed",
    )


# ---------------------------------------------------------------------------
# 2) Enrich (optional) — ai_classify + ai_extract → one structured row/doc.
#     v2 signatures take the parsed VARIANT directly; results wrap in :response.
# ---------------------------------------------------------------------------
if ENABLE_ENRICHMENT:

    @dp.table(
        comment="CONTRACT: document category + extracted fields; complaints become analyzable rows."
    )
    def support_docs_enriched():
        return spark.sql(
            """
            WITH e AS (
              SELECT
                path,
                ingest_time,
                ai_classify(parsed, '["return_policy", "faq", "complaint_letter"]'):response[0]::STRING AS doc_type,
                ai_extract(parsed,  '["complaint_type", "severity", "product_id"]'):response            AS extracted
              FROM STREAM support_docs_parsed
              WHERE try_cast(parsed:error_status AS STRING) IS NULL
            )
            SELECT
              path,
              ingest_time,
              doc_type,
              extracted:complaint_type::STRING AS complaint_type,
              extracted:severity::STRING       AS severity,
              extracted:product_id::STRING     AS product_id
            FROM e
            """
        )


# ---------------------------------------------------------------------------
# Pure helpers for the manual chunker (mirror of lib/chunking.py — keep in sync).
# ---------------------------------------------------------------------------
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
_TITLE_TYPES = {"title", "header", "section_header", "sectionheader", "heading"}
_CONTENT_KEYS = ("content", "text")
_PAGE_KEYS = ("page_id", "page_number", "page", "page_no", "pageIndex")


def _redact(text: str) -> str:
    """PII redaction BEFORE embedding — protects the deletion story downstream."""
    text = _EMAIL.sub("[EMAIL]", text)
    text = _PHONE.sub("[PHONE]", text)
    return text


def _coerce_page(value, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _extract_pages(parsed):
    """Group redacted element text by page; capture per-page title for citations."""
    pages: dict = {}
    page_titles: dict = {}
    doc_title = ""

    def walk(node, cur_page):
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
                    break
            for v in node.values():
                walk(v, page)
        elif isinstance(node, list):
            for v in node:
                walk(v, cur_page)

    walk(parsed, 0)
    out = []
    for page in sorted(pages):
        out.append(
            {
                "page": int(page),
                "title": page_titles.get(page, doc_title),
                "text": _redact("\n".join(pages[page])),
            }
        )
    return out


def _window_text(text: str):
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= CHUNK_SIZE_CHARS:
        return [text] if len(text) >= MIN_CHUNK_CHARS else []
    step = max(CHUNK_SIZE_CHARS - CHUNK_OVERLAP_CHARS, 1)
    out, i = [], 0
    while i < len(text):
        piece = text[i : i + CHUNK_SIZE_CHARS].strip()
        if len(piece) >= MIN_CHUNK_CHARS:
            out.append(piece)
        if i + CHUNK_SIZE_CHARS >= len(text):
            break
        i += step
    return out


_PAGE_STRUCT = T.ArrayType(
    T.StructType(
        [
            T.StructField("page", T.IntegerType()),
            T.StructField("title", T.StringType()),
            T.StructField("text", T.StringType()),
        ]
    )
)


@F.udf(returnType=_PAGE_STRUCT)
def extract_pages_udf(parsed_json: str):
    try:
        return _extract_pages(json.loads(parsed_json))
    except Exception:
        return []


@F.udf(returnType=T.ArrayType(T.StringType()))
def window_chunks_udf(page_text: str):
    return _window_text(page_text)


@F.udf(returnType=T.StringType())
def chunk_id_udf(path: str, page: int, seq: int):
    return hashlib.sha1(f"{path}::{page}::{seq}".encode()).hexdigest()


# ---------------------------------------------------------------------------
# 3) Chunk — CDF ON (required by the standard-endpoint Delta Sync vector index).
# ---------------------------------------------------------------------------
@dp.table(
    comment="CONTRACT: retrieval-ready chunks with citations (source_uri, chunk_position); PII redacted; CDF on for index sync.",
    table_properties={"delta.enableChangeDataFeed": "true"},
)
def support_chunks():
    if USE_AI_PREP_SEARCH:
        # Beta path (DBR 18.2+). variant_explode over document.contents[]; parse
        # failures filtered so they never reach retrieval. Confirm field names
        # against the ai_prep_search docs before relying on this in production.
        return spark.sql(
            """
            WITH prepped AS (
              SELECT path, ai_prep_search(parsed) AS result
              FROM STREAM support_docs_parsed
              WHERE try_cast(parsed:error_status AS STRING) IS NULL
            )
            SELECT
              chunk.value:chunk_id::STRING         AS chunk_id,
              chunk.value:chunk_content::STRING    AS chunk_content,
              chunk.value:chunk_to_embed::STRING   AS chunk_to_embed,
              chunk.value:chunk_position::INT      AS chunk_position,
              p.result:document.source_uri::STRING AS source_uri,
              p.path
            FROM prepped AS p,
                 LATERAL variant_explode(p.result:document.contents) AS chunk
            """
        )

    # Manual fallback — deterministic, any runtime. Produces the SAME columns.
    parsed = spark.readStream.table("support_docs_parsed")
    exploded = parsed.select(
        "path", F.explode(extract_pages_udf(F.to_json("parsed"))).alias("pg")
    ).select(
        "path",
        F.col("pg.page").alias("page"),
        F.col("pg.title").alias("title"),
        F.col("pg.text").alias("page_text"),
    )
    chunked = exploded.select(
        "path",
        "page",
        "title",
        F.posexplode(window_chunks_udf(F.col("page_text"))).alias("chunk_position", "chunk_content"),
    )
    return chunked.select(
        chunk_id_udf(F.col("path"), F.col("page"), F.col("chunk_position")).alias("chunk_id"),
        F.col("chunk_content"),
        # Context-enriched embedding text: fold the page title in, like ai_prep_search.
        F.concat_ws(
            "\n", F.coalesce(F.col("title"), F.lit("")), F.col("chunk_content")
        ).alias("chunk_to_embed"),
        F.col("chunk_position"),
        # Citation anchor: source document + page.
        F.concat(F.col("path"), F.lit(" (p."), F.col("page").cast("string"), F.lit(")")).alias(
            "source_uri"
        ),
        F.col("path"),
    )
