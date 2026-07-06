-- ============================================================================
-- Product 1 · Analytical mart (BI). Contract lives in the COMMENT.
-- ============================================================================
CREATE OR REPLACE MATERIALIZED VIEW eshop.products.daily_sales
COMMENT 'PRODUCT | Owner: analytics | SLA: refreshed daily 06:00 UTC | Consumers: BI dashboards'
AS SELECT
  year(o_orderdate)  AS order_year,
  month(o_orderdate) AS order_month,
  day(o_orderdate)   AS order_day,
  CAST(sum(o_totalprice) AS DECIMAL(18,2)) AS total_sales,
  count(o_orderkey)  AS order_count
FROM eshop.silver.orders_silver
GROUP BY 1, 2, 3;

-- Quick check
SELECT * FROM eshop.products.daily_sales ORDER BY order_year, order_month, order_day LIMIT 5;
