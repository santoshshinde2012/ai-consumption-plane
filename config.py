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
VS_ENDPOINT_TYPE = "STANDARD"                  # STANDARD (interactive) vs STORAGE_OPTIMIZED (massive corpus)
VS_INDEX = f"{PRODUCTS_SCHEMA}.support_docs_index"
# Current recommended managed-embedding model (older databricks-gte-large-en
# still works); required for the managed MCP AI Search server.
EMBEDDING_MODEL = "databricks-qwen3-embedding-0-6b"
INDEX_PRIMARY_KEY = "chunk_id"
EMBEDDING_SOURCE_COLUMN = "chunk_to_embed"     # context-enriched text (from ai_prep_search)
# The chunk table's column contract — both chunking paths must emit exactly these.
CHUNK_COLUMNS = ["chunk_id", "chunk_content", "chunk_to_embed", "chunk_position", "source_uri", "path"]
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
# Regression gates for the nightly retrieval evaluation (CI fails below these).
EVAL_ENFORCE_THRESHOLDS = True
EVAL_MIN_HIT_RATE = 0.80                        # hit-rate@k for HYBRID
EVAL_MIN_GROUNDEDNESS = 0.80                     # mean RetrievalGroundedness

# --- Secrets -----------------------------------------------------------------
# Databricks secret scope for any runtime credentials (external API keys, etc.).
# See lib/secrets.py; create with: databricks secrets create-scope eshop
SECRET_SCOPE = "eshop"

# --- Provisioning timeouts ----------------------------------------------------
INDEX_READY_TIMEOUT_S = 30 * 60


# --- Validation ---------------------------------------------------------------
_ENDPOINT_TYPES = {"STANDARD", "STORAGE_OPTIMIZED"}
_CAPACITIES = {"CU_1", "CU_2", "CU_4", "CU_8"}
_PUBLISH_MODES = {"TRIGGERED", "CONTINUOUS", "SNAPSHOT"}


def validate() -> None:
    """Fail fast on a misconfigured plane. Call at the top of each entrypoint.

    Catches the mistakes that otherwise surface deep inside a pipeline or a
    30-minute index build: empty names, invalid enums, nonsensical chunking.
    """
    problems: list[str] = []

    for name in ("CATALOG", "VS_ENDPOINT", "VS_INDEX", "EMBEDDING_MODEL",
                 "CHUNKS_TABLE", "FEATURES_TABLE", "LLM_ENDPOINT"):
        if not globals().get(name):
            problems.append(f"{name} must be non-empty")

    if VS_ENDPOINT_TYPE not in _ENDPOINT_TYPES:
        problems.append(f"VS_ENDPOINT_TYPE must be one of {_ENDPOINT_TYPES}")
    if ONLINE_STORE_CAPACITY not in _CAPACITIES:
        problems.append(f"ONLINE_STORE_CAPACITY must be one of {_CAPACITIES}")
    if ONLINE_PUBLISH_MODE not in _PUBLISH_MODES:
        problems.append(f"ONLINE_PUBLISH_MODE must be one of {_PUBLISH_MODES}")
    if not 0 < CHUNK_OVERLAP_CHARS < CHUNK_SIZE_CHARS:
        problems.append("require 0 < CHUNK_OVERLAP_CHARS < CHUNK_SIZE_CHARS")
    if MIN_CHUNK_CHARS <= 0:
        problems.append("MIN_CHUNK_CHARS must be positive")
    if EMBEDDING_SOURCE_COLUMN not in CHUNK_COLUMNS:
        problems.append("EMBEDDING_SOURCE_COLUMN must be one of CHUNK_COLUMNS")
    if INDEX_PRIMARY_KEY not in CHUNK_COLUMNS:
        problems.append("INDEX_PRIMARY_KEY must be one of CHUNK_COLUMNS")
    if not set(INDEX_QUERY_COLUMNS) <= set(CHUNK_COLUMNS):
        problems.append("INDEX_QUERY_COLUMNS must be a subset of CHUNK_COLUMNS")
    for name in ("EVAL_MIN_HIT_RATE", "EVAL_MIN_GROUNDEDNESS"):
        if not 0.0 <= globals()[name] <= 1.0:
            problems.append(f"{name} must be in [0, 1]")

    if problems:
        raise ValueError("Invalid config:\n  - " + "\n  - ".join(problems))


def require_genie_space() -> str:
    """Return GENIE_SPACE_ID or raise a clear message (it's set out-of-band)."""
    if not GENIE_SPACE_ID:
        raise ValueError(
            "GENIE_SPACE_ID is empty — create the Genie Space "
            "(03_agents/02_genie_space.md or 06_create_genie_space.py) and set it in config.py"
        )
    return GENIE_SPACE_ID
