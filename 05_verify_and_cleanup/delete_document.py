# Databricks notebook source
# MAGIC %pip install databricks-ai-search --quiet
# MAGIC %restart_python

# COMMAND ----------
"""Right-to-be-forgotten · delete one document end to end, and prove it's gone.

Because chunks never leave Unity Catalog governance and the index syncs from the
chunks table via Change Data Feed, deletion is: (1) delete the doc's chunks in
Silver, (2) trigger an index sync, (3) verify the chunk is no longer retrievable.
Test this path ONCE before the first legal request — a deletion story you have
never exercised is not a deletion story.

Usage: set DOC to the filename (or any source_uri substring) to purge.
NOTE: if the source PDF is still in the Bronze volume, the streaming pipeline
will re-ingest and re-chunk it on the next run — delete the volume file too for a
permanent removal. This script proves the index-sync half of the contract.
"""
import config
from lib.ai_search import get_search_client
from lib.retry import wait_until

config.validate()

DOC = "complaint_letter.pdf"  # the document to purge (matches source_uri / path)

# --- 1) Count, then delete the chunks in Silver --------------------------------
before = spark.sql(
    f"SELECT count(*) AS n FROM {config.CHUNKS_TABLE} WHERE source_uri LIKE '%{DOC}%'"
).first()["n"]
print(f"chunks matching {DOC}: {before}")

spark.sql(f"DELETE FROM {config.CHUNKS_TABLE} WHERE source_uri LIKE '%{DOC}%'")
print("deleted matching chunks from Silver")

# --- 2) Trigger an index sync so the deletion propagates ------------------------
index = get_search_client().get_index(
    endpoint_name=config.VS_ENDPOINT, index_name=config.VS_INDEX
)
try:
    index.sync()
    print("triggered index sync")
except Exception as e:
    print(f"sync() not available on this client ({e}); a TRIGGERED index syncs on schedule")

# --- 3) Verify the document is no longer retrievable ---------------------------
def _gone():
    hits = index.similarity_search(
        query_text=DOC,
        columns=[config.INDEX_PRIMARY_KEY, "source_uri"],
        num_results=10,
        query_type="HYBRID",
    )
    rows = hits.get("result", {}).get("data_array", [])
    return all(DOC not in str(r[1]) for r in rows)


wait_until(_gone, timeout_s=15 * 60, interval_s=20,
           on_wait=lambda d: print(f"waiting for index to drop {DOC} … (next in {d:.0f}s)"))
print(f"[ok] {DOC} is no longer retrievable from the index")
