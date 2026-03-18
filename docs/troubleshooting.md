# Troubleshooting Guide — Project Caravela

> REQ-062.1 (optional). Each pipeline layer adds its own section.

---

## Meltano (Ingestion Layer)

### 1. `meltano install` fails — `ModuleNotFoundError: No module named 'pkg_resources'`

**Symptoms:**
```
ModuleNotFoundError: No module named 'pkg_resources'
```

**Cause:** `setuptools>=81` (released 2026-02-06) removed `pkg_resources` entirely. Both `tap-csv` and `target-bigquery` depend on `pkg_resources` at install time.

**Fix:**
1. Confirm both `pip_url` entries in `meltano.yml` include `setuptools<70`:
   ```yaml
   pip_url: git+https://github.com/MeltanoLabs/tap-csv.git setuptools<70
   pip_url: git+https://github.com/z3z1ma/target-bigquery.git setuptools<70
   ```
2. Delete the existing plugin venvs and reinstall:
   ```bash
   rm -rf .meltano/
   meltano install
   ```

---

### 2. `meltano run` fails — env vars not resolved

**Symptoms:** Run fails with authentication or missing dataset errors. `meltano config print target-bigquery` output is missing `dataset`, `project`, or `credentials_path` keys.

**Cause:** Meltano auto-loads `.env` only from its own project directory (`meltano/.env`). The project's `.env` lives at the repo root, one level up.

**Fix:** Use the wrapper script or pass `--env-file` explicitly:
```bash
# Recommended
./launch_meltano.sh run

# Manual
meltano --env-file ../.env run tap-csv target-bigquery
```

**Verify:** Run `./launch_meltano.sh test` — all three keys (`project`, `credentials_path`, `dataset`) should show resolved values.

---

### 3. `meltano config print` shows no `dataset` key

**Symptoms:** The `dataset` field is silently absent from `meltano config print target-bigquery` output. No error is raised.

**Cause:** Meltano treats unresolved `$VAR` references as null and omits null keys from output — a silent failure mode.

**Fix:** Same as #2. Ensure `.env` is loaded via `--env-file ../.env` or the wrapper script.

**Diagnostic:** Compare output with and without `--env-file`:
```bash
# Without (may silently drop keys)
meltano config print target-bigquery

# With (should show all keys)
meltano --env-file ../.env config print target-bigquery
```

---

### 4. BigQuery load duplicates all rows on every run

**Symptoms:** Row counts in `olist_raw` tables double after each pipeline run.

**Cause:** `write_disposition` is set to `WRITE_APPEND` instead of `WRITE_TRUNCATE`.

**Fix:** Confirm in `meltano.yml`:
```yaml
write_disposition: WRITE_TRUNCATE
```
The Olist dataset is fixed/historical — full refresh is always correct.

---

### 5. `target-bigquery` stream timeout during geolocation load

**Symptoms:** `olist_order_items_dataset` or other tables fail with gRPC timeout errors during a run that includes the geolocation file.

**Cause:** `storage_write_api` method holds open gRPC streams per table. `tap-csv` processes files sequentially — the ~31s geolocation load (1M rows) causes earlier streams to hit BigQuery's 600s inactivity timeout.

**Fix:** Use `method: batch_job` (current default in `meltano.yml`). Trade-off: slower (~34 min total) but immune to idle timeouts.

```yaml
method: batch_job
```

---

### 6. `product_category_name_translation` first column header corrupted

**Symptoms:** `stg_products` join on `product_category_name` produces all NULLs for English category names. The first column in `product_category_name_translation` has an invisible BOM character prepended to its header.

**Cause:** `product_category_name_translation.csv` has a UTF-8 BOM (byte order mark).

**Current status:** Not an issue with `tap-csv` — Python's `csv` module strips BOM automatically. Would affect `tap-spreadsheets-anywhere` without `encoding: utf-8-sig` in the stream config.

**Diagnostic:** Check the first column name in BigQuery:
```sql
SELECT column_name
FROM `olist_raw.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'product_category_name_translation_view'
ORDER BY ordinal_position
LIMIT 1;
```
Expected: `product_category_name` (no `\ufeff` prefix).

---

### 7. BigQuery tables exist but dbt `source()` queries fail with "not found"

**Symptoms:** `dbt build` fails with `Table not found` errors on `olist_raw.*` sources, even though BigQuery Console shows the tables exist.

**Cause:** `target-bigquery` with `denormalized: false` creates two objects per stream:
- Base table (e.g., `olist_customers_dataset`) — contains a `data` JSON column. Do NOT query directly.
- Flat-column view (e.g., `olist_customers_dataset_view`) — the queryable table.

**Fix:** Ensure all `sources.yml` table names use the `_view` suffix:
```yaml
tables:
  - name: olist_customers_dataset_view
  - name: olist_orders_dataset_view
  # ... etc
```

---

### 8. `meltano run` fails on fresh clone — plugin not found

**Symptoms:**
```
Plugin 'tap-csv' is not known to Meltano
```
or similar error on first run after cloning.

**Cause:** `.meltano/` is gitignored. Plugin virtual environments are not committed and must be rebuilt locally.

**Fix:**
```bash
cd meltano/
meltano install
```
Run this once per fresh clone before any `meltano run` or `./launch_meltano.sh run`.

---

## dbt (Staging Layer)

### 9. Protobuf exit crash on `dbt deps` / `dbt parse` / `dbt compile`

**Symptoms:**
```
TypeError: MessageToJson() got an unexpected keyword argument 'always_print_fields_with_no_presence'
```
Process exits with code 1.

**Cause:** Known `protobuf` / `dbt-common` version incompatibility in dbt 1.11.7. The crash occurs in post-execution event logging, not during parsing or compilation. All operations complete successfully before the crash.

**Workaround:** Check `manifest.json` existence rather than process exit code:
```bash
cd dbt && dbt parse
ls -la target/manifest.json  # should exist with recent timestamp
```

**Impact:** None on functionality. `manifest.json`, compiled SQL, and installed packages are all generated correctly before the crash.

---

### 10. `dbt parse` fails — packages not installed

**Symptoms:**
```
Compilation Error: Macro 'dbt_expectations.expect_column_values_to_be_between' not found
```
or similar missing macro errors.

**Cause:** `dbt_utils` and `dbt_expectations` are declared in `packages.yml` but their macros aren't available until installed. `.dbt_packages/` is gitignored — not committed.

**Fix:**
```bash
cd dbt
dbt deps    # installs dbt_utils + dbt_expectations
dbt parse   # now succeeds
```
Run `dbt deps` once per fresh clone before any other dbt command.

---

### 11. `dbt build` fails with `Bad TIMESTAMP value` or `CAST('' AS TIMESTAMP)` error

**Symptoms:**
```
400 Bad request: Could not cast literal "" to type TIMESTAMP
```
Occurs when querying `stg_orders` or other models with timestamp columns.

**Cause:** `tap-csv` loads empty CSV cells as empty strings (`''`), not NULL. `CAST('' AS TIMESTAMP)` raises a BigQuery error.

**Fix:** Nullable timestamp and numeric columns must use `SAFE_CAST`, not `CAST`. `SAFE_CAST` returns NULL for unparseable values.

**Affected models:**
- `stg_orders` — `order_approved_at`, `order_delivered_carrier_date`, `order_delivered_customer_date`, `order_estimated_delivery_date`
- `stg_products` — `product_name_length`, `product_description_length`, `product_photos_qty`, `product_weight_g`, `product_length_cm`, `product_height_cm`, `product_width_cm`

**Diagnostic:** Check if empty strings exist in raw:
```sql
SELECT COUNT(*) FROM `olist_raw.olist_orders_dataset_view`
WHERE order_approved_at = '';
```

---

### 12. `stg_products` English category names are all NULL

**Symptoms:** `product_category_name_english` is NULL for every row in `stg_products`, even though the translation table has data.

**Cause (most likely):** The `sources.yml` table name for the translation table is missing the `_view` suffix. The LEFT JOIN silently matches zero rows — no error, just NULLs.

**Fix:** Confirm `sources.yml` has:
```yaml
- name: product_category_name_translation_view
```

**Diagnostic:**
```sql
-- Check translation table is queryable
SELECT COUNT(*) FROM `olist_raw.product_category_name_translation_view`;
-- Should return ~71 rows

-- Check join key alignment
SELECT product_category_name FROM `olist_raw.product_category_name_translation_view` LIMIT 5;
-- Verify no BOM prefix on first column header
```

---

### 13. 610 products show empty string instead of `'uncategorized'`

**Symptoms:** `product_category_name_english` contains `''` (empty string) for ~610 products instead of `'uncategorized'`.

**Cause:** `COALESCE` stops at the first non-NULL value. An empty string `''` is non-NULL, so `COALESCE('', 'uncategorized')` returns `''`. This happens when the Portuguese category name is blank in the source CSV — tap-csv loads it as `''` not NULL.

**Fix:** The COALESCE must include a CASE expression that converts empty/blank strings to NULL:
```sql
COALESCE(
    t.product_category_name_english,
    CASE WHEN TRIM(IFNULL(p.product_category_name, '')) = '' THEN NULL
         ELSE p.product_category_name END,
    'uncategorized'
)
```

**Verification:**
```sql
SELECT COUNT(*) FROM stg_products WHERE product_category_name_english = '';
-- Should return 0

SELECT COUNT(*) FROM stg_products WHERE product_category_name_english = 'uncategorized';
-- Should return 610
```

---

### 14. `env_var()` compilation error — environment variable not set

**Symptoms:**
```
Compilation Error: Env var required but not provided: 'GCP_PROJECT_ID'
```

**Cause:** dbt's `env_var('VAR')` without a fallback default throws a compilation error if the variable is not set in the shell environment.

**Which variables have defaults (safe for `dbt parse` without `.env`):**
- `BIGQUERY_ANALYTICS_DATASET` → defaults to `olist_analytics`
- `BIGQUERY_RAW_DATASET` → defaults to `olist_raw`

**Which variables have no default (required for `dbt build` / `dbt debug`):**
- `GCP_PROJECT_ID` — BigQuery project ID
- `GOOGLE_APPLICATION_CREDENTIALS` — service account key file path

**Fix:** Source `.env` before running dbt, or export the variables:
```bash
source .env   # from repo root
cd dbt && dbt build
```

---

### 15. `dbt build` succeeds but mart tables are empty (0 rows)

**Symptoms:** `dbt build` completes with no errors, all tests pass, but mart tables (`fct_sales`, `dim_customers`, etc.) have 0 rows.

**Cause:** Staging models are materialized as **views**, not tables. They resolve to the underlying `olist_raw` data at query time. If Meltano hasn't run (or ran against a different project/dataset), the raw tables are empty — views return 0 rows, and marts materialize empty tables. No error is raised.

**Fix:** Confirm raw data exists before running `dbt build`:
```sql
SELECT COUNT(*) FROM `olist_raw.olist_orders_dataset_view`;
-- Should return ~99,441
```

If empty, run the Meltano pipeline first:
```bash
cd meltano && ./launch_meltano.sh run
```

---

### 16. `stg_reviews` deduplication produces wrong row count

**Symptoms:** `stg_reviews` has significantly fewer rows than expected (~97k–98k). The `schema.yml` row count test (`expect_table_row_count_to_be_between`, min=95000, max=100000) may fail.

**Cause:** The `ROW_NUMBER()` window function is partitioned by the wrong column. If `PARTITION BY order_id` is used instead of `PARTITION BY review_id`, it drops 547 valid records where a single order has multiple reviews with distinct `review_id` values.

**Fix:** Confirm the dedup logic partitions on `review_id`:
```sql
ROW_NUMBER() OVER (
    PARTITION BY review_id        -- NOT order_id
    ORDER BY review_answer_timestamp DESC
) AS row_num
```

---

### 17. `stg_geolocation` returns 0 rows

**Symptoms:** `stg_geolocation` view returns no data. `dim_customers` and `dim_sellers` have NULL lat/lng for every row.

**Cause:** The bounding-box filter compares STRING values lexicographically if the `CAST AS FLOAT64` is missing from the WHERE clause. String comparison `'-35' <= geolocation_lat <= '5'` has different semantics than numeric — most rows are excluded.

**Fix:** Confirm the WHERE clause casts before comparing:
```sql
WHERE CAST(geolocation_lat AS FLOAT64) BETWEEN -35 AND 5
  AND CAST(geolocation_lng AS FLOAT64) BETWEEN -75 AND -34
```

**Verification:**
```sql
SELECT COUNT(*) FROM stg_geolocation;
-- Should return ~8,500 unique zip code prefixes
```

---

### 18. `profiles.yml` not found — wrong working directory

**Symptoms:**
```
ERROR: Could not find profile named 'caravela'
```
or
```
Runtime Error: Could not find a profiles.yml file
```

**Cause:** dbt looks for `profiles.yml` in the current working directory by default. If run from the repo root instead of `dbt/`, the file isn't found.

**Fix:** Either change to the dbt directory or specify the profiles path:
```bash
# Option 1 — change directory
cd dbt && dbt build

# Option 2 — specify profiles dir
dbt build --profiles-dir ./dbt --project-dir ./dbt
```

**Note:** All project scripts (`launch_dagster.sh`, Dagster `assets.py`) use `__file__`-relative paths and handle this automatically.

---

## dbt (Marts Layer)

### 19. `fct_sales.customer_unique_id` is all NULL

**Symptoms:** `fct_sales` materialises successfully but `customer_unique_id` is NULL for every row. The `not_null` test on `customer_unique_id` fails.

**Cause:** `stg_order_items` and `stg_customers` share no common column. Joining them directly produces zero matches — the JOIN silently returns NULL for all customer columns.

**Fix:** Use the three-source CTE pattern: `stg_order_items → stg_orders` (on `order_id`) → `stg_customers` (on `customer_id`):
```sql
WITH order_items AS (SELECT * FROM {{ ref('stg_order_items') }}),
     orders     AS (SELECT order_id, customer_id FROM {{ ref('stg_orders') }}),
     customers  AS (SELECT customer_id, customer_unique_id FROM {{ ref('stg_customers') }})
SELECT ...
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
JOIN customers c ON o.customer_id = c.customer_id
```

**Diagnostic:**
```sql
SELECT COUNT(*) FROM fct_sales WHERE customer_unique_id IS NULL;
-- Should return 0
```

---

### 20. `fct_sales` revenue double-counted — `order_payment_value` included

**Symptoms:** Revenue totals from `fct_sales` are ~2–3x higher than expected. Reconciliation test fails with large diffs.

**Cause:** `order_payment_value` is an order-level aggregate. Including it on item-level rows causes it to be counted once per item in the order — a 3-item order triples the payment value.

**Fix:** Do not include `order_payment_value` in `fct_sales`. Use `fct_payments` for payment analysis. Revenue in `fct_sales` is `total_sale_amount = price + freight_value` (item-level).

---

### 21. `fct_reviews` FK test fails — 756 orders have no items

**Symptoms:** `relationships` test on `fct_reviews.order_id → fct_sales.order_id` reports ~756 violations.

**Cause:** 756 orders in the Olist dataset have reviews but zero line items (itemless orders). They exist in `stg_orders` and `fct_reviews` but not in `fct_sales`.

**Fix:** The FK must target `stg_orders`, not `fct_sales`:
```yaml
- name: order_id
  tests:
    - relationships:
        to: ref('stg_orders')    # NOT ref('fct_sales')
        field: order_id
```

**Context:** This is the only mart FK that points to a staging table. See ADR-003.

---

### 22. `fct_payments.date_key` is all NULL

**Symptoms:** `fct_payments` builds successfully but `date_key` is NULL for every row.

**Cause:** `stg_payments` has no timestamp column — `date_key` must come from `stg_orders.order_purchase_timestamp`. If the `stg_orders` CTE is missing, there is no source for `date_key`.

**Fix:** Include an explicit `ref('stg_orders')` CTE:
```sql
WITH payments AS (SELECT * FROM {{ ref('stg_payments') }}),
     orders   AS (SELECT order_id, date_key FROM {{ ref('stg_orders') }})
SELECT p.*, o.date_key
FROM payments p
LEFT JOIN orders o ON p.order_id = o.order_id
```

**Secondary impact:** Without this `ref()`, dbt's DAG omits the `stg_orders → fct_payments` dependency edge, breaking Dagster lineage and execution ordering.

---

### 23. `dim_customers` / `dim_sellers` geolocation lat/lng all NULL

**Symptoms:** Every row in `dim_customers` or `dim_sellers` has NULL `geolocation_lat` and `geolocation_lng`, even though `stg_geolocation` has data.

**Cause:** Join key name mismatch. `stg_geolocation` exposes `zip_code_prefix`, while customers have `customer_zip_code_prefix` and sellers have `seller_zip_code_prefix`.

**Fix:** Verify the ON clause uses the correct column names on each side:
```sql
-- dim_customers
LEFT JOIN geo g ON c.customer_zip_code_prefix = g.zip_code_prefix

-- dim_sellers
LEFT JOIN geo g ON s.seller_zip_code_prefix = g.zip_code_prefix
```

---

### 24. `dim_customers` has duplicate rows — PK test fails

**Symptoms:** `unique` test on `dim_customers.customer_unique_id` fails. Row count is ~99k instead of ~96k.

**Cause:** `stg_customers` has multiple rows per `customer_unique_id` — a repeat customer appears once per order. Without deduplication, the dimension inherits these duplicates.

**Fix:** Deduplicate in the model:
```sql
ROW_NUMBER() OVER (
    PARTITION BY customer_unique_id
    ORDER BY customer_id
) AS row_num
...
WHERE row_num = 1
```

**Diagnostic:**
```sql
SELECT customer_unique_id, COUNT(*)
FROM stg_customers
GROUP BY 1 HAVING COUNT(*) > 1;
-- ~3,088 customers with multiple rows
```

---

### 25. `dim_date` — `date_spine` macro not found or row count wrong

**Symptoms:** `dbt compile` fails with `Macro 'dbt_utils.date_spine' not found`, or `dim_date` has an unexpected number of rows.

**Cause:**
- Macro not found → `dbt deps` was not run after a fresh clone.
- Wrong row count → `dbt_utils` version difference. Some versions treat `end_date` as exclusive (generates up to but NOT including the end date). The current `schema.yml` description says "2016-01-01 to 2018-12-30", suggesting the spine may stop one day short.

**Fix:**
```bash
dbt deps   # install dbt_utils
```

**Note:** The `date_spine` output column is `date_day` — rename it to `date_key` in the SELECT:
```sql
SELECT date_day AS date_key, ...
```

**Diagnostic:**
```sql
SELECT MIN(date_key), MAX(date_key), COUNT(*) FROM dim_date;
-- Expected: 2016-01-01, 2018-12-30 (or 2018-12-31), ~1095–1096 rows
```

---

### 26. `dim_products` missing 610 products — FK test fails on `fct_sales.product_id`

**Symptoms:** `relationships` test on `fct_sales.product_id → dim_products.product_id` reports ~1,603 violations.

**Cause:** A WHERE clause in `stg_products` or `dim_products` excluded products with blank category names. Those 610 products still appear in `stg_order_items` → `fct_sales`.

**Fix:** Remove any WHERE filter on category name. The COALESCE with CASE/NULLIF in `stg_products` correctly assigns `'uncategorized'` to blank-category products — no rows should be excluded.

**Diagnostic:**
```sql
SELECT COUNT(*) FROM dim_products WHERE product_category_name_english = 'uncategorized';
-- Should return 610
```

---

### 27. Dagster DAG missing `stg_orders → fct_payments` edge

**Symptoms:** In the Dagster UI asset graph, `fct_payments` shows no dependency on `stg_orders`. Materialising `fct_payments` before `stg_orders` may produce stale or NULL `date_key` values.

**Cause:** dbt builds its DAG from `ref()` calls. If `fct_payments` doesn't include `{{ ref('stg_orders') }}` in its SQL, dbt (and therefore Dagster via `manifest.json`) doesn't know the dependency exists.

**Fix:** The explicit CTE with `{{ ref('stg_orders') }}` in `fct_payments.sql` is the fix (see entry #22). Even if only used for `date_key`, the `ref()` call registers the DAG edge.

---

### 28. `fct_sales` row count inflated — fan-out from duplicate `customer_id` in staging

**Symptoms:** `fct_sales` row count test (`110k–120k`) fails high. Revenue sums are inflated.

**Cause:** If `stg_customers` has duplicate `customer_id` values (e.g., Meltano ran with `WRITE_APPEND` instead of `WRITE_TRUNCATE`, doubling raw data), the `JOIN customers c ON o.customer_id = c.customer_id` fans out — each order item produces N rows instead of 1.

**Fix:** Confirm Meltano uses `write_disposition: WRITE_TRUNCATE` (see entry #4). Then verify:
```sql
SELECT customer_id, COUNT(*) FROM stg_customers GROUP BY 1 HAVING COUNT(*) > 1;
-- Should return 0 rows (customer_id is unique in stg_customers)
```

**Note:** This is distinct from `customer_unique_id` duplication (entry #24) — `customer_id` should always be unique in staging even though `customer_unique_id` is not.

---

### 29. `dim_customers` / `dim_sellers` PK test fails — fan-out from geolocation join

**Symptoms:** `unique` test on `dim_customers.customer_unique_id` or `dim_sellers.seller_id` fails, even after deduplication.

**Cause:** If `stg_geolocation` has duplicate `zip_code_prefix` values (GROUP BY was dropped, or the bounding-box filter was removed causing multiple coordinate clusters per zip), the LEFT JOIN fans out dimensions.

**Fix:** Verify `stg_geolocation` has one row per zip:
```sql
SELECT zip_code_prefix, COUNT(*)
FROM stg_geolocation
GROUP BY 1 HAVING COUNT(*) > 1;
-- Should return 0 rows
```

If duplicates exist, check `stg_geolocation.sql` — the `GROUP BY geolocation_zip_code_prefix` and `AVG()` aggregation must be present.

---

### 30. `fct_sales.date_key` is NULL — `order_purchase_timestamp` unparseable

**Symptoms:** `not_null` test on `fct_sales.date_key` fails for a small number of rows.

**Cause:** `stg_orders` derives `date_key` as `DATE(SAFE_CAST(order_purchase_timestamp AS TIMESTAMP))`. If the raw value is malformed or empty, `SAFE_CAST` returns NULL silently — and that NULL propagates through the JOIN into `fct_sales`.

**Fix:** Check for NULL date_keys in staging:
```sql
SELECT order_id, order_purchase_timestamp
FROM stg_orders
WHERE date_key IS NULL;
```

If rows appear, inspect the raw values. `order_purchase_timestamp` is mandatory in the Olist dataset — NULLs indicate a data loading issue (partial load, encoding problem).

---

### 31. `assert_date_key_range` test does not catch NULL dates

**Symptoms:** Test passes green, but `fct_payments` has NULL `date_key` values that go undetected.

**Cause:** The singular test uses `WHERE date_key < '2016-01-01' OR date_key > '2018-12-31'` — SQL comparison operators exclude NULL values. NULL dates are neither out-of-range nor in-range; they are simply invisible to this test.

**Current state:** This is by design for `fct_payments` — the LEFT JOIN on `stg_orders` legitimately produces NULL `date_key` for orphan payments. No `not_null` test is applied to `fct_payments.date_key` for this reason (see changelog 2026-03-15).

**If you need to audit NULLs:**
```sql
SELECT 'fct_payments' AS source, COUNT(*) AS null_count
FROM fct_payments WHERE date_key IS NULL
UNION ALL
SELECT 'fct_sales', COUNT(*) FROM fct_sales WHERE date_key IS NULL
UNION ALL
SELECT 'fct_reviews', COUNT(*) FROM fct_reviews WHERE date_key IS NULL;
-- fct_payments: small number expected; fct_sales and fct_reviews: should be 0
```

---

### 32. `stg_reviews` uses `CAST` not `SAFE_CAST` for timestamps — latent runtime risk

**Symptoms:** `dbt build` fails on `stg_reviews` with `Bad TIMESTAMP value` error.

**Cause:** `stg_reviews` uses `CAST(review_creation_date AS TIMESTAMP)` and `CAST(review_answer_timestamp AS TIMESTAMP)` instead of `SAFE_CAST`. The `tap-csv` loader encodes empty CSV cells as `''` not NULL. If any review row has a blank timestamp, `CAST('' AS TIMESTAMP)` raises a BigQuery error.

**Current risk:** Low — review timestamps appear fully populated in the current Olist dataset. But this is inconsistent with `stg_orders`, which uses `SAFE_CAST` for the same reason.

**Fix (preventive):** Change to `SAFE_CAST` in `stg_reviews.sql`:
```sql
SAFE_CAST(review_creation_date AS TIMESTAMP) AS review_creation_date,
SAFE_CAST(review_answer_timestamp AS TIMESTAMP) AS review_answer_timestamp,
DATE(SAFE_CAST(review_creation_date AS TIMESTAMP)) AS date_key
```

---

### 33. `assert_payment_reconciliation` passes vacuously when `fct_sales` is empty

**Symptoms:** All tests pass green, including the reconciliation test, but `fct_sales` actually has 0 rows.

**Cause:** The test JOINs `fct_payments` to `fct_sales`. If `fct_sales` is empty (see entry #15 — raw data not loaded), the JOIN produces 0 result rows. Zero rows = zero violations = test passes. It proves nothing.

**Mitigation:** The row count test on `fct_sales` (`expect_table_row_count_to_be_between`, min=110000) should fail first and flag the root cause. Always investigate row count failures before trusting reconciliation results.

---

### 34. FLOAT64 precision drift in `total_sale_amount`

**Symptoms:** `total_sale_amount` values show floating-point artefacts (e.g., `29.990000000000002` instead of `29.99`). Aggregated GMV totals have small rounding discrepancies vs. raw source sums.

**Cause:** `price` and `freight_value` are cast to `FLOAT64` (IEEE 754 binary floating point) in `stg_order_items`. `price + freight_value` inherits this precision limitation.

**Impact:** Cosmetic for most analyses. The payment reconciliation test uses a `> R$20.00` threshold which absorbs floating-point noise. Dashboard KPIs showing currency values may display extra decimal places.

**Fix (if needed):** Either round in the mart:
```sql
ROUND(oi.price + oi.freight_value, 2) AS total_sale_amount
```
Or cast to `NUMERIC` in staging for exact decimal arithmetic:
```sql
CAST(price AS NUMERIC) AS price
```

---

### 35. `fct_sales` delivery timestamps repeated across items — misleading COUNT(*)

**Symptoms:** Delivery metrics (on-time rate, average delay) are subtly wrong. For example, on-time rate appears lower than expected.

**Cause:** `fct_sales` is at order-item granularity. `order_delivered_customer_date` and `order_estimated_delivery_date` are order-level attributes repeated across all items in an order. Using `COUNT(*)` instead of `COUNT(DISTINCT order_id)` over-weights multi-item orders.

**Impact:** A 5-item late order counts as 5 late deliveries instead of 1. Multi-item orders average ~1.15 items but late orders may correlate with larger baskets, skewing the rate.

**Fix:** Always use `COUNT(DISTINCT order_id)` for delivery calculations:
```sql
-- Correct
SELECT
    COUNT(DISTINCT CASE WHEN order_delivered_customer_date <= order_estimated_delivery_date
          THEN order_id END) * 1.0
    / COUNT(DISTINCT CASE WHEN order_delivered_customer_date IS NOT NULL THEN order_id END)
    AS on_time_rate
FROM fct_sales;

-- WRONG — counts items, not orders
SELECT COUNT(CASE WHEN ... END) * 1.0 / COUNT(*) ...
```
