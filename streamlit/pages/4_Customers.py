"""
pages/4_Customers.py — Customer Analysis
RFM segmentation, segment playbook, satisfaction scores, and delivery impact.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard_utils import (
    load_customer_rfm, load_satisfaction_summary,
    init_filters, render_sidebar_filters,
    apply_filters, apply_rfm_filters, make_period,
)
from notebooks.utils import SEGMENT_COLOURS, REGION_COLOURS

# ── Bootstrap ─────────────────────────────────────────────────────────────────
init_filters()

try:
    rfm = load_customer_rfm()
    sat = load_satisfaction_summary()
except Exception as e:
    st.error(f"Could not load data files: {e}")
    st.stop()

so_stub = None  # sales_df for sidebar category/state options
try:
    from dashboard_utils import load_sales_orders
    so_stub = load_sales_orders()
except Exception:
    pass

render_sidebar_filters(sales_df=so_stub)

# ── Apply filters ─────────────────────────────────────────────────────────────
rfm_f = apply_rfm_filters(rfm)
sat_f = apply_filters(sat, cat_col="primary_product_category")

# ── Page header ───────────────────────────────────────────────────────────────
st.title("👥 Customer Analysis")
st.caption(
    f"{len(rfm_f):,} customers · {sat_f['order_id'].nunique():,} reviewed orders in selection"
)

tab1, tab2, tab3, tab4 = st.tabs([
    "🎯 RFM Segments", "📋 Segment Playbook", "⭐ Satisfaction & NPS", "⏱️ Delivery Impact"
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — RFM SEGMENTS
# ─────────────────────────────────────────────────────────────────────────────
with tab1:
    st.caption(
        "ℹ️ **Date Range and Product Category filters are not applied to this tab.** "
        "RFM (Recency, Frequency, Monetary) segmentation uses a fixed reference date of "
        "2018-08-31 and spans all categories. Customer State and Region filters apply."
    )
    st.markdown(
        "**RFM analysis** scores each customer on three dimensions: "
        "**Recency** (days since last purchase — lower = higher score), "
        "**Frequency** (F1 = 1 order, F2 = 2 orders, F3 = 3+), and "
        "**Monetary** (total spend — higher = higher score). "
        "With 96.9% of customers making a single purchase, Olist's core challenge is "
        "converting first-time buyers into repeat customers — the Promising segment is key."
    )

    if rfm_f.empty:
        st.warning("No customer data matches the current filters.")
    else:
        repeat_rate = rfm_f["frequency"].gt(1).mean() * 100
        total_custs = len(rfm_f)

        k1, k2, k3 = st.columns(3)
        k1.metric("Customers in Selection", f"{total_custs:,}")
        k2.metric("Repeat Purchase Rate",   f"{repeat_rate:.1f}%",
                  help="% of customers who made more than one purchase")
        k3.metric("Single-Purchase Customers",
                  f"{(rfm_f['frequency'] == 1).mean():.1%}",
                  help="Olist's primary conversion opportunity")

        SEG_ORDER = ["Champions", "Loyal", "Promising", "Hibernating", "At Risk", "High Value Lost"]

        # ── Grouped bar: avg R / F / M per segment ────────────────────────────
        rfm_f = rfm_f.copy()
        rfm_f["f_numeric"] = rfm_f["f_tier"].map({"F1": 1, "F2": 2, "F3": 3})

        seg_avg = (
            rfm_f.groupby("segment")
            .agg(R=("r_score", "mean"), F=("f_numeric", "mean"), M=("m_score", "mean"))
            .reindex([s for s in SEG_ORDER if s in rfm_f["segment"].unique()])
            .reset_index()
        )
        seg_melt = seg_avg.melt(id_vars="segment", var_name="Metric", value_name="Avg Score")
        seg_melt["Metric"] = seg_melt["Metric"].map({
            "R": "Recency", "F": "Frequency", "M": "Monetary",
        })

        col_l, col_r = st.columns(2)
        with col_l:
            fig_bar = px.bar(
                seg_melt, x="segment", y="Avg Score", color="Metric",
                barmode="group",
                title="Average R / F / M Score by Segment",
                category_orders={"segment": SEG_ORDER},
                template="plotly_white",
                color_discrete_map={"Recency": "#3498db", "Frequency": "#e67e22", "Monetary": "#2ecc71"},
            )
            fig_bar.update_layout(height=380, xaxis_tickangle=-20)
            st.plotly_chart(fig_bar, width="stretch")

        # ── Heatmap: r_score × f_tier ─────────────────────────────────────────
        with col_r:
            heat = rfm_f.groupby(["r_score", "f_tier"]).size().reset_index(name="count")
            heat_pivot = (
                heat.pivot(index="r_score", columns="f_tier", values="count")
                .reindex(index=[5, 4, 3, 2, 1], columns=["F1", "F2", "F3"])
                .fillna(0).astype(int)
            )
            fig_heat = px.imshow(
                heat_pivot, text_auto=True,
                labels=dict(
                    x="Frequency Tier (F1=1 order, F2=2, F3=3+)",
                    y="Recency Score (5=most recent)",
                    color="Customers",
                ),
                title="RFM Heatmap: Recency Score × Frequency Tier",
                color_continuous_scale="YlOrRd",
                aspect="auto",
            )
            fig_heat.update_layout(height=380)
            st.plotly_chart(fig_heat, width="stretch")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — SEGMENT PLAYBOOK
# ─────────────────────────────────────────────────────────────────────────────
with tab2:
    st.caption(
        "ℹ️ **Date Range and Product Category filters are not applied.** "
        "Customer State and Region filters apply to segment counts and averages."
    )
    st.markdown(
        "**From data to decisions.** Each segment card shows the customer profile and the "
        "recommended marketing action. The largest opportunity is the **Promising** segment "
        "(~37K recent single-purchase customers). Converting even 5% of them into repeat "
        "buyers would nearly double the current repeat-customer base."
    )

    SEG_CONFIG = {
        "Champions":       {
            "emoji": "🏆", "kind": "success",
            "action": "VIP rewards programme, referral incentives, early access to new categories. These customers are your advocates — activate them."
        },
        "Loyal":           {
            "emoji": "💎", "kind": "success",
            "action": "Loyalty programme enrolment, exclusive category previews, cross-category upsell bundles. Nurture the relationship before they drift."
        },
        "Promising":       {
            "emoji": "✨", "kind": "info",
            "action": "Cross-sell recommendations and a first-repeat-purchase incentive (e.g. 10% off second order). This is the highest-ROI segment to convert."
        },
        "Hibernating":     {
            "emoji": "💤", "kind": "warning",
            "action": "Low-cost re-engagement email only. Deprioritise paid ad spend — focus budget on Promising segment instead."
        },
        "At Risk":         {
            "emoji": "⚠️", "kind": "warning",
            "action": "Win-back email campaign, satisfaction survey, targeted discount code. Act before they become High Value Lost."
        },
        "High Value Lost": {
            "emoji": "🔴", "kind": "error",
            "action": "Aggressive reactivation offer, personal outreach. These customers spent the most and have gone quiet — a personal touch may recover them."
        },
    }

    SEG_ORDER = ["Champions", "Loyal", "Promising", "Hibernating", "At Risk", "High Value Lost"]

    if rfm_f.empty:
        st.warning("No customer data matches the current filters.")
    else:
        seg_stats = (
            rfm_f.groupby("segment")
            .agg(
                count=("customer_unique_id", "count"),
                avg_spend=("monetary_value", "mean"),
                avg_recency=("recency_days", "mean"),
                avg_freq=("frequency", "mean"),
            )
            .to_dict("index")
        )

        row1_segs = ["Champions", "Loyal", "Promising"]
        row2_segs = ["Hibernating", "At Risk", "High Value Lost"]

        for row_segs in [row1_segs, row2_segs]:
            cols = st.columns(3)
            for col, seg in zip(cols, row_segs):
                cfg   = SEG_CONFIG[seg]
                stats = seg_stats.get(seg, {})
                count      = stats.get("count", 0)
                avg_spend  = stats.get("avg_spend", 0)
                avg_recency= stats.get("avg_recency", 0)

                body = (
                    f"**{cfg['emoji']} {seg}** — {count:,} customers\n\n"
                    f"- Avg spend: R${avg_spend:,.0f}\n"
                    f"- Last purchase: {avg_recency:.0f} days ago\n\n"
                    f"**Recommended action:** {cfg['action']}"
                )
                with col:
                    getattr(st, cfg["kind"])(body)

        st.markdown("---")
        # Segment size bar for quick comparison
        seg_counts = (
            rfm_f["segment"].value_counts()
            .reindex([s for s in SEG_ORDER if s in rfm_f["segment"].unique()])
            .reset_index()
            .rename(columns={"segment": "Segment", "count": "Customers"})
        )
        fig_seg = px.bar(
            seg_counts.sort_values("Customers"),
            x="Customers", y="Segment",
            orientation="h",
            title="Customer Count by Segment",
            template="plotly_white", text_auto=",d",
            color="Segment",
            color_discrete_map=SEGMENT_COLOURS,
        )
        fig_seg.update_layout(height=360, showlegend=False)
        st.plotly_chart(fig_seg, width="stretch")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — SATISFACTION & NPS
# ─────────────────────────────────────────────────────────────────────────────
with tab3:
    st.caption(
        "ℹ️ **Product Category filter is approximate** — based on the highest-revenue item "
        "per order (~10% of orders have multiple categories). All other filters apply."
    )
    st.markdown(
        "**Net Promoter Score (NPS)** measures customer loyalty: % promoters minus % detractors. "
        "Proxy scoring: review score 4–5 = promoter, 3 = passive, 1–2 = detractor. "
        "Scores above +50 are considered excellent. Olist's NPS proxy of ~+64 is strong, "
        "driven by the score-5 majority. Note the bimodal pattern — customers either love "
        "it (score 5) or hate it (score 1), with few in between."
    )

    if sat_f.empty:
        st.warning("No satisfaction data matches the current filters.")
    else:
        sat_ded = sat_f.drop_duplicates("order_id")

        # Overall NPS KPI
        nps_pct   = sat_ded["nps_category"].value_counts(normalize=True)
        nps_score = 100 * (nps_pct.get("promoter", 0) - nps_pct.get("detractor", 0))
        avg_score = sat_ded["review_score"].mean()

        k1, k2, k3 = st.columns(3)
        k1.metric("NPS Proxy Score",  f"+{nps_score:.1f}" if nps_score >= 0 else f"{nps_score:.1f}")
        k2.metric("Avg Review Score", f"{avg_score:.2f} / 5.0")
        k3.metric("Orders with Review", f"{len(sat_ded):,}")

        col_l, col_r = st.columns(2)

        # ── Review score distribution ──────────────────────────────────────
        with col_l:
            score_dist = (
                sat_f["review_score"].dropna().astype(int)
                .value_counts().sort_index().reset_index()
                .rename(columns={"review_score": "Score", "count": "Reviews"})
            )
            fig_dist = px.bar(
                score_dist, x="Score", y="Reviews",
                title="Review Score Distribution",
                labels={"Score": "Review Score (1–5)", "Reviews": "Number of Reviews"},
                template="plotly_white", text_auto=",d",
                color_discrete_sequence=["#3498db"],
            )
            fig_dist.update_layout(height=340)
            st.plotly_chart(fig_dist, width="stretch")

        # ── Avg score trend ────────────────────────────────────────────────
        with col_r:
            score_m = (
                sat_ded.groupby(["year", "month"])["review_score"]
                .mean().reset_index(name="avg_score")
            )
            score_m["period"] = make_period(score_m)
            score_m = score_m.sort_values("period")

            fig_trend = px.line(
                score_m, x="period", y="avg_score",
                title="Average Review Score by Month",
                labels={"avg_score": "Avg Score", "period": "Month"},
                template="plotly_white", markers=True,
                color_discrete_sequence=["#27ae60"],
            )
            fig_trend.update_yaxes(range=[1, 5])
            fig_trend.update_layout(hovermode="x unified", height=340)
            st.plotly_chart(fig_trend, width="stretch")

        # ── NPS stacked bar ────────────────────────────────────────────────
        nps_m = (
            sat_ded.groupby(["year", "month", "nps_category"])
            .size().reset_index(name="cnt")
        )
        total_m = sat_ded.groupby(["year", "month"]).size().reset_index(name="total")
        nps_m   = nps_m.merge(total_m, on=["year", "month"])
        nps_m["pct"]    = 100 * nps_m["cnt"] / nps_m["total"]
        nps_m["period"] = make_period(nps_m)
        nps_m = nps_m.sort_values("period")

        nps_score_m = (
            sat_ded.groupby(["year", "month"])
            .apply(lambda g: pd.Series({
                "nps": 100 * (
                    (g["nps_category"] == "promoter").mean() -
                    (g["nps_category"] == "detractor").mean()
                )
            }), include_groups=False)
            .reset_index()
        )
        nps_score_m["period"] = make_period(nps_score_m)
        nps_score_m = nps_score_m.sort_values("period")

        col_l, col_r = st.columns(2)
        with col_l:
            if not nps_m.empty:
                fig_nps_bar = px.bar(
                    nps_m, x="period", y="pct", color="nps_category",
                    barmode="stack",
                    title="NPS Category Mix by Month (100% Stacked)",
                    labels={"pct": "% of Reviews", "period": "Month",
                            "nps_category": "NPS Category"},
                    template="plotly_white",
                    color_discrete_map={
                        "promoter":  "#2ecc71",
                        "passive":   "#f39c12",
                        "detractor": "#e74c3c",
                    },
                    category_orders={"nps_category": ["promoter", "passive", "detractor"]},
                )
                fig_nps_bar.update_layout(height=360,
                                          legend=dict(orientation="h", y=-0.2))
                st.plotly_chart(fig_nps_bar, width="stretch")

        with col_r:
            if not nps_score_m.empty:
                fig_nps_line = px.line(
                    nps_score_m, x="period", y="nps",
                    title="NPS Proxy Score Trend",
                    labels={"nps": "NPS Score", "period": "Month"},
                    template="plotly_white", markers=True,
                    color_discrete_sequence=["#9b59b6"],
                )
                fig_nps_line.add_hline(y=0, line_dash="dash", line_color="gray")
                fig_nps_line.update_layout(hovermode="x unified", height=360)
                st.plotly_chart(fig_nps_line, width="stretch")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — DELIVERY IMPACT
# ─────────────────────────────────────────────────────────────────────────────
with tab4:
    st.caption(
        "ℹ️ **Product Category filter is approximate.** "
        "Only delivered orders with complete tracking data are shown."
    )
    st.markdown(
        "**Delivery delay is the single strongest predictor of customer dissatisfaction.** "
        "The score drops from 4.30 (early delivery) to 1.69 (7+ days late) — a 2.6-point "
        "collapse. Critically, early delivery doesn't just avoid complaints — it actively "
        "generates delight (4.30 vs 3.96 for on-time). Shifting orders from 'on-time' to "
        "'early' has a measurable satisfaction payoff."
    )

    BIN_ORDER = ["early", "on-time", "1-3d late", "4-7d late", "7+d late"]

    sat_del = sat_f.dropna(subset=["delay_bin"]).copy()

    if sat_del.empty:
        st.warning("No delivery data with tracking information matches the current filters.")
    else:
        # Avg score per bin
        avg_by_bin = (
            sat_del.groupby("delay_bin")["review_score"]
            .mean()
            .reindex([b for b in BIN_ORDER if b in sat_del["delay_bin"].unique()])
            .reset_index()
            .rename(columns={"review_score": "Avg Review Score", "delay_bin": "Delay Bin"})
        )
        # Order counts per bin for context
        bin_counts = sat_del["delay_bin"].value_counts()

        col_l, col_r = st.columns(2)
        with col_l:
            if not avg_by_bin.empty:
                colors = []
                for b in avg_by_bin["Delay Bin"]:
                    if b == "early":      colors.append("#27ae60")
                    elif b == "on-time":  colors.append("#2ecc71")
                    elif b == "1-3d late":colors.append("#f39c12")
                    elif b == "4-7d late":colors.append("#e67e22")
                    else:                 colors.append("#e74c3c")

                fig_bar = go.Figure(go.Bar(
                    x=avg_by_bin["Delay Bin"],
                    y=avg_by_bin["Avg Review Score"],
                    marker_color=colors,
                    text=avg_by_bin["Avg Review Score"].round(2),
                    textposition="outside",
                    hovertemplate="%{x}<br>Avg score: %{y:.2f}<extra></extra>",
                ))

                # Annotate the "satisfaction cliff"
                if "early" in avg_by_bin["Delay Bin"].values and "7+d late" in avg_by_bin["Delay Bin"].values:
                    early_score = avg_by_bin.loc[avg_by_bin["Delay Bin"] == "early", "Avg Review Score"].values[0]
                    late_score  = avg_by_bin.loc[avg_by_bin["Delay Bin"] == "7+d late", "Avg Review Score"].values[0]
                    fig_bar.add_annotation(
                        x="7+d late", y=late_score + 0.3,
                        text=f"▼ {early_score:.2f} → {late_score:.2f}<br>({early_score-late_score:.2f} pt drop)",
                        showarrow=True, arrowhead=2, arrowcolor="#e74c3c",
                        font=dict(color="#e74c3c", size=11),
                        bgcolor="white", bordercolor="#e74c3c",
                    )

                fig_bar.update_layout(
                    title="Average Review Score by Delivery Delay Bin",
                    xaxis_title="Delivery Timing",
                    yaxis_title="Avg Review Score (1–5)",
                    yaxis=dict(range=[0, 5.5]),
                    template="plotly_white",
                    height=400,
                )
                st.plotly_chart(fig_bar, width="stretch")

        with col_r:
            fig_box = px.box(
                sat_del, x="delay_bin", y="review_score",
                title="Review Score Distribution by Delay Bin",
                labels={"review_score": "Review Score (1–5)", "delay_bin": "Delay Bin"},
                template="plotly_white",
                category_orders={"delay_bin": BIN_ORDER},
                color="delay_bin",
                color_discrete_map={
                    "early": "#27ae60", "on-time": "#2ecc71",
                    "1-3d late": "#f39c12", "4-7d late": "#e67e22", "7+d late": "#e74c3c",
                },
            )
            fig_box.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_box, width="stretch")

        # Distribution footnote
        bin_summary = pd.DataFrame({
            "Delay Bin": [b for b in BIN_ORDER if b in bin_counts.index],
            "Orders": [bin_counts.get(b, 0) for b in BIN_ORDER if b in bin_counts.index],
        })
        st.dataframe(
            bin_summary.assign(**{"% of Total": lambda d: (100 * d["Orders"] / d["Orders"].sum()).round(1)})
                       .set_index("Delay Bin"),
            width="stretch",
        )
