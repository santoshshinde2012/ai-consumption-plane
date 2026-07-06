-- ============================================================================
-- Product 4 · Metric view — measures defined once, resolved identically by
-- dashboards, notebooks, and Genie/agents (synonyms = agent metadata).
-- DDL per https://docs.databricks.com/aws/en/business-semantics/metric-views/
-- Requires DBR 17.3+ compute.
-- ============================================================================
CREATE OR REPLACE VIEW eshop.products.sales_metrics
WITH METRICS LANGUAGE YAML AS
$$
version: 1.1
comment: 'PRODUCT | Owner: analytics | Certified metrics for BI, Genie, and agents'
source: eshop.silver.orders_silver
fields:
  - name: order_date
    expr: o_orderdate
    display_name: 'Order Date'
  - name: order_status
    expr: order_status
    display_name: 'Order Status'
measures:
  - name: total_revenue
    expr: SUM(o_totalprice)
    display_name: 'Total Revenue'
    synonyms: ['sales', 'income', 'turnover']
  - name: avg_order_value
    expr: AVG(o_totalprice)
    display_name: 'Average Order Value'
    synonyms: ['AOV', 'basket size']
$$;

-- Every consumer computes revenue identically:
SELECT order_status, MEASURE(total_revenue) AS total_revenue
FROM eshop.products.sales_metrics
GROUP BY order_status;
