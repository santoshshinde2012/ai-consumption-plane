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
"""
import time

import config
from lib.ai_search import get_search_client

client = get_search_client()  # AISearchClient if present, else VectorSearchClient

# --- Endpoint (idempotent) ----------------------------------------------------
try:
    client.create_endpoint(name=config.VS_ENDPOINT, endpoint_type=config.VS_ENDPOINT_TYPE)
    print(f"creating endpoint {config.VS_ENDPOINT} …")
except Exception as e:
    if "already exists" not in str(e).lower():
        raise
    print(f"endpoint {config.VS_ENDPOINT} already exists")

# --- Index (idempotent) --------------------------------------------------------
try:
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
except Exception as e:
    if "already exists" not in str(e).lower():
        raise
    print(f"index {config.VS_INDEX} already exists")

# --- Wait until queryable -------------------------------------------------------
index = client.get_index(endpoint_name=config.VS_ENDPOINT, index_name=config.VS_INDEX)
deadline = time.time() + 30 * 60
while time.time() < deadline:
    status = str(index.describe().get("status", {}))
    if "ONLINE" in status.upper() or '"ready":true' in status.replace(" ", "").lower():
        print("index is ready")
        break
    print("waiting for index …")
    time.sleep(30)
else:
    raise TimeoutError("Index not ready after 30 minutes — check the endpoint in the UI.")

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
