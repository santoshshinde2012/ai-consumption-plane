# Databricks notebook source
# MAGIC %pip install "databricks-feature-engineering>=0.13.0" --quiet
# MAGIC %restart_python

# COMMAND ----------
"""Product 2 (online) · publish customer_features to a Lakebase online store.

The production upgrade for real-time serving: the same governed offline
feature table, now served with millisecond latency for real-time inference —
the same client, three calls. The online copy stays in sync with the offline
table in the mode you choose:
  * TRIGGERED   — scheduled incremental sync (default)
  * CONTINUOUS  — streaming, lowest staleness
  * SNAPSHOT    — full bulk refresh
TRIGGERED and CONTINUOUS require Change Data Feed + NOT NULL primary keys on the
source table.

Docs:
  https://docs.databricks.com/aws/en/machine-learning/feature-store/online-feature-store
  https://docs.databricks.com/aws/en/oltp/projects/feature-store  (publish modes)

Guarded by config.ENABLE_ONLINE_STORE (default False) — a Lakebase online
store BILLS WHILE IT EXISTS. Requires databricks-feature-engineering >= 0.13.0
and a Lakebase-enabled workspace.
"""
from databricks.feature_engineering import FeatureEngineeringClient

import config

if not config.ENABLE_ONLINE_STORE:
    print(
        "config.ENABLE_ONLINE_STORE is False — skipping online publish.\n"
        f"Set it True to serve {config.FEATURES_TABLE} online. The store bills while it exists."
    )
else:
    fe = FeatureEngineeringClient()

    # 1) Provision (or reuse) the Lakebase online store.
    try:
        fe.create_online_store(
            name=config.ONLINE_STORE_NAME,          # provisions a Lakebase project
            capacity=config.ONLINE_STORE_CAPACITY,  # CU_1 / CU_2 / CU_4 / CU_8
        )
        print(f"created online store {config.ONLINE_STORE_NAME}")
    except Exception as e:
        if "already exists" not in str(e).lower():
            raise
        print(f"online store {config.ONLINE_STORE_NAME} already exists — reusing")

    online_store = fe.get_online_store(name=config.ONLINE_STORE_NAME)

    # 2) Publish the offline feature table into it.
    fe.publish_table(
        online_store=online_store,                       # the object, not a name string
        source_table_name=config.FEATURES_TABLE,
        online_table_name=config.ONLINE_FEATURES_TABLE,
        publish_mode=config.ONLINE_PUBLISH_MODE,         # TRIGGERED | CONTINUOUS | SNAPSHOT
    )
    print(
        f"published {config.FEATURES_TABLE} → {config.ONLINE_FEATURES_TABLE} "
        f"({config.ONLINE_PUBLISH_MODE}). Serve with FeatureLookup at inference time."
    )
