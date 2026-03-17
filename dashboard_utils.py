"""
dashboard_utils.py
Project Caravela — shared loaders, filter helpers, and sidebar renderer.

All page files import from here. Never query BigQuery — Parquet only.
"""
import sys
import json
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

# ── Repo-root on sys.path so pages can do: from notebooks.utils import ... ──
_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ── Constants ────────────────────────────────────────────────────────────────
_DATE_MIN = date(2017, 1, 1)
_DATE_MAX = date(2018, 8, 31)
_REGIONS  = ["Central-West", "North", "Northeast", "South", "Southeast"]

# ── Parquet loaders (cached) ─────────────────────────────────────────────────

@st.cache_data
def load_sales_orders():
    """Order-item granularity. 112,279 rows. Use drop_duplicates('order_id') for order-level metrics."""
    return pd.read_parquet(_ROOT / "data" / "sales_orders.parquet")

@st.cache_data
def load_customer_rfm():
    """Customer granularity. 95,420 rows. Fixed ref date 2018-08-31."""
    return pd.read_parquet(_ROOT / "data" / "customer_rfm.parquet")

@st.cache_data
def load_satisfaction_summary():
    """Review granularity. 97,379 rows (~244 dupes). Use drop_duplicates('order_id') for order-level."""
    return pd.read_parquet(_ROOT / "data" / "satisfaction_summary.parquet")

@st.cache_data
def load_geo_delivery():
    """State × month granularity. 533 rows. Has 'region' column (not 'customer_region')."""
    return pd.read_parquet(_ROOT / "data" / "geo_delivery.parquet")

@st.cache_data
def load_seller_performance():
    """Seller granularity. 3,068 rows. Full-period only (Jan 2017 – Aug 2018)."""
    return pd.read_parquet(_ROOT / "data" / "seller_performance.parquet")

@st.cache_data
def load_concentration_metrics():
    """Pre-computed Gini / CR4 / CR10 / HHI. 83 rows across 5 dimensions."""
    return pd.read_parquet(_ROOT / "data" / "concentration_metrics.parquet")

@st.cache_data
def load_geojson():
    """Brazil state boundaries. featureidkey='properties.sigla' matches 2-letter state codes."""
    with open(_ROOT / "data" / "brazil_states.geojson") as f:
        return json.load(f)

# ── Filter state initialisation ──────────────────────────────────────────────

def init_filters():
    """Initialise global filter keys in session_state. Safe to call multiple times."""
    defaults = {
        "date_start":       _DATE_MIN,
        "date_end":         _DATE_MAX,
        "category_filter":  [],
        "state_filter":     [],
        "region_filter":    [],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

# ── Sidebar renderer ─────────────────────────────────────────────────────────

def render_sidebar_filters(sales_df=None):
    """Render 4 sidebar filter widgets and sync to session_state."""
    init_filters()
    with st.sidebar:
        st.header("🔍 Filters")

        # Date range
        date_range = st.date_input(
            "Date Range",
            value=(st.session_state.date_start, st.session_state.date_end),
            min_value=_DATE_MIN,
            max_value=_DATE_MAX,
        )
        if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
            st.session_state.date_start = date_range[0]
            st.session_state.date_end   = date_range[1]

        # Product Category
        cats = (
            sorted(sales_df["product_category_name_english"].dropna().unique().tolist())
            if sales_df is not None else []
        )
        # Use key= so Streamlit manages session_state sync automatically.
        # Passing default= AND manually assigning the return value causes the
        # "double rerun" bug where the second multiselect click is dropped.
        st.multiselect("Product Category", cats, key="category_filter")

        # State
        states = (
            sorted(sales_df["customer_state"].dropna().unique().tolist())
            if sales_df is not None else []
        )
        st.multiselect("State", states, key="state_filter")

        # Region
        st.multiselect("Region", _REGIONS, key="region_filter")

        # Reset button — use on_click callback so session state is cleared
        # BEFORE the next render cycle. Direct mutation in script body fails
        # for keys owned by keyed widgets (StreamlitAPIException).
        def _reset():
            st.session_state.date_start      = _DATE_MIN
            st.session_state.date_end        = _DATE_MAX
            st.session_state.category_filter = []
            st.session_state.state_filter    = []
            st.session_state.region_filter   = []

        st.button("↺ Reset Filters", on_click=_reset, use_container_width=True)

        # Active filter summary
        _active = []
        if (st.session_state.date_start != _DATE_MIN
                or st.session_state.date_end != _DATE_MAX):
            _active.append("Date")
        if st.session_state.category_filter:
            n = len(st.session_state.category_filter)
            _active.append(f"{n} category" if n == 1 else f"{n} categories")
        if st.session_state.state_filter:
            n = len(st.session_state.state_filter)
            _active.append(f"{n} state" if n == 1 else f"{n} states")
        if st.session_state.region_filter:
            n = len(st.session_state.region_filter)
            _active.append(f"{n} region" if n == 1 else f"{n} regions")

        if _active:
            st.caption(f"Active: {', '.join(_active)}")
        else:
            st.caption("No active filters — showing all data")

# ── Filter application helpers ────────────────────────────────────────────────

def apply_filters(
    df,
    date_col="date_key",
    cat_col="product_category_name_english",
    state_col="customer_state",
    region_col="customer_region",
):
    """Apply all 4 session_state filters to a DataFrame. Empty list = show all."""
    fdf = df
    if date_col in fdf.columns:
        fdf = fdf[fdf[date_col] >= pd.Timestamp(st.session_state.date_start)]
        fdf = fdf[fdf[date_col] <= pd.Timestamp(st.session_state.date_end)]
    if st.session_state.category_filter and cat_col in fdf.columns:
        fdf = fdf[fdf[cat_col].isin(st.session_state.category_filter)]
    if st.session_state.state_filter and state_col in fdf.columns:
        fdf = fdf[fdf[state_col].isin(st.session_state.state_filter)]
    if st.session_state.region_filter and region_col in fdf.columns:
        fdf = fdf[fdf[region_col].isin(st.session_state.region_filter)]
    return fdf


def apply_geo_filters(df):
    """Filter geo_delivery by year/month (no date_key) + customer_state + region.
    Note: geo_delivery uses 'region' not 'customer_region'."""
    fdf = df.copy()
    fdf["_ym"] = fdf["year"] * 100 + fdf["month"]
    start_ym = st.session_state.date_start.year * 100 + st.session_state.date_start.month
    end_ym   = st.session_state.date_end.year   * 100 + st.session_state.date_end.month
    fdf = fdf[(fdf["_ym"] >= start_ym) & (fdf["_ym"] <= end_ym)]
    if st.session_state.state_filter:
        fdf = fdf[fdf["customer_state"].isin(st.session_state.state_filter)]
    if st.session_state.region_filter:
        fdf = fdf[fdf["region"].isin(st.session_state.region_filter)]
    return fdf.drop(columns=["_ym"])


def apply_rfm_filters(df):
    """Apply only state + region filters to customer_rfm (date/category not applicable)."""
    fdf = df
    if st.session_state.state_filter:
        fdf = fdf[fdf["customer_state"].isin(st.session_state.state_filter)]
    if st.session_state.region_filter:
        fdf = fdf[fdf["customer_region"].isin(st.session_state.region_filter)]
    return fdf


def apply_seller_filters(df):
    """Apply only state + region filters to seller_performance (no date/category)."""
    fdf = df
    if st.session_state.state_filter:
        fdf = fdf[fdf["seller_state"].isin(st.session_state.state_filter)]
    if st.session_state.region_filter:
        fdf = fdf[fdf["seller_region"].isin(st.session_state.region_filter)]
    return fdf

# ── Shared helpers ────────────────────────────────────────────────────────────

def make_period(df):
    """Return YYYY-MM string column from integer year/month columns."""
    return df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2)
