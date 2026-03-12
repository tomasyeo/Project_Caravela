"""
profile_source_data.py
Project Caravela — Olist E-Commerce Analytics Pipeline

Profiles all 9 source CSV files and writes docs/data_profile.json.
Run once from the project root:

    python scripts/profile_source_data.py

Re-run only if source data changes. All BRD test thresholds and staging
transformation decisions are traceable to this output.
"""

import csv
import json
import collections
import os
from datetime import datetime

RAW = "raw_data"
OUT = "docs/data_profile.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load(filename, encoding="utf-8-sig"):
    path = os.path.join(RAW, filename)
    with open(path, encoding=encoding) as f:
        return list(csv.DictReader(f))


def null_counts(rows):
    if not rows:
        return {}
    return {
        col: sum(1 for r in rows if not r[col])
        for col in rows[0].keys()
    }


def value_dist(rows, col):
    return dict(collections.Counter(r[col] for r in rows).most_common())


def numeric_range(rows, col):
    vals = [float(r[col]) for r in rows if r[col]]
    if not vals:
        return {}
    return {"min": min(vals), "max": max(vals), "zero_or_below": sum(1 for v in vals if v <= 0)}


# ---------------------------------------------------------------------------
# Load all files
# ---------------------------------------------------------------------------

print("Loading source files...")

customers   = load("olist_customers_dataset.csv")
orders      = load("olist_orders_dataset.csv")
items       = load("olist_order_items_dataset.csv")
payments    = load("olist_order_payments_dataset.csv")
reviews     = load("olist_order_reviews_dataset.csv")
products    = load("olist_products_dataset.csv")
sellers     = load("olist_sellers_dataset.csv")
geolocation = load("olist_geolocation_dataset.csv")
translation = load("product_category_name_translation.csv")

# ---------------------------------------------------------------------------
# Row counts
# ---------------------------------------------------------------------------

print("Profiling row counts...")

row_counts = {
    "olist_customers_dataset.csv":               len(customers),
    "olist_orders_dataset.csv":                  len(orders),
    "olist_order_items_dataset.csv":             len(items),
    "olist_order_payments_dataset.csv":          len(payments),
    "olist_order_reviews_dataset.csv":           len(reviews),
    "olist_products_dataset.csv":                len(products),
    "olist_sellers_dataset.csv":                 len(sellers),
    "olist_geolocation_dataset.csv":             len(geolocation),
    "product_category_name_translation.csv":     len(translation),
}

# ---------------------------------------------------------------------------
# Column headers
# ---------------------------------------------------------------------------

columns = {
    "customers":   list(customers[0].keys())   if customers   else [],
    "orders":      list(orders[0].keys())       if orders      else [],
    "items":       list(items[0].keys())        if items       else [],
    "payments":    list(payments[0].keys())     if payments    else [],
    "reviews":     list(reviews[0].keys())      if reviews     else [],
    "products":    list(products[0].keys())     if products    else [],
    "sellers":     list(sellers[0].keys())      if sellers     else [],
    "geolocation": list(geolocation[0].keys())  if geolocation else [],
    "translation": list(translation[0].keys())  if translation else [],
}

# ---------------------------------------------------------------------------
# Null counts
# ---------------------------------------------------------------------------

print("Profiling nulls...")

nulls = {
    "orders":   null_counts(orders),
    "products": null_counts(products),
    "reviews":  null_counts(reviews),
    "items":    null_counts(items),
}
# Filter to only cols with at least 1 null
nulls = {tbl: {c: n for c, n in counts.items() if n > 0}
         for tbl, counts in nulls.items()}

# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

print("Profiling orders...")

order_ids = set(r["order_id"] for r in orders)
customer_ids_in_orders = set(r["customer_id"] for r in orders)

orders_profile = {
    "total_orders":           len(orders),
    "distinct_customer_ids":  len(customer_ids_in_orders),
    "order_status_distribution": value_dist(orders, "order_status"),
    "null_approved_at":       sum(1 for r in orders if not r["order_approved_at"]),
    "null_delivered_carrier": sum(1 for r in orders if not r["order_delivered_carrier_date"]),
    "null_delivered_customer": sum(1 for r in orders if not r["order_delivered_customer_date"]),
}

# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

print("Profiling customers...")

cid_to_uid = {r["customer_id"]: r["customer_unique_id"] for r in customers}
uid_order_counts = collections.Counter(
    cid_to_uid.get(r["customer_id"], "") for r in orders
)

bad_zip_customers = sum(
    1 for r in customers
    if not r["customer_zip_code_prefix"].isdigit()
    or len(r["customer_zip_code_prefix"]) != 5
)

customers_profile = {
    "total_rows":                     len(customers),
    "distinct_customer_unique_id":    len(set(r["customer_unique_id"] for r in customers)),
    "distinct_customer_id":           len(set(r["customer_id"] for r in customers)),
    "customers_with_multiple_orders": sum(1 for v in uid_order_counts.values() if v > 1),
    "max_orders_per_customer":        max(uid_order_counts.values()) if uid_order_counts else 0,
    "bad_zip_format":                 bad_zip_customers,
    "top_10_states":                  dict(
        collections.Counter(r["customer_state"] for r in customers).most_common(10)
    ),
}

# ---------------------------------------------------------------------------
# Order items
# ---------------------------------------------------------------------------

print("Profiling order items...")

items_order_ids = set(r["order_id"] for r in items)
item_order_counts = collections.Counter(r["order_id"] for r in items)
prices    = [float(r["price"])         for r in items]
freights  = [float(r["freight_value"]) for r in items]

items_profile = {
    "total_rows":            len(items),
    "distinct_order_ids":    len(items_order_ids),
    "orders_with_multiple_items": sum(1 for v in item_order_counts.values() if v > 1),
    "max_items_per_order":   max(item_order_counts.values()) if item_order_counts else 0,
    "price":    {"min": min(prices),   "max": max(prices),   "zero_or_below": sum(1 for p in prices if p <= 0)},
    "freight":  {"min": min(freights), "max": max(freights), "negative": sum(1 for f in freights if f < 0)},
}

# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

print("Profiling payments...")

payment_order_counts = collections.Counter(r["order_id"] for r in payments)
installments = [int(r["payment_installments"]) for r in payments]
pay_values   = [float(r["payment_value"])       for r in payments]

boleto_rows   = [r for r in payments if r["payment_type"] == "boleto"]
not_def_rows  = [r for r in payments if r["payment_type"] == "not_defined"]
zero_val_rows = [r for r in payments if float(r["payment_value"]) == 0]
zero_val_excl_not_def = [
    r for r in payments
    if float(r["payment_value"]) == 0 and r["payment_type"] != "not_defined"
]
zero_install  = [r for r in payments if int(r["payment_installments"]) == 0]

payments_profile = {
    "total_rows":                    len(payments),
    "payment_type_distribution":     value_dist(payments, "payment_type"),
    "orders_with_multiple_payments": sum(1 for v in payment_order_counts.values() if v > 1),
    "installments": {
        "min": min(installments),
        "max": max(installments),
        "zero_installment_rows": len(zero_install),
        "zero_installment_types": value_dist(zero_install, "payment_type"),
    },
    "boleto_installment_distribution": value_dist(boleto_rows, "payment_installments"),
    "payment_value": {
        "min": min(pay_values),
        "max": max(pay_values),
        "zero_value_total":    len(zero_val_rows),
        "zero_value_excl_not_defined": len(zero_val_excl_not_def),
        "zero_value_excl_not_defined_types": value_dist(zero_val_excl_not_def, "payment_type"),
        "negative_value_rows": sum(1 for v in pay_values if v < 0),
    },
    "not_defined_rows": [
        {"order_id": r["order_id"], "payment_value": r["payment_value"],
         "payment_installments": r["payment_installments"]}
        for r in not_def_rows
    ],
}

# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------

print("Profiling reviews...")

review_id_counts  = collections.Counter(r["review_id"] for r in reviews)
order_review_counts = collections.Counter(r["order_id"] for r in reviews)

itemless_orders = order_ids - items_order_ids
review_order_ids = set(r["order_id"] for r in reviews)
reviewed_but_itemless = itemless_orders & review_order_ids

reviews_profile = {
    "total_rows":                    len(reviews),
    "duplicate_review_ids":          sum(1 for v in review_id_counts.values() if v > 1),
    "orders_with_multiple_reviews":  sum(1 for v in order_review_counts.values() if v > 1),
    "max_reviews_per_order":         max(order_review_counts.values()) if order_review_counts else 0,
    "review_score_distribution":     value_dist(reviews, "review_score"),
    "null_review_comment_title":     sum(1 for r in reviews if not r["review_comment_title"]),
    "null_review_comment_message":   sum(1 for r in reviews if not r["review_comment_message"]),
    "null_comment_title_pct":        round(
        sum(1 for r in reviews if not r["review_comment_title"]) / len(reviews), 4
    ),
    "null_comment_message_pct":      round(
        sum(1 for r in reviews if not r["review_comment_message"]) / len(reviews), 4
    ),
    "itemless_orders_with_reviews":  len(reviewed_but_itemless),
}

# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

print("Profiling products...")

trans_map = {r["product_category_name"]: r["product_category_name_english"]
             for r in translation}
product_categories = set(r["product_category_name"] for r in products
                         if r["product_category_name"])
untranslated = sorted(product_categories - set(trans_map.keys()))

products_profile = {
    "total_rows":               len(products),
    "columns":                  columns["products"],
    "misspelled_columns":       ["product_name_lenght", "product_description_lenght"],
    "corrected_columns":        ["product_name_length", "product_description_length"],
    "null_product_category":    sum(1 for r in products if not r["product_category_name"]),
    "distinct_categories":      len(product_categories),
    "translation_entries":      len(translation),
    "untranslated_categories":  untranslated,
    "translation_file_bom":     True,
}

# ---------------------------------------------------------------------------
# Sellers
# ---------------------------------------------------------------------------

print("Profiling sellers...")

bad_zip_sellers = sum(
    1 for r in sellers
    if not r["seller_zip_code_prefix"].isdigit()
    or len(r["seller_zip_code_prefix"]) != 5
)

sellers_profile = {
    "total_rows":     len(sellers),
    "bad_zip_format": bad_zip_sellers,
}

# ---------------------------------------------------------------------------
# Geolocation
# ---------------------------------------------------------------------------

print("Profiling geolocation...")

geo_zips = collections.Counter(r["geolocation_zip_code_prefix"] for r in geolocation)
lats = [float(r["geolocation_lat"]) for r in geolocation]
lngs = [float(r["geolocation_lng"]) for r in geolocation]

brazil_bounds = {"lat_min": -35, "lat_max": 5, "lng_min": -75, "lng_max": -34}
out_lat = sum(1 for v in lats if v < brazil_bounds["lat_min"] or v > brazil_bounds["lat_max"])
out_lng = sum(1 for v in lngs if v < brazil_bounds["lng_min"] or v > brazil_bounds["lng_max"])

# Zip match rates
cust_zips   = set(r["customer_zip_code_prefix"] for r in customers)
seller_zips = set(r["seller_zip_code_prefix"]   for r in sellers)
geo_zip_set = set(geo_zips.keys())

cust_zip_match   = len(cust_zips   & geo_zip_set)
seller_zip_match = len(seller_zips & geo_zip_set)
cust_row_match   = sum(1 for r in customers if r["customer_zip_code_prefix"] in geo_zip_set)
seller_row_match = sum(1 for r in sellers   if r["seller_zip_code_prefix"]   in geo_zip_set)

geolocation_profile = {
    "total_rows":                     len(geolocation),
    "distinct_zip_prefixes":          len(geo_zips),
    "max_rows_per_prefix":            max(geo_zips.values()),
    "avg_rows_per_prefix":            round(len(geolocation) / len(geo_zips), 1),
    "lat_range":                      {"min": min(lats), "max": max(lats)},
    "lng_range":                      {"min": min(lngs), "max": max(lngs)},
    "brazil_bounds":                  brazil_bounds,
    "outlier_lat_rows":               out_lat,
    "outlier_lng_rows":               out_lng,
    "customer_zip_match": {
        "distinct_zips_total":   len(cust_zips),
        "distinct_zips_matched": cust_zip_match,
        "match_pct":             round(cust_zip_match / len(cust_zips), 4),
        "row_match_pct":         round(cust_row_match / len(customers), 4),
    },
    "seller_zip_match": {
        "distinct_zips_total":   len(seller_zips),
        "distinct_zips_matched": seller_zip_match,
        "match_pct":             round(seller_zip_match / len(seller_zips), 4),
        "row_match_pct":         round(seller_row_match / len(sellers), 4),
    },
}

# ---------------------------------------------------------------------------
# Cross-table referential integrity
# ---------------------------------------------------------------------------

print("Profiling cross-table integrity...")

customer_ids_in_customers = set(r["customer_id"] for r in customers)

cross_table = {
    "orders_with_no_items": {
        "count": len(itemless_orders),
        "status_breakdown": dict(
            collections.Counter(
                orders_dict["order_status"]
                for oid in itemless_orders
                if (orders_dict := next((r for r in orders if r["order_id"] == oid), None))
            )
        ),
    },
    "orders_with_no_payment":          len(order_ids - set(r["order_id"] for r in payments)),
    "items_order_ids_not_in_orders":   len(items_order_ids - order_ids),
    "payment_order_ids_not_in_orders": len(set(r["order_id"] for r in payments) - order_ids),
    "customer_ids_not_in_customers":   len(customer_ids_in_orders - customer_ids_in_customers),
    "seller_ids_not_in_sellers": len(
        set(r["seller_id"] for r in items) -
        set(r["seller_id"] for r in sellers)
    ),
    "itemless_orders_with_reviews": len(reviewed_but_itemless),
}

# Recompute orders_with_no_items status breakdown without quadratic scan
itemless_dict = {r["order_id"]: r["order_status"] for r in orders if r["order_id"] in itemless_orders}
cross_table["orders_with_no_items"]["status_breakdown"] = dict(
    collections.Counter(itemless_dict.values()).most_common()
)

# ---------------------------------------------------------------------------
# Known data defects (staging fix reference)
# ---------------------------------------------------------------------------

known_defects = [
    {
        "id": "DEF-001",
        "table": "olist_order_reviews_dataset.csv",
        "description": "789 duplicate review_id values; 547 orders have multiple reviews (max 3)",
        "staging_fix": "stg_reviews: ROW_NUMBER() OVER (PARTITION BY review_id ORDER BY review_answer_timestamp DESC), keep rn=1",
        "brd_ref": "REQ-052.1",
    },
    {
        "id": "DEF-002",
        "table": "olist_geolocation_dataset.csv",
        "description": f"Coordinate outliers: {out_lat} lat rows outside [-35, 5]; {out_lng} lng rows outside [-75, -34]",
        "staging_fix": "stg_geolocation: WHERE lat BETWEEN -35 AND 5 AND lng BETWEEN -75 AND -34 before AVG()",
        "brd_ref": "REQ-054.1",
    },
    {
        "id": "DEF-003",
        "table": "olist_products_dataset.csv",
        "description": "2 categories have no English translation: ['pc_gamer', 'portateis_cozinha_e_preparadores_de_alimentos']. 610 products have null category_name.",
        "staging_fix": "stg_products: COALESCE(english_name, portuguese_name, 'uncategorized')",
        "brd_ref": "REQ-006.1",
    },
    {
        "id": "DEF-004",
        "table": "olist_order_payments_dataset.csv",
        "description": "3 rows with payment_type='not_defined', all payment_value=0.00",
        "staging_fix": "stg_payments: filter WHERE payment_type != 'not_defined'",
        "brd_ref": "REQ-017.1",
    },
    {
        "id": "DEF-005",
        "table": "olist_order_payments_dataset.csv",
        "description": "2 credit_card rows with payment_installments=0 (invalid)",
        "staging_fix": "stg_payments: GREATEST(payment_installments, 1)",
        "brd_ref": "REQ-017.1",
    },
    {
        "id": "DEF-006",
        "table": "olist_order_payments_dataset.csv",
        "description": "6 zero-value voucher payments (sequential 3, 4, 13, 14) — legitimate secondary payments",
        "staging_fix": "No fix needed. payment_value >= 0 test (not strictly > 0).",
        "brd_ref": "REQ-017.1",
    },
    {
        "id": "DEF-007",
        "table": "product_category_name_translation.csv",
        "description": "File contains UTF-8 BOM. First column may read as '\\ufeffproduct_category_name' depending on tap encoding.",
        "staging_fix": "Verify Meltano tap strips BOM, or pre-strip file before ingestion.",
        "brd_ref": "REQ-001.2",
    },
    {
        "id": "DEF-008",
        "table": "olist_orders_dataset.csv / olist_order_items_dataset.csv",
        "description": "775 orders have no order_items rows (603 unavailable, 164 canceled, 5 created, 2 invoiced, 1 shipped). 756 of these have review records.",
        "staging_fix": "Expected behaviour. fct_sales is item-granularity; itemless orders absent from fct_sales by design. fct_reviews.order_id links to stg_orders, not fct_sales.",
        "brd_ref": "REQ-011.1, REQ-052.1",
    },
    {
        "id": "DEF-009",
        "table": "olist_products_dataset.csv",
        "description": "Misspelled column names: 'product_name_lenght', 'product_description_lenght'",
        "staging_fix": "stg_products: rename to product_name_length, product_description_length",
        "brd_ref": "REQ-006.1",
    },
]

# ---------------------------------------------------------------------------
# Test threshold justifications
# ---------------------------------------------------------------------------

test_thresholds = {
    "fct_reviews.review_comment_title": {
        "mostly": 0.08,
        "null_pct_in_source": round(
            sum(1 for r in reviews if not r["review_comment_title"]) / len(reviews), 4
        ),
        "rationale": "88.3% null (11.7% non-null). Threshold 0.08 catches genuine degradation with margin.",
    },
    "fct_reviews.review_comment_message": {
        "mostly": 0.40,
        "null_pct_in_source": round(
            sum(1 for r in reviews if not r["review_comment_message"]) / len(reviews), 4
        ),
        "rationale": "58.7% null (41.3% non-null). Threshold 0.40 matches actual fill rate.",
    },
    "dim_customers.geolocation_lat_lng": {
        "mostly": 0.97,
        "row_match_pct_in_source": round(cust_row_match / len(customers), 4),
        "rationale": "99.7% row-level geo match. Threshold 0.97 gives meaningful signal on join quality degradation.",
    },
    "dim_sellers.geolocation_lat_lng": {
        "mostly": 0.97,
        "row_match_pct_in_source": round(seller_row_match / len(sellers), 4),
        "rationale": "99.8% row-level geo match. Same rationale as dim_customers.",
    },
    "fct_sales.row_count": {
        "min": 90000,
        "max": 200000,
        "actual_items_rows": len(items),
        "rationale": "112,650 order_items rows. Min 90k detects catastrophic partial load; max 200k allows for future growth.",
    },
}

# ---------------------------------------------------------------------------
# Assemble and write
# ---------------------------------------------------------------------------

profile = {
    "meta": {
        "generated_at":  datetime.now().isoformat(timespec="seconds"),
        "generated_by":  "scripts/profile_source_data.py",
        "raw_data_path": RAW,
        "brd_version":   "2.2",
        "note": "Read this file before profiling source CSVs. Re-run only if source data changes.",
    },
    "row_counts":          row_counts,
    "columns":             columns,
    "nulls":               nulls,
    "orders":              orders_profile,
    "customers":           customers_profile,
    "order_items":         items_profile,
    "payments":            payments_profile,
    "reviews":             reviews_profile,
    "products":            products_profile,
    "sellers":             sellers_profile,
    "geolocation":         geolocation_profile,
    "cross_table_integrity": cross_table,
    "known_defects":       known_defects,
    "test_thresholds":     test_thresholds,
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as f:
    json.dump(profile, f, indent=2)

print(f"\n✓ Profile written to {OUT}")
print(f"  Files profiled:    {len(row_counts)}")
print(f"  Known defects:     {len(known_defects)}")
print(f"  Total source rows: {sum(row_counts.values()):,}")
