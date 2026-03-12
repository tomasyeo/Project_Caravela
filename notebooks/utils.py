"""
utils.py
Project Caravela — Olist E-Commerce Analytics Pipeline

Canonical constants and helpers shared by all analytical notebooks and
dashboard.py. Import this module; do NOT redefine these values locally.

Usage:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))   # or .parent.parent from scripts/
    from utils import REGION_MAP, SEGMENT_COLOURS, REGION_COLOURS, STATUS_COLOURS, add_region
"""

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

def add_region(df, state_col: str):
    """Add a region column derived from a state code column.

    Args:
        df:        pandas DataFrame containing state_col.
        state_col: Column name holding 2-letter Brazilian state codes
                   (e.g. 'customer_state', 'seller_state').

    Returns:
        df with an added column whose name is derived by replacing
        '_state' with '_region' in state_col
        (e.g. 'customer_state' → 'customer_region').
        Unknown state codes are mapped to 'Unknown'.
    """
    out_col = state_col.replace("_state", "_region")
    df[out_col] = df[state_col].map(REGION_MAP).fillna("Unknown")
    return df
