# Data Dictionary — Project Caravela

> **Scope**: Full pipeline column reference — raw source layer, staging layer, mart layer, and Parquet
> export files. Covers business definitions, BigQuery types, derivation logic, data defects, and
> interpretation guidance across all layers.
>
> **Data Analyst sections**: Parquet file schemas (`data/`), derived column definitions, metric
> definitions, `notebooks/utils.py` API reference.
>
> **Data Engineer sections**: Raw source tables (`olist_raw` — 9 views), staging transformations
> (`stg_*` — 9 models), mart layer column definitions (`dim_*` / `fct_*` — 7 models), star schema
> relationship diagram.
>
> For machine-readable column constraints and dbt test declarations, see:
> - `dbt/models/staging/schema.yml`
> - `dbt/models/marts/schema.yml`

---

## Source Data Overview

| Source | Records | Period | Notes |
|---|---|---|---|
| Olist Brazilian E-Commerce | ~100k orders | Sep 2016 – Oct 2018 | Public Kaggle dataset |
| **Meaningful analysis window** | ~99.5k orders | **Jan 2017 – Aug 2018** | Excludes data-cut artefacts (see below) |

**Data-cut artefacts excluded from trend analysis:**
- 2016-11: 0 orders, 2016-12: 1 order (pre-dataset start)
- 2018-09: 16 raw order headers but only 1 with items in `fct_sales`; 2018-10: 4 orders (dataset truncation)

**Exchange rate**: R$3.65/USD (2018 annual average) used for all USD conversions.

---

## Parquet File Schemas

### 1. `data/sales_orders.parquet`

**Granularity**: Order-item (one row per item in an order) — ~112k rows
**Produced by**: `notebooks/01_sales_analysis.ipynb`
**Dashboard pages**: Executive Overview, Product Performance

| Column | Type | Description | Derivation / Notes |
|---|---|---|---|
| `order_id` | string | Unique order identifier | From `fct_sales`. Use `COUNT(DISTINCT order_id)` for order-level metrics — multiple items per order. |
| `order_item_id` | int | Item sequence within order (1, 2, 3…) | From `fct_sales` |
| `product_id` | string | Product identifier | FK to `dim_products` |
| `product_category_name_english` | string | English product category | From `dim_products`. COALESCE(english → portuguese → 'uncategorized'). 610 products labelled 'uncategorized'. **Always use this column**, not `product_category_name`. |
| `date_key` | date | Order purchase date | `DATE(order_purchase_timestamp)` from `fct_sales` |
| `year` | int | Year extracted from `date_key` | For time-series filtering |
| `month` | int | Month extracted from `date_key` | For time-series filtering |
| `order_status` | string | Order fulfilment status | 8 values: delivered (~96.8%), shipped, canceled, unavailable, invoiced, processing, created, approved |
| `total_sale_amount` | float | Item revenue = `price + freight_value` | Item-level. Sum across items for order total. Sum across orders for GMV. |
| `price` | float | Item unit price (R$) | Excludes freight |
| `freight_value` | float | Freight charged for this item (R$) | Allocated per item by Olist |
| `primary_payment_type` | string | Payment method for `payment_sequential=1` | Approximation: ~3% of orders have split payments — only the first payment method is captured. Values: credit_card (~77%), boleto (~19%), voucher, debit_card. |
| `primary_payment_installments` | int | Installment count for primary payment | Boleto is always 1. Credit card ranges 1–24. |
| `customer_state` | string | 2-letter Brazilian state code | e.g., SP, RJ, MG |
| `customer_region` | string | IBGE macro-region | 5 values: Southeast, South, Northeast, Central-West, North. Derived via `REGION_MAP` in `notebooks/utils.py`. |

**Item-granularity trap**: This file has one row per order-item. Naive `COUNT(*)` or `SUM()` over-counts orders. Always use `COUNT(DISTINCT order_id)` for order counts, and be aware that `primary_payment_type` is repeated across items of the same order.

---

### 2. `data/customer_rfm.parquet`

**Granularity**: Customer (one row per unique customer) — ~96k rows
**Produced by**: `notebooks/02_customer_analysis.ipynb`
**Dashboard pages**: Customer Analysis (RFM section)

| Column | Type | Description | Derivation / Notes |
|---|---|---|---|
| `customer_unique_id` | string | Unique customer identifier | From `dim_customers`. Deduplicated from `customer_id` (order-scoped). |
| `customer_state` | string | 2-letter state code | Customer's registered state |
| `customer_region` | string | IBGE macro-region | Derived via `REGION_MAP` |
| `recency_days` | int | Days since last order to reference date | `DATE_DIFF('2018-08-31', MAX(date_key), DAY)`. Lower = more recent. Only orders on or before 2018-08-31 included. |
| `frequency` | int | Total distinct orders | Typical range: 1–17. ~96.9% of customers have exactly 1 order. |
| `monetary_value` | float | Total lifetime spend (R$) | `SUM(total_sale_amount)` across all orders ≤ 2018-08-31 |
| `r_score` | int | Recency quintile (1–5) | 5 = most recent (lowest recency_days). `pd.qcut` with `duplicates='drop'`. |
| `f_tier` | string | Frequency tier | `F1` = 1 order, `F2` = 2 orders, `F3` = 3+ orders. 3-tier (not quintile) because 96.9% have 1 order — quintile scoring collapses. |
| `m_score` | int | Monetary quintile (1–5) | 5 = highest spend. Display attribute only — does not drive segment assignment. |
| `segment` | string | RFM segment label | 6 segments assigned by R×F combination only (see below) |

**RFM Reference Date**: Hardcoded `2018-08-31` — the last month with meaningful order volume. NOT `CURRENT_DATE` or `MAX(timestamp)`.

**RFM Segment Definitions** (RF-only assignment):

| Segment | R_score | F_tier | Interpretation |
|---|---|---|---|
| Champions | 4–5 | F3 | Recent + frequent buyers — highest-value customers |
| Loyal | 3–5 | F2 or F3 | Repeat buyers with moderate-to-high recency |
| Promising | 4–5 | F1 | Recent single-purchase — potential for conversion to repeat |
| At Risk | 1–2 | F2 or F3 | Previously active repeat buyers going dormant |
| High Value Lost | 1–2 | F3 | Former frequent buyers — long inactive |
| Hibernating | 1–3 | F1 | Single-purchase customers with low recency |

**Repeat purchase rate**: ~3.1% of customers have 2+ orders. This is a standalone KPI metric — expected for a marketplace where customers often buy once and leave.

**Dashboard filter notes**: Date Range and Product Category filters are **not applicable** to RFM data (computed over full customer history with fixed reference date). Dashboard should show `st.caption()` explaining this.

---

### 3. `data/satisfaction_summary.parquet`

**Granularity**: Order (one row per reviewed order) — ~97k rows
**Produced by**: `notebooks/02_customer_analysis.ipynb`
**Dashboard pages**: Customer Analysis (satisfaction/NPS section)

| Column | Type | Description | Derivation / Notes |
|---|---|---|---|
| `order_id` | string | Order identifier | From `fct_reviews` joined to `fct_sales` |
| `review_score` | int | Customer review score | 1–5 scale. Ordinal, not continuous. |
| `nps_category` | string | NPS proxy classification | `promoter` (score 4–5), `passive` (score 3), `detractor` (score 1–2) |
| `delivery_delay_days` | float | Actual − estimated delivery (days) | Negative = early delivery. NULL if not yet delivered. |
| `delay_bin` | string | Categorical delay bucket | 5 bins: `early` (< 0), `on-time` (0), `1-3d late`, `4-7d late`, `7+d late` |
| `date_key` | date | Order purchase date | For time-series filtering |
| `year` | int | Year from `date_key` | |
| `month` | int | Month from `date_key` | |
| `customer_state` | string | 2-letter state code | |
| `customer_region` | string | IBGE macro-region | Derived via `REGION_MAP` |
| `primary_product_category` | string | Category of highest-revenue item | Approximate for ~10% multi-item orders. Uses `product_category_name_english`. |

**NPS Proxy Calculation**:
- NPS = (% promoters) − (% detractors)
- Range: −100 to +100
- Score 1–2 = detractor, 3 = passive, 4–5 = promoter
- This is a proxy — true NPS uses a 0–10 "would recommend" scale

**Delay × Review Correlation**: The `early` bin captures the "positive surprise" effect — customers who receive orders before the estimated date tend to give higher scores. The sharpest score drop occurs between the `1-3d late` and `4-7d late` bins (~1.19 points).

---

### 4. `data/geo_delivery.parquet`

**Granularity**: State × month — ~533 rows
**Produced by**: `notebooks/03_geo_seller_analysis.ipynb`
**Dashboard pages**: Geographic Analysis (delivery performance)

| Column | Type | Description | Derivation / Notes |
|---|---|---|---|
| `customer_state` | string | 2-letter state code | Delivery destination state |
| `region` | string | IBGE macro-region | Derived via `REGION_MAP` |
| `year` | int | Year | Required for Date Range filter |
| `month` | int | Month | Required for Date Range filter |
| `total_orders` | int | Delivered orders in state×month | `COUNT(DISTINCT order_id)` where `order_status = 'delivered'` |
| `on_time_orders` | int | Orders delivered on or before estimate | `delivered_date <= estimated_date` |
| `on_time_rate` | float | On-time delivery percentage (0–1) | `on_time_orders / total_orders` |
| `avg_delay_days` | float | Average delivery delay (days) | Positive = late, negative = early. Weighted by order when aggregating to region level. |

**Minimum 30 orders threshold**: State×month cells with fewer than 30 delivered orders should be suppressed or greyed out in visualizations to avoid misleading rates from small samples.

**Regional aggregation note**: When computing region-level averages from state-level data, use order-weighted means — not simple averages. SP alone accounts for ~40% of Southeast orders; unweighted averaging gives small states (e.g., ES) equal influence.

---

### 5. `data/seller_performance.parquet`

**Granularity**: Seller (one row per seller) — ~3k rows
**Produced by**: `notebooks/03_geo_seller_analysis.ipynb`
**Dashboard pages**: Geographic Analysis (seller section)

| Column | Type | Description | Derivation / Notes |
|---|---|---|---|
| `seller_id` | string | Unique seller identifier | From `dim_sellers` |
| `seller_state` | string | 2-letter state code | Seller's registered state |
| `seller_region` | string | IBGE macro-region | Derived via `REGION_MAP` with `state_col="seller_state"` |
| `gmv` | float | Gross Merchandise Value (R$) | `SUM(total_sale_amount)` across all seller's items, full period |
| `order_count` | int | Distinct orders fulfilled | `COUNT(DISTINCT order_id)` |
| `avg_review_score` | float | Mean review score (1–5) | Average across all reviewed orders for this seller |
| `cancellation_rate` | float | Fraction of orders canceled (0–1) | `COUNT(DISTINCT canceled orders) / COUNT(DISTINCT all orders)`. Order-level, not item-level — fixes a prior bug where item-level counting inflated rates to >100% for multi-item canceled orders. |

**Full-period data**: This file has no date dimension — it covers Jan 2017 – Aug 2018 in aggregate. Dashboard should display a static label "Jan 2017 – Aug 2018" via `st.caption()`. Date Range filter is not applicable.

**Seller concentration**: Gini coefficient of seller GMV is 0.78 (high inequality — long tail of small sellers), but CR4 = 6.1% and HHI = 31 (highly competitive — no monopoly). This is a healthy marketplace pattern.

---

### 6. `data/concentration_metrics.parquet`

**Granularity**: One row per dimension × time period — 83 rows
**Produced by**: `notebooks/03_geo_seller_analysis.ipynb`
**Dashboard pages**: Available for KPI cards and trend charts

| Column | Type | Description | Derivation / Notes |
|---|---|---|---|
| `dimension` | string | What is being measured | Values: `seller_gmv`, `seller_gmv_monthly`, `category_seller_gmv`, `customer_monetary`, `category_revenue` |
| `gini` | float | Gini coefficient (0–1) | 0 = perfect equality, 1 = perfect inequality. Measures distribution shape. |
| `cr4` | float | CR4 — top 4 entities' share (0–1) | Share of total value held by largest 4 entities |
| `cr10` | float | CR10 — top 10 entities' share (0–1) | Share of total value held by largest 10 entities |
| `hhi` | float | Herfindahl-Hirschman Index (0–10000) | <1500 = competitive, 1500–2500 = moderate, >2500 = concentrated. Measures monopoly risk. |
| `n_entities` | int | Number of entities in the distribution | |
| `top_20pct_share` | float | Share held by top 20% of entities (0–1) | Pareto indicator — 0.80 means top 20% hold 80% of value |

**Interpreting Gini vs HHI**: These measure different things. High Gini + low HHI = many small players with a long tail (healthy marketplace inequality). High HHI = actual market concentration / monopoly risk. Example: seller Gini = 0.78 (high inequality) but HHI = 31 (extremely competitive).

**Dimension descriptions**:
- `seller_gmv`: Overall seller GMV distribution (1 row)
- `seller_gmv_monthly`: Seller GMV distribution per month (20 rows, Jan 2017–Aug 2018)
- `category_seller_gmv`: Seller concentration within each product category (60 rows)
- `customer_monetary`: Overall customer monetary distribution (1 row)
- `category_revenue`: Revenue distribution across product categories (1 row)

---

## Key Metric Definitions

### Metric 1 — Monthly Sales Trends (GMV + Volume)
- **GMV** (Gross Merchandise Value) = `SUM(total_sale_amount)` per month
- **Order count** = `COUNT(DISTINCT order_id)` per month
- Peak: Nov 2017 (7,544 orders — Black Friday effect)
- Growth: ~103% GMV increase from Jan 2017 to Aug 2018

### Metric 2 — Top Products by Revenue
- Ranked by `SUM(total_sale_amount)` per `product_category_name_english`
- Revenue-based (not unit count) — a few high-priced categories dominate
- Category Gini = 0.71 (high inequality but no single dominant category)

### Metric 3 — RFM Customer Segmentation
- See `customer_rfm.parquet` schema above for full specification
- Standalone KPI: repeat purchase rate (~3.1%)

### Metric 4 — Delivery Performance
- **On-time rate** = orders delivered ≤ estimated date / total delivered orders
- **Average delay** = mean of (actual − estimated) in days; negative = early
- Use `COUNT(DISTINCT order_id)` — delivery timestamps repeat across items

### Metric 5 — Review/Satisfaction Analysis
- Score distribution (1–5), monthly trend
- Delay × review correlation across 5 bins

### Metric 6 — Payment Method Distribution
- Donut: share by `primary_payment_type`
- Histogram: installment distribution for credit card orders only

### Metric 7 — Average Order Value (AOV)
- AOV = `SUM(total_sale_amount) / COUNT(DISTINCT order_id)` per period
- Can be broken down by payment type

### Metric 8 — Cancellation/Fulfilment Rate
- Cancellation % = canceled orders / total orders per month
- Unavailability % tracked separately
- Overall: ~96.8% delivered

### Metric 9 — NPS Proxy
- NPS = (% promoters) − (% detractors)
- Monthly 100% stacked bar (promoter / passive / detractor)

### Metric 10 — Seller Performance
- Scatter: GMV vs avg review score, sized by order count
- Pareto/Lorenz curve: cumulative GMV share by seller percentile

### Metric 11 — Regional E-commerce Penetration
- Choropleth: GMV by state (`brazil_states.geojson`, `featureidkey="properties.sigla"`)
- Bar: GMV by region

---

## Shared Constants (`notebooks/utils.py`)

All colour palettes and mappings are defined once in `notebooks/utils.py` and imported by notebooks, `scripts/generate_parquet.py`, and `dashboard_utils.py`.

| Constant | Type | Purpose |
|---|---|---|
| `REGION_MAP` | dict[str, str] | 27 state codes → 5 IBGE regions |
| `SEGMENT_COLOURS` | dict[str, str] | 6 RFM segment → hex colour |
| `REGION_COLOURS` | dict[str, str] | 5 regions → hex colour |
| `STATUS_COLOURS` | dict[str, str] | 8 order statuses → hex colour |
| `add_region(df, state_col)` | function | Adds region column; dynamic naming (`customer_state` → `customer_region`) |
| `lorenz_curve(values)` | function | Returns (x, y) cumulative share arrays |
| `gini_coefficient(values)` | function | Gini via trapezoidal Lorenz area |
| `hhi(values)` | function | Herfindahl-Hirschman Index × 10,000 |
| `concentration_summary(values, name)` | function | Full suite: gini, cr4, cr10, hhi, top_20pct_share |

---

## Raw Source Layer (`olist_raw` dataset)

All 9 raw tables are loaded by Meltano (`tap-csv → target-bigquery`). Every column arrives as STRING — no type inference is performed. All casts are the sole responsibility of the dbt staging layer.

**Important:** `target-bigquery` with `denormalized: false` stores data in base tables (with a `data` JSON column) and creates flat-column views with a `_view` suffix. dbt queries the `*_view` tables. Do not query base tables directly.

### `olist_customers_dataset_view`

| Column | Raw Type | Description |
|---|---|---|
| `customer_id` | STRING | Order-scoped customer identifier. One row per order — same customer placing multiple orders gets a different `customer_id` each time. FK target: `stg_orders.customer_id` |
| `customer_unique_id` | STRING | True customer PK — consistent across repeat purchases. 96,096 distinct values from 99,441 rows. |
| `customer_zip_code_prefix` | STRING | 5-digit zip code prefix (padded). Used for geolocation join in `dim_customers`. |
| `customer_city` | STRING | Customer city name (free text, Brazilian Portuguese). |
| `customer_state` | STRING | 2-letter Brazilian state code (e.g., SP, RJ, MG). Always present. |

### `olist_orders_dataset_view`

| Column | Raw Type | Description | Nulls |
|---|---|---|---|
| `order_id` | STRING | PK. Unique order identifier. 99,441 rows, all distinct. | 0 |
| `customer_id` | STRING | FK to `olist_customers_dataset_view.customer_id`. | 0 |
| `order_status` | STRING | Order lifecycle status. 8 values: delivered (96,478), shipped, canceled, unavailable, invoiced, processing, created, approved. | 0 |
| `order_purchase_timestamp` | STRING | When the order was placed. Cast: `TIMESTAMP`. Always present — used as `date_key` for fact FK joins. | 0 |
| `order_approved_at` | STRING | When payment was approved. Cast: `SAFE_CAST AS TIMESTAMP` (blank cells → NULL). | 160 blank |
| `order_delivered_carrier_date` | STRING | When the order was handed to the carrier. Cast: `SAFE_CAST AS TIMESTAMP`. | 1,783 blank |
| `order_delivered_customer_date` | STRING | When the customer received the order. Cast: `SAFE_CAST AS TIMESTAMP`. | 2,965 blank |
| `order_estimated_delivery_date` | STRING | Seller-provided estimated delivery date. Cast: `SAFE_CAST AS TIMESTAMP`. | small number blank |

**Note on blank handling**: `tap-csv` encodes blank CSV cells as `''`, not NULL. `SAFE_CAST('' AS TIMESTAMP)` returns NULL silently. `CAST('' AS TIMESTAMP)` raises a BigQuery error. All nullable timestamp columns use `SAFE_CAST`.

### `olist_order_items_dataset_view`

| Column | Raw Type | Description | Nulls |
|---|---|---|---|
| `order_id` | STRING | FK to `olist_orders_dataset_view.order_id`. | 0 |
| `order_item_id` | STRING | Item sequence within order (1-based). Cast: `INT64`. | 0 |
| `product_id` | STRING | FK to `olist_products_dataset_view.product_id`. | 0 |
| `seller_id` | STRING | FK to `olist_sellers_dataset_view.seller_id`. | 0 |
| `shipping_limit_date` | STRING | Deadline for seller to ship. Cast: `TIMESTAMP`. | 0 |
| `price` | STRING | Item unit price (R$). Cast: `FLOAT64`. Min 0.85, max 6,735. | 0 |
| `freight_value` | STRING | Freight cost allocated to this item (R$). Cast: `FLOAT64`. Min 0.0. | 0 |

**Granularity note**: 112,650 rows. 98,666 distinct order_ids — 9,803 orders have multiple items. 775 orders in `olist_orders_dataset_view` have no rows here (itemless orders: 603 unavailable, 164 canceled, etc.).

### `olist_order_payments_dataset_view`

| Column | Raw Type | Description | Defects |
|---|---|---|---|
| `order_id` | STRING | FK to `olist_orders_dataset_view.order_id`. | 0 |
| `payment_sequential` | STRING | Payment sequence within order (1-based). Cast: `INT64`. Compound PK component. | 0 |
| `payment_type` | STRING | Payment method. Source values: credit_card (76,795), boleto (19,784), voucher (5,775), debit_card (1,529), not_defined (3). | DEF-004: 3 `not_defined` rows filtered in `stg_payments` |
| `payment_installments` | STRING | Number of installments. Cast: `INT64`. Source range: 0–24. | DEF-005: 2 credit_card rows with installments=0, clamped to 1 in `stg_payments` via `GREATEST(..., 1)` |
| `payment_value` | STRING | Payment amount (R$). Cast: `FLOAT64`. Range: 0.0–13,664. | DEF-006: 6 zero-value vouchers — legitimate, not filtered |

### `olist_order_reviews_dataset_view`

| Column | Raw Type | Description | Defects / Notes |
|---|---|---|---|
| `review_id` | STRING | Review identifier. **Not unique in source** — 789 duplicate values. Deduplicated in `stg_reviews` via `ROW_NUMBER()`. | DEF-001 |
| `order_id` | STRING | FK to `olist_orders_dataset_view.order_id`. Not unique — 547 orders have multiple reviews. | — |
| `review_score` | STRING | Customer score. Cast: `INT64`. Source values: 1–5 only. | 0 |
| `review_comment_title` | STRING | Optional short title. Blank cells loaded as `''` (not NULL). ~88.3% blank. | tap-csv encoding |
| `review_comment_message` | STRING | Optional review body. Blank cells loaded as `''` (not NULL). ~58.7% blank. | tap-csv encoding |
| `review_creation_date` | STRING | When the review was created. Cast: `TIMESTAMP`. Used as `date_key` in `fct_reviews`. | 0 |
| `review_answer_timestamp` | STRING | When the review was answered. Cast: `TIMESTAMP`. Used as tiebreaker in deduplication. | 0 |

**Row count**: 99,224 source rows. After dedup: ~98,435 rows in `stg_reviews` and `fct_reviews`.

### `olist_products_dataset_view`

| Column | Raw Type | Description | Defects / Notes |
|---|---|---|---|
| `product_id` | STRING | PK. 32,951 rows, all distinct. | 0 |
| `product_category_name` | STRING | Portuguese category name. Blank (not NULL) for 610 products. **Do not use for analysis** — use `product_category_name_english` from `dim_products`. | DEF-003 |
| `product_name_lenght` | STRING | ⚠️ Misspelled source column. Character count of product name. Cast: `SAFE_CAST AS INT64`. Blank for 610 products. Renamed to `product_name_length` in `stg_products`. | DEF-009 |
| `product_description_lenght` | STRING | ⚠️ Misspelled source column. Character count of description. Same handling. Renamed to `product_description_length`. | DEF-009 |
| `product_photos_qty` | STRING | Number of product photos. Cast: `INT64`. | Blank for 610 |
| `product_weight_g` | STRING | Product weight in grams. Cast: `FLOAT64`. | 2 blank |
| `product_length_cm` | STRING | Product length in cm. Cast: `FLOAT64`. | 2 blank |
| `product_height_cm` | STRING | Product height in cm. Cast: `FLOAT64`. | 2 blank |
| `product_width_cm` | STRING | Product width in cm. Cast: `FLOAT64`. | 2 blank |

### `olist_sellers_dataset_view`

| Column | Raw Type | Description |
|---|---|---|
| `seller_id` | STRING | PK. 3,095 rows, all distinct. |
| `seller_zip_code_prefix` | STRING | 5-digit zip code prefix. Used for geolocation join in `dim_sellers`. |
| `seller_city` | STRING | Seller city name. |
| `seller_state` | STRING | 2-letter Brazilian state code. |

### `olist_geolocation_dataset_view`

| Column | Raw Type | Description | Notes |
|---|---|---|---|
| `geolocation_zip_code_prefix` | STRING | 5-digit zip code prefix. Cast: `STRING` (preserved as-is — leading zeros matter). | 19,015 distinct prefixes after dedup |
| `geolocation_lat` | STRING | Latitude. Cast: `FLOAT64`. Source range: -36.6 to +45.1. | DEF-002: 29 rows outside Brazil bounds, filtered in `stg_geolocation` |
| `geolocation_lng` | STRING | Longitude. Cast: `FLOAT64`. Source range: -101.5 to +121.1. | DEF-002: 37 rows outside Brazil bounds, filtered in `stg_geolocation` |
| `geolocation_city` | STRING | City name (not used in downstream models). | — |
| `geolocation_state` | STRING | State code (not used in downstream models — zip prefix used for join). | — |

**Size**: 1,000,163 rows — largest source file by a significant margin. Aggregated to 19,015 rows in `stg_geolocation` via `GROUP BY zip_code_prefix` after bounding-box filter.

### `product_category_name_translation_view`

| Column | Raw Type | Description | Notes |
|---|---|---|---|
| `product_category_name` | STRING | Portuguese category name (lookup key). 71 rows. | UTF-8 BOM in source file — handled transparently by tap-csv |
| `product_category_name_english` | STRING | English translation. | 2 untranslated categories: `pc_gamer`, `portateis_cozinha_e_preparadores_de_alimentos` |

---

## Staging Layer (`olist_analytics` dataset — `stg_*` prefix)

Staging models perform all type casting, defect corrections, deduplication, and renaming. Mart models (`dim_*`, `fct_*`) must reference staging models via `ref()`, not raw sources directly.

### Key Staging Transformations

| Model | Primary Transformations |
|---|---|
| `stg_customers` | Cast all columns from STRING. Pass-through — no defects. |
| `stg_orders` | Cast all columns. `SAFE_CAST` for 4 nullable timestamps. Derive `date_key` as `DATE(CAST(order_purchase_timestamp AS TIMESTAMP))`. |
| `stg_order_items` | Cast all columns. `order_item_id` cast to INT64. Pass-through otherwise. |
| `stg_payments` | Cast all columns. Filter `payment_type = 'not_defined'` (DEF-004). Clamp `payment_installments` to min 1 via `GREATEST(CAST(...), 1)` (DEF-005). |
| `stg_reviews` | Cast all columns. Deduplicate on `review_id` via `ROW_NUMBER() OVER (PARTITION BY review_id ORDER BY review_answer_timestamp DESC)`, keep rn=1 (DEF-001). Derive `date_key`. |
| `stg_products` | Cast all columns with `SAFE_CAST`. Rename `product_name_lenght → product_name_length` and `product_description_lenght → product_description_length` (DEF-009). Join `product_category_name_translation_view` for English names. COALESCE: `CASE WHEN TRIM(IFNULL(english, '')) = '' THEN NULL ELSE english END` → Portuguese → `'uncategorized'` (DEF-003). |
| `stg_geolocation` | Filter `lat BETWEEN -35 AND 5 AND lng BETWEEN -75 AND -34` (DEF-002). `GROUP BY zip_code_prefix`, `AVG(lat)`, `AVG(lng)`. Produces 1 row per zip prefix. |
| `stg_sellers` | Cast all columns. Pass-through — no defects. |
| `stg_product_category_name_translation` | Pass-through from `product_category_name_translation_view`. Source for `stg_products` COALESCE join. |

### Staging Column Types (post-cast)

All staging models expose columns in their final analytical types. The staging layer is the only place in the pipeline where STRING → typed casts occur. Downstream models (`dim_*`, `fct_*`) do not perform additional casts.

| Column type | Cast pattern | SAFE_CAST used? |
|---|---|---|
| Timestamps (required) | `CAST(col AS TIMESTAMP)` | No — failure means bad source data |
| Timestamps (nullable) | `SAFE_CAST(col AS TIMESTAMP)` | Yes — blank CSV cell → NULL, not error |
| Integer IDs | `CAST(col AS INT64)` | For sequential IDs where blank is impossible |
| Nullable integers | `SAFE_CAST(col AS INT64)` | For dimension attributes (product lengths, weights) |
| Float amounts | `CAST(col AS FLOAT64)` | For price, freight — always present |
| String keys | No cast (remain STRING) | customer_id, product_id, order_id, etc. |

---

## dbt Mart Layer (`olist_analytics` dataset — `dim_*` / `fct_*` prefix)

Mart models are the analytical Gold layer. They reference only staging models via `ref()` — never raw sources directly. Dimensions deduplicate and enrich staging; facts join across dimensions to produce the analytical grain consumed by notebooks and the dashboard.

---

### `dim_customers`

**PK**: `customer_unique_id`
**Grain**: One row per unique customer (deduped from `stg_customers` which has one row per order)
**Sources**: `stg_customers` LEFT JOIN `stg_geolocation` on `customer_zip_code_prefix = zip_code_prefix`
**Row count**: ~96,096

| Column | BigQuery Type | Description | Notes |
|---|---|---|---|
| `customer_unique_id` | STRING | True customer PK — consistent across repeat purchases | 96,096 distinct values. `customer_id` (order-scoped) is NOT exposed here. |
| `customer_city` | STRING | Customer's registered city | Free text, Brazilian Portuguese |
| `customer_state` | STRING | 2-letter Brazilian state code | e.g., SP, RJ, MG. Always present. |
| `customer_zip_code_prefix` | STRING | 5-digit zip code prefix | Join key to `stg_geolocation`. Leading zeros preserved (STRING, not INT). |
| `geolocation_lat` | FLOAT64 | Latitude of customer zip centroid | **NULLABLE** — ~0.3% of zip prefixes have no geolocation match (LEFT JOIN). Within Brazil bounds (−35 to +5). |
| `geolocation_lng` | FLOAT64 | Longitude of customer zip centroid | **NULLABLE** — same match rate as lat. Within Brazil bounds (−75 to −34). |

**Warning**: `customer_unique_id` vs `customer_id` — `stg_customers` has one row per `customer_id` (order-scoped). A single customer making 3 orders has 3 distinct `customer_id` values but 1 `customer_unique_id`. `dim_customers` deduplicates using `ROW_NUMBER() OVER (PARTITION BY customer_unique_id ORDER BY customer_id)` — only the first `customer_id` row is retained.

---

### `dim_products`

**PK**: `product_id`
**Grain**: One row per product
**Source**: `stg_products`
**Row count**: 32,951

| Column | BigQuery Type | Description | Notes |
|---|---|---|---|
| `product_id` | STRING | Product PK | 32,951 distinct values, all unique |
| `product_category_name_english` | STRING | English category name (primary analytical column) | COALESCE(english → Portuguese fallback → `'uncategorized'`). NEVER NULL. 610 products are `'uncategorized'`. **Always use this column** — `product_category_name` (Portuguese, not exposed in mart) has 610 blank-string entries that silently produce an empty-string bucket. |
| `product_name_length` | INT64 | Character count of product name | **NULLABLE** — blank for 610 uncategorized products. Correctly spelled (source has `product_name_lenght` — renamed in `stg_products`). |
| `product_description_length` | INT64 | Character count of product description | **NULLABLE** — blank for 610 uncategorized products. Correctly spelled (source has `product_description_lenght` — renamed in `stg_products`). |
| `product_photos_qty` | INT64 | Number of product photos | **NULLABLE** — blank for 610 products |
| `product_weight_g` | FLOAT64 | Product weight in grams | **NULLABLE** — 2 products blank in source |
| `product_length_cm` | FLOAT64 | Product length in cm | **NULLABLE** — 2 products blank in source |
| `product_height_cm` | FLOAT64 | Product height in cm | **NULLABLE** — 2 products blank in source |
| `product_width_cm` | FLOAT64 | Product width in cm | **NULLABLE** — 2 products blank in source |

**COALESCE guard detail**: `stg_products` uses `CASE WHEN TRIM(IFNULL(english_name, '')) = '' THEN NULL ELSE english_name END` before COALESCE — this converts both NULL and empty-string `''` to NULL so the COALESCE fallback chain fires correctly for the 2 untranslated categories (`pc_gamer`, `portateis_cozinha_e_preparadores_de_alimentos`).

---

### `dim_sellers`

**PK**: `seller_id`
**Grain**: One row per seller
**Sources**: `stg_sellers` LEFT JOIN `stg_geolocation` on `seller_zip_code_prefix = zip_code_prefix`
**Row count**: 3,095

| Column | BigQuery Type | Description | Notes |
|---|---|---|---|
| `seller_id` | STRING | Seller PK | 3,095 distinct values, all unique |
| `seller_city` | STRING | Seller's registered city | Free text |
| `seller_state` | STRING | 2-letter Brazilian state code | Always present |
| `seller_zip_code_prefix` | STRING | 5-digit zip code prefix | Join key to `stg_geolocation`. Leading zeros preserved (STRING). |
| `geolocation_lat` | FLOAT64 | Latitude of seller zip centroid | **NULLABLE** — ~0.2% of seller zips have no geolocation match |
| `geolocation_lng` | FLOAT64 | Longitude of seller zip centroid | **NULLABLE** — same rate as lat |

---

### `dim_date`

**PK**: `date_key`
**Grain**: One row per calendar day
**Source**: Generated via `dbt_utils.date_spine` macro (no staging model input)
**Row count**: 1,096 (2016-01-01 to 2018-12-31 inclusive)

| Column | BigQuery Type | Description | Notes |
|---|---|---|---|
| `date_key` | DATE | Calendar date (PK) | Direct output of `dbt_utils.date_spine`. Range: 2016-01-01 to 2018-12-31. FK target for all three fact tables. |
| `year` | INT64 | Calendar year | `EXTRACT(YEAR FROM date_key)`. Values: 2016, 2017, 2018. |
| `month` | INT64 | Calendar month (1–12) | `EXTRACT(MONTH FROM date_key)` |
| `day` | INT64 | Day of month (1–31) | `EXTRACT(DAY FROM date_key)` |
| `day_of_week` | INT64 | Day of week (1–7) | `EXTRACT(DAYOFWEEK FROM date_key)`. **BigQuery convention: 1 = Sunday, 7 = Saturday** — not ISO 8601 (where 1 = Monday). |
| `quarter` | INT64 | Calendar quarter (1–4) | `EXTRACT(QUARTER FROM date_key)` |

**Fact table `date_key` derivation**:
- `fct_sales`: `DATE(SAFE_CAST(order_purchase_timestamp AS TIMESTAMP))` from `stg_orders`
- `fct_reviews`: `DATE(CAST(review_creation_date AS TIMESTAMP))` from `stg_reviews`
- `fct_payments`: `DATE(SAFE_CAST(order_purchase_timestamp AS TIMESTAMP))` from `stg_orders` (via explicit CTE)

---

### `fct_sales`

**Compound PK**: (`order_id`, `order_item_id`)
**Grain**: One row per order item
**Sources**: `stg_order_items` → JOIN `stg_orders` (on `order_id`) → JOIN `stg_customers` (on `customer_id`)
**Row count**: ~112,650

| Column | BigQuery Type | Description | Notes |
|---|---|---|---|
| `order_id` | STRING | Order identifier (PK component) | FK to `dim_date` (via `date_key`). 98,666 distinct orders. |
| `order_item_id` | INT64 | Item sequence within order (PK component) | 1-based. Combined with `order_id` → unique row. |
| `product_id` | STRING | FK → `dim_products.product_id` | Always present |
| `seller_id` | STRING | FK → `dim_sellers.seller_id` | Always present |
| `customer_unique_id` | STRING | FK → `dim_customers.customer_unique_id` | Resolved via three-source CTE: `stg_order_items.order_id → stg_orders.customer_id → stg_customers.customer_unique_id`. Direct join from `stg_order_items` to `stg_customers` produces NULL — they share no key. |
| `date_key` | DATE | FK → `dim_date.date_key` | `DATE(SAFE_CAST(order_purchase_timestamp AS TIMESTAMP))`. Uses SAFE_CAST: blank purchase timestamps → NULL (rare but possible). |
| `order_status` | STRING | Order lifecycle status | 8 values: delivered (~96.8%), shipped, canceled, unavailable, invoiced, processing, created, approved |
| `price` | FLOAT64 | Item unit price (R$) | Excludes freight. Min 0.85. |
| `freight_value` | FLOAT64 | Freight cost allocated to this item (R$) | Min 0.0 (free shipping promotions) |
| `total_sale_amount` | FLOAT64 | `price + freight_value` | Item-level revenue. Sum across items for order total; sum across orders for GMV. **FLOAT64 precision**: use `ROUND(..., 2)` for currency display — IEEE 754 drift can produce values like 149.99999999998. |
| `order_delivered_customer_date` | TIMESTAMP | When the customer received the order | **NULLABLE** — NULL for ~3% of orders (undelivered, canceled, in transit). Order-level attribute repeated across all items of the same order. |
| `order_estimated_delivery_date` | TIMESTAMP | Seller-provided estimated delivery date | **NULLABLE** — small number of orders have no estimate. Order-level attribute — same caveat as above. |

**COUNT trap**: `order_delivered_customer_date` and `order_estimated_delivery_date` repeat across all items of the same order. Always use `COUNT(DISTINCT order_id)` for delivery rate calculations, NOT `COUNT(*)`.

**Excluded column**: `order_payment_value` is deliberately absent. It is an order-level aggregate — joining it onto item-level rows causes double-counting proportional to item count per order. Use `fct_payments` for payment analysis.

---

### `fct_reviews`

**PK**: `review_id`
**Grain**: One row per deduplicated review
**Source**: `stg_reviews` (deduplication performed in staging — 789 duplicate `review_id` values resolved via `ROW_NUMBER()`)
**Row count**: ~98,435

| Column | BigQuery Type | Description | Notes |
|---|---|---|---|
| `review_id` | STRING | Review PK | Unique after dedup. NOT unique in source (`stg_reviews` handles dedup). |
| `order_id` | STRING | FK → **`stg_orders.order_id`** (NOT `fct_sales.order_id`) | **Cross-boundary FK** — 756 orders have reviews but no items in `fct_sales` (itemless orders: canceled, unavailable). A FK test targeting `fct_sales` would fail for these 756 orders. NOT unique in `fct_reviews` — 547 orders have 2+ reviews with distinct `review_id` values. |
| `review_score` | INT64 | Customer review score (1–5) | Ordinal — do not treat as continuous. Bar chart (not histogram). |
| `review_comment_title` | STRING | Optional short review title | `''` (empty string) for ~88.3% of reviews — tap-csv encodes blank cells as `''`, not NULL. Filter with `NULLIF(review_comment_title, '')` for text analysis. |
| `review_comment_message` | STRING | Optional review body text | `''` for ~58.7% of reviews — same empty-string encoding. |
| `date_key` | DATE | FK → `dim_date.date_key` | `DATE(CAST(review_creation_date AS TIMESTAMP))`. Uses CAST (not SAFE_CAST) — `review_creation_date` is always present in source. |
| `review_answer_timestamp` | TIMESTAMP | When the seller/platform answered the review | Used as tiebreaker in `stg_reviews` deduplication (keep latest answer). Always present. |

---

### `fct_payments`

**Compound PK**: (`order_id`, `payment_sequential`)
**Grain**: One row per payment record (an order may have multiple payment methods)
**Sources**: `stg_payments` LEFT JOIN `stg_orders` (on `order_id`)
**Row count**: ~103,883 (after `not_defined` filter in staging)

| Column | BigQuery Type | Description | Notes |
|---|---|---|---|
| `order_id` | STRING | Order identifier (PK component) | An order can have multiple rows (split payments). |
| `payment_sequential` | INT64 | Payment sequence within order (PK component) | 1-based. `payment_sequential = 1` is the primary payment method. |
| `payment_type` | STRING | Payment method | 4 values post-filter: `credit_card` (~74%), `boleto` (~19%), `voucher` (~6%), `debit_card` (~1%). `not_defined` filtered in `stg_payments`. |
| `payment_installments` | INT64 | Number of installments | Min 1 (clamped in `stg_payments` via `GREATEST(..., 1)` — 2 credit_card rows had 0 installments). Boleto is always 1. Credit card range: 1–24. |
| `payment_value` | FLOAT64 | Payment amount (R$) | Min 0.0 (zero-value vouchers are valid). Range 0.0–13,664. |
| `date_key` | DATE | FK → `dim_date.date_key` | Derived from `stg_orders.order_purchase_timestamp` (not in `stg_payments`). **NULLABLE** — rare orders in `stg_payments` have no matching row in `stg_orders` (LEFT JOIN). No FK test on `date_key` in schema.yml by design. |

**DAG dependency note**: `fct_payments` includes an explicit `ref('stg_orders')` CTE even though `stg_orders` only provides `date_key`. Without this explicit reference, dbt's DAG omits the `stg_orders → fct_payments` edge, breaking Dagster's execution order guarantees and lineage visibility.

**Reconciliation**: For single-installment orders, `SUM(fct_payments.payment_value)` per order should equal `SUM(fct_sales.total_sale_amount)` within R$20.00. Multi-installment orders are excluded — Olist's `payment_value` includes credit card parcelamento interest, which legitimately exceeds price+freight. The R$20.00 threshold covers 13 known freight-subsidy anomalies (max diff R$16.50). See `tests/assert_payment_reconciliation.sql` and changelog 2026-03-15.

---

## Star Schema Relationships

```
                    ┌──────────────┐
                    │  dim_date    │
                    │  (date_key)  │
                    └──────┬───────┘
                           │ FK (date_key)
          ┌────────────────┼─────────────────┐
          │                │                 │
   ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
   │  fct_sales  │  │ fct_reviews │  │fct_payments │
   │ (order_id + │  │ (review_id) │  │ (order_id + │
   │order_item_id│  │             │  │payment_seq) │
   └──┬──┬──┬───┘  └──────┬──────┘  └─────────────┘
      │  │  │             │
      │  │  │             └── order_id → stg_orders ⚠️
      │  │  │                 (NOT fct_sales — 756 itemless orders)
      │  │  │
      │  │  └── seller_id ──────────→ dim_sellers (seller_id)
      │  └───── product_id ─────────→ dim_products (product_id)
      └───────── customer_unique_id → dim_customers (customer_unique_id)
```
