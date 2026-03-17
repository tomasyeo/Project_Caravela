"""
pages/5_Glossary.py — Glossary of business and analytical terms.
No filters. No charts. Self-serve reference for business stakeholders.
"""
import streamlit as st

# ── Page header ───────────────────────────────────────────────────────────────
st.title("📖 Glossary")
st.caption(
    "Plain-language definitions of every business and analytical term used in this dashboard. "
    "Use the search box to find a specific term."
)

search = st.text_input("🔍 Search terms and definitions...", "").strip().lower()
st.divider()

# ── Term definitions ──────────────────────────────────────────────────────────
# Each entry: { "term": str, "category": str, "definition": str }
TERMS = [
    {
        "term": "AOV — Average Order Value",
        "category": "Business Metrics",
        "definition": (
            "**AOV = Total Revenue ÷ Number of Orders.**\n\n"
            "Measures the typical basket size. A flat AOV alongside rising GMV means growth "
            "is driven by more customers, not by customers spending more per order. "
            "Strategies to increase AOV include upselling, cross-selling, and bundle offers."
        ),
    },
    {
        "term": "Boleto",
        "category": "Brazilian Market Context",
        "definition": (
            "A Brazilian bank slip (boleto bancário) payment method. The buyer receives a barcode, "
            "then pays at any bank, lottery shop, or online banking portal within the due date. "
            "No credit card is required — making it accessible to Brazil's large unbanked population. "
            "Boleto accounts for ~18% of Olist orders."
        ),
    },
    {
        "term": "Choropleth Map",
        "category": "Data Visualisation",
        "definition": (
            "A map where geographic regions (states, countries) are shaded in proportion to a data "
            "value — darker shade typically means a higher value. "
            "Used in the Geographic Analysis page to visualise GMV by Brazilian state."
        ),
    },
    {
        "term": "CR4 / CR10 — Concentration Ratio",
        "category": "Economics & Competition",
        "definition": (
            "The combined market share of the top 4 (CR4) or top 10 (CR10) entities. "
            "Used by economists to measure how much of a market is controlled by a few players.\n\n"
            "- **CR4 < 40%** = competitive market\n"
            "- **CR4 40–60%** = moderately concentrated\n"
            "- **CR4 > 60%** = highly concentrated\n\n"
            "In this dashboard, CR4 is computed for product categories and seller GMV."
        ),
    },
    {
        "term": "Gini Coefficient",
        "category": "Economics & Competition",
        "definition": (
            "A measure of inequality on a scale from 0 to 1.\n\n"
            "- **0** = perfect equality (every entity earns the same amount)\n"
            "- **1** = perfect inequality (one entity earns everything)\n\n"
            "In this dashboard:\n"
            "- **Category revenue Gini = 0.71** — popular categories earn much more, but this is normal retail inequality\n"
            "- **Seller GMV Gini = 0.78** — top sellers earn far more than average, but no single seller dominates\n"
            "- **Customer spend Gini = 0.48** — spend is moderately distributed, no 'whale' customer dependency\n\n"
            "High Gini + low HHI is the healthy pattern for a long-tail marketplace."
        ),
    },
    {
        "term": "GMV — Gross Merchandise Value",
        "category": "Business Metrics",
        "definition": (
            "**GMV = sum of (price + freight_value) for every item sold.**\n\n"
            "The total value of goods sold through the marketplace, before deducting platform fees, "
            "seller costs, or returns. GMV is the primary growth metric for marketplaces. "
            "Total Olist GMV (Jan 2017 – Aug 2018): **R$15.8M ≈ USD 4.3M** at 2018 exchange rates."
        ),
    },
    {
        "term": "HHI — Herfindahl-Hirschman Index",
        "category": "Economics & Competition",
        "definition": (
            "A measure of market concentration, ranging from near **0** (perfectly competitive) "
            "to **10,000** (monopoly — one entity holds 100% market share).\n\n"
            "**US Department of Justice thresholds:**\n"
            "- **< 1,500** = competitive market\n"
            "- **1,500 – 2,500** = moderately concentrated\n"
            "- **> 2,500** = highly concentrated (antitrust concern)\n\n"
            "Olist category HHI = **484** (competitive). Seller HHI = **35** (competitive). "
            "Neither dimension has monopoly risk."
        ),
    },
    {
        "term": "Lorenz Curve",
        "category": "Data Visualisation",
        "definition": (
            "A graph showing the cumulative share of a value (y-axis) versus the cumulative "
            "share of the population sorted from smallest to largest (x-axis).\n\n"
            "- **Perfect equality** follows the 45° diagonal line (every category/seller earns equally)\n"
            "- **The further the curve bows below the diagonal**, the more unequal the distribution\n"
            "- **The Gini coefficient** is calculated from the area between the diagonal and the curve\n\n"
            "Used in the Product Performance page to visualise category revenue inequality."
        ),
    },
    {
        "term": "NPS — Net Promoter Score",
        "category": "Business Metrics",
        "definition": (
            "A customer loyalty metric: **NPS = % Promoters − % Detractors**.\n\n"
            "In this dashboard, a **proxy NPS** is derived from review scores:\n"
            "- **Score 4–5** = Promoter (would recommend)\n"
            "- **Score 3** = Passive (neutral)\n"
            "- **Score 1–2** = Detractor (dissatisfied)\n\n"
            "NPS ranges from **−100** (all detractors) to **+100** (all promoters).\n"
            "- **Above +50** = excellent\n"
            "- **Above +70** = world-class\n\n"
            "Olist's proxy NPS: **+63.6** — strong performance for a marketplace."
        ),
    },
    {
        "term": "On-Time Rate",
        "category": "Business Metrics",
        "definition": (
            "**On-Time Rate = On-Time Orders ÷ Total Delivered Orders.**\n\n"
            "The percentage of orders delivered on or before the estimated delivery date. "
            "Calculated using the actual delivery timestamp vs the promised date. "
            "Olist's overall on-time rate: **~93%**.\n\n"
            "⚠️ Important: computed as a weighted ratio (total on-time ÷ total orders), not "
            "as a simple average of group rates — which would give misleading results due to "
            "Simpson's Paradox."
        ),
    },
    {
        "term": "Parcelamento",
        "category": "Brazilian Market Context",
        "definition": (
            "The Brazilian practice of splitting credit card purchases into monthly instalments "
            "(parcelas), often **interest-free** for the buyer. This is a defining feature of "
            "Brazilian e-commerce — it allows customers to buy higher-value items by spreading "
            "the cost over time, without incurring extra charges.\n\n"
            "On Olist, the median number of credit card instalments is **3**, but some orders "
            "are split into up to 12 payments."
        ),
    },
    {
        "term": "Pareto Curve (80/20 Rule)",
        "category": "Data Visualisation",
        "definition": (
            "A cumulative distribution curve showing what percentage of total output is generated "
            "by the top X% of contributors. Named after economist **Vilfredo Pareto**, who "
            "observed that roughly 80% of effects come from 20% of causes.\n\n"
            "In this dashboard:\n"
            "- The **Seller Pareto Curve** shows that the top ~20% of sellers generate ~82% of GMV\n"
            "- Reference lines at x=20% and y=80% make the classic 80/20 threshold visible"
        ),
    },
    {
        "term": "RFM — Recency, Frequency, Monetary",
        "category": "Customer Analytics",
        "definition": (
            "A classic customer segmentation framework that scores each customer on three dimensions:\n\n"
            "- **Recency (R)**: Days since the customer's last purchase. Lower days = higher score (1–5). "
            "A customer who bought last week is more valuable than one who bought two years ago.\n"
            "- **Frequency (F)**: Number of purchases. In this dataset: F1 = 1 order, F2 = 2 orders, "
            "F3 = 3+ orders. (Quintile scoring collapses because 96.9% of customers bought only once.)\n"
            "- **Monetary (M)**: Total spend. Higher spend = higher score (1–5).\n\n"
            "Customers are assigned to one of 6 segments based on their R and F scores: "
            "Champions, Loyal, Promising, Hibernating, At Risk, High Value Lost. "
            "The M score is displayed as additional context but does not change segment assignment."
        ),
    },
    {
        "term": "Simpson's Paradox",
        "category": "Statistics",
        "definition": (
            "A statistical phenomenon where a trend that appears in several subgroups **reverses** "
            "or disappears when the subgroups are combined.\n\n"
            "**Classic example**: A hospital's overall survival rate looks worse than another hospital's, "
            "but is actually better in every individual disease category — because it treats more "
            "severe cases.\n\n"
            "**In this dashboard**: On-time delivery rates are always computed as "
            "**total on-time orders ÷ total orders** (weighted sum), never as a simple average of "
            "group rates. Averaging group rates without weighting by volume would give larger, "
            "higher-volume states disproportionate influence on the result."
        ),
    },
    {
        "term": "Treemap",
        "category": "Data Visualisation",
        "definition": (
            "A chart where nested rectangles represent hierarchical data. Each rectangle's **area** "
            "is proportional to its value — larger rectangle = larger share. "
            "Colour can encode a second variable (e.g., revenue or quality tier). "
            "Useful for seeing part-to-whole relationships across many categories at a glance. "
            "Used in Product Performance (category revenue) and Geographic Analysis (seller quality tiers)."
        ),
    },
    {
        "term": "Seller Quality Tiers",
        "category": "Customer Analytics",
        "definition": (
            "A classification of sellers into 4 operational tiers based on review score and "
            "cancellation rate (for sellers with ≥10 orders):\n\n"
            "| Tier | Review Score | Cancellation Rate |\n"
            "|------|-------------|-------------------|\n"
            "| **Premium** | ≥ 4.0 | ≤ 2% |\n"
            "| **Good** | ≥ 3.5 | ≤ 5% |\n"
            "| **Average** | ≥ 3.0 | ≤ 10% |\n"
            "| **At Risk** | < 3.0 or cancel > 10% | — |\n\n"
            "Premium sellers account for ~25% of active sellers but generate ~60% of GMV."
        ),
    },
    {
        "term": "total_sale_amount",
        "category": "Data Definitions",
        "definition": (
            "The revenue metric used throughout this dashboard: **total_sale_amount = price + freight_value**, "
            "computed at the order-item level. This is the amount the customer actually paid "
            "(including delivery). It differs from the payment value because:\n"
            "1. Some orders use discount vouchers\n"
            "2. Instalment credit card payments may include interest added by the card issuer\n\n"
            "Using price + freight ensures consistency with the value of goods actually delivered."
        ),
    },
    {
        "term": "primary_payment_type / primary_payment_installments",
        "category": "Data Definitions",
        "definition": (
            "For orders with split payments (multiple payment methods), only the payment with "
            "**payment_sequential = 1** is used as the 'primary' method. This is an approximation "
            "that affects ~3% of orders. For most analyses, this distinction is negligible."
        ),
    },
]

# ── Render terms ──────────────────────────────────────────────────────────────
# Group by category
categories = {}
for t in TERMS:
    cat = t["category"]
    if cat not in categories:
        categories[cat] = []
    categories[cat].append(t)

# Filter if search active
if search:
    filtered = {
        cat: [t for t in terms if search in t["term"].lower() or search in t["definition"].lower()]
        for cat, terms in categories.items()
    }
    filtered = {cat: terms for cat, terms in filtered.items() if terms}
else:
    filtered = categories

if not filtered:
    st.warning("No terms match your search. Try a shorter keyword.")
else:
    for cat, terms in sorted(filtered.items()):
        st.subheader(cat)
        for t in terms:
            with st.expander(t["term"]):
                st.markdown(t["definition"])
        st.markdown("")  # spacing between categories
