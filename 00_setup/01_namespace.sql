-- ============================================================================
-- Step 1 · Namespace — one governed home for everything this build creates.
-- Idempotent: safe to re-run.
-- ============================================================================
CREATE CATALOG IF NOT EXISTS eshop;

CREATE SCHEMA IF NOT EXISTS eshop.bronze
  COMMENT 'Landing zone: append-only, replayable, no business logic.';
CREATE SCHEMA IF NOT EXISTS eshop.silver
  COMMENT 'Validated, conformed, chunked. Every table carries a contract.';
CREATE SCHEMA IF NOT EXISTS eshop.products
  COMMENT 'The product boundary (not "gold"): mart, features, index, metrics.';

-- Governed landing volume for unstructured documents.
CREATE VOLUME IF NOT EXISTS eshop.bronze.support_docs_raw
  COMMENT 'Raw support PDFs land here; Auto Loader picks them up incrementally.';
