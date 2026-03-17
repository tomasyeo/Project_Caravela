# Dashboard User Guide — Data Analyst Draft

> **Status**: Draft for REQ-050.1. Contains metric definitions, interpretation guidance,
> and business context. Dash Engineer to merge with technical operation sections
> (filter behaviour, layout, navigation).

---

## Overview

The Olist Analytics Dashboard provides four views analysing ~100k e-commerce orders
from the Brazilian marketplace Olist (Jan 2017 – Aug 2018). All data is pre-computed
in Parquet files — the dashboard requires no live database connection.

**Currency**: All monetary values are in Brazilian Reais (R$). For USD reference:
R$3.65/USD (2018 annual average), giving ~R$15.7M total GMV ≈ USD 4.3M.

---

## Page 1: Executive Overview

### What it shows
High-level business health: GMV trajectory, order volume, AOV, payment mix, and
fulfilment rates. This is the "at a glance" page for stakeholders who need a
2-minute summary.

### Key metrics

| KPI Card | Definition | What "good" looks like |
|---|---|---|
| Total GMV | Sum of `price + freight_value` across all items in filtered period | Growth month-over-month |
| Total Orders | `COUNT(DISTINCT order_id)` in filtered period | Consistent with or above GMV growth (if AOV is stable) |
| AOV | GMV / distinct orders | Stable or increasing — declining AOV with rising volume may indicate discounting |
| Delivery On-Time Rate | Delivered on or before estimated date / total delivered | >90% is healthy; Olist averages ~93% |

### Charts

**Monthly GMV + Order Volume** (two stacked panels — area + bar):
- The area chart (GMV) and bar chart (orders) are intentionally separate panels,
  not dual-axis. Dual-axis charts mislead by implying correlation through scale alignment.
- **What to look for**: Nov 2017 spike = Black Friday. Jan 2018 dip = post-holiday.
  Sustained growth through mid-2018 indicates marketplace expansion.
- **Caution**: Aug 2018 is the last complete month. Any partial-month data is excluded.

**Payment Distribution** (donut + installment histogram):
- Credit card dominates (~77%). Boleto (bank slip) is ~19% — unique to Brazil,
  popular with unbanked customers.
- Installment histogram (credit card only): median ~3 installments. Brazilian consumers
  routinely split purchases into 10–12 monthly installments ("parcelamento") even for
  modest amounts — this is culturally normal, not a sign of financial stress.
- `primary_payment_type` uses `payment_sequential=1`. ~3% of orders have split payments
  (e.g., voucher + credit card) — only the first method is shown.

**Cancellation & Fulfilment** (line + donut):
- ~96.8% of orders are delivered. Cancellation rate is ~1.2%.
- "Unavailable" is a separate status from "canceled" — it means the seller couldn't
  fulfil the order. Track both trends separately.
- **What to look for**: Rising cancellation % may indicate seller quality issues or
  stock management problems.

### How to interpret
- If GMV grows faster than order count → AOV is increasing (possible upselling or
  price inflation)
- If order count grows faster than GMV → AOV is declining (possible new lower-price
  categories or discounting)
- A spike in cancellations coinciding with high order volume may indicate capacity
  constraints during promotions

### Filters applied
All four filters (Date Range, Product Category, Customer State, Customer Region) apply.

---

## Page 2: Product Performance

### What it shows
Revenue concentration by product category, top performers, and category trends.

### Charts

**Top Products by Revenue** (horizontal bar + treemap):
- Ranked by `SUM(total_sale_amount)`, not unit count. High-price categories
  (e.g., `health_beauty`, `watches_gifts`, `bed_bath_table`) rank higher than
  high-volume but low-price categories.
- The treemap shows proportional share — useful for spotting the long tail.
- **610 products** are labelled `uncategorized` (source data had blank categories).
  These appear as a single bucket.

**Category Concentration**:
- Category revenue Gini = 0.71 → high inequality (a few categories drive most revenue)
  but no single category dominates (HHI is low).
- Top 3 categories account for ~22% of GMV — a diversified marketplace.

### Filters applied
Date Range, Product Category, Customer State, Customer Region all apply.

---

## Page 3: Geographic Analysis

### What it shows
Two distinct sections: delivery performance by region/state, and seller marketplace dynamics.

### Delivery Performance Section

**On-Time Rate by Region** (horizontal bar):
- Minimum 30 orders threshold per cell — sparse cells are suppressed to avoid misleading rates.
- South region typically has highest on-time rates; North/Northeast face longer distances
  and logistics challenges.

**Region × Month Delay Heatmap**:
- Fill colour = average delivery delay (days). Red = late, blue/green = early.
- Averages are **order-weighted** — SP's 40% market share is properly reflected,
  not averaged equally with smaller states.
- **What to look for**: Seasonal patterns (holiday spikes in Nov–Dec), persistent
  regional gaps that may indicate logistics infrastructure differences.

**Choropleth Map** (GMV by state):
- Uses `brazil_states.geojson` with `featureidkey="properties.sigla"`.
- SP dominates (~37% of GMV). RJ and MG are distant second/third.
- This is a market penetration view — compare to population share for
  per-capita insights (not computed in current data).

**Filters**: Date Range applies to `geo_delivery.parquet` (has year/month columns).
Customer State and Region filter both delivery and choropleth views.

### Seller Performance Section

**Scatter: GMV vs Avg Review Score** (sized by order count):
- Ideal sellers are top-right (high GMV + high reviews). Bottom-right sellers
  have volume but quality issues.
- Bubble size = order count. Small bubbles with extreme scores may be
  statistically unreliable (few reviews).

**Pareto/Lorenz Curve** (seller GMV concentration):
- X-axis = seller cumulative percentile (0–100%), Y-axis = cumulative GMV share.
- Diagonal = perfect equality. Bowing below = concentration.
- Seller Gini = 0.78: top 20% of sellers drive ~75% of GMV. However, CR4 = 6.1%
  and HHI = 31 — the marketplace is highly competitive with no monopoly risk.
- **Key insight**: High Gini + low HHI = healthy long-tail pattern. Many small
  sellers coexist with a few large ones, but no single seller dominates.

**Filters**: Seller performance is **full-period only** (Jan 2017 – Aug 2018).
Date Range filter does NOT apply — a static `st.caption()` label should indicate this.
Customer State/Region still filters by customer location (not seller location).

---

## Page 4: Customer Analysis

### What it shows
Two sections: RFM customer segmentation and satisfaction/NPS analysis.

### RFM Segmentation Section

**How RFM works**:
- **Recency** (R): Days since last purchase → quintile score 1–5 (5 = most recent)
- **Frequency** (F): Number of distinct orders → 3-tier: F1 (1 order), F2 (2), F3 (3+)
- **Monetary** (M): Total lifetime spend → quintile score 1–5 (5 = highest)
- Reference date: 2018-08-31 (fixed — not current date)

**Why 3-tier Frequency?** 96.9% of Olist customers made exactly 1 purchase. Quintile
scoring would put nearly all customers in the same bin. The 3-tier approach (F1/F2/F3)
creates meaningful separation.

**Segment interpretation guide**:

| Segment | Action | Business implication |
|---|---|---|
| **Champions** | Retain — exclusive offers, early access | Highest LTV; small group but disproportionate revenue |
| **Loyal** | Nurture — loyalty programs, cross-sell | Core repeat base; grow into Champions |
| **Promising** | Convert — incentivise second purchase | Recent single-buyers; highest conversion potential |
| **At Risk** | Re-engage — win-back campaigns, surveys | Previously active but going dormant; time-sensitive |
| **High Value Lost** | Win-back — aggressive offers, personal outreach | Former frequent buyers; high value if recovered |
| **Hibernating** | Low-cost reactivation or accept churn | One-time buyers, long inactive; lowest ROI for intervention |

**Repeat Purchase Rate KPI**: ~3.1% — meaning ~97% of customers buy only once.
This is typical for a marketplace (customers discover sellers on Olist, then may
transact directly on subsequent purchases). Not necessarily alarming, but indicates
a retention challenge.

**Heatmap (R_score × F_tier)**:
- Fill = customer count. Most cells cluster in R=low, F=F1 (Hibernating).
- Champions and At Risk segments are small but high-value.

**Filters**: Date Range and Product Category do **NOT** apply to RFM data.
RFM is computed over the full customer history with a fixed reference date.
A `st.caption()` note should explain this. State and Region filters still work.

### Satisfaction / NPS Section

**Review Score Distribution** (bar + monthly trend line):
- Scores are ordinal (1–5), not continuous — displayed as bar chart, not histogram.
- Distribution is heavily right-skewed: score 5 is ~57%, score 1 is ~12%.
- Monthly trend shows subtle improvement as marketplace matures.

**NPS Proxy** (100% stacked bar by month + NPS trend line):
- NPS = (% promoters) − (% detractors)
- **Important**: This is a proxy using review scores, not a true NPS survey (which
  uses a 0–10 "would you recommend" scale). Interpret directionally, not as absolute NPS.
- Score 4–5 = promoter, 3 = passive, 1–2 = detractor.

**Delay × Review Correlation** (bar: avg score by delay bin + box plot):
- 5 bins: early, on-time, 1-3d late, 4-7d late, 7+d late
- **Key finding**: The `early` bin has the highest average score — customers
  positively reward under-promised and over-delivered timelines.
- The sharpest satisfaction drop is between `1-3d late` → `4-7d late` (~1.19 points) —
  this is the critical threshold where customer patience runs out.
- **Actionable insight**: Setting conservative delivery estimates (so more orders
  arrive "early") is a better satisfaction strategy than trying to speed up all
  deliveries.

**Filters**: Date Range, Customer State, Region all apply. Product Category is
approximate — it uses the highest-revenue item's category for multi-item orders (~10%).

---

## Global Filter Behaviour

| Filter | Executive | Products | Geographic (delivery) | Geographic (sellers) | Customers (RFM) | Customers (satisfaction) |
|---|---|---|---|---|---|---|
| Date Range | Yes | Yes | Yes | **No** — full period | **No** — fixed ref date | Yes |
| Product Category | Yes | Yes | No | No | **No** | Yes (approx) |
| Customer State | Yes | Yes | Yes | Yes | Yes | Yes |
| Customer Region | Yes | Yes | Yes | Yes | Yes | Yes |

**Empty filter = show all**: When no values are selected in a multi-select filter,
all values are included (not none).

**Inapplicable filters**: Remain visible but inactive. A `st.caption()` note
explains why the filter doesn't apply to that section (e.g., "RFM uses fixed
reference date 2018-08-31 — Date Range filter not applied").

---

## Data Quality Notes for Interpretation

1. **Single-purchase marketplace**: ~97% of customers buy once. RFM segments are
   dominated by Hibernating/Promising. This is structurally normal for marketplaces.

2. **Split payment approximation**: ~3% of orders use multiple payment methods.
   Dashboard shows only the primary (first) payment. This slightly understates
   voucher usage.

3. **Multi-item category approximation**: ~10% of orders contain multiple items from
   different categories. `primary_product_category` in satisfaction data uses the
   highest-revenue item's category. Product Category filter may not perfectly
   match these orders.

4. **Uncategorized products**: 610 products (~1.9%) lack category labels in source
   data. These appear as "uncategorized" in all category breakdowns.

5. **Delivery timestamp anomalies**: Source data contains ~1,400 orders where
   carrier pickup is recorded after customer delivery, and ~23 where delivery
   precedes shipment. These are logistics recording errors in the source — delivery
   metrics include them as-is.

6. **Seller performance outliers**: Sellers with very few orders may show extreme
   review scores or cancellation rates. The scatter plot bubble size (order count)
   helps identify statistically unreliable points.
