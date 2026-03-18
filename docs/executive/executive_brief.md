# Executive Brief: Brazilian E-Commerce Insights

## Project Caravela — Data Pipeline Findings

---

## 1. Executive Summary

Project Caravela analysed approximately 100,000 orders from a leading Brazilian e-commerce marketplace spanning January 2017 to August 2018. The pipeline ingested nine source datasets through an end-to-end ELT architecture and produced a star-schema data warehouse powering 11 analytical metrics. The headline findings are:

- **R$15.8 million in Gross Merchandise Value** (~USD 4.3M) across 98,353 orders, with GMV roughly doubling from H1 to H2 2017 (~103% growth) before decelerating to ~38% in H1 2018.
- **Customer retention is critically low** — only 3.1% of the 95,420 unique customers made a repeat purchase, and 58.2% of all customers are classified as Hibernating in our RFM segmentation. The marketplace operates as a single-transaction platform for the vast majority of buyers.
- **Delivery performance is strong overall at 91.9% on-time**, but the Northeast lags at 85.7% — a 7.2 percentage-point gap versus the South (92.9%) that directly correlates with lower customer satisfaction scores.
- **Revenue is geographically concentrated**: the Southeast accounts for 64.6% of GMV, with São Paulo alone contributing 37.4%. The North (2.6% of GMV) and Central-West (6.5%) represent significant untapped growth corridors.

---

## 2. Market Overview

Over the 20-month observation window (January 2017 – August 2018), the marketplace processed **98,353 distinct orders totalling R$15,786,204 in GMV**. The platform experienced rapid growth in its first year: GMV roughly doubled between the first and second halves of 2017 (~103% half-on-half growth), driven primarily by volume increases rather than rising order values.

**November 2017 was the peak month**, with 7,451 orders generating R$1,179,144 in GMV — a clear Black Friday effect. Notably, Average Order Value (AOV) actually **declined 6%** during this peak (from R$168 in October to R$158 in November), confirming that the surge was discount-driven and volume-led, not a shift toward higher-value purchases.

The **overall AOV remained remarkably stable at R$160.51** throughout the observation period. Growth in the first half of 2018 decelerated to approximately 38% — still healthy, but suggesting the platform was entering a maturation phase where incremental customer acquisition becomes costlier.

**Order fulfilment was highly reliable**: 97.8% of orders reached "delivered" status, with a cancellation rate of just **0.46%**. The remaining 1.7% comprised orders in processing (0.3%), shipped (1.1%), invoiced (0.3%), or approved (< 0.01%) states — expected pipeline statuses at any point in time. This low cancellation rate signals strong inventory management and seller reliability across the platform.

> [!NOTE]
> **Data caveat:** September 2018 (16 orders) and October 2018 (4 orders) are excluded from trend analyses as data-collection artefacts from the dataset boundary.

---

## 3. Customer Insights

The customer base of **95,420 unique buyers** reveals a marketplace with high acquisition volume but minimal retention — a pattern characteristic of third-party marketplace models where brand loyalty accrues to sellers rather than the platform.

### RFM Segmentation

Recency, Frequency, and Monetary (RFM) analysis — anchored to a reference date of 31 August 2018 — segments the customer base into six groups:

| Segment | Customers | Share | Description |
| :--- | ---: | ---: | :--- |
| **Hibernating** | 55,552 | 58.2% | Have not purchased recently and bought only once. The dominant segment. |
| **Promising** | 36,956 | 38.7% | Recent single-purchase buyers with potential for conversion. |
| **Loyal** | 1,750 | 1.8% | Moderate recency with 2+ purchases. |
| **At Risk** | 959 | 1.0% | Formerly active multi-purchase buyers whose recency has dropped. |
| **Champions** | 131 | 0.1% | Recent, frequent, high-value buyers. The crown jewels. |
| **High Value Lost** | 72 | 0.1% | Previously high-frequency buyers who have churned. |

The **repeat purchase rate stands at just 3.1%** (2,912 of 95,420 customers). This is structurally low but not unusual for open marketplaces where customers search by product rather than returning to a specific storefront. It does, however, mean that **sustainable growth depends almost entirely on new customer acquisition** — a model with increasing cost pressure as the addressable market saturates.

### Customer Satisfaction (NPS Proxy)

Using review scores as an NPS proxy (scores 4–5 = promoter, 3 = passive, 1–2 = detractor), the platform achieves an **NPS of 63.6** — a strong result. Promoters represent 77.7% of reviewed orders, while detractors account for 14.1%.

However, the **delay-to-satisfaction correlation is dramatic**:

| Delivery Timing | Avg Review Score | Score Change |
| :--- | ---: | ---: |
| Early (before estimate) | 4.30 | — |
| On-time | 3.89 | −0.41 |
| 1–3 days late | 3.29 | −0.60 |
| **4–7 days late** | **2.11** | **−1.19** |
| 7+ days late | 1.69 | −0.42 |

The sharpest single cliff occurs between 1–3 days late and 4–7 days late — a **1.19-point plunge** that marks the threshold where customer patience breaks. This finding directly connects delivery operations to marketplace reputation.

---

## 4. Product and Revenue Performance

### Top Revenue Categories

Revenue concentration follows a long-tail distribution across 74 product categories, with the **top 15 categories accounting for 76.4% of total GMV**. The leading categories are:

| Rank | Category | GMV Share |
| ---: | :--- | ---: |
| 1 | **Health & Beauty** | 9.1% |
| 2 | **Watches & Gifts** | 8.2% |
| 3 | **Bed, Bath & Table** | 7.9% |

The category revenue Gini coefficient of **0.71** confirms high inequality, but the Herfindahl-Hirschman Index (HHI) of **484** indicates a competitive market with no single category dominating — a healthy long-tail that reduces concentration risk.

### Payment Methods

| Payment Type | Orders | Share | AOV |
| :--- | ---: | ---: | ---: |
| **Credit Card** | 75,716 | 77.0% | R$152 |
| **Boleto Bancário** | 19,555 | 19.9% | R$127 |
| **Voucher** | 1,534 | 1.6% | — |
| **Debit Card** | 1,469 | 1.5% | — |

Credit card users pay in a **median of 3 instalments** (mean 3.5), with 7.3% opting for 10 or more instalments — reflecting Brazil's deeply embedded instalment culture. Credit card orders carry a **20% higher AOV than boleto**, suggesting that instalment access enables larger basket sizes.

Freight costs represent **14.2% of GMV** (R$2.24 million), with categories like Christmas Supplies (36.7% freight-to-price ratio) and Food & Drink (29.7%) disproportionately affected — a factor in regional delivery economics.

---

## 5. Delivery and Operational Excellence

The marketplace achieves an **overall on-time delivery rate of 91.9%** across all delivered orders, but regional performance varies meaningfully:

| Region | On-Time Rate | Avg Promised Days | Avg Actual Days | Buffer |
| :--- | ---: | ---: | ---: | ---: |
| **South** | **92.9%** | 26.8 | 14.0 | 12.8d |
| **Southeast** | **92.5%** | 24.5 | 12.9 | 11.6d |
| **Central-West** | **92.0%** | 27.8 | 15.5 | 12.4d |
| **North** | **90.2%** | 41.1 | 23.6 | 17.5d |
| **Northeast** | **85.7%** | 31.7 | 20.6 | 11.1d |

The **Northeast underperforms by 7.2 percentage points** versus the South despite receiving generous delivery promises (31.7 days promised vs. 26.8 in the South). Actual transit times in the Northeast average 20.6 days — nearly double the Southeast's 12.9 days — reflecting the logistical challenges of serving Brazil's northern regions from a seller base concentrated in the Southeast.

Critically, the platform consistently **over-promises delivery windows** across all regions — actual delivery averages 11–17 days fewer than promised. While this creates positive surprise for most customers (90.2% of delivered orders arrive early), it also means the quoted delivery time may deter price-sensitive buyers from completing checkout.

The direct link between delivery delays and review scores (detailed in [Section 3](#3-customer-insights)) means that the Northeast's lower on-time rate is not merely an operational metric — it is a **customer satisfaction and retention liability** in the region that most needs growth investment.

---

## 6. Geographic and Seller Landscape

### Regional Revenue Distribution

The marketplace exhibits pronounced geographic concentration aligned with Brazil's economic geography:

| Region | GMV (R$) | Share |
| :--- | ---: | ---: |
| **Southeast** | 10,196,414 | **64.6%** |
| **South** | 2,286,868 | **14.5%** |
| **Northeast** | 1,873,522 | **11.9%** |
| **Central-West** | 1,020,339 | **6.5%** |
| **North** | 409,061 | **2.6%** |

São Paulo alone contributes **37.4% of total GMV**. The North and Central-West combined represent only 9.1% of revenue — a significant penetration gap given that these regions contain over 20% of Brazil's population.

### Seller Performance

The platform hosts **3,068 active sellers** with a pronounced Pareto distribution: the **top 18.3% of sellers generate 80% of GMV**. The seller Gini coefficient of **0.78** reflects high inequality, but CR4 (top 4 sellers) at just **6.1%** and HHI of **35** confirm that no individual seller dominates — the inequality is distributed across a long tail of small sellers, not driven by monopolistic concentration.

Seller quality tiering (among 1,268 sellers with 10+ orders):

| Tier | Sellers | GMV (R$) | Avg Score | Cancellation Rate |
| :--- | ---: | ---: | ---: | ---: |
| **Premium** | 767 | 9,000,701 | 4.33 | 0.0% |
| **Good** | 364 | 4,295,179 | 3.85 | 1.0% |
| **Average** | 100 | 811,287 | 3.44 | 2.0% |
| **At Risk** | 37 | 247,851 | 2.74 | 5.4% |

The platform-wide average seller review score is **3.98 out of 5**. The 37 "At Risk" sellers account for just R$248K — making targeted quality intervention both feasible and high-impact.

---

## 7. Key Risks and Mitigations

### Technical Risk: Historical Data Limitations

> **Risk:** This analysis is based on a historical dataset covering 2016–2018. Consumer behaviour, logistics infrastructure, payment preferences, and competitive dynamics in Brazilian e-commerce have evolved significantly since this period. Models and thresholds calibrated on this data may not generalise to current market conditions.
>
> **Mitigation:** The data pipeline is designed for repeatability — refreshing the source data and re-running the pipeline would regenerate all metrics with current figures. Key metric drift (AOV, on-time rate, NPS, repeat purchase rate) should be monitored quarterly against the baselines established here.

### Business Risk: Single-Purchase Customer Dominance

> **Risk:** With 96.9% of customers making only one purchase, customer acquisition cost (CAC) is amortised over a single transaction. As the addressable market in high-penetration regions (Southeast, South) saturates, acquiring new customers becomes progressively more expensive — threatening unit economics.
>
> **Mitigation:** Invest in post-purchase engagement (personalised follow-ups, category-based recommendations, loyalty programme) targeting the 36,956 "Promising" segment customers who purchased recently but only once. Even a modest improvement in repeat rate from 3.1% to 5% would materially reduce CAC dependency.

### Business Risk: Regional Delivery Disparity

> **Risk:** The Northeast's 85.7% on-time rate — combined with the demonstrated 2.61-point review score drop for late deliveries — creates a compounding disadvantage: poor delivery experience reduces satisfaction, which suppresses organic growth in a region that already contributes only 11.9% of GMV.
>
> **Mitigation:** Establish regional carrier partnerships and distribution centres in the Northeast and North. Set region-specific on-time SLAs and monitor against delivery promise accuracy.

---

## 8. Strategic Recommendations

### 1. Launch a Customer Retention Programme Targeting the "Promising" Segment

- **Evidence:** 38.7% of customers (36,956) are classified as Promising — recent single-purchase buyers. The overall repeat rate is just 3.1%, and cohort analysis shows it is declining (5.3% for H1 2017 cohorts vs. 2.6% for early 2018 cohorts).
- **Action:** Deploy personalised re-engagement campaigns (email, push notification) within 30 days of first purchase, emphasising complementary product categories. Measure success via repeat purchase rate lift by cohort.

### 2. Invest in North and Northeast Delivery Infrastructure

- **Evidence:** The Northeast on-time rate is 85.7% versus 92.9% in the South, and delayed orders score 1.69 vs. 4.30 for early deliveries. The North averages 23.6 actual transit days.
- **Action:** Partner with regional logistics providers; establish fulfilment hubs in Recife and Manaus. Set region-specific on-time SLAs with quarterly review cycles.

### 3. Optimise Delivery Promise Accuracy to Drive Conversion

- **Evidence:** All regions show an 11–17 day buffer between promised and actual delivery. While this creates positive surprise post-purchase, overly conservative estimates may reduce checkout conversion — especially for time-sensitive categories.
- **Action:** A/B test tighter delivery promises in the Southeast (where actual averages 12.9 days against a 24.5-day promise) and measure conversion rate impact.

### 4. Implement a Seller Quality Intervention Programme

- **Evidence:** 37 "At Risk" sellers (avg score 2.74, 5.4% cancellation rate) generate R$248K in GMV. Poor seller performance directly degrades platform NPS.
- **Action:** Issue performance warnings with a 90-day improvement window. Provide onboarding support (packaging, shipping best practices). Delist persistently underperforming sellers to protect platform reputation.

### 5. Capitalise on Instalment-Driven AOV Uplift

- **Evidence:** Credit card AOV (R$152) exceeds boleto AOV (R$127) by 20%, and 7.3% of credit card users choose 10+ instalments. Instalment access enables larger baskets.
- **Action:** Promote instalment options more prominently at checkout for boleto-inclined customers. Explore partnerships with fintechs to offer instalment plans on debit and boleto payments.

---

## 9. Appendix: Metric Definitions

| Metric | Definition |
| :--- | :--- |
| **GMV** | Total revenue: sum of `price + freight_value` across all order items. R$ with USD at R$3.65/USD (2018 avg). |
| **AOV** | GMV ÷ distinct order count (R$160.51 overall). |
| **On-Time Rate** | % of delivered orders where actual delivery date ≤ estimated delivery date. Order-level distinct count. |
| **NPS Proxy** | Scores 4–5 = promoter, 3 = passive, 1–2 = detractor. NPS = % promoters − % detractors. |
| **RFM Segments** | Recency (quintile 1–5), Frequency (3-tier: F1/F2/F3), Monetary (quintile 1–5). Assigned by R × F only. |
| **Repeat Purchase Rate** | % of unique customers with >1 order. Reference date: 31 Aug 2018. |
| **Observation Window** | Jan 2017 – Aug 2018 (20 months). Sep/Oct 2018 excluded. 2016 retained for RFM recency only. |
