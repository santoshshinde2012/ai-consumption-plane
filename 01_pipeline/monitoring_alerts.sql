-- ============================================================================
-- Operational monitoring · wire each query as a Databricks SQL Alert.
-- Create with: SQL editor -> save query -> "Create alert" -> set the condition
-- and a notification destination (email/Slack/PagerDuty).
-- Docs: https://docs.databricks.com/aws/en/sql/user/alerts/
-- ============================================================================

-- 1) DATA QUALITY — expectation failures in the last 24h.
--    Alert when failed_24h > 0 (or above your tolerated ratio).
SELECT
  exp.name,
  exp.dataset,
  SUM(exp.failed_records) AS failed_24h,
  SUM(exp.passed_records) AS passed_24h
FROM (
  SELECT timestamp, explode(from_json(
           details:flow_progress:data_quality:expectations,
           'array<struct<name string, dataset string,
                         passed_records long, failed_records long>>')) AS exp
  FROM event_log(TABLE(eshop.silver.orders_silver))
  WHERE event_type = 'flow_progress'
    AND timestamp > current_timestamp() - INTERVAL 24 HOURS
)
GROUP BY exp.name, exp.dataset
HAVING failed_24h > 0;

-- 2) PARSE FAILURES — documents ai_parse_document could not read.
--    These must never reach retrieval; alert when parse_errors > 0.
SELECT count(*) AS parse_errors
FROM eshop.silver.support_docs_parsed
WHERE try_cast(parsed:error_status AS STRING) IS NOT NULL;

-- 3) INDEX FRESHNESS — how long since the chunks table (index source) changed.
--    Alert when hours_since_change exceeds your freshness SLA.
SELECT
  max(timestamp)                                        AS last_commit,
  timestampdiff(HOUR, max(timestamp), current_timestamp()) AS hours_since_change
FROM (DESCRIBE HISTORY eshop.silver.support_chunks);

-- 4) EMPTY-RETRIEVAL CANARY — the products schema is populated at all.
--    Alert when either count is 0 (upstream pipeline stalled).
SELECT
  (SELECT count(*) FROM eshop.silver.support_chunks) AS chunk_count,
  (SELECT count(*) FROM eshop.products.customer_features) AS feature_count;
