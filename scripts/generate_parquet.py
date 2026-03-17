"""
generate_parquet.py
Project Caravela — Olist E-Commerce Analytics Pipeline

Quick-setup script: produces all 6 dashboard Parquet files directly from the
BigQuery analytics dataset without running the full Jupyter notebooks.

Run once after `dbt build` completes and before launching dashboard.py.
Output is schema-identical to what the 3 analytical notebooks produce.

Prerequisites
-------------
  - GCP_PROJECT_ID env var set
  - GOOGLE_APPLICATION_CREDENTIALS env var → service account JSON key path
  - BigQuery analytics dataset fully populated (dbt build succeeded)
  - pip install google-cloud-bigquery pandas pyarrow numpy

Usage
-----
    conda activate assignment2
    python scripts/generate_parquet.py

    # Optional: override dataset (default: olist_analytics)
    python scripts/generate_parquet.py --dataset olist_analytics

Output
------
  data/sales_orders.parquet          — order-item granularity (~112k rows, 15 cols)
  data/customer_rfm.parquet          — customer granularity (~96k rows, 10 cols)
  data/satisfaction_summary.parquet   — order granularity (~97k rows, 11 cols)
  data/geo_delivery.parquet          — state × month granularity (~540 rows, 8 cols)
  data/seller_performance.parquet    — seller granularity (~3k rows, 7 cols)
  data/concentration_metrics.parquet — summary metrics (~83 rows, 8 cols)
"""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from google.cloud import bigquery

# Load .env from project root (same file notebooks use)
load_dotenv(Path(__file__).parent.parent / ".env")

# Resolve project root and import shared utils
ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
sys.path.insert(0, str(ROOT / "notebooks"))
from utils import (  # noqa: E402
    REGION_MAP, add_region,
    lorenz_curve, gini_coefficient, hhi, concentration_summary,
)

# RFM reference date — hardcoded per ASMP-022; do NOT use CURRENT_DATE or MAX()
RFM_REF_DATE = "2018-08-31"

# Observation window: Jan 2017 – Aug 2018 (20 complete months)
# ASMP-025: 2018-09/10 are data cut artefacts; 2016 excluded from trend analyses.
OBS_START = "2017-01-01"
OBS_END = "2018-08-31"


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def get_client(project_id: str) -> bigquery.Client:
    """BigQuery client using google-cloud-bigquery (matches notebook pattern)."""
    return bigquery.Client(project=project_id)


def run_query(client: bigquery.Client, sql: str) -> pd.DataFrame:
    """Execute a BigQuery SQL query and return a DataFrame."""
    return client.query(sql).to_dataframe()


# ---------------------------------------------------------------------------
# Parquet 1: sales_orders.parquet
# Order-item granularity (15 columns). Used by Executive Overview and Product
# Performance pages. primary_payment_type / primary_payment_installments use
# payment_sequential=1 (~3% approximation for split-payment orders).
# ---------------------------------------------------------------------------

def gen_sales_orders(client: bigquery.Client, project: str, dataset: str) -> pd.DataFrame:
    print("  Querying sales_orders...")
    sql = f"""
    SELECT
        fs.order_id,
        fs.order_item_id,
        fs.product_id,
        dp.product_category_name_english,
        fs.date_key,
        d.year,
        d.month,
        fs.order_status,
        fs.total_sale_amount,
        fs.price,
        fs.freight_value,
        fp.payment_type         AS primary_payment_type,
        fp.payment_installments AS primary_payment_installments,
        dc.customer_state
    FROM `{project}.{dataset}.fct_sales` fs
    JOIN `{project}.{dataset}.dim_date` d ON fs.date_key = d.date_key
    JOIN `{project}.{dataset}.dim_customers` dc ON fs.customer_unique_id = dc.customer_unique_id
    JOIN `{project}.{dataset}.dim_products` dp ON fs.product_id = dp.product_id
    LEFT JOIN `{project}.{dataset}.fct_payments` fp
        ON fs.order_id = fp.order_id AND fp.payment_sequential = 1
    WHERE fs.date_key >= '{OBS_START}' AND fs.date_key <= '{OBS_END}'
    """
    df = run_query(client, sql)
    df["year"] = df["year"].astype("int64")
    df["month"] = df["month"].astype("int64")
    df = add_region(df, "customer_state")
    # Select exact columns in contract order
    cols = [
        "order_id", "order_item_id", "product_id", "product_category_name_english",
        "date_key", "year", "month", "order_status", "total_sale_amount",
        "price", "freight_value", "primary_payment_type",
        "primary_payment_installments", "customer_state", "customer_region",
    ]
    print(f"    {len(df):,} rows")
    return df[cols]


# ---------------------------------------------------------------------------
# Parquet 2: customer_rfm.parquet
# Customer granularity (10 columns). RFM scoring applied in Python.
# Segments: Champions, Loyal, Promising, At Risk, High Value Lost, Hibernating.
# ---------------------------------------------------------------------------

def _assign_segment(r_score: int, f_tier: str) -> str:
    """Assign RFM segment from R_score (1–5) and F_tier (F1/F2/F3).

    Checked in priority order — Champions before Loyal to resolve overlap.
    """
    r = int(r_score)
    if r >= 4 and f_tier == "F3":
        return "Champions"
    if r >= 3 and f_tier in ("F2", "F3"):
        return "Loyal"
    if r >= 4 and f_tier == "F1":
        return "Promising"
    if r <= 2 and f_tier == "F3":
        return "High Value Lost"
    if r <= 2 and f_tier in ("F2", "F3"):
        return "At Risk"
    return "Hibernating"  # r <= 3, F1 (the dominant bucket)


def gen_customer_rfm(client: bigquery.Client, project: str, dataset: str) -> pd.DataFrame:
    print("  Querying customer_rfm base...")
    sql = f"""
    SELECT
        s.customer_unique_id,
        c.customer_state,
        DATE_DIFF(DATE '{RFM_REF_DATE}', MAX(s.date_key), DAY) AS recency_days,
        COUNT(DISTINCT s.order_id) AS frequency,
        SUM(s.total_sale_amount) AS monetary_value
    FROM `{project}.{dataset}.fct_sales` s
    JOIN `{project}.{dataset}.dim_customers` c
        ON s.customer_unique_id = c.customer_unique_id
    WHERE s.date_key <= '{RFM_REF_DATE}'
    GROUP BY s.customer_unique_id, c.customer_state
    """
    df = run_query(client, sql)
    df["recency_days"] = df["recency_days"].astype("int64")
    df["frequency"] = df["frequency"].astype("int64")
    print(f"    {len(df):,} customers — scoring RFM...")

    # R_score: quintile 1–5 (lower days = higher score)
    df["r_score"] = pd.qcut(
        df["recency_days"], q=5, labels=[5, 4, 3, 2, 1], duplicates="drop"
    ).astype(int)

    # F_tier: 3-tier (quintiles collapse because 96.9% are single-purchase)
    df["f_tier"] = df["frequency"].apply(
        lambda x: "F1" if x == 1 else ("F2" if x == 2 else "F3")
    )

    # M_score: quintile 1–5
    df["m_score"] = pd.qcut(
        df["monetary_value"].rank(method="first"), q=5,
        labels=[1, 2, 3, 4, 5], duplicates="drop"
    ).astype(int)

    # Segment assignment (RF-only)
    df["segment"] = df.apply(
        lambda row: _assign_segment(row["r_score"], row["f_tier"]), axis=1
    )

    df = add_region(df, "customer_state")
    cols = [
        "customer_unique_id", "customer_state", "customer_region",
        "recency_days", "frequency", "monetary_value",
        "r_score", "f_tier", "m_score", "segment",
    ]
    print(f"    Segment distribution:\n{df['segment'].value_counts().to_string()}")
    return df[cols]


# ---------------------------------------------------------------------------
# Parquet 3: satisfaction_summary.parquet
# Order granularity (11 columns). Combines fct_sales + fct_reviews.
# primary_product_category = category of the highest-revenue item per order.
# ---------------------------------------------------------------------------

def gen_satisfaction_summary(client: bigquery.Client, project: str, dataset: str) -> pd.DataFrame:
    print("  Querying satisfaction_summary...")

    # Order-level delivery info + reviews
    sql = f"""
    WITH order_delivery AS (
        SELECT DISTINCT
            s.order_id,
            s.customer_unique_id,
            s.date_key,
            s.order_delivered_customer_date,
            s.order_estimated_delivery_date
        FROM `{project}.{dataset}.fct_sales` s
        WHERE s.date_key >= '{OBS_START}' AND s.date_key <= '{OBS_END}'
    ),
    primary_category AS (
        SELECT
            s.order_id,
            ARRAY_AGG(p.product_category_name_english
                      ORDER BY s.total_sale_amount DESC LIMIT 1)[OFFSET(0)]
                AS primary_product_category
        FROM `{project}.{dataset}.fct_sales` s
        JOIN `{project}.{dataset}.dim_products` p ON s.product_id = p.product_id
        WHERE s.date_key >= '{OBS_START}' AND s.date_key <= '{OBS_END}'
        GROUP BY s.order_id
    ),
    reviews_deduped AS (
        SELECT order_id, review_score
        FROM (
            SELECT order_id, review_score,
                   ROW_NUMBER() OVER (PARTITION BY order_id
                                      ORDER BY review_answer_timestamp DESC) AS rn
            FROM `{project}.{dataset}.fct_reviews`
        )
        WHERE rn = 1
    )
    SELECT
        od.order_id,
        r.review_score,
        CASE
            WHEN r.review_score >= 4 THEN 'promoter'
            WHEN r.review_score = 3 THEN 'passive'
            WHEN r.review_score <= 2 THEN 'detractor'
        END AS nps_category,
        TIMESTAMP_DIFF(od.order_delivered_customer_date,
                       od.order_estimated_delivery_date, DAY) AS delivery_delay_days,
        od.date_key,
        d.year,
        d.month,
        c.customer_state,
        pc.primary_product_category
    FROM order_delivery od
    JOIN `{project}.{dataset}.dim_date` d ON od.date_key = d.date_key
    JOIN `{project}.{dataset}.dim_customers` c ON od.customer_unique_id = c.customer_unique_id
    LEFT JOIN reviews_deduped r ON od.order_id = r.order_id
    LEFT JOIN primary_category pc ON od.order_id = pc.order_id
    """
    df = run_query(client, sql)
    df["year"] = df["year"].astype("int64")
    df["month"] = df["month"].astype("int64")

    # Delay bins (matching notebook: early / on-time / 1–3d late / 4–7d late / 7+d late)
    def _delay_bin(d):
        if pd.isna(d):
            return None
        d = float(d)
        if d < 0:
            return "early"
        if d == 0:
            return "on-time"
        if d <= 3:
            return "1-3d late"
        if d <= 7:
            return "4-7d late"
        return "7+d late"

    df["delay_bin"] = df["delivery_delay_days"].apply(_delay_bin)

    df = add_region(df, "customer_state")
    cols = [
        "order_id", "review_score", "nps_category", "delivery_delay_days",
        "delay_bin", "date_key", "year", "month", "customer_state",
        "customer_region", "primary_product_category",
    ]
    print(f"    {len(df):,} orders")
    return df[cols]


# ---------------------------------------------------------------------------
# Parquet 4: geo_delivery.parquet
# State × month granularity (8 columns). Dashboard aggregates state → region.
# Min 30 orders threshold enforced in dashboard.py — not here.
# ---------------------------------------------------------------------------

def gen_geo_delivery(client: bigquery.Client, project: str, dataset: str) -> pd.DataFrame:
    print("  Querying geo_delivery...")
    sql = f"""
    WITH order_level AS (
        SELECT DISTINCT
            order_id, customer_unique_id, date_key,
            order_delivered_customer_date, order_estimated_delivery_date
        FROM `{project}.{dataset}.fct_sales`
        WHERE order_delivered_customer_date IS NOT NULL
          AND date_key >= '{OBS_START}' AND date_key <= '{OBS_END}'
    )
    SELECT
        c.customer_state,
        d.year,
        d.month,
        COUNT(DISTINCT o.order_id) AS total_orders,
        COUNTIF(o.order_delivered_customer_date <= o.order_estimated_delivery_date)
            AS on_time_orders,
        ROUND(AVG(TIMESTAMP_DIFF(o.order_delivered_customer_date,
                                  o.order_estimated_delivery_date, DAY)), 2)
            AS avg_delay_days
    FROM order_level o
    JOIN `{project}.{dataset}.dim_customers` c ON o.customer_unique_id = c.customer_unique_id
    JOIN `{project}.{dataset}.dim_date` d ON o.date_key = d.date_key
    GROUP BY c.customer_state, d.year, d.month
    """
    df = run_query(client, sql)
    df["year"] = df["year"].astype("int64")
    df["month"] = df["month"].astype("int64")
    df["total_orders"] = df["total_orders"].astype("int64")
    df["on_time_orders"] = df["on_time_orders"].astype("int64")
    df["on_time_rate"] = (df["on_time_orders"] / df["total_orders"]).round(4)
    df = add_region(df, "customer_state")
    df = df.rename(columns={"customer_region": "region"})
    cols = [
        "customer_state", "region", "year", "month",
        "total_orders", "on_time_orders", "on_time_rate", "avg_delay_days",
    ]
    print(f"    {len(df):,} state×month cells")
    return df[cols]


# ---------------------------------------------------------------------------
# Parquet 5: seller_performance.parquet
# Seller granularity (7 columns). Full period Jan 2017 – Aug 2018.
# Cancellation rate: COUNT(DISTINCT canceled order_id) / COUNT(DISTINCT order_id).
# ---------------------------------------------------------------------------

def gen_seller_performance(client: bigquery.Client, project: str, dataset: str) -> pd.DataFrame:
    print("  Querying seller_performance...")
    sql = f"""
    WITH seller_orders AS (
        SELECT
            s.seller_id,
            s.order_id,
            s.total_sale_amount,
            s.order_status
        FROM `{project}.{dataset}.fct_sales` s
        WHERE s.date_key >= '{OBS_START}' AND s.date_key <= '{OBS_END}'
    ),
    seller_reviews AS (
        SELECT
            s.seller_id,
            AVG(r.review_score) AS avg_review_score
        FROM `{project}.{dataset}.fct_sales` s
        JOIN `{project}.{dataset}.fct_reviews` r ON s.order_id = r.order_id
        WHERE s.date_key >= '{OBS_START}' AND s.date_key <= '{OBS_END}'
        GROUP BY s.seller_id
    )
    SELECT
        so.seller_id,
        ds.seller_state,
        SUM(so.total_sale_amount) AS gmv,
        COUNT(DISTINCT so.order_id) AS order_count,
        SAFE_DIVIDE(
            COUNT(DISTINCT CASE WHEN so.order_status = 'canceled' THEN so.order_id END),
            COUNT(DISTINCT so.order_id)
        ) AS cancellation_rate,
        sr.avg_review_score
    FROM seller_orders so
    JOIN `{project}.{dataset}.dim_sellers` ds ON so.seller_id = ds.seller_id
    LEFT JOIN seller_reviews sr ON so.seller_id = sr.seller_id
    GROUP BY so.seller_id, ds.seller_state, sr.avg_review_score
    """
    df = run_query(client, sql)
    df = add_region(df, "seller_state")
    df["cancellation_rate"] = df["cancellation_rate"].astype(float).round(4)
    df["order_count"] = df["order_count"].astype("int64")
    cols = [
        "seller_id", "seller_state", "seller_region",
        "gmv", "order_count", "avg_review_score", "cancellation_rate",
    ]
    print(f"    {len(df):,} sellers")
    return df[cols]


# ---------------------------------------------------------------------------
# Parquet 6: concentration_metrics.parquet
# Pre-computed Gini, CR4, CR10, HHI across 5 dimensions (8 columns, ~83 rows).
# Matches NB03 export — self-contained from other Parquets.
# ---------------------------------------------------------------------------

def gen_concentration_metrics(
    client: bigquery.Client, project: str, dataset: str,
    seller_perf: pd.DataFrame,
) -> pd.DataFrame:
    print("  Computing concentration_metrics...")
    all_metrics = []

    # 1. Seller GMV (overall)
    s = concentration_summary(seller_perf["gmv"].values, name="seller_gmv")
    s["group_key"] = "overall"
    all_metrics.append(s)

    # 2. Seller GMV (monthly)
    monthly_seller = run_query(client, f"""
        SELECT d.year, d.month, s.seller_id,
               SUM(s.total_sale_amount) AS gmv
        FROM `{project}.{dataset}.fct_sales` s
        JOIN `{project}.{dataset}.dim_date` d ON s.date_key = d.date_key
        WHERE s.date_key >= '{OBS_START}' AND s.date_key <= '{OBS_END}'
        GROUP BY d.year, d.month, s.seller_id
    """)
    monthly_seller["period"] = (
        monthly_seller["year"].astype(str) + "-"
        + monthly_seller["month"].astype(str).str.zfill(2)
    )
    for period, grp in monthly_seller.groupby("period"):
        if len(grp) >= 50:
            stats = concentration_summary(grp["gmv"].values, name="seller_gmv_monthly")
            stats["group_key"] = period
            stats["n_entities"] = len(grp)
            all_metrics.append(stats)

    # 3. Category seller concentration (≥10 sellers per category)
    cat_seller = run_query(client, f"""
        SELECT p.product_category_name_english AS category,
               s.seller_id,
               SUM(s.total_sale_amount) AS gmv
        FROM `{project}.{dataset}.fct_sales` s
        JOIN `{project}.{dataset}.dim_products` p ON s.product_id = p.product_id
        WHERE s.date_key >= '{OBS_START}' AND s.date_key <= '{OBS_END}'
        GROUP BY p.product_category_name_english, s.seller_id
    """)
    for cat, grp in cat_seller.groupby("category"):
        if len(grp) >= 10:
            stats = concentration_summary(grp["gmv"].values, name="category_seller_gmv")
            stats["group_key"] = cat
            all_metrics.append(stats)

    # 4. Customer monetary (from customer_rfm.parquet)
    rfm_pq = pd.read_parquet(DATA_DIR / "customer_rfm.parquet")
    cs = concentration_summary(rfm_pq["monetary_value"].values, name="customer_monetary")
    cs["group_key"] = "overall"
    all_metrics.append(cs)

    # 5. Category revenue (from sales_orders.parquet)
    sales_pq = pd.read_parquet(DATA_DIR / "sales_orders.parquet")
    cat_rev = sales_pq.groupby("product_category_name_english")["total_sale_amount"].sum().values
    cr = concentration_summary(cat_rev, name="category_revenue")
    cr["group_key"] = "overall"
    all_metrics.append(cr)

    # Assemble
    df = pd.DataFrame(all_metrics)[[
        "dimension", "group_key", "gini", "cr4", "cr10", "hhi",
        "n_entities", "top_20pct_share",
    ]]
    df["n_entities"] = df["n_entities"].astype("int64")
    print(f"    {len(df):,} rows ({df['dimension'].nunique()} dimensions)")
    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate dashboard Parquet files from BigQuery analytics dataset."
    )
    parser.add_argument(
        "--project",
        default=os.environ.get("GCP_PROJECT_ID"),
        help="GCP project ID (default: $GCP_PROJECT_ID)",
    )
    parser.add_argument(
        "--dataset",
        default=os.environ.get("BIGQUERY_ANALYTICS_DATASET", "olist_analytics"),
        help="BigQuery dataset name (default: $BIGQUERY_ANALYTICS_DATASET or olist_analytics)",
    )
    args = parser.parse_args()

    if not args.project:
        print("ERROR: --project not provided and GCP_PROJECT_ID not set.")
        sys.exit(1)

    DATA_DIR.mkdir(exist_ok=True)

    print(f"Connecting to BigQuery project={args.project}, dataset={args.dataset}")
    client = get_client(args.project)

    # Generate in order (concentration_metrics depends on rfm + sales Parquets)
    tasks = [
        ("sales_orders", lambda: gen_sales_orders(client, args.project, args.dataset)),
        ("customer_rfm", lambda: gen_customer_rfm(client, args.project, args.dataset)),
        ("satisfaction_summary", lambda: gen_satisfaction_summary(client, args.project, args.dataset)),
        ("geo_delivery", lambda: gen_geo_delivery(client, args.project, args.dataset)),
        ("seller_performance", lambda: gen_seller_performance(client, args.project, args.dataset)),
    ]

    results = {}
    for name, fn in tasks:
        path = DATA_DIR / f"{name}.parquet"
        print(f"\n[{name}.parquet]")
        df = fn()
        df.to_parquet(path, index=False)
        results[name] = df
        print(f"  -> Saved to {path.relative_to(ROOT)} ({len(df):,} rows, {len(df.columns)} cols)")

    # concentration_metrics depends on seller_performance + rfm + sales Parquets
    name = "concentration_metrics"
    path = DATA_DIR / f"{name}.parquet"
    print(f"\n[{name}.parquet]")
    df = gen_concentration_metrics(
        client, args.project, args.dataset,
        seller_perf=results["seller_performance"],
    )
    df.to_parquet(path, index=False)
    print(f"  -> Saved to {path.relative_to(ROOT)} ({len(df):,} rows, {len(df.columns)} cols)")

    print("\nDone. All 6 Parquet files written to data/")
    print("Commit data/*.parquet before running dashboard.py — do NOT add to .gitignore.")


if __name__ == "__main__":
    main()
