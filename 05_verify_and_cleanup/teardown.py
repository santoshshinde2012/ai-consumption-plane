# Databricks notebook source
# MAGIC %pip install databricks-ai-search "databricks-feature-engineering>=0.13.0" --quiet
# MAGIC %restart_python

# COMMAND ----------
"""Teardown — stops all ongoing costs. Destructive; read the flags.

Deletes the vector index and endpoint and (if it exists) the Lakebase online
store — the assets that bill while idle — then drops the schemas.
Set DROP_CATALOG=True to remove everything.
"""
import config
from lib.ai_search import get_search_client

DROP_CATALOG = False  # set True to also drop the eshop catalog itself

client = get_search_client()

# --- Vector search assets (billed while they exist) ----------------------------
for label, fn in [
    (
        f"index {config.VS_INDEX}",
        lambda: client.delete_index(endpoint_name=config.VS_ENDPOINT, index_name=config.VS_INDEX),
    ),
    (f"endpoint {config.VS_ENDPOINT}", lambda: client.delete_endpoint(name=config.VS_ENDPOINT)),
]:
    try:
        fn()
        print(f"deleted {label}")
    except Exception as e:
        print(f"skip {label}: {e}")

# --- Online feature store (billed while it exists) -----------------------------
if config.ENABLE_ONLINE_STORE:
    try:
        from databricks.feature_engineering import FeatureEngineeringClient

        fe = FeatureEngineeringClient()
        # delete_online_store also removes published online tables in the store.
        fe.delete_online_store(name=config.ONLINE_STORE_NAME)
        print(f"deleted online store {config.ONLINE_STORE_NAME}")
    except Exception as e:
        print(f"skip online store {config.ONLINE_STORE_NAME}: {e}")

# --- Schemas / catalog ---------------------------------------------------------
targets = (
    [f"DROP CATALOG IF EXISTS {config.CATALOG} CASCADE"]
    if DROP_CATALOG
    else [
        f"DROP SCHEMA IF EXISTS {config.PRODUCTS_SCHEMA} CASCADE",
        f"DROP SCHEMA IF EXISTS {config.SILVER_SCHEMA} CASCADE",
        f"DROP SCHEMA IF EXISTS {config.BRONZE_SCHEMA} CASCADE",
    ]
)
for stmt in targets:
    spark.sql(stmt)
    print(stmt)

print(
    "\nDone. Also delete the Lakeflow pipeline and any Genie space you created via the UI."
)
