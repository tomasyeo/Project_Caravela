# Data Dictionary — Project Caravela

> **Scope**: Parquet export files in `data/` and key analytical columns.
> This document covers business definitions, derivation logic, and interpretation guidance
> for columns produced by the analysis layer (Jupyter notebooks / `scripts/generate_parquet.py`).
>
> For BigQuery mart and staging column definitions, see dbt `schema.yml` files:
> - `dbt/models/staging/schema.yml`
> - `dbt/models/marts/schema.yml`
>
> **Data Analyst sections**: Parquet schemas, derived columns, metric definitions, business context.
> **Data Engineer sections** *(TODO)*: Raw source columns, staging transformations, mart column descriptions.

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
