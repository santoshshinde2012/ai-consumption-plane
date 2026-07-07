"""Bronze · one landing discipline for both data shapes.

Lakeflow Spark Declarative Pipelines source file. The `pyspark.pipelines`
module replaces the legacy `import dlt`. In it:
  * @dp.materialized_view declares a batch-computed table (recomputed each run)
  * @dp.table            declares a streaming table (append-only, incremental)
The old @dlt.table covered both and still works.

Contracts: append-only, complete, replayable; no business logic.
"""
from pyspark import pipelines as dp
from pyspark.sql import functions as F

DOCS_VOLUME_PATH = "/Volumes/eshop/bronze/support_docs_raw"  # keep in sync with config.py


@dp.materialized_view(
    comment="CONTRACT: raw orders; ingestion metadata; no business logic."
)
def orders_bronze():
    # Batch source (samples.tpch.orders) → materialized view.
    return (
        spark.read.table("samples.tpch.orders")
        .withColumn("ingest_time", F.current_timestamp())
        .withColumn("source_system", F.lit("tpch_sample"))
    )


@dp.table(
    comment="CONTRACT: append-only raw documents as binary; path and timestamps preserved."
)
def support_docs_bronze():
    # Streaming source (Auto Loader on the volume) → streaming table.
    # binaryFile has a fixed schema (path, modificationTime, length, content);
    # schemaLocation gives Auto Loader a stable checkpoint. The "_schema" dir is
    # underscore-prefixed, so Auto Loader skips it during discovery.
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "binaryFile")  # bytes in, for ai_parse_document
        .option("cloudFiles.schemaLocation", f"{DOCS_VOLUME_PATH}/_schema")
        .load(DOCS_VOLUME_PATH)
        .select(
            "path",
            "modificationTime",
            "length",
            "content",
            F.current_timestamp().alias("ingest_time"),
        )
    )
