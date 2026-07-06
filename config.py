"""Single source of truth for every name used in this repo.

Edit here once; all notebooks import from this file.
In a Databricks Repo/Workspace folder, `import config` works on DBR 13+.

NOTE: Lakeflow pipeline source files (01_pipeline/*) can't import this module
(they run inside the pipeline's own context), so the handful of constants they
need are mirrored there with a "keep in sync" comment.
"""

# --- Unity Catalog namespace -------------------------------------------------
CATALOG = "eshop"
BRONZE_SCHEMA = f"{CATALOG}.bronze"
SILVER_SCHEMA = f"{CATALOG}.silver"
PRODUCTS_SCHEMA = f"{CATALOG}.products"

DOCS_VOLUME = f"{BRONZE_SCHEMA}.support_docs_raw"
DOCS_VOLUME_PATH = f"/Volumes/{CATALOG}/bronze/support_docs_raw"

# --- Tables & products --------------------------------------------------------
ORDERS_SOURCE = "samples.tpch.orders"                       # TPC-H sample data
PARSED_TABLE = f"{SILVER_SCHEMA}.support_docs_parsed"
ENRICHED_TABLE = f"{SILVER_SCHEMA}.support_docs_enriched"   # Step-4 enrich output
CHUNKS_TABLE = f"{SILVER_SCHEMA}.support_chunks"
FEATURES_TABLE = f"{PRODUCTS_SCHEMA}.customer_features"
ONLINE_FEATURES_TABLE = f"{PRODUCTS_SCHEMA}.customer_features_online"
MART_VIEW = f"{PRODUCTS_SCHEMA}.daily_sales"
METRIC_VIEW = f"{PRODUCTS_SCHEMA}.sales_metrics"
LOOKUP_FUNCTION = f"{PRODUCTS_SCHEMA}.lookup_customer_features"

# --- AI Search (formerly Vector Search) --------------------------------------
# The current SDK is `databricks-ai-search` / `AISearchClient`; the legacy
# `databricks-vectorsearch` / `VectorSearchClient` still runs. lib/ai_search.py
# picks whichever is installed. Docs teach AISearchClient.
VS_ENDPOINT = "eshop-search"
VS_ENDPOINT_TYPE = "STANDARD"                  # see article Step 1 for the SKU decision
VS_INDEX = f"{PRODUCTS_SCHEMA}.support_docs_index"
# Current recommended managed-embedding model (older databricks-gte-large-en
# still works); required for the managed MCP AI Search server.
EMBEDDING_MODEL = "databricks-qwen3-embedding-0-6b"
INDEX_PRIMARY_KEY = "chunk_id"
EMBEDDING_SOURCE_COLUMN = "chunk_to_embed"     # context-enriched text (from ai_prep_search)
# Columns requested at query time. source_uri + chunk_position are the citation anchors.
INDEX_QUERY_COLUMNS = ["chunk_id", "chunk_content", "source_uri", "chunk_position"]

# --- Chunking ----------------------------------------------------------------
# ai_prep_search is Beta and requires DBR 18.2+; default False = deterministic
# manual chunker (always runs, any supported runtime). Both paths emit the same
# columns so the index config below is identical either way.
# NOTE: mirrored in 01_pipeline/silver_docs.py — keep in sync.
USE_AI_PREP_SEARCH = False
CHUNK_SIZE_CHARS = 1000
CHUNK_OVERLAP_CHARS = 150
MIN_CHUNK_CHARS = 50

# --- Enrichment (Step-4 sub-step: ai_classify + ai_extract) ------------------
# One structured row per document. Costs AI_FUNCTIONS tokens (pennies for the 4
# sample docs); retrieval does not depend on it. Mirrored in silver_docs.py.
ENABLE_ENRICHMENT = True

# --- Online feature store (optional Step-6 upgrade) --------------------------
# Lakebase-backed online store for millisecond serving. BILLS WHILE IT EXISTS.
# Requires databricks-feature-engineering >= 0.13.0 and a Lakebase-enabled workspace.
ENABLE_ONLINE_STORE = False
ONLINE_STORE_NAME = "eshop-online"
ONLINE_STORE_CAPACITY = "CU_1"                 # valid: CU_1 / CU_2 / CU_4 / CU_8
ONLINE_PUBLISH_MODE = "TRIGGERED"              # TRIGGERED | CONTINUOUS | SNAPSHOT

# --- Agents ------------------------------------------------------------------
GENIE_SPACE_ID = ""   # paste after creating the Genie Space (03_agents/02_genie_space.md)
AGENT_GROUP = "support-agents"                 # UC group the grants in 04_grants.sql target

# --- Evaluation ---------------------------------------------------------------
EVAL_TOP_K = 5
LLM_ENDPOINT = "databricks-claude-sonnet-4-6"  # any Foundation Model API chat endpoint
