-- ============================================================================
-- Agent authorization · the ENTIRE security model is a handful of grants.
--
-- Managed MCP servers enforce on-behalf-of-user auth: when an agent calls a
-- tool for a user, the user's own Unity Catalog permissions apply. So the agent
-- group's grants are exactly what the agent can do — no prompt-engineered
-- guardrails, no application-code checks.
--
-- Note: there is no special "index" securable. An AI Search index is a
-- table-like UC object, so it takes an ordinary SELECT.
-- Replace `support-agents` with your group (config.AGENT_GROUP).
-- Docs: https://docs.databricks.com/aws/en/ai-search/query-ai-search
-- ============================================================================
GRANT USE CATALOG ON CATALOG eshop                                    TO `support-agents`;
GRANT USE SCHEMA  ON SCHEMA  eshop.products                           TO `support-agents`;

-- Unstructured retrieval (the index is a table-like object → SELECT):
GRANT SELECT      ON TABLE   eshop.products.support_docs_index        TO `support-agents`;

-- Deterministic lookups:
GRANT EXECUTE     ON FUNCTION eshop.products.lookup_customer_features  TO `support-agents`;

-- Structured analytics (metric view + mart, for the Genie Space):
GRANT SELECT      ON VIEW    eshop.products.sales_metrics             TO `support-agents`;
GRANT SELECT      ON TABLE   eshop.products.daily_sales               TO `support-agents`;

-- A member of `support-agents` reaches NOTHING in eshop.silver — no grant says so.
