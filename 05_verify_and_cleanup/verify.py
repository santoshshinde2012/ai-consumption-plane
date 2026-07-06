# Databricks notebook source
# MAGIC %pip install databricks-ai-search --quiet
# MAGIC %restart_python

# COMMAND ----------
"""One-shot health check across every stage of the plane."""
import config
from lib.ai_search import get_search_client

checks: list[tuple[str, str]] = []


def check(label: str, fn):
    try:
        detail = fn()
        checks.append(("PASS", f"{label}: {detail}"))
    except Exception as e:
        checks.append(("FAIL", f"{label}: {e}"))


def count(t: str) -> str:
    return f"{spark.table(t).count()} rows"


check("bronze.orders_bronze", lambda: count(f"{config.BRONZE_SCHEMA}.orders_bronze"))
check("bronze.support_docs_bronze", lambda: count(f"{config.BRONZE_SCHEMA}.support_docs_bronze"))
check("silver.orders_silver", lambda: count(f"{config.SILVER_SCHEMA}.orders_silver"))
check("silver.support_docs_parsed", lambda: count(config.PARSED_TABLE))
if config.ENABLE_ENRICHMENT:
    check("silver.support_docs_enriched", lambda: count(config.ENRICHED_TABLE))
check("silver.support_chunks (CDF)", lambda: count(config.CHUNKS_TABLE))
check("products.daily_sales", lambda: count(config.MART_VIEW))
check("products.customer_features", lambda: count(config.FEATURES_TABLE))
check(
    "products.sales_metrics MEASURE()",
    lambda: str(
        spark.sql(
            f"SELECT MEASURE(total_revenue) AS r FROM {config.METRIC_VIEW}"
        ).first()["r"]
    ),
)
check(
    "products.lookup_customer_features() -> JSON",
    lambda: str(
        spark.sql(
            f"SELECT {config.LOOKUP_FUNCTION}("
            f"(SELECT MIN(customer_key) FROM {config.FEATURES_TABLE})) AS j"
        ).first()["j"]
    ),
)
check(
    "vector index query",
    lambda: str(
        len(
            get_search_client()
            .get_index(endpoint_name=config.VS_ENDPOINT, index_name=config.VS_INDEX)
            .similarity_search(
                query_text="warranty", columns=[config.INDEX_PRIMARY_KEY], num_results=1
            )
            .get("result", {})
            .get("data_array", [])
        )
    )
    + " hit(s)",
)

print("\n=== AI CONSUMPTION PLANE — VERIFY ===")
for status, line in checks:
    print(f"[{status}] {line}")
failed = [line for status, line in checks if status == "FAIL"]
print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
if failed:
    raise SystemExit(1)
