

Excellent — a glossary page is a great addition. Let me lay out the full narrative flow for all 5 pages (4 analysis + 1 glossary).

---

## Page Flow & Narrative Blueprint

---

### Page 1: `pages/1_Executive.py`

**Title:** Executive Overview
**Purpose:** Give leadership a 60-second pulse check on the business, then let them drill into revenue, payments, and fulfilment health.

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ SIDEBAR                                                      │
│ ├ Date Range (date picker)                                   │
│ ├ Product Category (multiselect)                             │
│ ├ Customer State (multiselect)                               │
│ └ Customer Region (multiselect)                              │
├─────────────────────────────────────────────────────────────┤
│ MAIN AREA                                                    │
│                                                              │
│  st.title("Executive Overview")                              │
│  st.caption("Olist marketplace · Jan 2017 – Aug 2018")       │
│                                                              │
│  ┌─── KPI ROW (6 columns) ──────────────────────────────┐   │
│  │ Total GMV │ Orders │  AOV  │ On-Time │  NPS  │Repeat │   │
│  │ R$15.8M   │ 98.4K  │ R$161│  93.4%  │ +63.6 │ 3.1%  │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─ TABS ────────────────────────────────────────────────┐   │
│  │ 📈 Sales Trend │ 💰 Revenue & AOV │ 💳 Payments │ 📦 │   │
│  └───────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**KPI cards sit above the tabs** — always visible regardless of which tab is active.

---

**Tab 1: 📈 Sales Trend**

*Purpose:* Show how the business grew over time.

| Chart | Type | Question it answers | Answer (narrative) |
|---|---|---|---|
| Monthly Gross Merchandise Value | Area chart | "Is the business growing?" | GMV grew ~103% from Jan 2017 to Aug 2018, with a Black Friday spike in Nov 2017 (annotated vertical line). Growth is volume-driven — AOV stayed flat. |
| Monthly Order Count | Bar chart (stacked below area) | "Is growth coming from more orders or bigger orders?" | Order volume mirrors GMV closely — confirming growth is customer-acquisition-driven, not basket-size-driven. |

*Narrative text:*
> Gross Merchandise Value (GMV) — the total value of goods sold — doubled in 20 months. The Black Friday 2017 spike (7,544 orders) was 2× the monthly average, but the underlying trend is steady organic growth.

---

**Tab 2: 💰 Revenue & AOV**

*Purpose:* Understand pricing dynamics and whether different payment methods affect order size.

| Chart | Type | Question it answers | Answer |
|---|---|---|---|
| Average Order Value by Month | Line chart with markers | "Are customers spending more per order over time?" | AOV (Average Order Value) is remarkably flat at ~R$160. Growth is purely from more customers, not larger baskets. |
| AOV by Payment Type | Horizontal bar | "Do payment methods influence how much people spend?" | Credit card orders average R$164 — higher than boleto (bank slip) at R$145. Installment capability likely enables larger purchases. |

*Narrative text:*
> Average Order Value (AOV) = total revenue ÷ number of orders. A flat AOV with rising GMV means Olist's growth engine is customer acquisition, not upselling. Credit card users spend ~13% more — likely because installments reduce perceived cost.

---

**Tab 3: 💳 Payment Mix**

*Purpose:* Understand how customers pay and the role of installment credit.

| Chart | Type | Question it answers | Answer |
|---|---|---|---|
| Payment Type Distribution | Donut chart | "How do customers prefer to pay?" | Credit card dominates at 77% of orders. Boleto (Brazilian bank slip) is second at ~18%. Vouchers and debit cards are niche. |
| Credit Card Installment Distribution | Histogram | "How many installments do credit card users choose?" | Median is 3 installments, but there's a long tail up to 10–12. This reveals that Brazilian "parcelamento" (installment culture) is core to the buying experience. |

*Narrative text:*
> Brazil has a unique "parcelamento" culture — splitting purchases into monthly installments on credit cards, often interest-free. 77% of Olist orders use credit cards, with a median of 3 installments. This isn't just a payment method — it's a demand enabler.

---

**Tab 4: 📦 Order Health**

*Purpose:* Check fulfilment reliability and flag any operational concerns.

| Chart | Type | Question it answers | Answer |
|---|---|---|---|
| Cancellation & Unavailability Rate Over Time | Line chart (two series) | "Are cancellations getting worse?" | Cancellation rate is consistently below 1% (~0.46% overall). No upward trend — operations are stable. |
| Overall Order Status Breakdown | Donut chart | "What happens to a typical order?" | 96.8% of orders are delivered successfully. The remaining ~3% are spread across shipped, invoiced, processing, and canceled — no single failure mode dominates. |

*Narrative text:*
> A cancellation rate below 0.5% is excellent for a marketplace. The donut shows that the vast majority of orders complete the full lifecycle. "Unavailable" status (seller couldn't fulfil) is near zero — suggesting good inventory signalling.

---

### Page 2: `pages/2_Products.py`

**Title:** Product Performance
**Purpose:** Identify which product categories drive revenue, how concentrated the portfolio is, and where logistics costs eat into margins.

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  st.title("Product Performance")                             │
│  st.caption("Revenue analysis across 74 product categories") │
│                                                              │
│  ┌─ TABS ────────────────────────────────────────────────┐   │
│  │ 🏆 Revenue Rankings │ 📊 Concentration │ 🚚 Freight  │   │
│  └───────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

All 4 sidebar filters apply.

---

**Tab 1: 🏆 Revenue Rankings**

*Purpose:* Which categories make the most money?

| Chart | Type | Question it answers | Answer |
|---|---|---|---|
| Top N Categories by Revenue | Horizontal bar (sorted desc) | "Which product categories generate the most revenue?" | Health & beauty, watches & gifts, and bed/bath/table are the top 3. Top 15 categories account for ~76% of total GMV. |
| Revenue Share Treemap | Treemap | "How does revenue distribute visually across categories?" | The treemap makes proportions intuitive — a few large blocks dominate, with a long tail of small categories. |

*Interactive element:* `st.slider("Top N categories", 5, 30, 15)` above the charts.

*Narrative text:*
> Revenue is concentrated in a handful of popular categories, but Olist carries 74 categories in total — a diversified portfolio. The top 15 alone generate over three-quarters of all sales.

---

**Tab 2: 📊 Category Concentration**

*Purpose:* Is the business dangerously dependent on a few categories?

| Chart | Type | Question it answers | Answer |
|---|---|---|---|
| Category Revenue Lorenz Curve | Area chart | "How unequal is revenue across categories?" | The Lorenz curve shows the bottom 50% of categories contribute only ~10% of revenue. The Gini coefficient is 0.71 — high inequality, but this is normal for retail. |
| Gini + HHI KPI cards | `st.metric()` cards | "Should we worry about over-dependence?" | Gini = 0.71 (high inequality — a few categories dominate). But HHI = 484 (competitive — no single category has monopoly power). High Gini + low HHI = healthy long-tail pattern. |

*Narrative text:*
> The Gini coefficient measures inequality (0 = all categories earn equally, 1 = one category earns everything). The Herfindahl-Hirschman Index (HHI) measures monopoly risk (above 2,500 = concentrated market). Olist has high inequality (Gini 0.71) but low monopoly risk (HHI 484) — meaning popular categories earn more, but no single category dominates. This is a healthy portfolio.

---

**Tab 3: 🚚 Freight Impact**

*Purpose:* Where do shipping costs eat into the value proposition?

| Chart | Type | Question it answers | Answer |
|---|---|---|---|
| Freight-to-Price Ratio by Category | Horizontal bar (top 15, sorted desc) | "Which categories have the highest relative shipping cost?" | Christmas supplies (37%), signalling & security (30%), and food/drink (30%) have the highest freight burden. Furniture categories (23–26%) are driven by weight and volume. |

*Narrative text:*
> Freight accounts for 14.2% of total GMV (R$2.2M). For bulky or heavy categories, shipping can exceed 30% of the item price — this affects customer perception of value and return likelihood. Categories with high freight ratios may benefit from subsidised shipping promotions or local fulfilment partnerships.

*Filter on chart:* Minimum 100 items threshold to avoid noisy small categories.

---

### Page 3: `pages/3_Geographic.py`

**Title:** Geographic Analysis
**Purpose:** Understand where customers are, how delivery performs across Brazil's vast geography, and which sellers drive the marketplace.

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  st.title("Geographic Analysis")                             │
│  st.caption("Brazil's 27 states across 5 macro-regions")     │
│                                                              │
│  ┌─ TABS ────────────────────────────────────────────────┐   │
│  │ 🗺️ Market Map │ 🚚 Delivery │ 👥 Sellers            │   │
│  └───────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

Sidebar filters: Date Range applies to delivery only. State and Region apply throughout. Product Category does not apply — `st.caption()` note in sidebar.

---

**Tab 1: 🗺️ Market Map**

*Purpose:* Where is Olist's customer base?

| Chart | Type | Question it answers | Answer |
|---|---|---|---|
| GMV by State (choropleth) | Choropleth map | "Which states generate the most revenue?" | São Paulo (SP) dominates at ~37% of GMV. Rio de Janeiro and Minas Gerais follow. The Southeast region accounts for the majority — reflecting Brazil's economic geography. |
| GMV by Region | Bar chart | "How do the 5 macro-regions compare?" | Southeast > South > Northeast > Central-West > North. The North region (Amazon basin) has minimal e-commerce penetration — likely infrastructure-driven. |

*Narrative text:*
> Brazil's 5 macro-regions have vastly different e-commerce adoption. The Southeast (São Paulo, Rio, Minas Gerais) is the economic heartland and dominates marketplace activity. The North and Central-West represent growth frontiers — low penetration today, but infrastructure investments could unlock demand.

---

**Tab 2: 🚚 Delivery Performance**

*Purpose:* Does delivery quality vary by region, and is Olist keeping its promises?

`st.caption("ℹ️ Date Range filter applies to this tab. Product Category filter is not applicable — delivery data is aggregated across all categories.")`

| Chart | Type | Question it answers | Answer |
|---|---|---|---|
| On-Time Delivery Rate by Region | Horizontal bar | "Which regions get their orders on time?" | South and Southeast lead at ~94–95%. North trails at ~88% — longer distances and fewer logistics hubs. |
| Average Delivery Delay: Region × Month | Heatmap | "Are delays seasonal or structural?" | The heatmap reveals that delays spike in specific months (e.g., post-Black Friday) and are consistently worse in the North. Grey cells indicate insufficient data (fewer than 30 orders). |
| Delivery Promise vs Reality | Grouped bar by region | "Is Olist over-promising or under-promising?" | Olist consistently promises more days than actual delivery takes — a conservative strategy that creates positive surprise. North customers get the most "buffer" (promise 30+ days, deliver in ~21). |

*Narrative text:*
> On-time rate = percentage of orders delivered by the estimated date. Olist uses conservative delivery estimates — actual delivery is almost always faster than promised. This "under-promise, over-deliver" strategy protects satisfaction scores but may discourage price-sensitive customers who see long estimated delivery times at checkout.

---

**Tab 3: 👥 Seller Analysis**

*Purpose:* How healthy is the seller ecosystem?

`st.caption("ℹ️ Full period data (Jan 2017 – Aug 2018). Date Range filter is not applied — seller metrics require the complete observation window.")`

| Chart | Type | Question it answers | Answer |
|---|---|---|---|
| Seller Performance Scatter | Scatter (x=GMV, y=avg review score, size=order count, color=region) | "Are high-volume sellers also high-quality?" | Most sellers cluster in the low-GMV, high-score quadrant. A few large sellers (top-right) maintain both volume and quality — these are marketplace anchors. |
| Seller Pareto Curve (GMV Concentration) | Line chart | "How concentrated is seller revenue?" | The top 20% of sellers generate ~82% of GMV. The Pareto curve shows this visually — the 80/20 reference lines make it intuitive. |
| Seller Quality Tiers | Treemap (tier × region × GMV) | "How many sellers are 'Premium' vs 'At Risk'?" | 767 Premium sellers (score ≥ 4.0, cancel ≤ 2%) drive R$9M in GMV. Only 37 sellers are At Risk. The marketplace is quality-healthy. |
| Seller Concentration Trend | Line chart | "Is revenue getting more or less concentrated over time?" | Monthly seller Gini coefficient edged from 0.63 to 0.66 over 20 months — a slow but steady increase. The marketplace is slightly consolidating toward top sellers. |

*Narrative text:*
> The Pareto curve (named after economist Vilfredo Pareto) shows what percentage of total revenue is generated by the top X% of sellers. A steeper curve = more concentration. The Gini coefficient (0 = all sellers earn equally, 1 = one seller earns everything) trending upward signals that top sellers are capturing a growing share — worth monitoring for marketplace health.

---

### Page 4: `pages/4_Customers.py`

**Title:** Customer Analysis
**Purpose:** Segment customers by behaviour, understand what drives satisfaction, and provide actionable recommendations.

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  st.title("Customer Analysis")                               │
│  st.caption("95,420 unique customers · 97,379 reviewed orders")│
│                                                              │
│  ┌─ TABS ────────────────────────────────────────────────┐   │
│  │ 🎯 RFM │ 📋 Playbook │ ⭐ Satisfaction │ ⏱️ Delivery │   │
│  └───────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

**Tab 1: 🎯 RFM Segments**

*Purpose:* Classify customers by purchase behaviour using RFM (Recency, Frequency, Monetary) analysis.

`st.caption("ℹ️ Date Range and Product Category filters are not applied — RFM segmentation uses a fixed reference date of 2018-08-31 and is computed across all categories.")`

| Chart | Type | Question it answers | Answer |
|---|---|---|---|
| Repeat Purchase Rate | `st.metric()` KPI | "How many customers come back?" | Only 3.1% of customers made more than one purchase. This is typical for marketplaces (customers are loyal to the platform, not individual sellers), but represents a growth opportunity. |
| Average R / F / M Scores by Segment | Grouped bar | "How do segments differ on each dimension?" | Champions have high scores across all three dimensions. Hibernating customers have low Recency (haven't bought recently) and F1 (single purchase). |
| RFM Heatmap: Recency × Frequency | Heatmap | "Where are most customers concentrated?" | The overwhelming majority sit in the bottom-left: R-score 1–3, F1 (single purchase). The top-right (high R, F3) is the Champions zone — tiny but high-value. |

*Narrative text:*
> RFM analysis scores each customer on three dimensions: **Recency** (how recently they purchased — lower days = higher score), **Frequency** (how often — F1 = once, F2 = twice, F3 = three or more), and **Monetary** (how much they spent). Combined, these scores assign customers to segments that guide marketing strategy. With 96.9% single-purchase customers, Olist's primary challenge is converting first-time buyers into repeat customers.

---

**Tab 2: 📋 Segment Playbook**

*Purpose:* Translate data segments into business actions.

`st.caption("ℹ️ Date Range and Product Category filters are not applied — same as RFM tab.")`

No charts — this tab is **action cards** with segment stats:

```
Row 1 (3 columns):
┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐
│ 🏆 Champions (131)   │ │ 💎 Loyal (1,750)     │ │ ✨ Promising (36,956)│
│                      │ │                      │ │                      │
│ Avg spend: R$892     │ │ Avg spend: R$511     │ │ Avg spend: R$139     │
│ Avg recency: 42 days │ │ Avg recency: 138 days│ │ Avg recency: 58 days │
│ 3+ orders each       │ │ 2–3 orders each      │ │ Single purchase      │
│                      │ │                      │ │                      │
│ ACTION: VIP rewards, │ │ ACTION: Loyalty      │ │ ACTION: Cross-sell   │
│ referral program,    │ │ program, exclusive   │ │ recommendations,     │
│ early access to new  │ │ previews, upsell     │ │ first-repeat-purchase│
│ categories           │ │ bundles              │ │ incentive (e.g. 10%  │
│                      │ │                      │ │ off second order)    │
└──────────────────────┘ └──────────────────────┘ └──────────────────────┘

Row 2 (3 columns):
┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐
│ ⚠️ At Risk (959)     │ │ 🔴 High Value        │ │ 💤 Hibernating       │
│                      │ │    Lost (72)         │ │    (55,552)          │
│ Avg spend: R$464     │ │ Avg spend: R$735     │ │ Avg spend: R$122     │
│ Avg recency: 412 days│ │ Avg recency: 498 days│ │ Avg recency: 373 days│
│ 2–3 orders, fading   │ │ 3+ orders, gone      │ │ Single purchase, old │
│                      │ │                      │ │                      │
│ ACTION: Win-back     │ │ ACTION: Aggressive   │ │ ACTION: Low-cost     │
│ email campaign,      │ │ reactivation offer,  │ │ re-engagement email, │
│ satisfaction survey, │ │ personal outreach,   │ │ deprioritise ad spend│
│ targeted discount    │ │ "we miss you" bundle │ │ — focus budget on    │
│                      │ │                      │ │ Promising segment    │
└──────────────────────┘ └──────────────────────┘ └──────────────────────┘
```

*Narrative text:*
> The largest opportunity is the **Promising** segment: 36,956 recent single-purchase customers. Converting even 5% of them into repeat buyers would nearly double the current repeat customer base. Meanwhile, **Hibernating** is the largest segment by count (55,552) but the lowest ROI for reactivation spend — these are old, low-value, single-purchase customers.

---

**Tab 3: ⭐ Satisfaction & NPS**

*Purpose:* Track customer happiness and the Net Promoter Score proxy.

`st.caption("ℹ️ Product Category filter is approximate — based on the highest-revenue item per order (~10% of orders have multiple categories).")`

| Chart | Type | Question it answers | Answer |
|---|---|---|---|
| Review Score Distribution | Bar chart (scores 1–5) | "Are customers happy?" | Heavily skewed positive: score 5 is the most common (~57%). But there's a notable "bimodal" pattern — score 1 is the second most common (~12%). Customers either love it or hate it; few are lukewarm. |
| Average Review Score by Month | Line chart | "Is satisfaction trending up or down?" | Relatively stable around 4.0–4.1. No major deterioration despite rapid growth — operations scaled well. |
| NPS Category by Month (100% Stacked) | 100% stacked bar | "What's the promoter/detractor split over time?" | The Net Promoter Score (NPS) proxy uses review scores: 4–5 = promoter, 3 = passive, 1–2 = detractor. Promoters consistently dominate at ~70%. |
| NPS Score Trend | Line chart | "Is the NPS score improving?" | NPS hovers around +60 to +70 — strong by marketplace standards. Minor dips correlate with Black Friday fulfilment pressure. |

*Narrative text:*
> Net Promoter Score (NPS) measures customer loyalty: % promoters minus % detractors. Scores above +50 are considered excellent. Olist's NPS proxy of +63.6 is strong, driven by the 5-star majority. The bimodal review distribution (many 5s and 1s, fewer 2–4s) suggests delivery experience is a binary: customers are delighted when early, angry when late.

---

**Tab 4: ⏱️ Delivery Impact**

*Purpose:* Prove that delivery speed is the #1 driver of customer satisfaction.

`st.caption("ℹ️ Product Category filter is approximate. Only delivered orders with tracking data are shown.")`

| Chart | Type | Question it answers | Answer |
|---|---|---|---|
| Average Review Score by Delay Bin | Bar chart (annotated) | "How much does late delivery hurt satisfaction?" | The "satisfaction cliff": early deliveries score 4.30, on-time 3.96, 1–3 days late 3.41, 4–7 days late 2.22, 7+ days late 1.69. Each bin drops dramatically. Annotated arrow shows the 4.30→1.69 range. |
| Review Score Distribution by Delay Bin | Box plot | "Is the drop consistent or driven by outliers?" | Box plots confirm it's structural, not outlier-driven. The median for 7+ days late is 1.0 (the minimum). The interquartile range narrows as delays increase — late customers uniformly give low scores. |

*Narrative text:*
> This is the single most actionable finding: **delivery delay is the strongest predictor of customer dissatisfaction**. The score drops from 4.30 (early delivery) to 1.69 (7+ days late) — a 2.6-point collapse. Early delivery doesn't just avoid complaints; it actively generates delight (score 4.30 vs on-time 3.96). Investing in logistics to shift orders from "on-time" to "early" has a measurable satisfaction payoff.

---

### Page 5: `pages/5_Glossary.py` (NEW)

**Title:** Glossary
**Purpose:** Define business and analytical terms used throughout the dashboard so non-technical stakeholders can self-serve understanding.

**No sidebar filters.** No charts. Clean reference page.

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  st.title("📖 Glossary")                                    │
│  st.caption("Terms and definitions used in this dashboard")  │
│                                                              │
│  Searchable: st.text_input("🔍 Search terms...")             │
│                                                              │
│  ┌─ Alphabetical / Categorised sections ─────────────────┐  │
│  │                                                        │  │
│  │  [expandable sections via st.expander]                 │  │
│  │                                                        │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Terms to include:**

| Term | Definition |
|---|---|
| **AOV (Average Order Value)** | Total revenue divided by number of orders. Measures typical basket size. |
| **Boleto** | A Brazilian bank slip payment method. The buyer prints or receives a barcode, then pays at any bank or lottery shop within the due date. No credit card required. |
| **Choropleth Map** | A map where regions are shaded by data values (e.g., darker = more revenue). Used to visualise geographic patterns. |
| **CR4 / CR10 (Concentration Ratio)** | The combined market share of the top 4 (or 10) entities. CR4 above 40% may indicate an oligopoly. |
| **Gini Coefficient** | A measure of inequality from 0 (perfect equality) to 1 (one entity has everything). In this dashboard: 0.71 for categories (concentrated but healthy), 0.78 for sellers (top sellers earn much more), 0.48 for customers (moderate). |
| **GMV (Gross Merchandise Value)** | The total value of goods sold through the marketplace, before deducting fees, refunds, or costs. Calculated as price + freight per item. |
| **HHI (Herfindahl-Hirschman Index)** | A measure of market concentration from 0 to 10,000. Below 1,500 = competitive market. 1,500–2,500 = moderately concentrated. Above 2,500 = highly concentrated. Used by the US Department of Justice for antitrust analysis. |
| **Lorenz Curve** | A graph showing cumulative share of value (y-axis) versus cumulative share of population (x-axis). A perfectly equal distribution follows the 45° diagonal. The further the curve bows below the diagonal, the more unequal the distribution. |
| **NPS (Net Promoter Score)** | A customer loyalty metric: % promoters minus % detractors. In this dashboard, we use review scores as a proxy: 4–5 = promoter, 3 = passive, 1–2 = detractor. Scores range from -100 to +100; above +50 is excellent. |
| **On-Time Rate** | Percentage of orders delivered on or before the estimated delivery date. Calculated as on-time orders ÷ total delivered orders. |
| **Parcelamento** | The Brazilian practice of splitting credit card purchases into monthly installments, often interest-free. A core feature of Brazilian e-commerce. |
| **Pareto Curve (80/20 Rule)** | A cumulative distribution showing what percentage of total output comes from the top percentage of contributors. Named after economist Vilfredo Pareto, who observed that ~80% of effects come from ~20% of causes. |
| **RFM (Recency, Frequency, Monetary)** | A customer segmentation framework. Recency = days since last purchase (lower = better). Frequency = number of orders (higher = better). Monetary = total spend (higher = better). Customers are scored on each dimension and grouped into actionable segments. |
| **Simpson's Paradox** | A statistical phenomenon where a trend that appears in subgroups reverses when groups are combined. In this dashboard, we avoid it by always computing weighted averages (e.g., on-time rate = total on-time orders ÷ total orders, not average of group rates). |
| **Treemap** | A chart where rectangles represent categories, sized by value. Larger rectangles = larger share. Useful for seeing proportions at a glance. |

---

### Updated `dashboard.py` Navigation

```python
pages = st.navigation([
    st.Page("pages/1_Executive.py",  title="Executive Overview"),
    st.Page("pages/2_Products.py",   title="Product Performance"),
    st.Page("pages/3_Geographic.py", title="Geographic Analysis"),
    st.Page("pages/4_Customers.py",  title="Customer Analysis"),
    st.Page("pages/5_Glossary.py",   title="Glossary"),
])
```

---

### Revision Summary vs Previous Plan

| Change | Reason |
|---|---|
| Added `pages/5_Glossary.py` | User requested — business audience needs accessible definitions |
| All pages use `st.tabs()` for horizontal tab layout | User requested — one focused narrative/story per tab |
| KPI row sits **above** tabs on Executive page | Always visible regardless of active tab |
| Expanded abbreviated terms at least once per tab | User requested — "AOV (Average Order Value)", "NPS (Net Promoter Score)", etc. |
| Added narrative text per tab | Each tab opens with 2–3 sentences of business-accessible explanation |
| Segment Playbook is its own tab (not merged with RFM) | Gives it the space it deserves as the standout decision-support feature |
| Freight Impact and Category Economics are separate tabs on Products | Each tells a distinct story |
| Glossary includes a search filter | `st.text_input` filters visible terms — useful with 15+ entries |
