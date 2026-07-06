# Databricks notebook source
# MAGIC %pip install databricks-sdk databricks-ai-search --quiet
# MAGIC %restart_python

# COMMAND ----------
"""Agent exposure · verify the three tool surfaces and print your MCP URLs.

Managed MCP servers are hosted by Databricks and governed by Unity Catalog —
this script does not create anything; it confirms the assets exist and gives
you the exact URLs to plug into an MCP client (AI Playground, Claude Desktop,
Cursor, or agent code — see 05_mcp_client_example.py). Docs:
https://docs.databricks.com/aws/en/generative-ai/mcp/managed-mcp
"""
from databricks.sdk import WorkspaceClient

import config
from lib.ai_search import get_search_client

w = WorkspaceClient()
host = w.config.host.rstrip("/")
catalog, schema = config.PRODUCTS_SCHEMA.split(".")

# --- 1) Vector index reachable? -------------------------------------------------
index = get_search_client().get_index(
    endpoint_name=config.VS_ENDPOINT, index_name=config.VS_INDEX
)
n = index.similarity_search(
    query_text="return window", columns=[config.INDEX_PRIMARY_KEY], num_results=1
)
assert n.get("result", {}).get("data_array"), "Vector index returned no results"
print(f"[ok] vector index {config.VS_INDEX} answers queries")

# --- 2) UC function tool present? ------------------------------------------------
spark.sql(f"DESCRIBE FUNCTION {config.LOOKUP_FUNCTION}")
print(f"[ok] function {config.LOOKUP_FUNCTION} exists")

# --- 3) Genie space configured? ----------------------------------------------------
genie = (
    f"{host}/api/2.0/mcp/genie/{config.GENIE_SPACE_ID}"
    if config.GENIE_SPACE_ID
    else "(create the space per 02_genie_space.md, then set config.GENIE_SPACE_ID)"
)

print(
    f"""
Your managed MCP servers (per {host}):

  Unstructured retrieval : {host}/api/2.0/mcp/ai-search/{catalog}/{schema}
  Structured analytics   : {genie}
  Deterministic lookups  : {host}/api/2.0/mcp/functions/{catalog}/{schema}

Test them in AI Playground (add tools -> MCP), with 05_mcp_client_example.py,
or any MCP client with OAuth to this workspace. On-behalf-of-user auth enforces
each caller's own Unity Catalog permissions on every call (see 04_grants.sql).
"""
)
