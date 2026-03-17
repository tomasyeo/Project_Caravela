"""
utils.py
Project Caravela — Olist E-Commerce Analytics Pipeline

Canonical constants and helpers shared by all analytical notebooks and
dashboard.py. Import this module; do NOT redefine these values locally.

Usage:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))   # or .parent.parent from scripts/
    from utils import (
        REGION_MAP, SEGMENT_COLOURS, REGION_COLOURS, STATUS_COLOURS,
        add_region, lorenz_curve, gini_coefficient, hhi, concentration_summary,
    )
"""

import numpy as np

# ---------------------------------------------------------------------------
# Geographic: Brazilian state → IBGE macro-region mapping
# 26 states + 1 Federal District (DF) = 27 entries
# ---------------------------------------------------------------------------

REGION_MAP: dict[str, str] = {
    # North (7)
    "AM": "North", "AC": "North", "RO": "North",
    "RR": "North", "AP": "North", "PA": "North", "TO": "North",
    # Northeast (9)
    "MA": "Northeast", "PI": "Northeast", "CE": "Northeast",
    "RN": "Northeast", "PB": "Northeast", "PE": "Northeast",
    "AL": "Northeast", "SE": "Northeast", "BA": "Northeast",
    # Central-West (3 states + DF)
    "MT": "Central-West", "MS": "Central-West",
    "GO": "Central-West", "DF": "Central-West",
    # Southeast (4)
    "MG": "Southeast", "ES": "Southeast",
    "RJ": "Southeast", "SP": "Southeast",
    # South (3)
    "PR": "South", "SC": "South", "RS": "South",
}

# ---------------------------------------------------------------------------
# Colour palettes — consistent across notebooks and dashboard
# ---------------------------------------------------------------------------

# 6 RFM segment colours (green=best, red=dormant)
SEGMENT_COLOURS: dict[str, str] = {
    "Champions":       "#2ecc71",   # bright green
    "Loyal":           "#27ae60",   # dark green
    "Promising":       "#f1c40f",   # yellow
    "At Risk":         "#e67e22",   # orange
    "High Value Lost": "#e74c3c",   # red
    "Hibernating":     "#95a5a6",   # grey
}

# 5 region colours — chosen for distinctness on adjacent choropleth areas
REGION_COLOURS: dict[str, str] = {
    "Southeast":   "#3498db",   # blue  (largest market, centre-right)
    "South":       "#27ae60",   # green (adjacent to Southeast — contrast needed)
    "Central-West":"#9b59b6",   # purple
    "Northeast":   "#e67e22",   # orange
    "North":       "#e74c3c",   # red
}

# 8 order status colours
STATUS_COLOURS: dict[str, str] = {
    "delivered":    "#2ecc71",   # green
    "shipped":      "#3498db",   # blue
    "invoiced":     "#f1c40f",   # yellow
    "processing":   "#f39c12",   # amber
    "approved":     "#95a5a6",   # grey-blue
    "created":      "#bdc3c7",   # light grey
    "canceled":     "#e74c3c",   # red
    "unavailable":  "#c0392b",   # dark red
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def add_region(df, state_col="customer_state"):
    """Add a region column derived from a state code column.

    Args:
        df:        pandas DataFrame containing state_col.
        state_col: Column name holding 2-letter Brazilian state codes
                   (e.g. 'customer_state', 'seller_state').

    Returns:
        Copy of df with an added column whose name is derived by replacing
        '_state' with '_region' in state_col
        (e.g. 'customer_state' → 'customer_region').
        Unknown state codes are mapped to 'Unknown'.
    """
    df = df.copy()
    out_col = state_col.replace("_state", "_region")
    df[out_col] = df[state_col].map(REGION_MAP).fillna("Unknown")
    return df


def lorenz_curve(values):
    """Compute Lorenz curve coordinates from a 1-D array of non-negative values.

    Args:
        values: array-like of non-negative numbers (e.g. GMV per seller).

    Returns:
        (x, y) tuple of numpy arrays, both starting at (0, 0) and ending at
        (1, 1).  x = cumulative share of population (sorted ascending by value),
        y = cumulative share of total value.
    """
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    v = np.sort(v)
    cumulative = np.cumsum(v)
    x = np.arange(1, len(v) + 1) / len(v)
    y = cumulative / cumulative[-1]
    return np.insert(x, 0, 0.0), np.insert(y, 0, 0.0)


def gini_coefficient(values):
    """Gini coefficient via trapezoidal area under the Lorenz curve.

    Returns a float in [0, 1].  0 = perfect equality, 1 = perfect inequality.
    """
    x, y = lorenz_curve(values)
    return 1.0 - 2.0 * float(np.trapz(y, x))


def hhi(values):
    """Herfindahl-Hirschman Index (HHI) from raw values.

    HHI = sum of squared market shares × 10 000.
    Range: ~0 (perfect competition) to 10 000 (monopoly).
    US DOJ thresholds: <1500 competitive, 1500–2500 moderate, >2500 concentrated.
    """
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    shares = v / v.sum()
    return float(np.sum(shares ** 2) * 10_000)


def concentration_summary(values, name=""):
    """Compute a full suite of concentration metrics for a 1-D value array.

    Returns a dict with keys: dimension, gini, cr4, cr10, hhi, n_entities,
    top_20pct_share.
    """
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    v_sorted = np.sort(v)[::-1]  # descending
    total = v_sorted.sum()
    n = len(v_sorted)
    top_20_n = max(1, int(np.ceil(n * 0.20)))
    return {
        "dimension": name,
        "gini": gini_coefficient(v),
        "cr4": float(v_sorted[:4].sum() / total) if n >= 4 else float("nan"),
        "cr10": float(v_sorted[:10].sum() / total) if n >= 10 else float("nan"),
        "hhi": hhi(v),
        "n_entities": n,
        "top_20pct_share": float(v_sorted[:top_20_n].sum() / total),
    }
