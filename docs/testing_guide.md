# Testing Guide — Project Caravela
# REQ-064.1: dbt data quality test documentation with threshold evidence.
# Evidence base: docs/data_profile.json (generated 2026-03-09, annotated 2026-03-18).

---

## Overview

Project Caravela uses two complementary dbt test mechanisms, both executed via `dbt test` or `dbt build`:

| Mechanism | Location | What it tests |
|---|---|---|
| Generic tests (schema.yml) | `dbt/models/staging/schema.yml`, `dbt/models/marts/schema.yml` | Column constraints, value ranges, referential integrity, accepted values |
| Singular tests (SQL files) | `dbt/tests/` | Cross-table assertions, conditional business rules |

All tests run in topological order during `dbt build` — a failing staging test blocks dependent mart models.

---

## Test Infrastructure

### Package Versions

| Package | Version | Source |
|---|---|---|
| `dbt-core` | 1.11.7 | pip |
| `dbt-bigquery` | (compatible) | pip |
| `dbt_utils` | ≥1.0.0, <2.0.0 | `dbt-labs/dbt_utils` (dbt Hub) |
| `dbt_expectations` | 0.6.0 | `git: https://github.com/metaplane/dbt-expectations` (main) |

### Critical Package Constraint: metaplane/dbt-expectations v0.6.0

The original `calogica/dbt-expectations` package was deprecated after v0.10.4 and is incompatible with dbt-core ≥1.8. This project uses the **metaplane fork** as its continuation.

**The metaplane fork does not support a `mostly` parameter on any macro.** All macros delegate to `expression_is_true`, which has no proportion-threshold logic. Confirmed by reading macro source:

```
expect_column_values_to_not_be_null(model, column_name, row_condition=None)
expect_column_value_lengths_to_be_between(model, column_name, min_value, max_value, row_condition, strictly)
```

**Consequence:** Four proportion-based tests specified in the BRD cannot be implemented with this package:
- `stg_reviews.review_comment_title` (calibrated mostly=0.08)
- `stg_reviews.review_comment_message` (calibrated mostly=0.40)
- `dim_customers.geolocation_lat` / `geolocation_lng` (calibrated mostly=0.97)
- `dim_sellers.geolocation_lat` / `geolocation_lng` (calibrated mostly=0.97)

Calibration evidence is preserved in `docs/data_profile.json` under `test_thresholds`. See [Known Omissions](#known-omissions) for workaround options.

### Additional Constraint: tap-csv Empty-String Encoding

`tap-csv` (MeltanoLabs) stores blank CSV cells as empty strings `''`, not SQL NULLs. This affects how fill-rate tests must be written:

- `expect_column_values_to_not_be_null` → **will not catch blank strings**, trivially passes at 100%
- `expect_column_value_lengths_to_be_between(min_value=1)` → **correctly catches empty strings**

Where fill-rate guards exist in this project, they use the length-based approach — for example, `dim_products.product_category_name_english` uses `expect_column_value_lengths_to_be_between(min_value=1)` to confirm COALESCE produced a non-empty string. The `stg_reviews` comment column fill-rate guards are omitted entirely (proportion tests require `mostly`, which is unavailable — see [Known Omissions](#known-omissions)).

---

## How to Run Tests

```bash
# Run all tests (after models are materialised)
cd dbt && dbt test

# Run tests + models together (topological order, recommended)
cd dbt && dbt build

# Run tests for a single model
dbt test --select stg_payments

# Run tests for a model and all its dependents
dbt test --select stg_payments+

# Run only singular tests
dbt test --select test_type:singular

# Run only generic tests
dbt test --select test_type:generic
```

Prerequisites: `GOOGLE_APPLICATION_CREDENTIALS` and `GCP_PROJECT_ID` must be set. `manifest.json` must exist (`dbt parse` if not). Models must be materialised before running tests alone.

---

## Generic Tests — Staging Layer

### `stg_customers`

| Column | Tests | Evidence |
|---|---|---|
| `customer_id` | `not_null`, `unique` | 99,441 rows, 99,441 distinct customer_ids (profile: `customers.distinct_customer_id`) |
| `customer_unique_id` | `not_null` | 96,096 distinct — not unique (2,997 customers have multiple orders) |
| `customer_state` | `not_null` | All 99,441 rows have a state (profile: no nulls recorded for customers) |

---

### `stg_orders`

| Column / Test | Tests | Evidence |
|---|---|---|
| `order_id` | `not_null`, `unique` | 99,441 rows, all distinct (profile: `orders.total_orders`) |
| `customer_id` | `not_null` | Required FK to stg_customers |
| `order_status` | `not_null`, `accepted_values` | 8 statuses confirmed: delivered (96,478), shipped (1,107), canceled (625), unavailable (609), invoiced (314), processing (301), created (5), approved (2). Profile: `orders.order_status_distribution` |

**Model-level temporal pair test:**

```yaml
- dbt_expectations.expect_column_pair_values_A_to_be_greater_than_B:
    column_A: order_approved_at
    column_B: order_purchase_timestamp
    or_equal: true
```

Evidence: 0 violations in source data (profile: `orders.null_approved_at = 160` — nulls are excluded from pair comparison automatically by dbt-expectations). Two additional pair tests (`carrier_date >= approved_at` and `customer_date >= carrier_date`) were **removed** — source data has 1,359 and 23 violations respectively (logistics anomalies). See changelog 2026-03-15.

---

### `stg_order_items`

| Column | Tests | Evidence |
|---|---|---|
| `order_id` + `order_item_id` | `unique_combination_of_columns` (model-level) | Compound PK: 112,650 rows, all (order_id, order_item_id) pairs distinct. Profile: `order_items.total_rows` |
| `order_id` | `not_null` | Required FK |
| `order_item_id` | `not_null` | Required compound PK component |
| `product_id` | `not_null` | Required FK |
| `seller_id` | `not_null` | Required FK |
| `price` | `not_null` | Profile: `order_items.price.zero_or_below = 0` — no negative prices |
| `freight_value` | `not_null` | Profile: `order_items.freight.negative = 0` |

---

### `stg_payments`

| Column | Tests | Evidence |
|---|---|---|
| `order_id` | `not_null` | Required FK |
| `payment_sequential` | `not_null` | Required compound PK component |
| `payment_type` | `not_null`, `accepted_values` | 4 values post-filter: credit_card (76,795), boleto (19,784), voucher (5,775), debit_card (1,529). `not_defined` (3 rows) filtered in staging. Profile: `payments.payment_type_distribution` |
| `payment_installments` | `expect_column_values_to_be_between(min_value=1)` | Profile: `payments.installments.zero_installment_rows = 2` (both credit_card). Clamped to 1 via `GREATEST(..., 1)` in staging (DEF-005). min_value=1 confirms clamp is active. |
| `payment_value` | `expect_column_values_to_be_between(min_value=0)` | Profile: `payments.payment_value.negative_value_rows = 0`. Zero is valid — 6 zero-value vouchers are legitimate secondary payments (DEF-006). `min_value=0` not `>0`. |

---

### `stg_reviews`

| Column | Tests | Evidence |
|---|---|---|
| `review_id` | `not_null`, `unique` | After deduplication: 789 duplicate review_ids removed via `ROW_NUMBER() OVER (PARTITION BY review_id ...)`. Profile: `reviews.duplicate_review_ids = 789` |
| `order_id` | `not_null` | **Not unique** — 547 orders have multiple reviews with distinct review_ids. Profile: `reviews.orders_with_multiple_reviews = 547` |
| `review_score` | `expect_column_values_to_be_between(min_value=1, max_value=5)` | Profile: `reviews.review_score_distribution` — scores 1–5 only |
| `review_comment_title` | Description only (no test) | See [Known Omissions](#known-omissions) |
| `review_comment_message` | Description only (no test) | See [Known Omissions](#known-omissions) |

---

### `stg_products`

| Column | Tests | Evidence |
|---|---|---|
| `product_id` | `not_null`, `unique` | 32,951 rows, all distinct. Profile: `products.total_rows` |
| `product_category_name` | No test | Raw Portuguese — 610 empty-string rows (not NULL after tap-csv). Cannot test reliably. |
| `product_category_name_english` | No test at staging | Tested at mart layer (`dim_products`) |
| `product_name_length` | No test | Nullable: 610 rows have empty source field → `SAFE_CAST` returns NULL. See changelog 2026-03-15 (DEF-009). |
| `product_description_length` | No test | Same as above. |

**DEF-009 note**: Source has misspelled columns `product_name_lenght` / `product_description_lenght`. Renamed in staging. Column rename success is validated by `not_null` tests on the correctly-spelled names in `dim_products` (mart layer).

---

### `stg_geolocation`

| Column | Tests | Evidence |
|---|---|---|
| `zip_code_prefix` | `not_null`, `unique` | After `GROUP BY` aggregation: 19,015 distinct zip prefixes. Profile: `geolocation.distinct_zip_prefixes` |
| `geolocation_lat` | `expect_column_values_to_be_between(min_value=-35, max_value=5)` | Profile: `geolocation.brazil_bounds.lat_min=-35, lat_max=5`. Source outliers: lat up to +45° (29 rows). Filter applied before AVG(). Profile: `geolocation.outlier_lat_rows=29` |
| `geolocation_lng` | `expect_column_values_to_be_between(min_value=-75, max_value=-34)` | Profile: `geolocation.brazil_bounds.lng_min=-75, lng_max=-34`. Source outliers: lng up to +121° (37 rows). Profile: `geolocation.outlier_lng_rows=37` |

---

### `stg_sellers`

| Column | Tests | Evidence |
|---|---|---|
| `seller_id` | `not_null`, `unique` | 3,095 rows, all distinct. Profile: `sellers.total_rows` |

---

### `stg_product_category_name_translation`

| Column | Tests | Evidence |
|---|---|---|
| `product_category_name` | `not_null` | 71 rows, lookup key. Profile: `products.translation_entries=71` |

---

## Generic Tests — Mart Layer

### `dim_customers`

| Column | Tests | Evidence |
|---|---|---|
| `customer_unique_id` | `not_null`, `unique` | PK. Profile: `customers.distinct_customer_unique_id=96,096` |
| `geolocation_lat` / `geolocation_lng` | Description only | Calibrated mostly=0.97. Profile: `geolocation.customer_zip_match.row_match_pct=0.9972`. Cannot implement — see [Known Omissions](#known-omissions) |

---

### `dim_products`

| Column | Tests | Evidence |
|---|---|---|
| `product_id` | `not_null`, `unique` | PK. 32,951 rows. |
| `product_category_name_english` | `not_null`, `expect_column_value_lengths_to_be_between(min_value=1)` | COALESCE guarantees non-null, non-empty: English → Portuguese (non-blank) → 'uncategorized'. 610 empty-source-category products labelled 'uncategorized'. 13 untranslated Portuguese names retain their Portuguese name. Profile: `products.null_product_category=610`, `products.untranslated_categories=['pc_gamer', 'portateis_cozinha_e_preparadores_de_alimentos']` |
| `product_name_length` | No test | Nullable (SAFE_CAST of blank source field). Rename from `product_name_lenght` confirmed by column existence. |
| `product_description_length` | No test | Same as above. |

---

### `dim_sellers`

| Column | Tests | Evidence |
|---|---|---|
| `seller_id` | `not_null`, `unique` | PK. 3,095 rows. |
| `geolocation_lat` / `geolocation_lng` | Description only | Calibrated mostly=0.97. Profile: `geolocation.seller_zip_match.row_match_pct=0.9977`. Cannot implement — see [Known Omissions](#known-omissions) |

---

### `dim_date`

| Column / Test | Tests | Evidence |
|---|---|---|
| `date_key` | `not_null`, `unique` | PK. DATE type, direct output of `dbt_utils.date_spine`. |
| Range (model-level) | `dbt_utils.expression_is_true: "date_key >= cast('2016-01-01' as date) and date_key <= cast('2018-12-31' as date)"` | Data window: first order 2016-09-04, last 2018-10-17. Range 2016-01-01 to 2018-12-31 provides full coverage with buffer. Profile: `monthly_distribution.date_range` |
| Row count (model-level) | `expect_table_row_count_to_be_between(min_value=1000, max_value=1100)` | 2016-01-01 to 2018-12-30 = 1095 calendar days. |

**Note on range test**: Originally specified as `dbt_expectations.expect_column_values_to_be_between`. Implemented as `dbt_utils.expression_is_true` — achieves the same guard with confirmed working macro.

---

### `fct_sales`

| Column / Test | Tests | Evidence |
|---|---|---|
| `order_id` + `order_item_id` | `unique_combination_of_columns` (model-level) | Compound PK. Profile: `order_items.total_rows=112,650` |
| Row count (model-level) | `expect_table_row_count_to_be_between(min_value=110000, max_value=120000)` | 112,650 source rows confirmed from live BigQuery. Bounds detect partial load (< 110k) or duplicate ingestion (> 120k). Profile: `order_items.total_rows` |
| `order_id` | `not_null` | Compound PK component |
| `order_item_id` | `not_null` | Compound PK component |
| `customer_unique_id` | `not_null`, `relationships → dim_customers.customer_unique_id` | Resolved via three-source CTE: order_items → orders → customers |
| `product_id` | `not_null`, `relationships → dim_products.product_id` | FK. WHERE filter removed from stg_products to prevent 1,603 FK violations (610 'uncategorized' products). See changelog 2026-03-15 |
| `seller_id` | `not_null`, `relationships → dim_sellers.seller_id` | FK |
| `date_key` | `not_null`, `relationships → dim_date.date_key` | FK. DATE type. Derived from `DATE(CAST(order_purchase_timestamp AS TIMESTAMP))` |
| `total_sale_amount` | `expect_column_values_to_be_between(min_value=0)` | Profile: `order_items.price.min=0.85`, `order_items.freight.min=0.0`. Sum ≥ 0 guaranteed. |

---

### `fct_reviews`

| Column / Test | Tests | Evidence |
|---|---|---|
| `review_id` | `not_null`, `unique` | PK. Deduplicated in stg_reviews. Profile: `reviews.duplicate_review_ids=789` removed. |
| Row count (model-level) | `expect_table_row_count_to_be_between(min_value=95000, max_value=100000)` | **Critical dedup guard.** If dedup partitions on `order_id` instead of `review_id`, 547 valid records are incorrectly dropped. Profile: `reviews.total_rows=99,224` minus 789 duplicates ≈ 98,435. Bounds: min 95k, max 100k. |
| `order_id` | `not_null`, `relationships → stg_orders.order_id` | **FK targets `stg_orders`, NOT `fct_sales`.** 756 itemless orders have reviews but no fct_sales rows. Profile: `cross_table_integrity.itemless_orders_with_reviews=756`. See ADR-003. |
| `review_score` | `expect_column_values_to_be_between(min_value=1, max_value=5)` | Profile: `reviews.review_score_distribution` — only scores 1–5 in source |

---

### `fct_payments`

| Column / Test | Tests | Evidence |
|---|---|---|
| `order_id` + `payment_sequential` | `unique_combination_of_columns` (model-level) | Compound PK. Profile: `payments.orders_with_multiple_payments=2,961` |
| `order_id` | `not_null` | Compound PK component |
| `payment_sequential` | `not_null` | Compound PK component |
| `payment_type` | `accepted_values` | 4 values post-staging filter. Profile: `payments.payment_type_distribution` |
| `payment_installments` | `expect_column_values_to_be_between(min_value=1)` | Staging clamp applied. Profile: `payments.installments.zero_installment_rows=2` now clamped. |
| `payment_value` | `expect_column_values_to_be_between(min_value=0)` | Zero valid (6 vouchers). Profile: `payments.payment_value.negative_value_rows=0`. |
| `date_key` | No FK/not_null test | Nullable: `fct_payments` uses `LEFT JOIN stg_orders`. Payments for orders absent from stg_orders will have NULL date_key. Adding `not_null` would fail legitimately. See changelog 2026-03-15. |

---

## Singular Tests

### `assert_boleto_single_installment.sql`

**Business rule**: All boleto payments must have exactly 1 installment.

**Evidence**: Profile `payments.boleto_installment_distribution` shows 100% of 19,784 boleto rows have 1 installment in source. DEF-005 clamps `payment_installments=0` to 1 in stg_payments — no boleto rows were affected (both zero-installment rows were `credit_card`), but the test validates the business constraint is not violated by future data or model changes.

**Pass condition**: Zero rows returned.

```sql
SELECT order_id, payment_sequential, payment_installments
FROM {{ ref('fct_payments') }}
WHERE payment_type = 'boleto'
  AND payment_installments != 1
```

---

### `assert_payment_reconciliation.sql`

**Business rule**: Payment totals should reconcile with sales totals within R$20.00, for single-installment orders only.

**Calibration history**:
- Original spec threshold: `> R$1.00`
- Diagnostic query (2026-03-15) found 249 violations at R$1.00:
  - 236 multi-installment orders: Olist `payment_value` includes credit card parcelamento interest, which legitimately inflates payment_total above price+freight_value. Excluded via `MAX(payment_installments) = 1` filter.
  - 13 single-installment orders: genuine freight-subsidy anomalies, diffs up to R$16.50 (avg R$6.15).
- Final threshold: `> R$20.00` — accommodates known anomalies while catching model bugs (wrong JOIN or double-counting produces 10×+ errors). After calibration: 0 violations.

**Pass condition**: Zero rows returned.

---

### `assert_date_key_range.sql`

**Business rule**: All date_key values across fact tables must fall within the known data window (2016-01-01 to 2018-12-31).

**Evidence**: Profile `monthly_distribution.date_range` confirms source data spans 2016-09-04 to 2018-10-17. The dim_date table covers 2016-01-01 to 2018-12-31 (with buffer). Any fact row outside this window indicates a casting error or unexpected source data.

**Covers**: `fct_sales`, `fct_reviews`, `fct_payments` — all three fact date_key columns.

**Pass condition**: Zero rows returned.

---

## Known Omissions

### Proportion Tests (mostly parameter unavailable)

Four fill-rate guards cannot be implemented with metaplane/dbt-expectations v0.6.0:

| Test Target | Calibrated mostly | Fill rate in source | Workaround available? |
|---|---|---|---|
| `stg_reviews.review_comment_title` | 0.08 | 11.7% non-blank | Partial: `expect_column_value_lengths_to_be_between(min_value=1)` confirms format but not fill rate |
| `stg_reviews.review_comment_message` | 0.40 | 41.3% non-blank | Same partial workaround |
| `dim_customers.geolocation_lat/lng` | 0.97 | 99.7% rows matched | None — requires proportion support |
| `dim_sellers.geolocation_lat/lng` | 0.97 | 99.8% rows matched | None — requires proportion support |

**Options if proportion tests are required:**
1. Write custom singular SQL tests that compute fill rate and fail if below threshold.
2. Switch to a dbt test package that supports `mostly` (no maintained option currently compatible with dbt-core 1.11).
3. Accept the current state — calibration evidence is preserved in `docs/data_profile.json` under `test_thresholds`.

### Delivery Timestamp Pair Tests

Two temporal ordering tests were removed after source data investigation:

| Test | Violations in source | Decision |
|---|---|---|
| `order_delivered_carrier_date >= order_approved_at` | 1,359 rows | Removed — logistics anomaly in Olist data (timestamps recorded out of order at source) |
| `order_delivered_customer_date >= order_delivered_carrier_date` | 23 rows | Removed — same issue |

Retained: `order_approved_at >= order_purchase_timestamp` (0 violations). See changelog 2026-03-15.

---

## Interpreting Test Failures

| Failure pattern | Likely cause | Where to look |
|---|---|---|
| `unique` fails on a PK | Deduplication logic broken or removed | Check staging model's `ROW_NUMBER()` / `GROUP BY` clause |
| `relationships` fails on FK | Upstream dim model missing rows or wrong join key | Check dim model's WHERE clause — `stg_products` WHERE filter incident (changelog 2026-03-15) |
| `expect_table_row_count` too low | Partial Meltano load or `WRITE_APPEND` duplication | Check Meltano run logs; verify `WRITE_TRUNCATE` disposition |
| `expect_table_row_count` too high | Duplicate ingestion | Same as above |
| `assert_boleto_single_installment` fails | stg_payments clamp removed or payment type filter broken | Check `stg_payments.sql` GREATEST() and WHERE clauses |
| `assert_payment_reconciliation` fails | Wrong JOIN in fct_payments or fct_sales, or double-counting | Check CTEs in both models; diff > R$20 on single-installment order is unambiguous model error |
| `assert_date_key_range` fails | Casting error in staging → NULL becomes epoch date, or unexpected source timestamps | Check `DATE(CAST(... AS TIMESTAMP))` in staging models; SAFE_CAST returns NULL not epoch |
| `accepted_values` fails on payment_type | `not_defined` rows not filtered in staging | Check `WHERE payment_type != 'not_defined'` in `stg_payments.sql` |
