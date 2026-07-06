# Databricks notebook source
# MAGIC %pip install databricks-feature-engineering --quiet
# MAGIC %restart_python

# COMMAND ----------
"""Product 2 · Customer feature set (ML) — offline table, idempotent.

Any Unity Catalog Delta table with a primary key is a feature table:
https://docs.databricks.com/aws/en/machine-learning/feature-store/uc/feature-tables-uc

Production upgrades (documented, optional):
  * Designate a TIMESERIES column IN THE PRIMARY KEY (the TIMESERIES designation,
    not merely a timestamp in the key — without it the as-of join matches exact
    timestamps only) for point-in-time-correct training joins that prevent label
    leakage: https://docs.databricks.com/aws/en/machine-learning/feature-store/concepts
  * Publish into a Lakebase-backed Online Feature Store for millisecond serving —
    see 02b_online_feature_store.py.
"""
from databricks.feature_engineering import FeatureEngineeringClient
from pyspark.sql import functions as F

import config

fe = FeatureEngineeringClient()

customer_features = (
    spark.table(f"{config.SILVER_SCHEMA}.orders_silver")
    .groupBy(F.col("o_custkey").alias("customer_key"))
    .agg(
        F.count("o_orderkey").alias("total_orders"),
        F.avg("o_totalprice").cast("decimal(18,2)").alias("avg_order_value"),
        F.countDistinct(F.date_format("o_orderdate", "yyyy-MM")).alias("months_active"),
        # Same >500 "High" threshold as the original article's segmentation —
        # one governed column instead of a whole extra "Platinum" layer.
        F.avg(F.when(F.col("o_totalprice") > 500, 1.0).otherwise(0.0)).alias("high_value_ratio"),
    )
)

try:
    fe.create_table(
        name=config.FEATURES_TABLE,
        primary_keys=["customer_key"],
        df=customer_features,
        description="PRODUCT | Owner: ml-platform | Purpose: churn + CLV models",
    )
    print(f"created {config.FEATURES_TABLE}")
except Exception as e:  # idempotent re-run: table already exists -> merge fresh values
    if "already exists" in str(e).lower():
        fe.write_table(name=config.FEATURES_TABLE, df=customer_features, mode="merge")
        print(f"{config.FEATURES_TABLE} exists — merged fresh feature values")
    else:
        raise

display(spark.table(config.FEATURES_TABLE).limit(5))
