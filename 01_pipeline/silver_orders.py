"""Silver (structured) · quality as named, monitored expectations.

Every rule has a name and an action; every run emits pass/fail metrics
to the pipeline event log.
"""
from pyspark import pipelines as dp
from pyspark.sql import functions as F


@dp.materialized_view(
    comment="CONTRACT: validated orders; no invalid prices; normalized status; metrics on every run."
)
@dp.expect_or_drop("valid_price", "o_totalprice > 0")
@dp.expect_or_drop("valid_order_key", "o_orderkey IS NOT NULL")
@dp.expect("known_status", "o_orderstatus IN ('F','O','P')")  # warn-only: observe first
def orders_silver():
    return (
        spark.read.table("orders_bronze")
        .withColumn(
            "order_status",
            F.when(F.col("o_orderstatus") == "F", "Fulfilled")
            .when(F.col("o_orderstatus") == "O", "Open")
            .otherwise("Unknown"),
        )
    )
