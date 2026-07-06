-- ============================================================================
-- Agent tool · deterministic lookup as a Unity Catalog function.
-- Exposed automatically at /api/2.0/mcp/functions/eshop/products
--
-- The documented UC-function tool pattern returns a SCALAR; JSON packs a whole
-- feature row into one string the agent can parse.
-- Pattern: https://docs.databricks.com/aws/en/agents/agent-framework/structured-retrieval-tools
-- ============================================================================
CREATE OR REPLACE FUNCTION eshop.products.lookup_customer_features(customer BIGINT)
RETURNS STRING
COMMENT 'AGENT TOOL: returns governed churn features for one customer, as JSON.'
RETURN SELECT to_json(struct(total_orders, avg_order_value, months_active, high_value_ratio))
       FROM eshop.products.customer_features
       WHERE customer_key = customer;

-- Smoke test with any customer_key present in the feature table (scalar call):
SELECT eshop.products.lookup_customer_features(
  (SELECT MIN(customer_key) FROM eshop.products.customer_features)
) AS features_json;
