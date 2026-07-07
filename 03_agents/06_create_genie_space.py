# Databricks notebook source
# MAGIC %pip install databricks-sdk --quiet
# MAGIC %restart_python

# COMMAND ----------
"""Genie-space-as-code · create the space programmatically where the API allows.

Genie Space management is a newer, evolving API surface. This script attempts
the SDK/REST call and, if the endpoint isn't available in your workspace/SDK
version, prints the exact manual steps (02_genie_space.md) instead of failing —
so the plane stays reproducible without pretending an API exists that doesn't.

On success it prints the space_id to paste into config.GENIE_SPACE_ID.
"""
import json

from databricks.sdk import WorkspaceClient

import config

w = WorkspaceClient()

warehouse_id = None
try:
    warehouses = list(w.warehouses.list())
    warehouse_id = warehouses[0].id if warehouses else None
except Exception:
    pass

payload = {
    "display_name": "E-Shop Sales",
    "description": "Certified sales metrics for agents and analysts.",
    "warehouse_id": warehouse_id,
    "table_identifiers": [config.METRIC_VIEW, config.MART_VIEW],
}

created_id = None
# Try the SDK's genie surface, then a raw REST POST, before giving up gracefully.
try:
    if hasattr(w, "genie") and hasattr(w.genie, "create_space"):
        space = w.genie.create_space(**payload)  # type: ignore[attr-defined]
        created_id = getattr(space, "space_id", None) or getattr(space, "id", None)
    else:
        resp = w.api_client.do("POST", "/api/2.0/genie/spaces", body=payload)
        created_id = resp.get("space_id") or resp.get("id")
except Exception as e:
    print(
        "Programmatic Genie Space creation isn't available here "
        f"({type(e).__name__}: {e}).\n"
        "Create it via the UI per 03_agents/02_genie_space.md — add "
        f"{config.METRIC_VIEW} and {config.MART_VIEW}, then set config.GENIE_SPACE_ID."
    )

if created_id:
    print(f"created Genie Space: {created_id}")
    print(f"Set in config.py:  GENIE_SPACE_ID = \"{created_id}\"")
    print(json.dumps(payload, indent=2))
