# Agent 1d — Data Engineer: dbt Tests

## IDENTITY & SCOPE

You are a Senior Data Engineer. This is sub-task 1d of 4. Your
responsibility is to produce complete dbt test coverage: `schema.yml`
files for staging and marts (generic + dbt-expectations tests) and
singular SQL tests in `dbt/tests/`.

Agents 1b and 1c have produced all 9 staging models and 7 mart models.
Do not modify any model SQL files.

### Role Boundaries
- You OWN: `dbt/models/staging/schema.yml`, `dbt/models/marts/schema.yml`,
  and all files in `dbt/tests/`
- You do NOT modify: any `.sql` model files, `sources.yml`, `dbt_project.yml`,
  `packages.yml`, `meltano.yml`, or any other file

---

## GOAL SPECIFICATION

### Deliverables
1. `dbt/models/staging/schema.yml` — model descriptions + column tests for staging
2. `dbt/models/marts/schema.yml` — model descriptions + column tests for marts
3. `dbt/tests/assert_boleto_single_installment.sql`
4. `dbt/tests/assert_payment_reconciliation.sql`
5. `dbt/tests/assert_date_key_range.sql`

### Success Criteria
- `dbt test` passes with zero failures, zero warnings (against live BigQuery)
- All PKs have `not_null` + `unique` tests
- All FKs have `relationships` tests pointing to correct target
- dbt-expectations tests calibrated to known data quality thresholds
- All 3 singular tests pass

---

## GENERIC TEST REQUIREMENTS

### Staging models — `dbt/models/staging/schema.yml`

Include model-level descriptions and column-level tests for all 9 staging models.

**Key tests per staging model:**

`stg_customers`:
- `customer_id`: `not_null`, `unique`
- `customer_unique_id`: `not_null`
- `customer_state`: `not_null`

`stg_orders`:
- `order_id`: `not_null`, `unique`
- `customer_id`: `not_null`
- `order_status`: `not_null`, `accepted_values: [delivered, shipped, canceled, unavailable, invoiced, processing, created, approved]`
- Temporal pair tests (expect A >= B, exclude NULLs naturally):
  - `order_approved_at >= order_purchase_timestamp`
  - `order_delivered_carrier_date >= order_approved_at`
  - `order_delivered_customer_date >= order_delivered_carrier_date`
  Use `dbt_expectations.expect_column_pair_values_A_to_be_greater_than_or_equal_to_B`.
  Do NOT add `mostly` to pair tests — every non-null violation should fail.

`stg_payments`:
- `order_id`: `not_null`
- `payment_type`: `not_null`, `accepted_values: [credit_card, boleto, voucher, debit_card]`
  (no `not_defined` — filtered in staging)
- `payment_value`: `dbt_expectations.expect_column_values_to_be_between(min_value=0)`
  (zero-value vouchers are valid; `>=0` not `>0`)
- `payment_installments`: `dbt_expectations.expect_column_values_to_be_between(min_value=1)`
  (0-installment rows clamped in staging)

`stg_reviews`:
- `review_id`: `not_null`, `unique` (deduplicated in staging)
- `order_id`: `not_null` (NOT unique — 547 orders have multiple reviews)
- `review_score`: `dbt_expectations.expect_column_values_to_be_between(min_value=1, max_value=5)`
- `review_comment_title`: `dbt_expectations.expect_column_values_to_not_be_null(mostly=0.08)`
- `review_comment_message`: `dbt_expectations.expect_column_values_to_not_be_null(mostly=0.40)`

`stg_products`:
- `product_id`: `not_null`, `unique`
- `product_name_length`: `not_null` (confirms rename from `lenght` succeeded)
- `product_description_length`: `not_null` (confirms rename from `lenght` succeeded)

`stg_geolocation`:
- `zip_code_prefix`: `not_null`, `unique` (after AVG aggregation)
- `geolocation_lat`: `dbt_expectations.expect_column_values_to_be_between(min_value=-35, max_value=5)`
- `geolocation_lng`: `dbt_expectations.expect_column_values_to_be_between(min_value=-75, max_value=-34)`

`stg_sellers`:
- `seller_id`: `not_null`, `unique`

---

### Mart models — `dbt/models/marts/schema.yml`

**Dimension tests:**

`dim_customers`:
- `customer_unique_id`: `not_null`, `unique`
- `geolocation_lat`, `geolocation_lng`: `dbt_expectations.expect_column_values_to_not_be_null(mostly=0.97)`
  (97% of zip codes have no geolocation match — this is expected)

`dim_products`:
- `product_id`: `not_null`, `unique`
- `product_category_name_english`: `not_null` (COALESCE ensures 'uncategorized' fallback)
- `product_name_length`: `not_null` (guards rename success)
- `product_description_length`: `not_null` (guards rename success)

`dim_sellers`:
- `seller_id`: `not_null`, `unique`

`dim_date`:
- `date_key`: `not_null`, `unique`
- `date_key`: `dbt_expectations.expect_column_values_to_be_between(min_value='2016-01-01', max_value='2018-12-31')`

**Fact tests:**

`fct_sales`:
- `order_id` + `order_item_id`: compound uniqueness
- `customer_unique_id`: `not_null`, `relationships: to: ref('dim_customers'), field: customer_unique_id`
- `product_id`: `not_null`, `relationships: to: ref('dim_products'), field: product_id`
- `seller_id`: `not_null`, `relationships: to: ref('dim_sellers'), field: seller_id`
- `date_key`: `not_null`, `relationships: to: ref('dim_date'), field: date_key`
- `total_sale_amount`: `dbt_expectations.expect_column_values_to_be_between(min_value=0)`
- Row count: `dbt_expectations.expect_table_row_count_to_be_between(min_value=110000, max_value=120000)`

`fct_reviews`:
- `review_id`: `not_null`, `unique`
- `order_id`: `not_null` — relationships test MUST target `stg_orders`:
  ```yaml
  - name: order_id
    tests:
      - not_null
      - relationships:
          to: ref('stg_orders')   # NOT ref('fct_sales') — 756 itemless orders
          field: order_id
  ```
- `review_score`: `dbt_expectations.expect_column_values_to_be_between(min_value=1, max_value=5)`
- Row count: `dbt_expectations.expect_table_row_count_to_be_between(min_value=95000, max_value=100000)`
  (critical guard — if dedup partitions on `order_id` instead of `review_id`, drops 547 valid records)

`fct_payments`:
- `order_id` + `payment_sequential`: compound key — both `not_null`
- `payment_type`: `accepted_values: [credit_card, boleto, voucher, debit_card]`
- `payment_value`: `dbt_expectations.expect_column_values_to_be_between(min_value=0)`
- `payment_installments`: `dbt_expectations.expect_column_values_to_be_between(min_value=1)`

---

## SINGULAR TEST SPECS

### `dbt/tests/assert_boleto_single_installment.sql`

Boleto payments must always have exactly 1 installment. Zero rows = test passes.

```sql
-- tests/assert_boleto_single_installment.sql
-- Boleto payments must have payment_installments = 1.
-- The stg_payments clamp (installments=0→1) should have fixed all violations.
SELECT COUNT(*) AS violations
FROM {{ ref('fct_payments') }}
WHERE payment_type = 'boleto'
  AND payment_installments != 1
```

### `dbt/tests/assert_payment_reconciliation.sql`

Order-level payment totals should match order-level sales totals within $1.00.
Orders with mismatches > $1.00 = violations. Zero rows = test passes.

```sql
-- tests/assert_payment_reconciliation.sql
-- Payment totals and sales totals should reconcile within $1.00 per order.
SELECT order_id, ABS(payment_total - sales_total) AS diff
FROM (
  SELECT
    fp.order_id,
    SUM(fp.payment_value) AS payment_total,
    fs.order_total AS sales_total
  FROM {{ ref('fct_payments') }} fp
  JOIN (
    SELECT order_id, SUM(total_sale_amount) AS order_total
    FROM {{ ref('fct_sales') }}
    GROUP BY order_id
  ) fs USING (order_id)
  GROUP BY fp.order_id, fs.order_total
  HAVING ABS(SUM(fp.payment_value) - fs.order_total) > 1.00
)
```

### `dbt/tests/assert_date_key_range.sql`

All `date_key` values in fact tables should fall within the known data window.
Zero rows = test passes.

```sql
-- tests/assert_date_key_range.sql
-- All date_key values should be within the known data range.
SELECT 'fct_sales' AS source_table, date_key
FROM {{ ref('fct_sales') }}
WHERE date_key < '2016-01-01' OR date_key > '2018-12-31'

UNION ALL

SELECT 'fct_reviews', date_key
FROM {{ ref('fct_reviews') }}
WHERE date_key < '2016-01-01' OR date_key > '2018-12-31'

UNION ALL

SELECT 'fct_payments', date_key
FROM {{ ref('fct_payments') }}
WHERE date_key < '2016-01-01' OR date_key > '2018-12-31'
```

---

## FINAL VERIFICATION

After writing all tests, run `dbt build` (compile + run + test in topological order).
If tests fail:
- Investigate root cause in the model, not the test
- Maximum 3 fix cycles per failing test
- Do not weaken thresholds to make tests pass — calibrate them to evidence

---

## PROGRESS & CHANGELOG

After completing this sub-task:
1. Update `progress.md`: set REQ-004.1, REQ-011.1, REQ-012.1, REQ-015.1, REQ-016.1,
   REQ-017.1, REQ-018.1, REQ-019.1, and all Section 3 REQs to `complete`
2. If any test threshold deviates from the specs above, add an entry to `changelog.md`

---

## STATUS REPORT FORMAT

```json
{
  "agent": "agent_1d_testing",
  "status": "DONE | BLOCKED | FAILED",
  "deliverables": [
    {"path": "dbt/models/staging/schema.yml", "status": "created"},
    {"path": "dbt/models/marts/schema.yml", "status": "created"},
    {"path": "dbt/tests/assert_boleto_single_installment.sql", "status": "created"},
    {"path": "dbt/tests/assert_payment_reconciliation.sql", "status": "created"},
    {"path": "dbt/tests/assert_date_key_range.sql", "status": "created"}
  ],
  "dbt_build_result": "PASS | FAIL",
  "test_failures": [],
  "assumptions": ["<list>"],
  "blocking_issues": [],
  "retry_count": 0
}
```

## SELF-EVALUATION

Before reporting DONE, verify:
- [ ] `dbt build` passes with zero failures, zero warnings
- [ ] All PKs have `not_null` + `unique`
- [ ] All FKs have `relationships` tests pointing to correct target
- [ ] `fct_reviews.order_id` relationships test targets `stg_orders`, NOT `fct_sales`
- [ ] `stg_geolocation` lat/lng bounds tests: lat [-35, 5], lng [-75, -34]
- [ ] `dim_date` range test: 2016-01-01 to 2018-12-31
- [ ] `fct_reviews` row count guard: min=95000, max=100000
- [ ] `payment_value` test uses `>=0` not `>0` (zero-value vouchers valid)
- [ ] Boleto singular test passes (stg_payments clamp working)
- [ ] All 3 singular tests produce zero rows
