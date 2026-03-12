# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. Aligned with BRD v3.7 (2026-03-11). Last updated: 2026-03-11.

## Project Overview

**Project Caravela** — End-to-end data pipeline for the Brazilian E-Commerce Dataset by Olist (~100k orders, 2016–2018). Source CSVs are in `raw_data/`. Requirements and BRD are in `requirements/`.

## Confirmed Toolchain (Non-Negotiable)

| Layer | Tool |
|---|---|
| Ingestion | Meltano (`tap-spreadsheets-anywhere` → `target-bigquery`) → BigQuery `olist_raw` dataset |
| Transformation (ELT) | dbt → BigQuery `olist_analytics` dataset |
| Data Quality | dbt-expectations generic tests + dbt singular tests (both via `dbt test`) |
| Orchestration | Dagster (manual + daily 09:00 SGT schedule) via `dagster-dbt` |
| Analysis | SQLAlchemy + pandas + Jupyter notebooks |
| Dashboard | Streamlit (`dashboard.py`), sourcing data from Parquet files |

**No alternatives to the above tools are in scope.** No Python ingestion scripts, no live BigQuery queries in Streamlit. Parquet files are produced by the analysis layer (Jupyter), not by dbt.

## BigQuery Dataset Architecture

### Raw Dataset (`olist_raw`)
One table per source CSV, loaded by Meltano. 9 tables total.

### Analytics Dataset (`olist_analytics`) — Star Schema
**Fact tables:**
- `fct_sales` — order-item granularity; FKs to all 4 dims; `total_sale_amount` = price + freight_value; includes `order_delivered_customer_date` and `order_estimated_delivery_date` (NULLABLE TIMESTAMP, order-level attributes repeated across item rows — use `COUNT(DISTINCT order_id)` for delivery rate calculations)
- `fct_reviews` — review granularity; PK: `review_id`; FK: `order_id` → `stg_orders` (not fct_sales)
- `fct_payments` — payment-method granularity; compound key: (`order_id`, `payment_sequential`)

**Dimension tables:**
- `dim_customers` — PK: `customer_unique_id`; includes city, state, zip, geolocation lat/lng
- `dim_products` — PK: `product_id`; includes English category name (COALESCE fallback)
- `dim_sellers` — PK: `seller_id`; includes city, state, zip, geolocation lat/lng
- `dim_date` — PK: `date_key`; includes year, month, day, day_of_week, quarter

### dbt Lineage
```
olist_raw.customers              → stg_customers  → dim_customers
                                   stg_customers  → fct_sales (customer_unique_id resolution)
olist_raw.orders                 → stg_orders     → fct_sales
                                   stg_orders     → fct_payments (date_key via order_purchase_timestamp)
olist_raw.order_items            → stg_order_items → fct_sales
olist_raw.products +             → stg_products   → dim_products
  olist_raw.product_category_name_translation
olist_raw.sellers                → stg_sellers    → dim_sellers
olist_raw.geolocation            → stg_geolocation → dim_customers (lat/lng), dim_sellers (lat/lng)
olist_raw.order_payments         → stg_payments   → fct_payments
olist_raw.order_reviews          → stg_reviews    → fct_reviews
(generated)                                       → dim_date
```
Final schema tables must be produced from staging models, not directly from raw tables.

## Meltano Configuration

**Prerequisite:** `meltano install` must be run on any fresh clone before `meltano run`. This installs tap and target plugin virtual environments under `.meltano/`. One-time setup per machine.

### Key `meltano.yml` constraints

- **Stream names = BigQuery table names**: Each stream's `stream_name` in `tap-spreadsheets-anywhere` config becomes the BigQuery table name in `olist_raw`. These are the contract with `sources.yml` — they must exactly match the 9 names in ASMP-001: `olist_customers_dataset`, `olist_orders_dataset`, `olist_order_items_dataset`, `olist_order_payments_dataset`, `olist_order_reviews_dataset`, `olist_products_dataset`, `olist_sellers_dataset`, `olist_geolocation_dataset`, `product_category_name_translation`. Do NOT deviate without updating `sources.yml`.
- **Relative path**: `raw_data/` must be configured as a relative path from the `meltano/` directory (e.g. `../raw_data/`). Absolute paths break reproducibility across machines (REQ-036.1).
- **BOM encoding**: `product_category_name_translation.csv` requires `encoding: utf-8-sig` in its stream config. This is the only file that needs it — the UTF-8 BOM corrupts the first column header without this setting, causing the `stg_products` staging join to silently produce nulls.
- **Write disposition**: `target-bigquery` must be configured with `write_disposition: WRITE_TRUNCATE`. `WRITE_APPEND` duplicates all rows on every Dagster scheduled run — the dataset is fixed/historical so full refresh is always correct.
- **All columns load as STRING**: `tap-spreadsheets-anywhere` performs no type inference. Every column in every raw table arrives as STRING. All casts are the sole responsibility of the dbt staging layer (ASMP-028).

### Known packaging issue — `setuptools` v81 breaks Meltano plugins

**Background:** `setuptools` v81.0.0 (released 2026-02-06) removed `pkg_resources` entirely. Older Meltano community plugins (`target-bigquery`, `tap-spreadsheets-anywhere`) depend on `pkg_resources` at install time. If pip resolves `setuptools>=81` into a plugin's venv, the plugin fails to install or import with `ModuleNotFoundError: No module named 'pkg_resources'`.

**Workaround:** Add `setuptools<70` to the `pip_url` field for each affected plugin in `meltano.yml`. Meltano installs each plugin in an isolated venv under `.meltano/` — the extra package in `pip_url` forces a compatible setuptools into that venv.

```yaml
# target-bigquery
pip_url: git+https://github.com/z3z1ma/target-bigquery.git setuptools<70

# tap-spreadsheets-anywhere (apply same fix — same pkg_resources exposure)
pip_url: tap-spreadsheets-anywhere setuptools<70
```

Apply this to **both plugins** before running `meltano install`. If `meltano install` has already been run without the fix, delete `.meltano/` and re-run after adding the `setuptools<70` entries.

### Geolocation performance note
`olist_geolocation_dataset.csv` has 1,000,163 rows — larger than all other source files combined. `tap-spreadsheets-anywhere` streams it without loading into memory, but the BigQuery load job takes several minutes. The Dagster `meltano_ingest` asset will appear as "running" with no visible progress during this load. **This is expected — do not interrupt the run.**

## Critical Implementation Notes

- **`customer_unique_id` resolution**: `fct_sales` is a **three-source model** (`stg_order_items` + `stg_orders` + `stg_customers`). `stg_order_items` has `order_id` but no `customer_id`. `customer_id` is in `stg_orders` — but it is order-scoped (one value per order, not per customer). `customer_unique_id` is the true customer PK and lives only in `stg_customers`. Resolution path: `stg_order_items.order_id → stg_orders.customer_id → stg_customers.customer_unique_id`. Joining `stg_order_items` directly to `stg_customers` produces no matches and materialises null `customer_unique_id` silently — the FK test fires after the fact. Required CTE pattern:
  ```sql
  WITH order_items AS (SELECT * FROM {{ ref('stg_order_items') }}),
       orders     AS (SELECT order_id, customer_id, ... FROM {{ ref('stg_orders') }}),
       customers  AS (SELECT customer_id, customer_unique_id FROM {{ ref('stg_customers') }})
  -- Join: order_items → orders (on order_id) → customers (on customer_id)
  ```
- **`stg_reviews` deduplication**: Source has 789 duplicate `review_id` values. Deduplicate using `ROW_NUMBER() OVER (PARTITION BY review_id ORDER BY review_answer_timestamp DESC)` before building `fct_reviews`. After deduplication `review_id` is unique — but `order_id` is NOT unique in `fct_reviews` (547 orders have multiple review records with distinct `review_id` values). Test design: apply `unique` + `not_null` to `review_id` only; apply `not_null` only to `order_id` — do NOT add a `unique` test to `order_id`.
- **`stg_geolocation` bounding box**: Filter to Brazil bounds (`lat BETWEEN -35 AND 5`, `lng BETWEEN -75 AND -34`) before AVG() aggregation. Source has coordinate outliers (lat up to +45°, lng up to +121°).
- **`stg_products` COALESCE**: Apply `COALESCE(english_name, portuguese_name, 'uncategorized')` — 2 categories have no translation, 610 products have null category.
- **`stg_products` column renames (DEF-009)**: Source `olist_products_dataset.csv` has two misspelled column names: `product_name_lenght` and `product_description_lenght`. Rename in the `stg_products` SELECT list to `product_name_length` and `product_description_length`. Failure to rename propagates the misspellings into `dim_products` and silently breaks any downstream reference to the correctly-spelled names. Both columns must be `not_null` tested in `dim_products` `schema.yml` to confirm the rename succeeded.
- **`stg_products` dual-source declaration**: `stg_products` is the only staging model joining two raw tables. Both must be declared in `sources.yml` — using `source()` for both keeps the full lineage visible in the dbt DAG (and therefore in Dagster's asset graph). Do NOT reference `product_category_name_translation` as a hardcoded table name:
  ```yaml
  # sources.yml
  sources:
    - name: olist_raw
      tables:
        - name: olist_products_dataset
        - name: product_category_name_translation
  ```
  In the model: `{{ source('olist_raw', 'product_category_name_translation') }}`
- **`stg_payments` fixes — must be in staging, not in `fct_payments`**: (1) Filter `payment_type = 'not_defined'` (3 rows, all zero-value — error/test records with no business value). (2) Clamp `payment_installments = 0` → `1` via `GREATEST(CAST(payment_installments AS INT64), 1)` (2 credit_card rows with semantically invalid 0 installments). Both fixes belong in `stg_payments`, not `fct_payments`. Convention: all source defect corrections happen at the staging layer so that every downstream consumer (including `fct_payments` and any future model) inherits clean data. Applying these in `fct_payments` would leave `stg_payments` serving corrupted rows and make the dbt-expectations accepted-values / range tests misleading — they would pass on the mart while staging remains uncleaned.
- **`fct_reviews.order_id`** links to `stg_orders`, NOT `fct_sales` — 756 itemless orders have reviews but no `fct_sales` rows (those orders had no items). The dbt `relationships` test in `schema.yml` must target the staging model — this is the only place in the project where a mart FK points to a staging table rather than another mart:
  ```yaml
  - name: order_id
    tests:
      - not_null
      - relationships:
          to: ref('stg_orders')   # NOT ref('fct_sales') — 756 itemless orders exist
          field: order_id
  ```
- **`order_payment_value` removed** from `fct_sales` — order-level aggregate on item-level fact causes double-counting. Use `fct_payments` directly.
- **`fct_payments` requires explicit `ref('stg_orders')`**: `date_key` is derived from `order_purchase_timestamp` which lives in `stg_orders`, not `stg_payments`. The model must include `ref('stg_orders')` as a CTE source alongside `ref('stg_payments')` — without it dbt's DAG omits the dependency, losing execution-order guarantees and Dagster lineage visibility.
- **`dim_date` generation**: Use `dbt_utils.date_spine(datepart="day", start_date="cast('2016-01-01' as date)", end_date="cast('2018-12-31' as date)")`. Range `2016-01-01` to `2018-12-31` gives full coverage with buffer (first order 2016-09-04, last 2018-10-17, review/delivery dates can extend beyond). `dbt_utils` is already a declared package dependency — no additional install required.
- **`date_key` type confirmed: `DATE`**. `dim_date.date_key` is a DATE PK — direct output of `dbt_utils.date_spine`, no casting needed. All three fact tables derive `date_key` by casting the source timestamp: `DATE(CAST(timestamp_col AS TIMESTAMP))`. FK joins work natively (same type both sides). Staging cast patterns:
  - `stg_orders` → `fct_sales` / `fct_payments`: `DATE(CAST(order_purchase_timestamp AS TIMESTAMP)) AS date_key`
  - `stg_reviews` → `fct_reviews`: `DATE(CAST(review_creation_date AS TIMESTAMP)) AS date_key`
  - `dim_date` range test: `expect_column_values_to_be_between(min_value='2016-01-01', max_value='2018-12-31')`
- **`product_category_name_translation.csv`** has a UTF-8 BOM — resolved: configure `encoding: utf-8-sig` in the `meltano.yml` stream config for this file (see Meltano Configuration section). Without it the BOM character is prepended to the first column header, causing the staging join to produce silently null values.

## dbt Packages

| Package | Purpose |
|---|---|
| `dbt-expectations` | Generic tests in schema.yml (column validation, pair tests, row counts) |
| `dbt_utils` | Recommended — `date_spine` for dim_date, utility macros |

Both declared in `packages.yml`, installed via `dbt deps`.

## Dagster Architecture

- **`dagster-dbt`** auto-generates one asset per dbt model from `manifest.json`
- **Meltano asset**: shell command executing `meltano run`, wired as upstream dependency
- **Execution mode**: `dbt build` (interleaved run + test in topological order)
- **Schedule**: daily 09:00 SGT (`Asia/Singapore`), plus manual triggering via UI/CLI
- Asset descriptions inherited from dbt `schema.yml` model descriptions
- **No partition strategy** — fixed historical dataset; `WRITE_TRUNCATE` replaces full tables on every run. Do NOT configure `PartitionsDefinition` on any asset.

### Dagster Project File Structure (O-03)
```
dagster/
  dagster_project/
    __init__.py       ← Definitions object (assets + jobs + schedules + resources)
    assets.py         ← @dbt_assets decorator + Meltano shell asset
    schedules.py      ← daily 09:00 SGT ScheduleDefinition
    resources.py      ← DbtCliResource + credential config
  pyproject.toml      ← [tool.dagster] section pointing to dagster_project module
```

### dbt profiles.yml — Environment Variable Interpolation (O-08)
dbt must authenticate to BigQuery via the service account key. Do NOT hardcode the keyfile path — use `env_var()` so the profile works across machines:
```yaml
# dbt/profiles.yml
caravela:
  target: dev
  outputs:
    dev:
      type: bigquery
      method: service-account
      project: "{{ env_var('GCP_PROJECT_ID') }}"
      dataset: olist_analytics
      keyfile: "{{ env_var('GOOGLE_APPLICATION_CREDENTIALS') }}"
      threads: 4
      timeout_seconds: 300
```
Both `GCP_PROJECT_ID` and `GOOGLE_APPLICATION_CREDENTIALS` must be set before `dagster dev` or `dbt build`.

### dbt Asset Pattern (O-05 + O-11)
Use `DbtCliResource` with `dbt.cli(["build"])`. The `manifest.json` path must use `__file__`-relative resolution — a relative path breaks when `dagster dev` is launched from a non-`dagster/` directory:
```python
# dagster/dagster_project/assets.py
DBT_MANIFEST_PATH = (
    Path(__file__).parent.parent.parent / "dbt" / "target" / "manifest.json"
)

@dbt_assets(manifest=DBT_MANIFEST_PATH)
def caravela_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()
```
Do NOT use the older split `DbtRun` + `DbtTest` ops — `dbt build` runs models and tests interleaved so a failing staging test blocks dependent mart models.

### Meltano Asset Wiring (O-02 + O-04 + O-12 + O-13)
`@dbt_assets` generates assets for dbt **models** only — not sources. Wire Meltano as upstream by declaring each `olist_raw` table as a Dagster `AssetSpec`. **The first element of each `AssetKey` must exactly match the source name in `sources.yml`** — if they differ, the Meltano→dbt edge disappears from the graph silently. Since `sources.yml` declares `name: olist_raw`, the key prefix is `["olist_raw", ...]`.

Forward Meltano stdout/stderr to Dagster's log system so failures are visible in the UI:
```python
RAW_TABLES = [
    AssetKey(["olist_raw", "olist_customers_dataset"]),
    AssetKey(["olist_raw", "olist_orders_dataset"]),
    AssetKey(["olist_raw", "olist_order_items_dataset"]),
    AssetKey(["olist_raw", "olist_order_payments_dataset"]),
    AssetKey(["olist_raw", "olist_order_reviews_dataset"]),
    AssetKey(["olist_raw", "olist_products_dataset"]),
    AssetKey(["olist_raw", "olist_sellers_dataset"]),
    AssetKey(["olist_raw", "olist_geolocation_dataset"]),
    AssetKey(["olist_raw", "product_category_name_translation"]),
]

@asset(
    deps=RAW_TABLES,
    description=(
        "Runs Meltano ingestion: tap-spreadsheets-anywhere → target-bigquery. "
        "Loads all 9 Olist CSV source files into BigQuery olist_raw dataset. "
        "Write disposition: WRITE_TRUNCATE (full refresh on every run)."
    ),
)
def meltano_ingest(context: AssetExecutionContext):
    result = subprocess.run(
        ["meltano", "run", "tap-spreadsheets-anywhere", "target-bigquery"],
        cwd=Path(__file__).parent.parent.parent / "meltano",  # must set cwd
        capture_output=True,
        text=True,
    )
    if result.stdout:
        context.log.info(result.stdout)
    if result.returncode != 0:
        context.log.error(result.stderr)
        raise Exception(f"meltano run failed:\n{result.stderr}")
```

### Job Definition and Definitions Object (O-09)
`ScheduleDefinition` requires a job. Without `define_asset_job`, the schedule has nothing to target and Dagster raises a validation error at startup:
```python
# dagster/dagster_project/__init__.py
from dagster import Definitions, define_asset_job, AssetSelection
from .assets import caravela_dbt_assets, meltano_ingest
from .schedules import full_pipeline_schedule
from .resources import dbt_resource

full_pipeline_job = define_asset_job(
    name="full_pipeline_job",
    selection=AssetSelection.all(),
)

defs = Definitions(
    assets=[meltano_ingest, caravela_dbt_assets],
    jobs=[full_pipeline_job],
    schedules=[full_pipeline_schedule],
    resources={"dbt": dbt_resource},
)
```

### Schedule Definition (O-10)
Use `execution_timezone` — do not manually convert to UTC. This makes the intent explicit and avoids silent errors if the cron expression is ever edited:
```python
# dagster/dagster_project/schedules.py
from dagster import ScheduleDefinition
from . import full_pipeline_job

full_pipeline_schedule = ScheduleDefinition(
    job=full_pipeline_job,
    cron_schedule="0 9 * * *",
    execution_timezone="Asia/Singapore",
)
```

### Pre-start Requirement: `manifest.json` (O-01)
`dagster-dbt` reads `manifest.json` at **import time**. Run `dbt parse` before `dagster dev` on any fresh clone:
```bash
cd dbt && dbt parse   # generates target/manifest.json — no BigQuery connection needed
cd .. && dagster dev
```

### Credentials Propagation (O-06)
`GOOGLE_APPLICATION_CREDENTIALS` and `GCP_PROJECT_ID` must be set in the **Dagster process environment**. Verify before `dagster dev`:
```bash
echo $GOOGLE_APPLICATION_CREDENTIALS   # must return the key file path
echo $GCP_PROJECT_ID                   # must return the GCP project ID
```

### Version Compatibility (O-14)
`dagster-dbt` has hard version constraints on `dbt-core`. Mismatched versions produce silent import failures or `AttributeError` at runtime. Pin a compatible trio in `environment.yml`:
```yaml
- dbt-core>=1.7,<1.9
- dbt-bigquery>=1.7,<1.9
- dagster-dbt>=0.22,<0.23
```
Confirm compatible versions during `dbt deps` and `dagster dev` — if imports fail, check version alignment first.

### Schedule Execution (O-07)
`dagster dev` starts both the webserver and daemon — schedule fires correctly in development. For production-like setups, both processes must run:
```bash
dagster-webserver -h 0.0.0.0 -p 3000 &
dagster-daemon run &
```
Running only `dagster-webserver` shows the schedule in the UI but it will never trigger.

## Documentation

### Diagramming Tools
| Diagram | Tool | Format |
|---|---|---|
| Pipeline architecture | draw.io | SVG exported to `docs/diagrams/` |
| Data lineage | Mermaid (in `docs/data_lineage.md`) | Text — renders natively in GitHub, version-controlled |
| Star schema ERD | dbdiagram.io | PNG/SVG exported + DBML source committed for diffability |
| dbt lineage (live) | `dbt docs serve` | Auto-generated from manifest — not committed |
| Dagster asset graph (live) | Dagster UI | Auto-generated from Definitions — not committed |

### dbt Documentation
`dbt docs generate` compiles the `catalog.json` + `manifest.json` into a browsable schema explorer. `dbt docs serve` starts a local server (default :8080) with an interactive DAG and data dictionary. These files live in `target/` — not committed (covered by `.gitignore: dbt/target/`). Include `dbt docs generate && dbt docs serve` in the local run setup document as an optional diagnostic step.

### Optional Documentation (Recommended — not in BRD scope)
- **Architecture Decision Records (ADRs)** — `docs/decisions/ADR-001.md` format; capture key choices (e.g. DATE vs INTEGER for `date_key`, dataset rename, `fct_reviews → stg_orders` FK)
- **Troubleshooting guide** — common failure modes: missing `manifest.json`, wrong `GOOGLE_APPLICATION_CREDENTIALS`, BigQuery dataset not pre-created, Meltano venv not activated
- **Data dictionary** — column-level business definitions beyond dbt descriptions; useful for stakeholder handoff
- **Testing guide** — documents dbt-expectations thresholds with source-data evidence; links to `docs/data_profile.json`

## Source Data

| File | Contents |
|---|---|
| `olist_customers_dataset.csv` | Customer IDs, city, state, zip |
| `olist_orders_dataset.csv` | Order headers, status, timestamps |
| `olist_order_items_dataset.csv` | Line items, price, freight, seller |
| `olist_order_payments_dataset.csv` | Payment type and value |
| `olist_order_reviews_dataset.csv` | Customer reviews and scores |
| `olist_products_dataset.csv` | Product attributes |
| `olist_sellers_dataset.csv` | Seller location |
| `olist_geolocation_dataset.csv` | Zip → lat/lng mapping (1M rows) |
| `product_category_name_translation.csv` | Portuguese → English category names (BOM) |

## Data Quality Testing

Two complementary mechanisms, both run via `dbt test` / `dbt build`:
- **dbt-expectations generic tests** — declared in `schema.yml`; column ranges, accepted values, pair comparisons, row counts, null thresholds
- **dbt singular tests** — SQL files in `tests/`; cross-table assertions, conditional logic, FK violation counts

Key test thresholds (calibrated from `docs/data_profile.json`):
- `review_comment_title` null: `mostly=0.08`
- `review_comment_message` null: `mostly=0.40`
- `geolocation_lat/lng` null: `mostly=0.97`
- `payment_value` ≥ 0 (not strictly > 0; zero-value vouchers are valid)

### Non-obvious implementation patterns

**Temporal pair tests** use `expect_column_pair_values_A_to_be_greater_than_or_equal_to_B`. NULL handling: dbt-expectations excludes rows where either column is NULL from the comparison — the test passes on NULL rows by default. This is the correct behaviour for nullable timestamps (`order_approved_at`, `order_delivered_carrier_date`, `order_delivered_customer_date`). Do not add `mostly` to pair tests — the test should catch any non-null violation.

**Boleto installments singular test** pattern:
```sql
-- tests/assert_boleto_single_installment.sql
SELECT COUNT(*) AS violations
FROM {{ ref('fct_payments') }}
WHERE payment_type = 'boleto'
  AND payment_installments != 1
```
A passing singular test returns zero rows. This test only passes after `stg_payments` correctly clamps 0-installment rows.

**Financial reconciliation singular test** pattern:
```sql
-- tests/assert_payment_reconciliation.sql
SELECT order_id, COUNT(*) AS violations
FROM (
    SELECT
        fp.order_id,
        ABS(SUM(fp.payment_value) - fs.order_total) AS diff
    FROM {{ ref('fct_payments') }} fp
    JOIN (
        SELECT order_id, SUM(total_sale_amount) AS order_total
        FROM {{ ref('fct_sales') }}
        GROUP BY order_id
    ) fs USING (order_id)
    GROUP BY fp.order_id, fs.order_total
    HAVING ABS(SUM(fp.payment_value) - fs.order_total) > 1.00
) violations
```

**`fct_reviews` dedup guard**: The row count test (`expect_table_row_count_to_be_between`, min=95000, max=100000) is a critical guard — if dedup logic partitions on `order_id` instead of `review_id`, it drops 547 valid records for orders with multiple reviews. The test catches this class of error.

## Analysis Scope (from BRD v2.3)

**Four notebooks — exploratory/analytical fully separated:**
- `00_eda.ipynb` — exploratory only; Gold layer schema verification + distribution checks; informs analytical choices; no Parquet output required
- `01_sales_analysis.ipynb` — metrics 1, 2, 6, 7, 8; exports `sales_orders.parquet`
- `02_customer_analysis.ipynb` — metrics 3, 5, 9 + delay×review correlation; exports `customer_rfm.parquet`, `satisfaction_summary.parquet`
- `03_geo_seller_analysis.ipynb` — metrics 4 (ALL delivery KPIs), 10, 11; exports `geo_delivery.parquet`, `seller_performance.parquet`

**Analytical notebooks are self-contained** — no cross-notebook variable dependencies. Each opens with a markdown cell referencing relevant `00_eda.ipynb` findings. Staging models (`stg_*`) are NOT queried from notebooks — delivery timestamps are in `fct_sales` per REQ-008.1.

**11 confirmed metrics:**
1. Monthly sales trends
2. Top-selling products by **revenue** (not units), derived from `total_sale_amount`
3. RFM customer segmentation — see RFM spec below
4. Delivery performance (on-time rate, average delay)
5. Review/satisfaction analysis
6. Payment method distribution
7. Average Order Value (AOV) trend
8. Fulfilment/cancellation rate by status
9. NPS proxy (score 1–2 = detractor, 3 = passive, 4–5 = promoter)
10. Seller performance summary (GMV + avg review score + cancellation rate per seller)
11. Regional e-commerce penetration (5 official Brazilian regions)

**RFM Specification (REQ-055.1 / ASMP-022):**
- Reference date: `2018-08-31` — hardcoded, not `CURRENT_DATE` or `MAX(timestamp)`
- Observation window for trends: `2017-01-01` to `2018-08-31` (20 months)
- Recency: quintile scoring (1–5); lower days = higher score
- Frequency: 3-tier only — F1=1 order, F2=2 orders, F3=3+ orders (quintile collapses: 96.9% of customers have 1 order)
- Monetary: quintile scoring (1–5)
- Segments (RF-only assignment): Champions (R4–5, F3), Loyal (R3–5, F2–3), Promising (R4–5, F1), At Risk (R1–2, F2–3), High Value Lost (R1–2, F3), Hibernating (R1–3, F1)
- M_score stored in Parquet as display attribute — shown in grouped bar chart; does not drive assignment
- Standalone metric: repeat purchase rate (~96.9% single-purchase expected — marketplace stickiness)

**Data observations (ASMP-025) — apply to all trend analyses:**
- Exclude 2018-09 (16 orders) and 2018-10 (4 orders): data cut artefacts
- Exclude 2016-11 (0 orders) and 2016-12 (1 order) from seasonality/trend lines
- Meaningful window: Jan 2017 – Aug 2018; peak Nov 2017 (7,544 orders, Black Friday)
- Retain 2016 orders in customer history for RFM Recency only

**Regional state mapping (ASMP-008):**
- North: AM, AC, RO, RR, AP, PA, TO
- Northeast: MA, PI, CE, RN, PB, PE, AL, SE, BA
- Central-West: MT, MS, GO, DF
- Southeast: MG, ES, RJ, SP
- South: PR, SC, RS

Dashboard views: Executive Overview, Product Performance, Geographic Analysis, Customer Analysis.
Dashboard global filters: Date Range, Product Category, Customer State, **Customer Region** (4th filter added v2.3).

## Dashboard Architecture (ASMP-027)

**File structure:**
```
dashboard.py              ← thin entry point: page config + st.navigation() only
dashboard_utils.py        ← @st.cache_data Parquet loaders + init_filters()
pages/
  1_Executive.py
  2_Products.py
  3_Geographic.py
  4_Customers.py
notebooks/utils.py        ← pure Python constants; no Streamlit import
```

**Filter state:** `st.session_state` keys — `date_start`, `date_end`, `category_filter`, `state_filter`, `region_filter`. Initialised by `init_filters()` called at top of every page. Empty list = show all.

**Filter applicability per page:**
| Filter | Executive | Products | Geographic | Customers (RFM) | Customers (satisfaction) |
|---|---|---|---|---|---|
| Date Range | ✓ | ✓ | ✓ geo_delivery only | ✗ fixed ref date | ✓ |
| Product Category | ✓ | ✓ | ✗ | ✗ | ✓ approx |
| Customer State | ✓ | ✓ | ✓ | ✓ | ✓ |
| Customer Region | ✓ | ✓ | ✓ | ✓ | ✓ |

Inapplicable filters display `st.caption()` notes — they are not hidden. `seller_performance.parquet` is full-period only — static label "Jan 2017 – Aug 2018" via `st.caption()` above seller section on Geographic page.

**Choropleth `featureidkey` confirmed: `properties.sigla`** — verified against `data/brazil_states.geojson`. Use `featureidkey="properties.sigla"` in all `px.choropleth` calls.

**Run order (full end-to-end — single developer or grader):**
- **[Platform Engineer — one-time]** `bq mk --dataset <project>:olist_raw && bq mk --dataset <project>:olist_analytics` — pre-create BigQuery datasets
- **[Data Engineer]** `cd dbt && dbt deps` — installs dbt-expectations + dbt_utils (mandatory on fresh clone)
- **[Data Engineer]** `dbt parse` — generates `target/manifest.json` for Dagster (run before `dagster dev`)
- **[Data Engineer]** `dbt build` — populates BigQuery `olist_analytics` dataset; signs off before Data Analyst begins
- **[Data Analyst]** Run `01_sales_analysis.ipynb`, `02_customer_analysis.ipynb`, `03_geo_seller_analysis.ipynb` in order — each exports Parquet to `data/`; OR: `python scripts/generate_parquet.py --project <gcp_project_id>` (quick setup, no notebooks required)
- **[Dash Engineer]** `streamlit run dashboard.py` — reads committed Parquet files; no BigQuery access required

`00_eda.ipynb` is exploratory — no Parquet output, run independently at any time (Data Analyst only).
Optional: `dbt docs generate && dbt docs serve` — interactive schema + lineage browser on :8080 (do not commit `target/` output).

**A-06 — `notebooks/utils.py` is a single point of failure.** All 3 analytical notebooks, `scripts/generate_parquet.py`, and `dashboard_utils.py` import from it. Verify it imports cleanly before running any of those consumers.

## Parquet File Inventory

All files committed to `data/` in repo root. Notebooks export and `dashboard_utils.py` reads using relative paths. Do NOT add to `.gitignore`.

| File | Granularity | Rows est. | Produced by | Dashboard use |
|---|---|---|---|---|
| `data/sales_orders.parquet` | Order-item | ~112k | `01_sales_analysis.ipynb` | Executive Overview, Product Performance |
| `data/customer_rfm.parquet` | Customer | ~96k | `02_customer_analysis.ipynb` | Customer Analysis (RFM) |
| `data/satisfaction_summary.parquet` | Order | ~97k | `02_customer_analysis.ipynb` | Customer Analysis (NPS, reviews, delay) |
| `data/geo_delivery.parquet` | State × month | ~540 | `03_geo_seller_analysis.ipynb` | Geographic Analysis (delivery) |
| `data/seller_performance.parquet` | Seller | ~3k | `03_geo_seller_analysis.ipynb` | Geographic Analysis (sellers) |

**Key column notes:**
- `sales_orders.parquet`: `primary_payment_type` and `primary_payment_installments` use `payment_sequential=1` per order (~3% split-payment approximation). Use `COUNT(DISTINCT order_id)` for payment distribution — same item-granularity trap as delivery metrics.
- `satisfaction_summary.parquet`: `primary_product_category` = category of highest-revenue item per order. Product Category filter is approximate for ~10% multi-item orders.
- `geo_delivery.parquet`: includes `year`/`month` columns — Date Range filter works. `seller_performance.parquet` is full-period only — dashboard shows static "Jan 2017 – Aug 2018" label on seller view.
- `customer_rfm.parquet`: Date Range and Product Category filters not applicable — dashboard shows a `st.caption()` note on the RFM section; filters remain visible but are not applied.
- All `customer_region` / `seller_region` columns derived from `notebooks/utils.py` REGION_MAP — single source, no drift between files.

## Visualization

**Libraries:** `plotly.express` for all 3 analytical notebooks + `pages/*.py` (dashboard page files). `seaborn`/`matplotlib` for `00_eda.ipynb` only (exploratory, not reused). `dashboard.py` is a thin entry point — it contains no charts and does not import plotly.
**Streamlit rendering:** `st.plotly_chart(fig, use_container_width=True)`
**Choropleth:** `data/brazil_states.geojson` committed to repo (27 features, source: codeforamerica/click_that_hood). `featureidkey="properties.sigla"` — confirmed matches `customer_state`/`seller_state` 2-letter codes. Do not fetch at runtime.

**Chart types per metric:**
| Metric | Primary | Secondary | Notes |
|---|---|---|---|
| 1. Monthly GMV + volume | Two stacked panels: area (GMV) + bar (order count) | — | No dual-axis — misleads on correlation |
| 2. Top products | Horizontal bar (sorted desc) | Treemap | Bar for ranking, treemap for proportion |
| 3. RFM segments | Bar (avg R/F/M score per segment, grouped) | Heatmap (R_score × F_tier, fill=count) | Scatter R vs M excluded — overlapping clusters don't separate by segment |
| 4. Delivery performance | Horizontal bar (on-time rate by region) | Heatmap (region × month, avg delay); use region not state — state cells are sparse | Min 30 orders threshold; suppress sparse cells as grey |
| 5. Review distribution | Bar (score 1–5 counts) | Line (avg score by month) | Scores are ordinal — bar not histogram |
| 6. Payment distribution | Donut (type share) | Histogram (installments, credit card only) | — |
| 7. AOV trend | Line by month + payment type | Bar (AOV by payment type) | Shares base query with Metric 1 |
| 8. Cancellation rate | Line (cancellation % + unavailability % over time) | Donut (overall status mix) | Stacked bar excluded — delivered (96.8%) makes other statuses invisible |
| 9. NPS proxy | 100% stacked bar by month (promoter/passive/detractor) | Line (NPS score trend) | — |
| 10. Seller performance | Scatter (GMV vs avg_score, sized by orders) | Pareto curve (x = seller percentile %, not rank) | Normalise Pareto x-axis for 80/20 readability |
| 11. Regional penetration | Choropleth map (fill = GMV by state) | Bar (GMV by region) | Requires `data/brazil_states.geojson` |
| Delay × score | Bar (avg score by delay bin) | Box plot (distribution per bin) | 5 bins: early / on-time / 1–3d late / 4–7d late / 7+d late — early bin captures positive surprise effect |
| Repeat purchase rate | `st.metric()` KPI card (prominent) | — | Standalone metric per ASMP-022; not a chart |
| Headline KPIs | `st.metric()` cards at top of each view | — | GMV, orders, AOV, on-time rate, NPS, repeat purchase rate |

**`notebooks/utils.py` contents (canonical — do not redefine in notebooks):**
- `REGION_MAP` — 27 states + DF mapped to 5 regions
- `SEGMENT_COLOURS` — 6 RFM segment colours (green → red scale)
- `REGION_COLOURS` — 5 region colours (Southeast=blue, South=green, Central-West=purple, Northeast=orange, North=red — distinct hues for adjacent map regions)
- `STATUS_COLOURS` — 8 order status colours (green=delivered, red=canceled/unavailable, yellow=pending)
- `add_region(df, state_col)` — applies REGION_MAP to a DataFrame column

## Required Deliverables Checklist

- [ ] Meltano pipeline loading all 9 CSVs to BigQuery `olist_raw`
- [ ] dbt project with 9 staging models + 7 mart models (3 fact + 4 dim)
- [ ] dbt-expectations generic tests + singular SQL tests
- [ ] Dagster project with `dagster-dbt` integration + Meltano asset + daily schedule
- [ ] Jupyter notebooks: `00_eda.ipynb`, `01_sales_analysis.ipynb`, `02_customer_analysis.ipynb`, `03_geo_seller_analysis.ipynb` (11 metrics total)
- [ ] `notebooks/utils.py` — canonical REGION_MAP dict, SEGMENT_COLOURS, REGION_COLOURS, STATUS_COLOURS, `add_region()` helper (imported by all 3 analytical notebooks and `dashboard_utils.py`)
- [ ] `data/brazil_states.geojson` — Brazilian state boundaries for choropleth map (feature IDs must match 2-letter state codes e.g. `"SP"`)
- [ ] Parquet feature datasets in `data/` (exported from notebooks, not dbt) — see Parquet Inventory below
- [ ] `dashboard.py` — thin entry point (page config + `st.navigation()` only; no charts, no data loading)
- [ ] `dashboard_utils.py` — `@st.cache_data` Parquet loaders + `init_filters()` (imports from `notebooks/utils.py`)
- [ ] `pages/` — `1_Executive.py`, `2_Products.py`, `3_Geographic.py`, `4_Customers.py` (four dashboard views; each calls `init_filters()` at top)
- [ ] Pipeline architecture diagram + architecture document
- [ ] Data lineage diagram
- [ ] Star schema diagram
- [ ] Technical report (tool selection rationale + schema justification)
- [ ] Project implementation document
- [ ] Local run setup document
- [ ] `changelog.md`
- [ ] Dashboard user guide
- [ ] `docs/executive_brief.md` — narrative source for NotebookLM slide generation *(REQ-066.1)*
- [ ] Executive slide deck (Google Slides → `.pptx` in `docs/`)
- [ ] `progress.md` — implementation status tracker (REQ-level; updated throughout implementation) *(REQ-065.1)*
- [ ] `docs/decisions/ADR-001-date-key-type.md` *(REQ-061.1)*
- [ ] `docs/decisions/ADR-002-dataset-rename.md` *(REQ-061.1)*
- [ ] `docs/decisions/ADR-003-fct-reviews-fk-target.md` *(REQ-061.1)*
- [ ] `docs/troubleshooting.md` *(optional — REQ-062.1)*
- [ ] `docs/data_dictionary.md` *(optional — REQ-063.1)*
- [ ] `docs/testing_guide.md` *(optional — REQ-064.1)*

## Source Data Profile

`docs/data_profile.json` contains the pre-computed source data profile generated by `scripts/profile_source_data.py`. **Read this file before profiling source CSVs — do not re-run validation queries against raw_data/ unless source data has changed.**

The profile contains:
- Row counts and column headers for all 9 source files
- Null distributions per column
- Value distributions (order_status, payment_type, review_score, etc.)
- Cross-table referential integrity findings
- 9 known data defects with staging fix references and BRD pointers
- Test threshold justifications with source data evidence (mostly values, match rates)

To regenerate (only if source data changes):
```bash
python scripts/profile_source_data.py
```

## BigQuery Connection

Credentials provided externally (ASMP-015). Use SQLAlchemy with `sqlalchemy-bigquery` for Python connections in notebooks. Service account key path via `GOOGLE_APPLICATION_CREDENTIALS` environment variable, not hardcoded.

## Development Environment

- Python 3.11, conda environment `assignment2`
- Conda preferred; pip as fallback
- Meltano manages its own plugin venvs under `.meltano/`
- macOS/Linux supported; Windows via WSL2 only
