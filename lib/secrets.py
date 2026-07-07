"""Runtime secret access via Databricks secret scopes.

Keep credentials (external API keys, tokens) out of source and out of config.py.
On Databricks, ``dbutils.secrets.get`` reads from a scope; locally this falls
back to environment variables so the same code runs in tests/CI.

Create a scope once:
    databricks secrets create-scope eshop
    databricks secrets put-secret eshop some_api_key
"""
from __future__ import annotations

import os


def get_secret(key: str, scope: str | None = None, default: str | None = None) -> str | None:
    """Return a secret from the Databricks scope, else env var, else default.

    Env fallback key is the upper-cased ``key`` (e.g. ``some_api_key`` →
    ``SOME_API_KEY``), so CI can inject the same value without a workspace.
    """
    scope = scope or os.environ.get("DATABRICKS_SECRET_SCOPE", "eshop")
    try:
        dbutils  # type: ignore[name-defined]  # injected in Databricks
        return dbutils.secrets.get(scope=scope, key=key)  # noqa: F821
    except Exception:
        return os.environ.get(key.upper(), default)
