"""AI Search client factory — one import site for the whole repo.

Databricks renamed Vector Search to **AI Search**, including the SDK:
the current package is ``databricks-ai-search`` (``AISearchClient``), and the
legacy ``databricks-vectorsearch`` (``VectorSearchClient``) still runs. Both
expose the same surface this build uses — ``create_endpoint``,
``create_delta_sync_index``, ``get_index``, ``delete_index``,
``delete_endpoint`` — and index objects share ``similarity_search`` /
``describe``.

This factory prefers the new client and transparently falls back, so every
script calls ``get_search_client()`` and never hard-codes the SDK name.
"""
from __future__ import annotations


def get_search_client():
    """Return an AI Search client, preferring the current SDK.

    Order: databricks-ai-search (AISearchClient) → databricks-vectorsearch
    (VectorSearchClient). Raises a clear error if neither is installed.
    """
    try:
        from databricks.ai_search.client import AISearchClient

        return AISearchClient()
    except Exception:
        pass
    try:
        from databricks.vector_search.client import VectorSearchClient

        return VectorSearchClient()
    except Exception as e:  # neither package present
        raise ImportError(
            "No AI Search SDK found. Install one of:\n"
            "  %pip install databricks-ai-search      # current\n"
            "  %pip install databricks-vectorsearch   # legacy (still supported)"
        ) from e
