# Dashboard User Guide — Project Caravela

> **Audience**: Business stakeholders, graders, and developers running or evaluating
> the dashboard. No database or cloud access required — all data is pre-loaded.

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Layout and Navigation](#2-layout-and-navigation)
3. [Global Filters](#3-global-filters)
4. [Page 1: Executive Overview](#4-page-1-executive-overview)
5. [Page 2: Product Performance](#5-page-2-product-performance)
6. [Page 3: Geographic Analysis](#6-page-3-geographic-analysis)
7. [Page 4: Customer Analysis](#7-page-4-customer-analysis)
8. [Page 5: Glossary](#8-page-5-glossary)
9. [Data Quality Notes](#9-data-quality-notes)

---

## 1. Getting Started

### Prerequisites

- Python environment: conda env `assignment2`
- All Parquet files committed to `data/` — no BigQuery connection needed

### Running locally

```bash
cd /path/to/Project_Caravela
conda activate assignment2
streamlit run dashboard.py
```

The app opens at `http://localhost:8501` in your browser. The first load takes
a few seconds while Streamlit caches the Parquet files; subsequent page switches
are near-instant.

### Data source

All 6 Parquet files in `data/` are read-only inputs:

| File | Rows | Used by |
|------|------|---------|
| `sales_orders.parquet` | 112,279 | Executive, Products |
| `customer_rfm.parquet` | 95,420 | Customer Analysis (RFM) |
| `satisfaction_summary.parquet` | 97,379 | Executive, Customer Analysis |
| `geo_delivery.parquet` | 533 | Geographic Analysis (delivery) |
| `seller_performance.parquet` | 3,068 | Geographic Analysis (sellers) |
| `concentration_metrics.parquet` | 83 | Products, Geographic (Gini trend) |

**Currency**: All monetary values are in Brazilian Reais (R$).
For USD reference: R$3.65/USD (2018 annual average) → total GMV ~R$15.7M ≈ USD 4.3M.

---

## 2. Layout and Navigation

### Page navigation

The left sidebar contains the page list. Click any page name to switch views.
The current page is highlighted. There are 5 pages:

| Page | Icon | Focus |
|------|------|-------|
| Executive Overview | 📊 | Business health at a glance |
| Product Performance | 🏷️ | Revenue by category, concentration |
| Geographic Analysis | 🗺️ | Market map, delivery, seller ecosystem |
| Customer Analysis | 👥 | RFM segments, satisfaction, NPS |
| Glossary | 📖 | Business and analytical term definitions |

### Tab layout

Each analysis page uses horizontal tabs — one focused story per tab. Switching
tabs does not reset filters. All tabs on a page share the same filtered dataset.

### Headline KPIs

The Executive Overview page pins 6 KPI cards above the tabs so they remain
visible regardless of which tab is active. Other pages surface relevant KPIs
at the top of each tab.

---

## 3. Global Filters

### Filter controls

The sidebar (below the page list) contains 4 filters that apply across all pages:

| Filter | Type | Default |
|--------|------|---------|
| Date Range | Date range picker | Jan 2017 – Aug 2018 (full period) |
| Product Category | Multi-select | All categories |
| State | Multi-select | All states |
| Region | Multi-select | All 5 regions |

**Empty selection = show all.** Selecting nothing in a multi-select includes all
values — it is not equivalent to selecting none.

### Reset button

The **↺ Reset Filters** button at the bottom of the sidebar restores all four
filters to their defaults in a single click.

### Filter applicability

Not every filter applies to every section. Inapplicable filters remain visible
in the sidebar but are not applied to that section — a caption note on the page
explains why.

| Filter | Executive | Products | Geographic (delivery) | Geographic (sellers) | Customers (RFM) | Customers (satisfaction) |
|--------|-----------|----------|-----------------------|----------------------|-----------------|--------------------------|
| Date Range | ✓ | ✓ | ✓ | ✗ full period only | ✗ fixed ref date | ✓ |
| Product Category | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ approx |
| State | ✓ | ✓ | ✓ | ✓ seller home state | ✓ | ✓ |
| Region | ✓ | ✓ | ✓ | ✓ seller home region | ✓ | ✓ |

**State / Region on the seller section** filters by where the seller is *based*,
not where they shipped to. A caption on the Seller Analysis tab makes this explicit.

**Product Category on satisfaction** is approximate — it uses the highest-revenue
item's category for multi-item orders (~10% of orders). The caption on that tab
notes this.

### Multi-select behaviour

Selections persist when switching pages. If you apply a State filter on the
Geographic page and navigate to Products, the same State filter is still active.
The active filter summary at the bottom of the sidebar shows a compact list of
any non-default filters currently applied.

---

## 4. Page 1: Executive Overview

### Purpose

60-second pulse check: GMV trajectory, order volume, AOV, payment mix, and
fulfilment rates. For stakeholders who need a 2-minute summary.

### KPI cards (always visible above tabs)

| KPI | Definition | Healthy signal |
|-----|------------|----------------|
| Total GMV | Sum of `price + freight_value` across all items | Month-over-month growth |
| Total Orders | `COUNT(DISTINCT order_id)` | Consistent with GMV growth |
| AOV | GMV ÷ distinct orders | Stable or increasing |
| On-Time Rate | Delivered on or before estimated date ÷ total delivered | >90%; Olist ~93% |
| NPS Proxy | % promoters − % detractors (review-based) | >+50 excellent; Olist ~+64 |
| Repeat Rate | % customers with more than 1 purchase | Any increase is positive |

### Tabs

**📈 Sales Trend**
- Two stacked panels: area chart (GMV) + bar chart (order count). Intentionally
  not dual-axis — dual-axis implies correlation through scale alignment.
- Black Friday 2017 (Nov) is annotated — the single largest spike (~7,500 orders,
  ~2× monthly average).
- What to look for: If GMV grows faster than orders, AOV is rising (upselling or
  price mix shift). If orders grow faster, AOV is declining (discounting or
  new lower-price categories).

**💰 Revenue & AOV**
- Monthly AOV trend line + AOV by payment type bar.
- Credit card users have higher AOV than boleto users — instalment capability
  enables larger purchases without upfront cost.

**💳 Payment Mix**
- Donut (payment type share) + histogram (credit card instalment count).
- Boleto (bank slip) is uniquely Brazilian — popular with the unbanked population,
  no credit card required.
- Instalment histogram shows median ~3 instalments. Splitting into 10–12 monthly
  payments ("parcelamento") is culturally normal in Brazil, not a sign of financial
  stress.

**📦 Order Health**
- Cancellation rate trend line + overall order status donut.
- ~96.8% of orders are delivered. Watch for rising cancellation % during
  high-volume periods — may indicate seller capacity constraints.
- "Unavailable" (seller cannot fulfil after acceptance) is tracked separately
  from "canceled" (customer or platform cancellation).

---

## 5. Page 2: Product Performance

### Purpose

Which categories generate revenue, how concentrated is that revenue, and where
do shipping costs eat into customer value?

### Tabs

**🏆 Revenue Rankings**
- Slider selects top N categories (5–30). Horizontal bar (sorted by revenue) +
  treemap (proportional share).
- Rankings are by `SUM(total_sale_amount)` — revenue, not units sold. High-price
  categories rank higher than high-volume but low-price ones.
- 610 products are labelled `uncategorized` (blank category in source data).

**📊 Category Concentration**
- Lorenz curve + Gini, HHI, CR4, CR10 KPI cards.
- **Lorenz curve**: the 45° diagonal = perfect equality. The further the red curve
  bows below, the more unequal revenue distribution is.
- **Gini = 0.71**: high inequality — a few categories drive most revenue. Normal
  for retail.
- **HHI = 484**: well below the 1,500 competitive threshold — no single category
  dominates.
- High Gini + low HHI = healthy long-tail marketplace pattern.

**🚚 Freight Impact**
- Freight-to-price ratio by category (top 15, min 100 items).
- Categories with ratios above 30% may be uncompetitive for online delivery —
  candidates for subsidised shipping or regional fulfilment partnerships.
- Overall freight = ~14% of total item price across the platform.

---

## 6. Page 3: Geographic Analysis

### Purpose

Where are customers, how does delivery quality vary by region, and how healthy
is the seller ecosystem?

### Tabs

**🗺️ Market Map**
- Choropleth (GMV by state, shaded intensity) + horizontal bar (GMV by region).
- SP (~37% of GMV) dominates. RJ and MG are distant second and third.
- North and Central-West represent low-penetration growth frontiers.

**🚚 Delivery Performance**
- On-time rate by region (horizontal bar) + days ahead/behind schedule by region
  (bar, colour-coded green/red) + region × month delay heatmap.
- On-time rates are **order-weighted** (total on-time ÷ total orders), not simple
  averages of group rates. This prevents Simpson's Paradox — averaging group rates
  without weighting by volume gives larger, high-order-count states disproportionate
  influence.
- Heatmap cells with fewer than 30 orders are suppressed (shown as grey) to avoid
  misleading rates from small samples.
- Olist systematically delivers *ahead* of the promised date — negative avg delay
  values mean "arrived early". This is a deliberate conservative-estimate strategy
  that converts late anxiety into pleasant surprise.
- **Date Range filter applies to this tab.** Product Category filter does not.

**👥 Seller Analysis**
- Seller scatter (GMV vs avg review score, bubble = order count, colour = region)
  + Pareto curve + quality tier treemap + monthly Gini trend.
- **Pareto curve**: X-axis is seller percentile (%), not rank — makes the 80/20
  threshold readable at a glance. Reference lines at x=20% and y=80%.
- **Quality tiers** (sellers with ≥10 orders): Premium (score ≥4.0, cancel ≤2%),
  Good (≥3.5, ≤5%), Average (≥3.0, ≤10%), At Risk (below thresholds).
- **Gini trend**: a rising line means top sellers are capturing a growing share
  of GMV over time — warrants monitoring for marketplace diversity.
- **Date Range filter does NOT apply** to this tab — seller metrics require the
  full observation window to be meaningful. A static caption shows the period
  (Jan 2017 – Aug 2018).
- **State / Region filter applies to seller home location**, not buyer location.

---

## 7. Page 4: Customer Analysis

### Purpose

Who are the customers, how should they be prioritised, and does delivery quality
drive satisfaction scores?

### Tabs

**🎯 RFM Segments**
- Repeat rate KPI + grouped bar (avg R/F/M score per segment) + RFM heatmap
  (Recency score × Frequency tier, fill = customer count).
- **RFM (Recency, Frequency, Monetary)** scores each customer on three dimensions:
  - **Recency**: days since last purchase → quintile score 1–5 (5 = most recent)
  - **Frequency**: F1 (1 order), F2 (2 orders), F3 (3+ orders)
  - **Monetary**: total lifetime spend → quintile score 1–5
- Reference date is **fixed at 2018-08-31** — not today's date. Recency scores
  reflect the state of the customer base at dataset cut-off.
- **Why 3-tier Frequency?** 96.9% of customers made exactly 1 purchase. Quintile
  scoring collapses all of them into one bin. The 3-tier approach creates meaningful
  separation between one-time, returning, and loyal buyers.
- Date Range and Product Category filters **do not apply** to RFM — a caption
  note explains this. State and Region filters apply.

**📋 Segment Playbook**
- Action cards per segment + segment size comparison bar.
- Each card shows customer count, average spend, average days since last purchase,
  and a concrete recommended marketing action.

| Segment | Profile | Priority action |
|---------|---------|-----------------|
| Champions | Recent, frequent, high spend | VIP rewards, referral incentives |
| Loyal | Regular repeat buyers | Loyalty programme, cross-sell bundles |
| Promising | Recent single-buyers (~37K) | Incentivise second purchase — highest ROI |
| At Risk | Previously active, going quiet | Win-back campaign, satisfaction survey |
| High Value Lost | Former high-spenders, now inactive | Aggressive reactivation, personal outreach |
| Hibernating | One-time buyers, long inactive | Low-cost email only; deprioritise paid spend |

- The Promising segment (~37K customers) is the highest-opportunity group.
  Converting 5% into repeat buyers would nearly double the current repeat base.

**⭐ Satisfaction & NPS**
- Review score distribution (bar) + monthly avg score trend + NPS stacked bar
  by month + NPS trend line.
- **NPS Proxy = (% promoters) − (% detractors)**. Scores 4–5 = promoter, 3 =
  passive, 1–2 = detractor. This is a proxy using review scores, not a formal
  NPS survey (which uses a 0–10 "recommend" scale). Interpret directionally.
- Distribution is bimodal: score 5 is ~57%, score 1 is ~12%. Customers either
  love the experience or have a poor one — few are neutral.

**⏱️ Delivery Impact**
- Avg review score by delay bin (colour-coded bar + satisfaction cliff annotation)
  + score distribution box plot + bin summary table.
- 5 delay bins: early, on-time, 1–3d late, 4–7d late, 7+d late.
- **Key finding**: Early delivery (4.30 avg score) outperforms on-time (4.11) —
  under-promising and over-delivering actively generates delight, not just
  avoids complaints.
- **Satisfaction cliff**: the score collapses from 3.29 (1–3d late) to 2.11
  (4–7d late) — a 1.19-point drop. Once an order is more than 3 days late,
  customer patience runs out sharply.
- **Actionable implication**: Setting conservative delivery estimates (so more
  orders arrive "early") is more effective than trying to speed up all deliveries.

---

## 8. Page 5: Glossary

### Purpose

Plain-language definitions of every business, analytical, and statistical term
used in the dashboard. Designed for business stakeholders who may not be
familiar with terms like Gini coefficient, Lorenz curve, or Simpson's Paradox.

### How to use

- Use the **search box** at the top to find a specific term — search matches
  both term names and definition text.
- Terms are grouped by category: Business Metrics, Customer Analytics,
  Data Visualisation, Economics & Competition, Statistics, Brazilian Market
  Context, Data Definitions.
- Each term expands in place — click the term name to read the definition.

---

## 9. Data Quality Notes

These are known properties of the source data that affect interpretation.
They do not represent errors in the dashboard.

1. **Single-purchase marketplace**: ~97% of customers buy once. RFM segments
   are dominated by Hibernating and Promising. This is structurally normal for
   marketplaces — customers discover sellers via Olist, then may transact directly
   on repeat purchases.

2. **Split payment approximation**: ~3% of orders use multiple payment methods
   (e.g., voucher + credit card). The dashboard shows only the primary (first)
   payment method. Voucher usage is slightly understated.

3. **Multi-item category approximation**: ~10% of orders contain items from
   multiple categories. `primary_product_category` in satisfaction data uses the
   highest-revenue item's category. The Product Category filter may not perfectly
   isolate these orders.

4. **Uncategorised products**: 610 products (~1.9%) have blank category labels
   in the source data. These appear as `"uncategorized"` in all category breakdowns.

5. **Delivery timestamp anomalies**: ~1,400 orders have carrier pickup recorded
   after customer delivery; ~23 have delivery before shipment. These are logistics
   recording errors in the source data — delivery metrics include them as-is.

6. **Seller performance outliers**: Sellers with very few orders may show extreme
   review scores or cancellation rates. The scatter plot bubble size (order count)
   helps identify statistically unreliable data points. Quality tier classification
   requires ≥10 orders.

7. **Instalment interest**: For multi-instalment credit card orders, the payment
   value recorded by Olist may include card-issuer interest. The dashboard uses
   `price + freight_value` (not payment value) as the revenue metric — this ensures
   consistency with the value of goods actually delivered.

8. **Data period**: The dataset covers Sep 2016 – Oct 2018, but only Jan 2017 –
   Aug 2018 represents a complete, reliable observation window. The first two months
   (Nov–Dec 2016) and last two months (Sep–Oct 2018) are partial and excluded from
   trend analyses.
