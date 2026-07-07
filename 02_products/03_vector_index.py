# Databricks notebook source
# MAGIC %pip install databricks-ai-search --quiet
# MAGIC # Legacy fallback (still supported): %pip install databricks-vectorsearch
# MAGIC %restart_python

# COMMAND ----------
"""Product 3 · Vector index (RAG) — endpoint + Delta Sync index, idempotent.

Managed embeddings keep the index in sync with the chunks table and are
required by the managed MCP AI Search server. The index embeds the
context-enriched chunk_to_embed column and serves hybrid (semantic + BM25)
retrieval. Docs:
https://docs.databricks.com/aws/en/ai-search/create-ai-search

Idempotency uses explicit existence checks (list_*), not error-message
matching, and provisioning waits use capped exponential backoff.
"""
import config
from lib.ai_search import get_search_client
from lib.retry import wait_until

config.validate()
client = get_search_client()  # AISearchClient if present, else VectorSearchClient


def _names(listing: dict, *keys: str) -> set[str]:
    """Pull object names out of a list_* response, tolerant of key naming."""
    for k in keys:
        items = listing.get(k)
        if isinstance(items, list):
            return {i.get("name") for i in items if isinstance(i, dict)}
    return set()


# --- Endpoint (idempotent via explicit existence check) ------------------------
try:
    endpoints = _names(client.list_endpoints(), "endpoints")
except Exception:
    endpoints = set()
if config.VS_ENDPOINT in endpoints:
    print(f"endpoint {config.VS_ENDPOINT} already exists")
else:
    client.create_endpoint(name=config.VS_ENDPOINT, endpoint_type=config.VS_ENDPOINT_TYPE)
    print(f"creating endpoint {config.VS_ENDPOINT} …")

# --- Index (idempotent via explicit existence check) ---------------------------
try:
    indexes = _names(client.list_indexes(name=config.VS_ENDPOINT), "vector_indexes", "indexes")
except Exception:
    indexes = set()
if config.VS_INDEX in indexes:
    print(f"index {config.VS_INDEX} already exists")
else:
    client.create_delta_sync_index(
        endpoint_name=config.VS_ENDPOINT,
        index_name=config.VS_INDEX,
        source_table_name=config.CHUNKS_TABLE,          # CDF enabled in the pipeline
        pipeline_type="TRIGGERED",
        primary_key=config.INDEX_PRIMARY_KEY,           # chunk_id
        embedding_source_column=config.EMBEDDING_SOURCE_COLUMN,   # chunk_to_embed
        embedding_model_endpoint_name=config.EMBEDDING_MODEL,     # databricks-qwen3-embedding-0-6b
    )
    print(f"creating index {config.VS_INDEX} …")

# --- Wait until queryable (typed status + capped backoff) ----------------------
index = client.get_index(endpoint_name=config.VS_ENDPOINT, index_name=config.VS_INDEX)


def _ready():
    status = index.describe().get("status", {})
    detailed = str(status.get("detailed_state", "")).upper()
    if status.get("ready") is True or "ONLINE" in detailed:
        return True
    if "FAILED" in detailed or "OFFLINE" in detailed:
        raise RuntimeError(f"Index entered a failed state: {status}")
    return False


wait_until(
    _ready,
    timeout_s=config.INDEX_READY_TIMEOUT_S,
    interval_s=15,
    on_wait=lambda d: print(f"waiting for index … (next check in {d:.0f}s)"),
)
print("index is ready")

# --- Smoke query: hybrid = semantic + BM25 keyword -----------------------------
cols = config.INDEX_QUERY_COLUMNS  # chunk_id, chunk_content, source_uri, chunk_position
hits = index.similarity_search(
    query_text="what is the return window for electronics?",
    columns=cols,
    num_results=3,
    query_type="HYBRID",
)
for row in hits.get("result", {}).get("data_array", []):
    r = dict(zip(cols, row))
    print(f"- {r['source_uri']} #{r['chunk_position']} :: {str(r['chunk_content'])[:80]}…")

# One more quality notch (optional): the built-in reranker is a single extra
# argument — ~10% relevance lift for ~1.5s added latency, per the docs.
#   from databricks.ai_search.reranker import DatabricksReranker
#   index.similarity_search(..., reranker=DatabricksReranker(columns_to_rerank=["chunk_content"]))
