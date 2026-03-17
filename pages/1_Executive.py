"""
pages/1_Executive.py — Executive Overview
60-second pulse check: GMV trends, AOV, payments, and order health.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from dashboard_utils import (
    load_sales_orders, load_satisfaction_summary, load_geo_delivery,
    load_customer_rfm, init_filters, render_sidebar_filters,
    apply_filters, apply_geo_filters, apply_rfm_filters, make_period,
)
from notebooks.utils import REGION_COLOURS, STATUS_COLOURS

# ── Bootstrap ─────────────────────────────────────────────────────────────────
init_filters()

try:
    so  = load_sales_orders()
    sat = load_satisfaction_summary()
    geo = load_geo_delivery()
    rfm = load_customer_rfm()
except Exception as e:
    st.error(f"Could not load data files: {e}")
    st.stop()

render_sidebar_filters(sales_df=so)

# ── Apply filters ─────────────────────────────────────────────────────────────
so_f  = apply_filters(so)
sat_f = apply_filters(sat, cat_col="primary_product_category")
geo_f = apply_geo_filters(geo)
rfm_f = apply_rfm_filters(rfm)

if so_f.empty:
    st.warning("No sales data matches the current filters. Please adjust your selection.")
    st.stop()

# ── Derived datasets ──────────────────────────────────────────────────────────
pay_orders = so_f.drop_duplicates("order_id")      # order-level view of sales
sat_ded    = sat_f.drop_duplicates("order_id") if not sat_f.empty else sat_f

# ── Headline KPIs (always visible above tabs) ─────────────────────────────────
total_gmv    = so_f["total_sale_amount"].sum()
total_orders = so_f["order_id"].nunique()
aov          = total_gmv / total_orders if total_orders > 0 else 0

on_time_den  = geo_f["total_orders"].sum() if not geo_f.empty else 0
on_time_rate = geo_f["on_time_orders"].sum() / on_time_den if on_time_den > 0 else float("nan")

if not sat_ded.empty and "nps_category" in sat_ded.columns:
    nps_pct  = sat_ded["nps_category"].value_counts(normalize=True)
    nps_score = 100 * (nps_pct.get("promoter", 0) - nps_pct.get("detractor", 0))
else:
    nps_score = float("nan")

repeat_rate = rfm_f["frequency"].gt(1).mean() * 100 if not rfm_f.empty else float("nan")

# ── Page header ───────────────────────────────────────────────────────────────
st.title("📊 Executive Overview")
st.caption("Olist marketplace · Jan 2017 – Aug 2018 · Brazilian e-commerce dataset")

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total GMV",
          f"R${total_gmv:,.0f}",
          help="Gross Merchandise Value — total value of goods sold (price + freight)")
c2.metric("Total Orders",        f"{total_orders:,}",
          help="Count of distinct orders in the selected period")
c3.metric("AOV",
          f"R${aov:,.2f}",
          help="Average Order Value = GMV ÷ Orders")
c4.metric("On-Time Rate",
          f"{on_time_rate:.1%}" if on_time_den > 0 else "N/A",
          help="% of orders delivered on or before the estimated date")
c5.metric("NPS Proxy",
          (f"+{nps_score:.1f}" if nps_score >= 0 else f"{nps_score:.1f}") if not pd.isna(nps_score) else "N/A",
          help="Net Promoter Score proxy: % promoters minus % detractors (review ≥4 = promoter, ≤2 = detractor)")
c6.metric("Repeat Rate",
          f"{repeat_rate:.1f}%" if not pd.isna(repeat_rate) else "N/A",
          help="% of customers who made more than one purchase")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Sales Trend", "💰 Revenue & AOV", "💳 Payment Mix", "📦 Order Health"
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — SALES TREND
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    st.markdown(
        "**Gross Merchandise Value (GMV)** — the total value of goods sold — grew ~103% from "
        "Jan 2017 to Aug 2018. The Black Friday 2017 spike (7,500+ orders) was roughly 2× the "
        "monthly average. Growth is volume-driven: the order count chart mirrors the GMV line "
        "closely, meaning Olist's engine is customer acquisition, not larger baskets."
    )

    monthly = (
        so_f.groupby(["year", "month"])
        .agg(gmv=("total_sale_amount", "sum"), orders=("order_id", "nunique"))
        .reset_index()
    )
    monthly["period"] = make_period(monthly)
    monthly = monthly.sort_values("period")

    if monthly.empty:
        st.info("No monthly data available for the selected filters.")
    else:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.06,
            row_heights=[0.6, 0.4],
            subplot_titles=("Monthly GMV (R$)", "Monthly Order Count"),
        )
        fig.add_trace(
            go.Scatter(
                x=monthly["period"], y=monthly["gmv"],
                fill="tozeroy", name="GMV",
                line=dict(color="#27ae60", width=2),
                hovertemplate="<b>%{x}</b><br>GMV: R$%{y:,.0f}<extra></extra>",
            ), row=1, col=1,
        )
        fig.add_trace(
            go.Bar(
                x=monthly["period"], y=monthly["orders"],
                name="Orders", marker_color="#3498db",
                hovertemplate="<b>%{x}</b><br>Orders: %{y:,}<extra></extra>",
            ), row=2, col=1,
        )
        # Black Friday annotation (only if in filtered range)
        # Note: add_vline with annotation_text fails on categorical string axes —
        # Plotly tries sum(x)/len(x) internally which blows up on strings.
        # Use add_shape + add_annotation instead.
        if "2017-11" in monthly["period"].values:
            fig.add_shape(
                type="line",
                xref="x", yref="paper",
                x0="2017-11", x1="2017-11",
                y0=0, y1=1,
                line=dict(color="orange", width=1.5, dash="dash"),
            )
            fig.add_annotation(
                xref="x", yref="paper",
                x="2017-11", y=0.97,
                text="🛍️ Black Friday 2017",
                showarrow=False,
                font=dict(color="orange", size=11),
                xanchor="left",
            )
        fig.update_layout(
            height=480, template="plotly_white",
            showlegend=False, hovermode="x unified",
            margin=dict(t=50, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — REVENUE & AOV
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    st.markdown(
        "**Average Order Value (AOV)** = total revenue ÷ number of orders. A flat AOV line "
        "with rising GMV confirms growth is driven by more customers, not larger baskets. "
        "Credit card users spend ~13% more than boleto (bank slip) users — installment capability "
        "likely enables larger purchases by reducing the perceived upfront cost."
    )

    monthly_aov = (
        pay_orders.groupby(["year", "month"])
        .agg(gmv=("total_sale_amount", "sum"), orders=("order_id", "count"))
        .reset_index()
    )
    monthly_aov["period"] = make_period(monthly_aov)
    monthly_aov["aov"] = monthly_aov["gmv"] / monthly_aov["orders"]
    monthly_aov = monthly_aov.sort_values("period")

    aov_pay = (
        pay_orders.groupby("primary_payment_type")
        .agg(gmv=("total_sale_amount", "sum"), orders=("order_id", "count"))
        .reset_index()
    )
    aov_pay["aov"] = aov_pay["gmv"] / aov_pay["orders"]
    aov_pay = aov_pay.sort_values("aov", ascending=True)

    col_l, col_r = st.columns([2, 1])
    with col_l:
        if not monthly_aov.empty:
            fig_aov = px.line(
                monthly_aov, x="period", y="aov",
                title="Average Order Value (AOV) by Month",
                labels={"aov": "AOV (R$)", "period": "Month"},
                template="plotly_white", markers=True,
                color_discrete_sequence=["#e67e22"],
            )
            fig_aov.update_layout(hovermode="x unified", height=350)
            st.plotly_chart(fig_aov, use_container_width=True)

    with col_r:
        if not aov_pay.empty:
            fig_aov_pay = px.bar(
                aov_pay, x="aov", y="primary_payment_type",
                orientation="h",
                title="AOV by Payment Type",
                labels={"aov": "AOV (R$)", "primary_payment_type": "Payment Type"},
                template="plotly_white", text_auto=".0f",
                color_discrete_sequence=["#9b59b6"],
            )
            fig_aov_pay.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig_aov_pay, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — PAYMENT MIX
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.markdown(
        "Brazil has a unique **parcelamento** culture — splitting credit card purchases into "
        "monthly instalments, often interest-free. Credit card dominates at ~77% of orders, "
        "with a median of 3 instalments. This is not just a payment preference — it's a demand "
        "enabler that allows customers to buy more expensive items by spreading the cost."
    )

    pay_type = (
        pay_orders["primary_payment_type"]
        .value_counts()
        .reset_index()
        .rename(columns={"primary_payment_type": "payment_type", "count": "orders"})
    )
    cc = pay_orders[
        pay_orders["primary_payment_type"] == "credit_card"
    ]["primary_payment_installments"].dropna()

    col_l, col_r = st.columns(2)
    with col_l:
        if not pay_type.empty:
            fig_donut = px.pie(
                pay_type, values="orders", names="payment_type",
                title="Payment Type Distribution",
                hole=0.45, template="plotly_white",
                color_discrete_sequence=["#3498db", "#e67e22", "#2ecc71", "#9b59b6"],
            )
            fig_donut.update_traces(textposition="outside", textinfo="percent+label")
            fig_donut.update_layout(showlegend=False, height=380)
            st.plotly_chart(fig_donut, use_container_width=True)

    with col_r:
        if len(cc) > 0:
            fig_hist = px.histogram(
                x=cc.astype(int), nbins=12,
                title="Credit Card Instalments",
                labels={"x": "Number of Instalments", "y": "Orders"},
                template="plotly_white",
                color_discrete_sequence=["#3498db"],
            )
            fig_hist.update_layout(bargap=0.05, height=380, showlegend=False)
            st.plotly_chart(fig_hist, use_container_width=True)

        median_inst = int(cc.median()) if len(cc) > 0 else "N/A"
        st.metric("Median Instalments (credit card)", median_inst)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — ORDER HEALTH
# ─────────────────────────────────────────────────────────────────────────────
with tab4:
    st.markdown(
        "A cancellation rate below 0.5% is excellent for a marketplace of this scale. "
        "The status donut shows that 96.8% of orders complete the full delivery lifecycle. "
        "'Unavailable' status — where a seller cannot fulfil an order after acceptance — "
        "is near zero, indicating good seller inventory signalling."
    )

    orders_m = pay_orders.copy()
    orders_m["period"] = make_period(orders_m)

    status_m = (
        orders_m.groupby(["period", "order_status"])["order_id"]
        .count().reset_index(name="cnt")
    )
    total_m = (
        orders_m.groupby("period")["order_id"]
        .count().reset_index(name="total")
    )
    status_m = status_m.merge(total_m, on="period")
    status_m["pct"] = 100 * status_m["cnt"] / status_m["total"]
    cancel_line = status_m[
        status_m["order_status"].isin(["canceled", "unavailable"])
    ].sort_values("period")

    status_overall = (
        pay_orders["order_status"].value_counts().reset_index()
        .rename(columns={"order_status": "Status", "count": "Orders"})
    )

    col_l, col_r = st.columns([2, 1])
    with col_l:
        if not cancel_line.empty:
            fig_cancel = px.line(
                cancel_line, x="period", y="pct", color="order_status",
                title="Cancellation & Unavailability Rate Over Time",
                labels={"pct": "% of Orders", "period": "Month", "order_status": "Status"},
                template="plotly_white", markers=True,
                color_discrete_map={"canceled": "#e74c3c", "unavailable": "#c0392b"},
            )
            fig_cancel.update_layout(hovermode="x unified", height=360)
            st.plotly_chart(fig_cancel, use_container_width=True)
        else:
            st.info("No cancellation or unavailability events in the selected period.")

    with col_r:
        if not status_overall.empty:
            fig_status = px.pie(
                status_overall, values="Orders", names="Status",
                title="Order Status Breakdown",
                hole=0.45, template="plotly_white",
                color="Status",
                color_discrete_map=STATUS_COLOURS,
            )
            fig_status.update_traces(textposition="outside", textinfo="percent+label")
            fig_status.update_layout(showlegend=False, height=360)
            st.plotly_chart(fig_status, use_container_width=True)
