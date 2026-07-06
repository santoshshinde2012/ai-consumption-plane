# Databricks notebook source
# MAGIC %pip install databricks-mcp databricks-sdk --quiet
# MAGIC %restart_python

# COMMAND ----------
"""Consumer side · connect an agent to a managed MCP server. Zero glue code.

"Zero glue code" is checkable — this is the ENTIRE integration layer for the
unstructured-retrieval tool. Tool discovery and the tool schema come from the
platform; these same ~10 lines are identical in LangGraph, the OpenAI Agents
SDK, or any MCP-capable framework.

On-behalf-of-user auth means each caller's own Unity Catalog permissions are
enforced on every call (see 04_grants.sql). Docs:
https://docs.databricks.com/aws/en/generative-ai/mcp/managed-mcp
"""
from databricks.sdk import WorkspaceClient
from databricks_mcp import DatabricksMCPClient

import config

w = WorkspaceClient()  # user, service principal, or OBO credentials
catalog, schema = config.PRODUCTS_SCHEMA.split(".")

mcp = DatabricksMCPClient(
    server_url=f"{w.config.host}/api/2.0/mcp/ai-search/{catalog}/{schema}",
    workspace_client=w,
)

# Tools are named catalog__schema__object.
tools = mcp.list_tools()
print("tools:", [t.name for t in tools])

result = mcp.call_tool(
    f"{catalog}__{schema}__support_docs_index",
    {"query": "what is the return window for electronics?"},
)
print("".join(c.text for c in result.content))

# The other two managed-MCP servers work the same way — only the server_url path
# changes: /api/2.0/mcp/genie/{space_id} and /api/2.0/mcp/functions/{catalog}/{schema}.
