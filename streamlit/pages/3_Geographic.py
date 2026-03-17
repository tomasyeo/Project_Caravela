"""
pages/3_Geographic.py — Geographic Analysis
Market map, delivery performance, and seller ecosystem health.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard_utils import (
    load_sales_orders, load_geo_delivery, load_seller_performance,
    load_concentration_metrics, load_geojson,
    init_filters, render_sidebar_filters,
    apply_filters, apply_geo_filters, apply_seller_filters, make_period,
)
from notebooks.utils import REGION_COLOURS

# ── Bootstrap ─────────────────────────────────────────────────────────────────
init_filters()

try:
    so  = load_sales_orders()
    geo = load_geo_delivery()
    sp  = load_seller_performance()
    cm  = load_concentration_metrics()
    brazil_geo = load_geojson()
except Exception as e:
    st.error(f"Could not load data files: {e}")
    st.stop()

render_sidebar_filters(sales_df=so)
st.caption("ℹ️ Product Category filter does not apply to this page — delivery and seller data are aggregated across all categories.")

# Apply filters
so_f  = apply_filters(so, cat_col="product_category_name_english")
geo_f = apply_geo_filters(geo)
sp_f  = apply_seller_filters(sp)

# ── Page header ───────────────────────────────────────────────────────────────
st.title("🗺️ Geographic Analysis")
st.caption("Brazil's 27 states across 5 macro-regions: North, Northeast, Central-West, Southeast, South")

tab1, tab2, tab3 = st.tabs([
    "🗺️ Market Map", "🚚 Delivery Performance", "👥 Seller Analysis"
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — MARKET MAP
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    st.markdown(
        "**Where is Olist's customer base?** Brazil's 5 macro-regions have vastly different "
        "e-commerce adoption rates. The Southeast (São Paulo, Rio, Minas Gerais) is the economic "
        "heartland. The North and Central-West represent growth frontiers — low penetration today, "
        "but infrastructure investment could unlock significant demand."
    )

    if so_f.empty:
        st.warning("No sales data matches the current filters.")
    else:
        state_gmv = (
            so_f.groupby("customer_state")["total_sale_amount"]
            .sum().reset_index()
            .rename(columns={"total_sale_amount": "GMV (R$)"})
        )
        region_gmv = (
            so_f.groupby("customer_region")["total_sale_amount"]
            .sum().reset_index()
            .rename(columns={"total_sale_amount": "GMV (R$)", "customer_region": "Region"})
            .sort_values("GMV (R$)", ascending=False)
        )

        # Headline KPIs for this tab
        top_state  = state_gmv.nlargest(1, "GMV (R$)").iloc[0]
        top_region = region_gmv.iloc[0]
        k1, k2, k3 = st.columns(3)
        k1.metric("Top State",  top_state["customer_state"],
                  f"R${top_state['GMV (R$)']:,.0f}")
        k2.metric("Top Region", top_region["Region"],
                  f"R${top_region['GMV (R$)']:,.0f}")
        k3.metric("States with Orders", len(state_gmv))

        col_l, col_r = st.columns([3, 2])
        with col_l:
            fig_map = px.choropleth(
                state_gmv,
                geojson=brazil_geo,
                locations="customer_state",
                featureidkey="properties.sigla",
                color="GMV (R$)",
                color_continuous_scale="YlOrRd",
                title="GMV by State",
                labels={"GMV (R$)": "GMV (R$)", "customer_state": "State"},
            )
            fig_map.update_geos(fitbounds="locations", visible=False)
            fig_map.update_layout(
                height=480, margin={"r": 0, "t": 40, "l": 0, "b": 0},
                coloraxis_colorbar=dict(title="GMV (R$)"),
            )
            st.plotly_chart(fig_map, width="stretch")

        with col_r:
            fig_region = px.bar(
                region_gmv, x="GMV (R$)", y="Region",
                orientation="h",
                title="GMV by Region",
                template="plotly_white", text_auto=",.0f",
                color="Region", color_discrete_map=REGION_COLOURS,
            )
            fig_region.update_layout(height=480, showlegend=False)
            st.plotly_chart(fig_region, width="stretch")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — DELIVERY PERFORMANCE
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown(
        "**Does delivery quality vary by region, and is Olist keeping its promises?** "
        "On-time rate = % of orders delivered on or before the estimated date. "
        "The delay heatmap shows which region-month combinations have the worst delays. "
        "Olist consistently delivers earlier than promised — a 'conservative estimate' strategy "
        "that turns late anxiety into pleasant surprise."
    )
    st.caption("ℹ️ Date Range filter applies to this tab. Product Category filter is not applicable.")

    if geo_f.empty:
        st.warning("No delivery data matches the current filters.")
    else:
        geo_f = geo_f.copy()
        geo_f["period"] = make_period(geo_f)

        # On-time rate by region (weighted — Simpson's Paradox protection)
        region_del = (
            geo_f.groupby("region")
            .agg(total=("total_orders", "sum"), on_time=("on_time_orders", "sum"))
            .reset_index()
        )
        region_del = region_del[region_del["total"] >= 30].copy()
        region_del["on_time_rate"] = region_del["on_time"] / region_del["total"]
        region_del = region_del.sort_values("on_time_rate")

        # Weighted avg delay by region (for the "ahead/behind" bar)
        region_delay = (
            geo_f.groupby("region")
            .apply(lambda g: pd.Series({
                "total": g["total_orders"].sum(),
                "avg_delay": (
                    (g["avg_delay_days"] * g["total_orders"]).sum() / g["total_orders"].sum()
                    if g["total_orders"].sum() > 0 else float("nan")
                ),
            }), include_groups=False)
            .reset_index()
        )
        region_delay = region_delay[region_delay["total"] >= 30].copy()
        region_delay["schedule_status"] = region_delay["avg_delay"].apply(
            lambda x: "Ahead of schedule" if x < 0 else "Behind schedule"
        )

        col_l, col_r = st.columns(2)
        with col_l:
            if not region_del.empty:
                fig_ontime = px.bar(
                    region_del, x="on_time_rate", y="region",
                    orientation="h",
                    title="On-Time Delivery Rate by Region",
                    labels={"on_time_rate": "On-Time Rate", "region": "Region"},
                    template="plotly_white", text_auto=".1%",
                    color="region", color_discrete_map=REGION_COLOURS,
                )
                fig_ontime.update_xaxes(tickformat=".0%")
                fig_ontime.update_layout(height=360, showlegend=False)
                st.plotly_chart(fig_ontime, width="stretch")

        with col_r:
            if not region_delay.empty:
                fig_delay_bar = px.bar(
                    region_delay.sort_values("avg_delay"),
                    x="avg_delay", y="region",
                    orientation="h",
                    title="Days Ahead (−) / Behind (+) Schedule by Region",
                    labels={"avg_delay": "Avg Days vs Promised", "region": "Region"},
                    template="plotly_white", text_auto=".1f",
                    color="schedule_status",
                    color_discrete_map={
                        "Ahead of schedule": "#27ae60",
                        "Behind schedule": "#e74c3c",
                    },
                )
                fig_delay_bar.add_vline(
                    x=0, line_dash="dash", line_color="gray", line_width=1,
                )
                fig_delay_bar.update_layout(height=360, showlegend=True,
                                            legend=dict(orientation="h", y=-0.2))
                st.plotly_chart(fig_delay_bar, width="stretch")

        # Delivery heatmap: region × month (weighted avg delay)
        def _weighted_delay(g):
            total = g["total_orders"].sum()
            return (g["avg_delay_days"] * g["total_orders"]).sum() / total if total > 0 else float("nan")

        region_month = (
            geo_f.groupby(["region", "period"])
            .apply(lambda g: pd.Series({
                "total": g["total_orders"].sum(),
                "delay": _weighted_delay(g),
            }), include_groups=False)
            .reset_index()
        )
        region_month.loc[region_month["total"] < 30, "delay"] = float("nan")
        heat_pivot = region_month.pivot(index="region", columns="period", values="delay")

        if not heat_pivot.empty and not heat_pivot.isnull().all().all():
            fig_heat = px.imshow(
                heat_pivot,
                text_auto=".1f",
                labels=dict(x="Month", y="Region", color="Avg Delay (days)"),
                title="Average Delivery Delay by Region × Month (grey = fewer than 30 orders)",
                color_continuous_scale="RdYlGn_r",
                aspect="auto",
            )
            fig_heat.update_layout(height=320)
            st.plotly_chart(fig_heat, width="stretch")
        else:
            st.info("Not enough data for the delivery heatmap with current filters.")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — SELLER ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.caption("ℹ️ Seller data covers the full period (Jan 2017 – Aug 2018). Date Range filter is not applied — seller metrics require the complete observation window to be meaningful.")
    st.caption("ℹ️ Customer State / Region filters apply to seller home state — they show sellers based in that location, not sellers who sold to customers there.")

    st.markdown(
        "**How healthy is the seller ecosystem?** The scatter plot shows each seller's "
        "revenue vs. satisfaction score. The Pareto curve reveals how concentrated GMV is "
        "among top sellers. The quality tier treemap classifies sellers by operational "
        "excellence — most revenue comes from Premium and Good tier sellers."
    )

    if sp_f.empty:
        st.warning("No seller data matches the current filters.")
        st.stop()

    # ── Seller quality tier assignment ────────────────────────────────────────
    def _quality_tier(row):
        score  = row["avg_review_score"]
        cancel = row["cancellation_rate"]
        if pd.isna(score):
            return "Unrated"
        if score >= 4.0 and cancel <= 0.02:
            return "Premium"
        if score >= 3.5 and cancel <= 0.05:
            return "Good"
        if score >= 3.0 and cancel <= 0.10:
            return "Average"
        return "At Risk"

    sp_f = sp_f.copy()
    sp_f["quality_tier"] = sp_f.apply(_quality_tier, axis=1)
    active = sp_f[sp_f["order_count"] >= 10].copy()

    # ── Headline KPIs ─────────────────────────────────────────────────────────
    total_sellers = len(sp_f)
    premium_pct   = (sp_f["quality_tier"] == "Premium").mean() * 100
    top20_gmv     = sp_f.nlargest(max(1, int(len(sp_f) * 0.20)), "gmv")["gmv"].sum()
    top20_share   = top20_gmv / sp_f["gmv"].sum() * 100 if sp_f["gmv"].sum() > 0 else 0

    k1, k2, k3 = st.columns(3)
    k1.metric("Total Sellers", f"{total_sellers:,}")
    k2.metric("Premium Sellers (≥10 orders)", f"{premium_pct:.0f}%",
              help="Score ≥ 4.0 and cancellation rate ≤ 2%")
    k3.metric("Top 20% Seller GMV Share", f"{top20_share:.0f}%")

    col_l, col_r = st.columns(2)

    # ── Scatter: GMV vs avg review score ──────────────────────────────────────
    with col_l:
        scatter_df = sp_f.dropna(subset=["avg_review_score"])
        if not scatter_df.empty:
            fig_scatter = px.scatter(
                scatter_df,
                x="gmv", y="avg_review_score",
                size="order_count",
                color="seller_region",
                color_discrete_map=REGION_COLOURS,
                title="Seller Performance: GMV vs Avg Review Score",
                labels={
                    "gmv": "GMV (R$)",
                    "avg_review_score": "Avg Review Score (1–5)",
                    "order_count": "Orders",
                    "seller_region": "Region",
                },
                template="plotly_white",
                hover_data=["seller_id", "seller_state", "order_count"],
                size_max=30,
                opacity=0.7,
            )
            fig_scatter.update_layout(height=400)
            st.plotly_chart(fig_scatter, width="stretch")

    # ── Pareto curve ──────────────────────────────────────────────────────────
    with col_r:
        sp_sorted = sp_f.sort_values("gmv", ascending=False).reset_index(drop=True)
        sp_sorted["cum_gmv_pct"]  = 100 * sp_sorted["gmv"].cumsum() / sp_sorted["gmv"].sum()
        sp_sorted["seller_pct"]   = 100 * (sp_sorted.index + 1) / len(sp_sorted)

        fig_pareto = px.line(
            sp_sorted, x="seller_pct", y="cum_gmv_pct",
            title="Seller Pareto Curve — GMV Concentration",
            labels={
                "seller_pct": "Seller Percentile (%)",
                "cum_gmv_pct": "Cumulative GMV (%)",
            },
            template="plotly_white",
            color_discrete_sequence=["#e74c3c"],
        )
        fig_pareto.add_hline(y=80, line_dash="dash", line_color="#7f8c8d",
                             annotation_text="80% GMV", annotation_position="top right")
        fig_pareto.add_vline(x=20, line_dash="dash", line_color="#7f8c8d",
                             annotation_text="20% sellers", annotation_position="top right")
        fig_pareto.update_layout(height=400)
        st.plotly_chart(fig_pareto, width="stretch")

    # ── Quality tiers treemap ─────────────────────────────────────────────────
    tier_data = active[active["quality_tier"] != "Unrated"].copy()
    if not tier_data.empty:
        TIER_COLOURS = {
            "Premium": "#27ae60", "Good": "#2ecc71",
            "Average": "#f39c12", "At Risk": "#e74c3c",
        }
        fig_tiers = px.treemap(
            tier_data,
            path=["quality_tier", "seller_region"],
            values="gmv",
            color="quality_tier",
            color_discrete_map=TIER_COLOURS,
            title="Seller GMV by Quality Tier & Region (sellers with ≥10 orders)",
            labels={"gmv": "GMV (R$)"},
        )
        fig_tiers.update_layout(height=380)
        st.plotly_chart(fig_tiers, width="stretch")

    # ── Seller Gini concentration trend ──────────────────────────────────────
    seller_trend = cm[cm["dimension"] == "seller_gmv_monthly"].copy()
    if not seller_trend.empty and "group_key" in seller_trend.columns:
        seller_trend = seller_trend.sort_values("group_key")
        fig_gini = px.line(
            seller_trend, x="group_key", y="gini",
            title="Seller Revenue Concentration Over Time (Monthly Gini Coefficient)",
            labels={"group_key": "Month", "gini": "Gini Coefficient"},
            template="plotly_white", markers=True,
            color_discrete_sequence=["#9b59b6"],
        )
        fig_gini.update_layout(hovermode="x unified", height=320)
        fig_gini.add_hline(
            y=seller_trend["gini"].mean(), line_dash="dot", line_color="#bdc3c7",
            annotation_text=f"Average: {seller_trend['gini'].mean():.2f}",
        )
        st.plotly_chart(fig_gini, width="stretch")
        st.caption(
            "A rising Gini trend means top sellers are capturing a growing share of GMV over time. "
            "This warrants monitoring — gradual consolidation can reduce marketplace diversity."
        )
