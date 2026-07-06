# Create the Genie Space (UI — ~3 minutes)

Genie Spaces are created in the UI (no public DDL). This gives agents
natural-language access to the structured products, with the metric view's
synonyms doing the semantic heavy lifting.

1. In the workspace sidebar, open **Genie** → **New space** (name: `E-Shop Sales`).
2. Add data: `eshop.products.sales_metrics` and `eshop.products.daily_sales`
   (a space supports up to 25 Unity Catalog tables/views).
3. Optional but recommended: add sample questions —
   *"What was total revenue last month?"*, *"Average order value by status?"*
4. Save, then copy the **space ID** from the space URL:
   `…/genie/rooms/<SPACE_ID>` (or the space settings panel).
5. Paste it into `config.py` → `GENIE_SPACE_ID = "<SPACE_ID>"`.
6. Sanity-check in the Genie chat: ask *"total revenue by order status"* —
   the answer should match the `MEASURE()` query from
   `02_products/04_sales_metric_view.sql`.

The space is then callable by agents at `/api/2.0/mcp/genie/<SPACE_ID>`
(printed for you by `03_mcp_smoke_test.py`).
