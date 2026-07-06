# The AI Consumption Plane on Databricks

End-to-end, runnable source code for the article **"The AI Consumption Plane on Databricks: A Hands-On Build"** — one Bronze → Silver refinement flow that terminates in four governed data products (analytical mart, feature set, vector index, metric view), exposed to AI agents through Databricks managed MCP servers, with measured retrieval quality.

> Article series: *Rethinking Bronze, Silver, and Gold for the AI era* — Part 2 (hands-on build).

## What you'll build

```
 RAW           BRONZE                SILVER                          PRODUCTS (the boundary)
 orders ──► orders_bronze ──► orders_silver (expectations) ──┬─► daily_sales      → BI
                                                             ├─► customer_features → ML → online store
                                                             └─► sales_metrics     → SQL · Genie
 PDFs  ──► support_docs_bronze ─► support_docs_parsed
              (binary, volume)     ├─► support_docs_enriched  (ai_classify + ai_extract → analytics)
                                   └─► support_chunks ──────────► support_docs_index → RAG
 ──────────────── every object governed by Unity Catalog ────────────────────────────────
                                          │
                Managed MCP:  /ai-search · /genie · /functions   (on-behalf-of-user auth)
                                          ▼
                        MLflow 3 retrieval evaluation (Step 10)
```

## Prerequisites

- Databricks workspace with **Unity Catalog** enabled, permissions to create catalogs/schemas/volumes, pipelines, AI Search endpoints, and SQL functions.
- **DBR 17.3+** or **serverless environment version 3+** (required by `ai_parse_document`; region-dependent — check [AI function availability](https://docs.databricks.com/aws/en/sql/language-manual/functions/ai_parse_document)). **DBR 18.2+** only if you flip `config.USE_AI_PREP_SEARCH = True` (the Beta chunker) — the deterministic default runs on any supported runtime.
- Access to the `samples` catalog (TPC-H sample data) — enabled by default in most workspaces.
- For the optional online store: `databricks-feature-engineering >= 0.13.0` and a Lakebase-enabled workspace.
- Python libs are installed per-notebook via `%pip` magics; `requirements.txt` mirrors them for local IDEs. The AI Search SDK is auto-selected by `lib/ai_search.py` (`databricks-ai-search`/`AISearchClient`, falling back to legacy `databricks-vectorsearch`).

## Quickstart — run in order

| Step | File | What it does |
|---|---|---|
| 1 | `00_setup/01_namespace.sql` | Catalog `eshop`, schemas `bronze/silver/products`, docs volume |
| 2 | `00_setup/02_generate_sample_docs.py` | Writes 4 synthetic PDFs (policies, FAQ, warranty, complaint with planted PII) into the volume |
| 3 | `01_pipeline/{bronze,silver_orders,silver_docs}.py` | Create a **Lakeflow Spark Declarative Pipeline** whose source is this folder (UI: *Pipelines → Create → add the three `.py` files*; serverless recommended; default catalog `eshop`, target schema `silver`). Run it. Optional: `databricks bundle deploy` using `databricks.yml`. |
| 3b | `01_pipeline/event_log_quality.sql` | *After a pipeline run* — query expectation pass/fail counts from the event log; publishes a governed quality view |
| 4 | `02_products/01_daily_sales_mart.sql` | Materialized-view mart |
| 5 | `02_products/02_customer_features.py` | Unity Catalog feature table (idempotent create + merge) |
| 5b | `02_products/02b_online_feature_store.py` | *Optional* — publish features to a Lakebase online store (offline **and** online) |
| 6 | `02_products/03_vector_index.py` | AI Search endpoint + Delta Sync index (waits until ready, cited smoke query) |
| 7 | `02_products/04_sales_metric_view.sql` | Metric view with agent metadata (synonyms) + `MEASURE()` check |
| 8 | `03_agents/01_lookup_function.sql` | UC function agent tool (returns a JSON feature row) |
| 8b | `03_agents/04_grants.sql` | Grant the agent group its tools — the entire agent security model |
| 9 | `03_agents/02_genie_space.md` | UI steps to create the Genie Space; paste `space_id` into `config.py` |
| 10 | `03_agents/03_mcp_smoke_test.py` | Verifies assets and prints your three managed-MCP URLs |
| 10b | `03_agents/05_mcp_client_example.py` | The whole consumer side — connect an agent to a managed MCP server (~10 lines) |
| 11 | `04_evaluation/retrieval_eval.py` | Hit-rate HYBRID vs ANN + MLflow `RetrievalGroundedness` over real LLM answers |
| 12 | `05_verify_and_cleanup/verify.py` | One-shot health check of every stage |
| 13 | `05_verify_and_cleanup/teardown.py` | Deletes index/endpoint/online store and drops schemas (**stops all costs**) |

The Silver docs pipeline (`01_pipeline/silver_docs.py`) implements the full article Step 4 — **parse → enrich → chunk**. It parses with `ai_parse_document(content, map('version','2.0'))`, and (with `config.ENABLE_ENRICHMENT = True`, the default) emits `silver.support_docs_enriched` via `ai_classify` + `ai_extract` — one structured row per document, "one document in, two data shapes out."

All names live in **`config.py`** — edit once, everything follows.

## Develop & test locally

No workspace needed for the fast feedback loop:

```bash
pip install -r requirements-dev.txt
ruff check .          # lint
pytest -q             # unit tests for the chunking/redaction logic (lib/chunking.py)
python -m compileall 01_pipeline 02_products   # syntax-check pipeline/notebook files
databricks bundle validate -t dev              # optional: validate the Lakeflow bundle
```

The same checks run in CI on every push (`.github/workflows/ci.yml`).

## Design decisions (read before running)

- **Both chunk paths, one column contract.** `ai_prep_search` is Beta (and needs DBR 18.2+), so `config.USE_AI_PREP_SEARCH = False` by default: the pipeline uses a deterministic manual chunker (page-aware element walker + overlapping windows). Either path emits the **same columns** — `chunk_id`, `chunk_content`, `chunk_to_embed`, `chunk_position`, `source_uri`, `path` — so the index config never changes. Flip the flag for the platform-native path (`variant_explode` over `document.contents[]`, per the [IDP docs](https://docs.databricks.com/aws/en/agents/agent-bricks/intelligent-document-processing)).
- **The index embeds `chunk_to_embed`, not raw text.** That's the context-enriched column (title + chunk); `chunk_content` is kept separately for display/citations.
- **Citations are first-class.** `source_uri` + `chunk_position` travel with every chunk, so RAG answers can cite *"the return policy, page 1"* — the smoke query and the MLflow retriever both surface them.
- **Pure logic is unit-tested.** The chunking/redaction algorithm lives in `lib/chunking.py` (no Spark imports) and is covered by `tests/test_chunking.py`; `silver_docs.py` inlines the same logic to stay runnable inside Lakeflow. CI (`.github/workflows/ci.yml`) runs ruff, `compileall`, and the tests on every push.
- **PII is redacted in Silver, before embedding.** Regex email/phone redaction in the chunker; swap in `ai_query` or a PII library for production.
- **Parse failures never reach retrieval.** Both chunk paths filter rows where `parsed:error_status` is set, per the "Operate It" checklist.
- **Idempotent by construction.** `IF NOT EXISTS` / `CREATE OR REPLACE` and content-addressable `chunk_id`s everywhere; re-running any step is safe.
- **Managed embeddings** (`databricks-qwen3-embedding-0-6b`, the current recommended model; `databricks-gte-large-en` still works) — required by the managed MCP AI Search server.
- **SDK-agnostic.** `lib/ai_search.py` prefers the current `AISearchClient` and falls back to the legacy `VectorSearchClient`, so the build runs on either.

## Cost notes

The vector search **endpoint** and any **online feature store** bill while they exist — run `05_verify_and_cleanup/teardown.py` when done. `ai_parse_document` calls are billed under the `AI_FUNCTIONS` product; the 4 sample PDFs cost pennies.

## Repo ↔ article map

`00–01` = article Act I (Steps 1–4, incl. parse **and** enrich, plus the event-log quality query) · `02` = Act II (Steps 5–8, feature set offline **and** online) · `03` = Act III Step 9 (three agent tools + grants + MCP client) · `04` = Step 10 (measured quality) · `05` = "Operate It" checklist · `lib` + `tests` + `.github` = the CI/regression gate the checklist calls for.

## License

MIT — see `LICENSE`.
