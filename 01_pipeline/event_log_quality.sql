-- ============================================================================
-- Step 3 (observability) · "What passed validation last night?" is one query.
--
-- Pipeline expectations emit pass/fail counts to the event log on every run.
-- The event_log table function is owner-only; publish a view for the team.
-- Run this AFTER the Lakeflow pipeline has completed at least one update.
-- Docs: https://docs.databricks.com/aws/en/ldp/monitor-event-logs
--       https://docs.databricks.com/aws/en/sql/language-manual/functions/event_log
-- ============================================================================
SELECT
  exp.name,
  exp.dataset,
  exp.passed_records,
  exp.failed_records
FROM (
  SELECT explode(from_json(
           details:flow_progress:data_quality:expectations,
           'array<struct<name string, dataset string,
                         passed_records long, failed_records long>>')) AS exp
  FROM event_log(TABLE(eshop.silver.orders_silver))
  WHERE event_type = 'flow_progress'
)
ORDER BY failed_records DESC;

-- Optional: publish a governed view so analysts can query quality without
-- owning the pipeline (grant SELECT on it to your analyst group).
CREATE OR REPLACE VIEW eshop.silver.orders_quality_log AS
SELECT
  timestamp,
  exp.name,
  exp.dataset,
  exp.passed_records,
  exp.failed_records
FROM (
  SELECT timestamp, explode(from_json(
           details:flow_progress:data_quality:expectations,
           'array<struct<name string, dataset string,
                         passed_records long, failed_records long>>')) AS exp
  FROM event_log(TABLE(eshop.silver.orders_silver))
  WHERE event_type = 'flow_progress'
);
