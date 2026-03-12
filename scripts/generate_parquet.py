"""
generate_parquet.py
Project Caravela — Olist E-Commerce Analytics Pipeline

Quick-setup script: produces all 5 dashboard Parquet files directly from the
BigQuery analytics dataset without running the full Jupyter notebooks.

Run once after `dbt build` completes and before launching dashboard.py.

Prerequisites
-------------
  - GOOGLE_APPLICATION_CREDENTIALS env var → service account JSON key path
  - BigQuery analytics dataset fully populated (dbt build succeeded)
  - pip install sqlalchemy-bigquery google-cloud-bigquery pandas pyarrow numpy

Usage
-----
    conda activate DSAI-2_ooc
    python scripts/generate_parquet.py --project <gcp_project_id>

    # Optional: override dataset name (default: olist_analytics)
    python scripts/generate_parquet.py --project my-proj --dataset olist_analytics

Open Items
----------
  date_key type (INTEGER / DATE / STRING) is an open item flagged for the
  data engineer — see REQ-008.1 Open Item (3) in the BRD. The observation
  window filter in this script uses dim_date.year / dim_date.month (integers,
  format-agnostic). The FK join `fct_sales.date_key = dim_date.date_key` will
  work regardless of type as long as both sides share the same type in BigQuery.

Output
------
  data/sales_orders.parquet      — order-item granularity (~112k rows)
  data/customer_rfm.parquet      — customer granularity (~96k rows)
  data/satisfaction_summary.parquet — order granularity (~97k rows)
  data/geo_delivery.parquet      — state × month granularity (~540 rows)
  data/seller_performance.parquet — seller granularity (~3k rows)
"""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine

# Resolve project root and import shared utils
ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
sys.path.insert(0, str(ROOT / "notebooks"))
from utils import REGION_MAP, add_region  # noqa: E402

# Trend analysis observation window: 2017-01-01 to 2018-08-31 (20 complete months)
# ASMP-025: Sep/Oct 2018 are data cut artefacts (16 and 4 orders). 2016 excluded
# from trend analyses — platform ramp-up noise (Nov 2016: 0 orders; other 2016
# months: 1–4 orders) distorts trend lines.
OBS_FILTER = "((dd.year = 2017) OR (dd.year = 2018 AND dd.month <= 8))"

# RFM customer history filter: full purchase history up to 2018-08-31.
# ASMP-022 + ASMP-025: 2016 orders ARE included — a customer last active in 2016
# is genuinely dormant and must appear in the Hibernating segment. Excluding 2016
# would understate dormancy and overstate the active customer base.
# Only Sep/Oct 2018 artefact months are excluded.
RFM_HIST_FILTER = "((dd.year < 2018) OR (dd.year = 2018 AND dd.month <= 8))"

# RFM reference date — hardcoded per ASMP-022; do NOT use CURRENT_DATE or MAX()
RFM_REF_DATE = "2018-08-31"


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def get_engine(project: str, dataset: str):
    """SQLAlchemy engine for BigQuery analytics dataset."""
    return create_engine(f"bigquery://{project}/{dataset}")


def T(project: str, dataset: str, name: str) -> str:
    """Fully-qualified BigQuery table reference."""
    return f"`{project}.{dataset}.{name}`"


# ---------------------------------------------------------------------------
# Parquet 1: sales_orders.parquet
# Order-item granularity. Used by Executive Overview and Product Performance.
# primary_payment_type / primary_payment_installments use payment_sequential=1
# (~3% approximation for split-payment orders — see BRD REQ-025.1 notes).
# ---------------------------------------------------------------------------

def gen_sales_orders(engine, project: str, dataset: str) -> pd.DataFrame:
    print("  Querying sales_orders...")
    sql = f"""
    SELECT
        fs.order_id,
        fs.order_item_id,
        fs.customer_unique_id,
        fs.product_id,
        fs.seller_id,
        fs.order_status,
        fs.price,
        fs.freight_value,
        fs.total_sale_amount,
        fs.order_delivered_customer_date,
        fs.order_estimated_delivery_date,
        dd.year,
        dd.month,
        dd.day,
        dc.customer_state,
        dc.customer_city,
        dp.product_category,
        ds.seller_state,
        fp.payment_type         AS primary_payment_type,
        fp.payment_installments AS primary_payment_installments
    FROM {T(project, dataset, 'fct_sales')} fs
    JOIN {T(project, dataset, 'dim_date')} dd
        ON fs.date_key = dd.date_key
    JOIN {T(project, dataset, 'dim_customers')} dc
        ON fs.customer_unique_id = dc.customer_unique_id
    JOIN {T(project, dataset, 'dim_products')} dp
        ON fs.product_id = dp.product_id
    JOIN {T(project, dataset, 'dim_sellers')} ds
        ON fs.seller_id = ds.seller_id
    LEFT JOIN {T(project, dataset, 'fct_payments')} fp
        ON fs.order_id = fp.order_id AND fp.payment_sequential = 1
    WHERE {OBS_FILTER}
    """
    df = pd.read_sql(sql, engine)
    df = add_region(df, "customer_state")
    df = add_region(df, "seller_state")
    print(f"    {len(df):,} rows")
    return df


# ---------------------------------------------------------------------------
# Parquet 2: customer_rfm.parquet
# Customer granularity. RFM scoring applied in Python.
# Segments: Champions, Loyal, Promising, At Risk, High Value Lost, Hibernating.
# ---------------------------------------------------------------------------

def _rfm_segment(r: int, f: int) -> str:
    """Assign RFM segment from R_score (1–5) and F_tier (1–3).

    F_tier encoding: 1 = 1 order, 2 = 2 orders, 3 = 3+ orders.
    Segment rules reflect that 96.9% of Olist customers are single-purchasers
    (F=1), so F-tier is sparse at higher values — see ASMP-022.
    """
    if r >= 4 and f == 3:
        return "Champions"
    if r >= 3 and f >= 2:
        return "Loyal"
    if r >= 4 and f == 1:
        return "Promising"
    if r <= 2 and f == 3:
        return "High Value Lost"
    if r <= 2 and f >= 2:
        return "At Risk"
    return "Hibernating"   # r <= 3, f == 1 (the dominant bucket)


def gen_customer_rfm(engine, project: str, dataset: str) -> pd.DataFrame:
    print("  Querying customer_rfm base...")
    sql = f"""
    SELECT
        fs.customer_unique_id,
        dc.customer_state,
        DATE_DIFF(
            DATE '{RFM_REF_DATE}',
            MAX(DATE(dd.year, dd.month, dd.day)),
            DAY
        )                          AS recency_days,
        COUNT(DISTINCT fs.order_id) AS frequency,
        SUM(fs.total_sale_amount)   AS monetary
    FROM {T(project, dataset, 'fct_sales')} fs
    JOIN {T(project, dataset, 'dim_date')} dd
        ON fs.date_key = dd.date_key
    JOIN {T(project, dataset, 'dim_customers')} dc
        ON fs.customer_unique_id = dc.customer_unique_id
    WHERE {RFM_HIST_FILTER}
    GROUP BY fs.customer_unique_id, dc.customer_state
    """
    df = pd.read_sql(sql, engine)
    print(f"    {len(df):,} customers — scoring RFM...")

    # Recency: lower days → more recent → higher score (1=worst, 5=best)
    df["R_score"] = pd.qcut(
        df["recency_days"], q=5, labels=[5, 4, 3, 2, 1], duplicates="drop"
    ).astype(int)

    # Frequency: 3-tier (quintiles collapse because 96.9% are single-purchase)
    df["F_tier"] = df["frequency"].apply(lambda x: 1 if x == 1 else (2 if x == 2 else 3))

    # Monetary: higher spend → higher score (1=lowest, 5=highest)
    df["M_score"] = pd.qcut(
        df["monetary"], q=5, labels=[1, 2, 3, 4, 5], duplicates="drop"
    ).astype(int)

    df["segment"] = df.apply(lambda row: _rfm_segment(row["R_score"], row["F_tier"]), axis=1)

    df = add_region(df, "customer_state")
    print(f"    Segment distribution:\n{df['segment'].value_counts().to_string()}")
    return df


# ---------------------------------------------------------------------------
# Parquet 3: satisfaction_summary.parquet
# Order granularity. Combines fct_sales (aggregated) + fct_reviews.
# primary_product_category = category of the highest-revenue item per order.
# ---------------------------------------------------------------------------

def gen_satisfaction_summary(engine, project: str, dataset: str) -> pd.DataFrame:
    print("  Querying satisfaction_summary...")

    # Pull item-level sales data for order aggregation
    sql_sales = f"""
    SELECT
        fs.order_id,
        fs.customer_unique_id,
        fs.order_status,
        fs.order_delivered_customer_date,
        fs.order_estimated_delivery_date,
        fs.total_sale_amount,
        dd.year,
        dd.month,
        dc.customer_state,
        dp.product_category
    FROM {T(project, dataset, 'fct_sales')} fs
    JOIN {T(project, dataset, 'dim_date')} dd
        ON fs.date_key = dd.date_key
    JOIN {T(project, dataset, 'dim_customers')} dc
        ON fs.customer_unique_id = dc.customer_unique_id
    JOIN {T(project, dataset, 'dim_products')} dp
        ON fs.product_id = dp.product_id
    WHERE {OBS_FILTER}
    """
    items = pd.read_sql(sql_sales, engine)

    # primary_product_category = category with highest total_sale_amount per order
    primary_cat = (
        items.sort_values("total_sale_amount", ascending=False)
        .groupby("order_id")["product_category"]
        .first()
        .rename("primary_product_category")
    )

    # Aggregate to order level
    orders = (
        items.groupby("order_id")
        .agg(
            customer_unique_id=("customer_unique_id", "first"),
            customer_state=("customer_state", "first"),
            order_status=("order_status", "first"),
            order_delivered_customer_date=("order_delivered_customer_date", "first"),
            order_estimated_delivery_date=("order_estimated_delivery_date", "first"),
            order_gmv=("total_sale_amount", "sum"),
            year=("year", "first"),
            month=("month", "first"),
        )
        .join(primary_cat)
        .reset_index()
    )

    # Pull reviews (separate query — fct_reviews links to all orders, incl. itemless)
    # fct_reviews PK is review_id, not order_id — 547 orders have multiple review_ids.
    # Deduplicate to one row per order_id (latest review_answer_timestamp) before
    # merging, so the output stays at order granularity.
    sql_reviews = f"""
    SELECT
        order_id,
        review_score,
        review_comment_message,
        review_answer_timestamp
    FROM {T(project, dataset, 'fct_reviews')}
    """
    reviews = pd.read_sql(sql_reviews, engine)
    reviews = (
        reviews.sort_values("review_answer_timestamp", ascending=False)
        .drop_duplicates(subset="order_id", keep="first")
        .drop(columns="review_answer_timestamp")
    )

    # Left join: orders without reviews keep NaN review_score
    df = orders.merge(reviews, on="order_id", how="left")

    # Delivery delay in days (positive = late, negative = early)
    df["delay_days"] = (
        (pd.to_datetime(df["order_delivered_customer_date"]) -
         pd.to_datetime(df["order_estimated_delivery_date"]))
        .dt.total_seconds() / 86400
    )

    # 5-bin delay label (only for delivered orders with both timestamps)
    def _delay_bin(d):
        if pd.isna(d):
            return None
        if d < 0:
            return "Early"
        if d == 0:
            return "On time"
        if d <= 3:
            return "1–3d late"
        if d <= 7:
            return "4–7d late"
        return "7+d late"

    df["delay_bin"] = df["delay_days"].apply(_delay_bin)

    # nps_bucket — promoter/passive/detractor; null where no review
    def _nps_bucket(score):
        if pd.isna(score):
            return None
        return "promoter" if score >= 4 else ("passive" if score == 3 else "detractor")

    df["nps_bucket"] = df["review_score"].apply(_nps_bucket)

    # is_on_time — True/False for delivered orders with both timestamps; None otherwise
    delivered_mask = (
        (df["order_status"] == "delivered") &
        df["order_delivered_customer_date"].notna() &
        df["order_estimated_delivery_date"].notna()
    )
    df["is_on_time"] = None
    df.loc[delivered_mask, "is_on_time"] = (
        pd.to_datetime(df.loc[delivered_mask, "order_delivered_customer_date"]) <=
        pd.to_datetime(df.loc[delivered_mask, "order_estimated_delivery_date"])
    )

    df = add_region(df, "customer_state")
    print(f"    {len(df):,} orders")
    return df


# ---------------------------------------------------------------------------
# Parquet 4: geo_delivery.parquet
# State × month granularity for the geographic delivery heatmap.
# Dashboard aggregates state → region. Min 30 orders threshold enforced
# in dashboard.py (suppress sparse cells as grey) — not here.
# ---------------------------------------------------------------------------

def gen_geo_delivery(engine, project: str, dataset: str) -> pd.DataFrame:
    print("  Querying geo_delivery...")
    sql = f"""
    WITH order_delivery AS (
        SELECT
            dc.customer_state,
            dd.year,
            dd.month,
            fs.order_id,
            fs.order_status,
            fs.order_delivered_customer_date,
            fs.order_estimated_delivery_date
        FROM {T(project, dataset, 'fct_sales')} fs
        JOIN {T(project, dataset, 'dim_date')} dd
            ON fs.date_key = dd.date_key
        JOIN {T(project, dataset, 'dim_customers')} dc
            ON fs.customer_unique_id = dc.customer_unique_id
        WHERE {OBS_FILTER}
        -- Deduplicate to order level (fct_sales is item-level)
        QUALIFY ROW_NUMBER() OVER (PARTITION BY fs.order_id ORDER BY fs.order_item_id) = 1
    )
    SELECT
        customer_state,
        year,
        month,
        COUNT(DISTINCT order_id)                                        AS order_count,
        COUNTIF(order_status = 'delivered'
                AND order_delivered_customer_date IS NOT NULL
                AND order_delivered_customer_date <= order_estimated_delivery_date)
                                                                         AS on_time_count,
        SAFE_DIVIDE(
            COUNTIF(order_status = 'delivered'
                    AND order_delivered_customer_date IS NOT NULL
                    AND order_delivered_customer_date <= order_estimated_delivery_date),
            COUNTIF(order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL)
        )                                                                AS on_time_rate,
        AVG(
            CASE WHEN order_status = 'delivered'
                      AND order_delivered_customer_date IS NOT NULL
                 THEN TIMESTAMP_DIFF(
                          order_delivered_customer_date,
                          order_estimated_delivery_date,
                          DAY)
            END
        )                                                                AS avg_delay_days
    FROM order_delivery
    GROUP BY customer_state, year, month
    """
    df = pd.read_sql(sql, engine)
    df = add_region(df, "customer_state")
    print(f"    {len(df):,} state×month cells")
    return df


# ---------------------------------------------------------------------------
# Parquet 5: seller_performance.parquet
# Seller granularity. Full observation window only (no time filter on seller).
# avg_review_score attributes each review to all sellers in that order — known
# approximation for multi-seller orders (most orders are single-seller).
# ---------------------------------------------------------------------------

def gen_seller_performance(engine, project: str, dataset: str) -> pd.DataFrame:
    print("  Querying seller_performance...")
    sql = f"""
    WITH
    -- One row per order_id in fct_reviews (deduplicate multi-review orders).
    -- Mirrors the deduplication in gen_satisfaction_summary (C-02 fix).
    reviews_deduped AS (
        SELECT
            order_id,
            review_score
        FROM (
            SELECT
                order_id,
                review_score,
                ROW_NUMBER() OVER (
                    PARTITION BY order_id
                    ORDER BY review_answer_timestamp DESC
                ) AS rn
            FROM {T(project, dataset, 'fct_reviews')}
        )
        WHERE rn = 1
    ),
    -- One row per (seller_id, order_id). AVG(review_score) in seller_agg will
    -- then operate on one score per order, not one score per item (C-03 fix).
    seller_orders AS (
        SELECT
            fs.seller_id,
            fs.order_id,
            SUM(fs.total_sale_amount)             AS order_gmv,
            MAX(fs.order_status)                  AS order_status,
            MAX(fs.order_delivered_customer_date) AS delivered_date,
            MAX(fs.order_estimated_delivery_date) AS estimated_date,
            MAX(rd.review_score)                  AS review_score
        FROM {T(project, dataset, 'fct_sales')} fs
        JOIN {T(project, dataset, 'dim_date')} dd
            ON fs.date_key = dd.date_key
        LEFT JOIN reviews_deduped rd
            ON fs.order_id = rd.order_id
        WHERE {OBS_FILTER}
        GROUP BY fs.seller_id, fs.order_id
    ),
    seller_agg AS (
        SELECT
            seller_id,
            COUNT(DISTINCT order_id)   AS order_count,
            SUM(order_gmv)             AS gmv,
            SAFE_DIVIDE(
                COUNTIF(order_status = 'delivered'
                        AND delivered_date IS NOT NULL
                        AND delivered_date <= estimated_date),
                COUNTIF(order_status = 'delivered'
                        AND delivered_date IS NOT NULL)
            )                          AS on_time_rate,
            SAFE_DIVIDE(
                COUNTIF(order_status IN ('canceled', 'unavailable')),
                COUNT(DISTINCT order_id)
            )                          AS cancellation_rate,
            AVG(review_score)          AS avg_review_score
        FROM seller_orders
        GROUP BY seller_id
    )
    SELECT
        sa.seller_id,
        sa.order_count,
        sa.gmv,
        sa.on_time_rate,
        sa.cancellation_rate,
        sa.avg_review_score,
        ds.seller_state,
        ds.seller_city,
        ds.geolocation_lat,
        ds.geolocation_lng
    FROM seller_agg sa
    JOIN {T(project, dataset, 'dim_sellers')} ds
        ON sa.seller_id = ds.seller_id
    """
    df = pd.read_sql(sql, engine)
    df = add_region(df, "seller_state")
    print(f"    {len(df):,} sellers")
    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate dashboard Parquet files from BigQuery analytics dataset."
    )
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--dataset", default="olist_analytics", help="BigQuery dataset name (default: olist_analytics)")
    args = parser.parse_args()

    DATA_DIR.mkdir(exist_ok=True)

    print(f"Connecting to bigquery://{args.project}/{args.dataset}")
    engine = get_engine(args.project, args.dataset)

    tasks = [
        ("sales_orders",        gen_sales_orders),
        ("customer_rfm",        gen_customer_rfm),
        ("satisfaction_summary",gen_satisfaction_summary),
        ("geo_delivery",        gen_geo_delivery),
        ("seller_performance",  gen_seller_performance),
    ]

    for name, fn in tasks:
        path = DATA_DIR / f"{name}.parquet"
        print(f"\n[{name}.parquet]")
        df = fn(engine, args.project, args.dataset)
        df.to_parquet(path, index=False)
        print(f"  ✓ Saved to {path.relative_to(ROOT)}")

    print("\nDone. All 5 Parquet files written to data/")
    print("Commit data/*.parquet before running dashboard.py — do NOT add to .gitignore.")


if __name__ == "__main__":
    main()
