"""
pages/2_Products.py — Product Performance
Revenue rankings, category concentration, and freight cost analysis.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard_utils import (
    load_sales_orders, init_filters, render_sidebar_filters,
    apply_filters,
)
from notebooks.utils import lorenz_curve, gini_coefficient, hhi as calc_hhi

# ── Bootstrap ─────────────────────────────────────────────────────────────────
init_filters()

try:
    so = load_sales_orders()
except Exception as e:
    st.error(f"Could not load data files: {e}")
    st.stop()

render_sidebar_filters(sales_df=so)
so_f = apply_filters(so)

if so_f.empty:
    st.warning("No data matches the current filters. Please adjust your selection.")
    st.stop()

# ── Page header ───────────────────────────────────────────────────────────────
st.title("🏷️ Product Performance")
st.caption(
    f"Analysing {so_f['product_category_name_english'].nunique()} product categories "
    f"across {so_f['order_id'].nunique():,} orders"
)

tab1, tab2, tab3 = st.tabs([
    "🏆 Revenue Rankings", "📊 Category Concentration", "🚚 Freight Impact"
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — REVENUE RANKINGS
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    st.markdown(
        "**Which categories make the most money?** Revenue is concentrated in a handful of "
        "popular categories — but Olist carries 74 in total. Use the slider to see more or "
        "fewer categories. The bar chart ranks by revenue; the treemap shows relative proportions "
        "visually. The top 15 categories typically account for ~76% of total GMV."
    )

    top_n = st.slider("Top N categories", min_value=5, max_value=30, value=15, step=5)

    cat_rev = (
        so_f.groupby("product_category_name_english")["total_sale_amount"]
        .sum()
        .sort_values(ascending=False)
        .head(top_n)
        .reset_index()
        .rename(columns={
            "total_sale_amount": "Revenue (R$)",
            "product_category_name_english": "Category",
        })
    )

    col_l, col_r = st.columns(2)
    with col_l:
        fig_bar = px.bar(
            cat_rev.sort_values("Revenue (R$)"),
            x="Revenue (R$)", y="Category",
            orientation="h",
            title=f"Top {top_n} Categories by Revenue",
            template="plotly_white", text_auto=",.0f",
            color_discrete_sequence=["#e67e22"],
        )
        fig_bar.update_layout(height=max(350, top_n * 24), showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_r:
        fig_tree = px.treemap(
            cat_rev, path=["Category"], values="Revenue (R$)",
            title=f"Revenue Share — Top {top_n} Categories",
            color="Revenue (R$)", color_continuous_scale="YlOrRd",
        )
        fig_tree.update_layout(height=max(350, top_n * 24))
        st.plotly_chart(fig_tree, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — CATEGORY CONCENTRATION
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown(
        "**Is the business dangerously dependent on a few categories?** "
        "The **Lorenz curve** visualises inequality: a perfectly equal distribution follows the "
        "45° diagonal; the more the red curve bows downward, the more unequal the distribution. "
        "The **Gini coefficient** (0 = all categories earn equally, 1 = one category earns "
        "everything) summarises this in one number. The **HHI (Herfindahl-Hirschman Index)** "
        "measures monopoly risk — below 1,500 means no category dominates. "
        "High Gini + low HHI is the healthy long-tail pattern for a marketplace."
    )

    all_cat_rev = (
        so_f.groupby("product_category_name_english")["total_sale_amount"]
        .sum().values
    )
    n_cats = len(all_cat_rev)

    if n_cats >= 2:
        gini    = gini_coefficient(all_cat_rev)
        hhi_val = calc_hhi(all_cat_rev)
        sorted_rev = np.sort(all_cat_rev)[::-1]
        cr4  = sorted_rev[:4].sum()  / all_cat_rev.sum() if n_cats >= 4  else float("nan")
        cr10 = sorted_rev[:10].sum() / all_cat_rev.sum() if n_cats >= 10 else float("nan")

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Gini Coefficient", f"{gini:.2f}",
                  help="0 = perfectly equal; 1 = one category earns everything")
        k2.metric("HHI", f"{hhi_val:,.0f}",
                  help="<1,500 competitive · 1,500–2,500 moderate · >2,500 concentrated")
        k3.metric("CR4 (top-4 share)",  f"{cr4:.1%}"  if not np.isnan(cr4)  else "N/A",
                  help="Combined revenue share of the 4 largest categories")
        k4.metric("CR10 (top-10 share)", f"{cr10:.1%}" if not np.isnan(cr10) else "N/A",
                  help="Combined revenue share of the 10 largest categories")

        if hhi_val < 1500:
            st.info(
                f"Portfolio health: **diversified** — Gini {gini:.2f} indicates revenue "
                f"inequality (popular categories earn more), but HHI {hhi_val:,.0f} confirms "
                f"no single category holds monopoly power."
            )
        else:
            st.warning(
                f"Portfolio health: **concentrated** — HHI {hhi_val:,.0f} indicates significant "
                f"dependence on top categories. Consider diversification."
            )

        x_l, y_l = lorenz_curve(all_cat_rev)
        fig_lorenz = go.Figure()
        fig_lorenz.add_trace(go.Scatter(
            x=[0, 100], y=[0, 100],
            mode="lines", name="Perfect Equality",
            line=dict(color="#bdc3c7", dash="dash", width=1.5),
        ))
        fig_lorenz.add_trace(go.Scatter(
            x=x_l * 100, y=y_l * 100,
            mode="lines", name=f"Actual (Gini = {gini:.2f})",
            line=dict(color="#e74c3c", width=2.5),
            fill="tonexty", fillcolor="rgba(231,76,60,0.12)",
            hovertemplate="Bottom %{x:.0f}% of categories earn %{y:.1f}% of revenue<extra></extra>",
        ))
        fig_lorenz.update_layout(
            title="Category Revenue Lorenz Curve",
            xaxis_title="Cumulative Share of Categories (%)",
            yaxis_title="Cumulative Share of Revenue (%)",
            template="plotly_white", hovermode="x unified", height=420,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig_lorenz, use_container_width=True)

    else:
        st.info("Select more categories to compute concentration metrics.")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — FREIGHT IMPACT
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown(
        "**Where do shipping costs eat into the value proposition?** "
        "Freight accounts for ~14% of total GMV (R$2.2M). For bulky or heavy categories, "
        "shipping can exceed 30% of the item price — this directly affects the customer's "
        "perceived value and likelihood to return. Categories with high freight ratios "
        "are candidates for subsidised shipping or regional fulfilment partnerships."
    )
    st.caption("ℹ️ Categories with fewer than 100 items are excluded to avoid small-sample noise.")

    freight_cat = (
        so_f.groupby("product_category_name_english")
        .agg(
            freight=("freight_value", "sum"),
            price=("price", "sum"),
            items=("order_id", "count"),
        )
        .reset_index()
    )
    freight_cat = freight_cat[freight_cat["items"] >= 100].copy()

    if freight_cat.empty:
        st.info("Not enough data for freight analysis with current filters.")
    else:
        freight_cat["Freight / Price (%)"] = 100 * freight_cat["freight"] / freight_cat["price"]
        freight_cat = (
            freight_cat.sort_values("Freight / Price (%)", ascending=False)
            .head(15)
            .sort_values("Freight / Price (%)")
            .rename(columns={"product_category_name_english": "Category"})
        )

        total_freight = so_f["freight_value"].sum()
        total_price   = so_f["price"].sum()

        k1, k2 = st.columns(2)
        k1.metric("Total Freight Cost", f"R${total_freight:,.0f}")
        k2.metric("Freight as % of Item Price",
                  f"{100*total_freight/total_price:.1f}%" if total_price > 0 else "N/A")

        fig_freight = px.bar(
            freight_cat,
            x="Freight / Price (%)", y="Category",
            orientation="h",
            title="Top 15 Categories by Freight-to-Price Ratio (min 100 items)",
            template="plotly_white", text_auto=".1f",
            color="Freight / Price (%)",
            color_continuous_scale="RdYlGn_r",
        )
        fig_freight.update_layout(
            height=500, showlegend=False, coloraxis_showscale=False,
        )
        st.plotly_chart(fig_freight, use_container_width=True)
