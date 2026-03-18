# Technical Report — Project Caravela

## 1. Introduction

Project Caravela is an end-to-end data pipeline for the Brazilian E-Commerce Dataset by Olist (~100k orders, 2016–2018). The pipeline ingests 9 CSV source files into BigQuery, transforms them through a staging + mart layer using dbt, orchestrates execution with Dagster, analyses the data in Jupyter notebooks, and presents insights through a Streamlit dashboard.

This report documents the rationale behind each tool selection and the schema design decisions that shape the analytics layer.

---

## 2. Tool Selection Rationale

### 2.1 Ingestion — Meltano (tap-csv → target-bigquery)

| Criterion | Decision |
|---|---|
| **Selected** | Meltano with `tap-csv` extractor and `target-bigquery` loader |
| **Alternatives considered** | Custom Python ingestion scripts, direct BigQuery `bq load` CLI |
| **Decision** | Meltano — declarative YAML config, Singer-based plugin ecosystem |

**Rationale:**
- **Declarative configuration**: All 9 source files are defined in `meltano.yml` with stream names, file paths, and key columns. Adding or modifying a source requires only a YAML change, not code changes.
- **Singer protocol compliance**: Meltano's tap/target architecture separates extraction from loading. The extractor (`tap-csv`) handles CSV parsing and schema inference; the loader (`target-bigquery`) handles BigQuery authentication, table creation, and write disposition — neither component knows about the other.
- **Reproducibility**: Relative paths (`../raw_data/`) and environment variable interpolation (`$GCP_PROJECT_ID`, `$GOOGLE_APPLICATION_CREDENTIALS`, `$BIGQUERY_RAW_DATASET`) ensure the pipeline works across machines without hardcoded paths. Meltano does not auto-load `.env` from the repo root (only from its own project directory), so the wrapper script `meltano/launch_meltano.sh` passes `--env-file ../.env` on every invocation.
- **Write disposition**: `WRITE_TRUNCATE` is configured on `target-bigquery`, ensuring every run performs a full refresh. This is correct for a fixed historical dataset — `WRITE_APPEND` would duplicate all rows on every scheduled Dagster run.
- **Load method**: `method: batch_job` is used instead of `storage_write_api`. The write API holds open gRPC streams per table; when `tap-csv` processes files sequentially, earlier streams go idle during the ~31s geolocation load (1M rows) and hit BigQuery's 600s inactivity timeout. Batch jobs use traditional load jobs with no persistent streams, immune to idle timeouts.
- **View generation**: `target-bigquery` is configured with `generate_view: true` and `denormalized: false`, producing flat-column views (suffixed `_view`) that the dbt staging layer references via `sources.yml`.

**Known constraint — `setuptools` compatibility:**
`setuptools` v81+ removed `pkg_resources`, which older Meltano plugins depend on. Both `tap-csv` and `target-bigquery` include `setuptools<70` in their `pip_url` to pin a compatible version within each plugin's isolated venv. See ADR-004 for extractor selection history.

### 2.2 Transformation — dbt (ELT on BigQuery)

| Criterion | Decision |
|---|---|
| **Selected** | dbt-core 1.11.x with dbt-bigquery adapter |
| **Alternatives considered** | pandas-based Python transforms, BigQuery stored procedures |
| **Decision** | dbt — SQL-first, declarative lineage, built-in testing |

**Rationale:**
- **ELT pattern**: All transformations execute inside BigQuery (pushdown). Source CSVs arrive as all-STRING columns (tap-csv performs no type inference). The dbt staging layer is solely responsible for type casting via `CAST()` and `SAFE_CAST()` — this is a deliberate design choice (ASMP-028) that centralises all schema enforcement in one layer.
- **Lineage graph**: dbt's `ref()` and `source()` macros automatically build a dependency DAG. Every model declares its upstream dependencies explicitly, which Dagster inherits via `dagster-dbt` for orchestration.
- **Materialisation strategy**: Staging models materialise as **views** (lightweight, always-current); mart models materialise as **tables** (pre-computed for query performance). This is configured in `dbt_project.yml`:
  ```yaml
  models:
    caravela:
      staging:
        +materialized: view
      marts:
        +materialized: table
  ```
- **Reusability**: The staging layer cleans data defects once (deduplication, bounding-box filtering, installment clamping, `not_defined` filtering), so every downstream consumer — mart models, notebooks, dashboard — inherits clean data without re-implementing fixes.
- **Environment variable interpolation**: `profiles.yml` and `sources.yml` use dbt's `env_var()` function with fallback defaults for dataset names (`BIGQUERY_ANALYTICS_DATASET` → `olist_analytics`, `BIGQUERY_RAW_DATASET` → `olist_raw`). This aligns with the `.env` centralisation pattern used by Meltano and the notebooks, while preserving `dbt parse` compatibility without `.env` loaded.

**dbt packages:**

| Package | Purpose |
|---|---|
| `dbt_utils` (>=1.0.0, <2.0.0) | `date_spine` macro for `dim_date` generation; `unique_combination_of_columns` for compound PK tests |
| `dbt-expectations` (metaplane/main) | Generic tests in `schema.yml`: value ranges, accepted values, row counts, temporal pair comparisons, string length checks. **Note: `mostly` parameter is not supported** — the metaplane fork (v0.6.0) has no proportion-threshold logic. Fill-rate guards are omitted; calibration evidence preserved in `docs/data_profile.json`. See changelog 2026-03-18. |

### 2.3 Data Quality — dbt-expectations + Singular Tests

| Criterion | Decision |
|---|---|
| **Selected** | dbt-expectations generic tests + custom singular SQL tests |
| **Alternatives considered** | Great Expectations (standalone), Soda, custom Python assertions |
| **Decision** | dbt-native testing — runs within the same DAG, same materialisation pass |

**Rationale:**
- **Integrated execution**: `dbt build` interleaves model materialisation and testing in topological order. A failing staging test blocks dependent mart models from materialising — preventing corrupt data from propagating downstream.
- **Two complementary mechanisms**:
  - **Generic tests** (declared in `schema.yml`): Column-level validations — `not_null`, `unique`, `accepted_values`, `expect_column_values_to_be_between`, `expect_table_row_count_to_be_between`, `expect_column_value_lengths_to_be_between`, temporal pair tests. Thresholds calibrated from source data profiling (`docs/data_profile.json`). **Proportion-based (`mostly`) tests are not available** in the installed metaplane fork — four fill-rate guards are documented but not enforced; see `docs/testing_guide.md` Known Omissions.
  - **Singular tests** (SQL files in `tests/`): Cross-table assertions that cannot be expressed as generic tests — boleto single-installment validation, payment-to-sales financial reconciliation, `date_key` range verification.
- **No external orchestration needed**: Tests run as part of the dbt DAG, which Dagster already orchestrates. Adding Great Expectations would require a separate execution context, credentials setup, and failure-handling logic.

### 2.4 Orchestration — Dagster (with dagster-dbt)

| Criterion | Decision |
|---|---|
| **Selected** | Dagster 1.12.x with `dagster-dbt` 0.28.x |
| **Alternatives considered** | Apache Airflow, Prefect, manual cron scheduling |
| **Decision** | Dagster — asset-centric model, native dbt integration, unified UI |

**Rationale:**
- **Asset-centric model**: Dagster models the pipeline as a graph of data assets, not a graph of tasks. Each dbt model becomes a Dagster asset automatically via `@dbt_assets`. The Meltano ingestion step is wired as an upstream `@multi_asset` producing 9 `olist_raw` table assets. This creates a single, unified lineage graph: `meltano_ingest → olist_raw/* → stg_* → dim_*/fct_*`.
- **`dagster-dbt` integration**: The `@dbt_assets` decorator reads `manifest.json` at import time and generates one asset per dbt model. `dbt.cli(["build"])` runs models and tests interleaved — a failing staging test halts the build before dependent marts materialise.
- **Schedule**: `ScheduleDefinition` with `cron_schedule="0 9 * * *"` and `execution_timezone="Asia/Singapore"` — no manual UTC conversion required.
- **UI observability**: The Dagster web UI shows asset materialisation status, run history, logs (Meltano stdout/stderr forwarded via `context.log`), and schedule status. `dagster dev` starts both webserver and daemon for development.
- **Manifest pre-generation**: `dbt parse` must run before `dagster dev` on fresh clones — `dagster-dbt` reads `manifest.json` at Python import time, not at execution time.

### 2.5 Analysis — Jupyter Notebooks + google-cloud-bigquery

| Criterion | Decision |
|---|---|
| **Selected** | Jupyter notebooks with `google-cloud-bigquery` Python client |
| **Alternatives considered** | Python scripts, dbt metrics layer, BigQuery console, SQLAlchemy + `sqlalchemy-bigquery` |
| **Decision** | Notebooks — exploratory + reproducible analytical workflow |

**Rationale:**
- **Separation of concerns**: Four notebooks serve distinct purposes — `00_eda.ipynb` (exploratory, no output), `01_sales_analysis.ipynb`, `02_customer_analysis.ipynb`, `03_geo_seller_analysis.ipynb` (each exports Parquet files). Notebooks are self-contained with no cross-notebook variable dependencies.
- **BigQuery connection**: `google.cloud.bigquery.Client` via `GOOGLE_APPLICATION_CREDENTIALS` environment variable. Queries target the `olist_analytics` mart tables (star schema), not raw or staging tables. `sqlalchemy-bigquery` was considered but the native client offers a simpler API (`client.query(sql).to_dataframe()`) with fewer dependencies.
- **Parquet export**: Each analytical notebook exports pre-computed DataFrames to `data/*.parquet`. This decouples the dashboard from BigQuery — the Streamlit dashboard reads committed Parquet files and requires no database credentials.
- **Visualisation**: Plotly Express for all analytical notebooks and dashboard pages. Seaborn/matplotlib used only in `00_eda.ipynb` for exploratory plots.

### 2.6 Dashboard — Streamlit

| Criterion | Decision |
|---|---|
| **Selected** | Streamlit with multi-page architecture |
| **Alternatives considered** | Looker, Metabase, Dash (Plotly), custom React app |
| **Decision** | Streamlit — Python-native, rapid prototyping, zero frontend build step |

**Rationale:**
- **Architecture**: Thin entry point (`dashboard.py`) with `st.navigation()` routing to 4 page files under `pages/`. Data loading via `@st.cache_data` decorators in `dashboard_utils.py`. Shared constants (region map, colour palettes) imported from `notebooks/utils.py`.
- **Data source**: Parquet files in `data/` — no live BigQuery connection. This means the dashboard can run independently on any machine with Python, without GCP credentials.
- **4 global filters**: Date Range, Product Category, Customer State, Customer Region. Filter applicability varies by page (e.g., RFM section uses a fixed reference date, not the date range filter). Inapplicable filters show `st.caption()` explanatory notes.
- **Choropleth maps**: `data/brazil_states.geojson` committed to repo. `featureidkey="properties.sigla"` matches 2-letter state codes. No runtime fetch required.

---

## 3. Schema Design — Star Schema Justification

### 3.1 Why Star Schema?

The star schema was chosen over normalised (3NF) and flat denormalised alternatives for the following reasons:

| Criterion | Star Schema | 3NF | Flat Table |
|---|---|---|---|
| Query simplicity | Single fact-to-dim joins | Multi-hop joins through bridge tables | No joins needed |
| Analytical performance | Good — BigQuery optimises star joins | Slower — more joins | Fastest — but massive redundancy |
| Maintainability | Dims evolve independently | Complex referential integrity | Schema changes cascade everywhere |
| Data quality | Clear grain per fact table | Normalisation enforces integrity | Duplication introduces inconsistency |
| Dashboard suitability | Filter on dims, aggregate on facts | Over-normalised for BI tools | Filter and aggregate directly |

**Decision**: Star schema balances query performance with analytical flexibility. Each fact table has a clear grain (order-item, review, payment), and dimension tables provide reusable lookup attributes for filtering and grouping.

### 3.2 Fact Tables

#### `fct_sales` — Order-Item Grain (~112k rows)
- **Grain**: One row per order-item (not per order). An order with 3 items produces 3 `fct_sales` rows.
- **Composite key**: `order_id` + `order_item_id` (no surrogate key — natural composite is unique and meaningful).
- **FKs**: `product_id → dim_products`, `seller_id → dim_sellers`, `customer_unique_id → dim_customers`, `date_key → dim_date`.
- **Derived measure**: `total_sale_amount = price + freight_value`. Computed in the model, not left to downstream consumers.
- **3-source CTE pattern**: `stg_order_items → stg_orders (customer_id) → stg_customers (customer_unique_id)`. Direct join of items to customers produces zero matches — the intermediate `customer_id` resolution through orders is required.
- **Delivery timestamps**: `order_delivered_customer_date` and `order_estimated_delivery_date` are nullable TIMESTAMP columns. These are order-level attributes repeated across item rows — delivery analysis must use `COUNT(DISTINCT order_id)` to avoid inflating delivery counts by item multiplicity.

#### `fct_reviews` — Review Grain (~97k rows post-dedup)
- **PK**: `review_id` (unique after ROW_NUMBER deduplication — 789 source duplicates removed).
- **FKs**: `order_id → stg_orders` (cross-boundary — see below), `date_key → dim_date`.
- **FK deviation**: `order_id` references `stg_orders`, NOT `fct_sales`. Reason: 756 orders have reviews but no items (itemless orders). Pointing to `fct_sales` would orphan these reviews. This is the only FK in the mart layer that targets a staging table rather than another mart. See ADR-003.
- **`order_id` is NOT unique**: 547 orders have multiple reviews with distinct `review_id` values. The `unique` test applies to `review_id` only.
- **`date_key`**: Derived from `review_creation_date` (not `order_purchase_timestamp`), so a review's date_key may differ from its order's date_key.

#### `fct_payments` — Payment-Method Grain
- **Compound PK**: `order_id` + `payment_sequential`. An order paid with 2 methods (e.g., credit card + voucher) produces 2 rows.
- **FKs**: `date_key → dim_date` (nullable — no FK relationship test applied; see test design below).
- **`date_key` nullable**: Derived from `stg_orders.order_purchase_timestamp` via LEFT JOIN. NULL when the order record is missing. The explicit `{{ ref('stg_orders') }}` CTE is required even though only `date_key` is selected — without it, dbt's DAG omits the `stg_orders → fct_payments` dependency edge, breaking Dagster lineage and execution ordering.
- **`order_payment_value` excluded from `fct_sales`**: Order-level payment aggregate on an item-level fact causes double-counting. Payment analysis uses `fct_payments` directly.

### 3.3 Dimension Tables

#### `dim_customers` — PK: `customer_unique_id`
- **Deduplication**: Multiple `customer_id` values map to a single `customer_unique_id` (repeat customers). Deduplicated via `ROW_NUMBER()` partitioned by `customer_unique_id`.
- **Geolocation enrichment**: `geolocation_lat` and `geolocation_lng` joined from `stg_geolocation` by zip code prefix. Nullable — not all zip codes have geolocation data.

#### `dim_products` — PK: `product_id`
- **Category translation**: `product_category_name_english` uses `COALESCE(english_name, portuguese_name, 'uncategorized')`. The Portuguese fallback includes a `CASE/NULLIF` guard to convert empty strings to NULL (tap-csv loads blanks as `''`, not NULL, so a bare COALESCE would stop at the empty string). 2 categories have no English translation (retain Portuguese name); 610 products have no category at all (labelled `'uncategorized'`).
- **Nullable numeric columns**: 7 product attribute columns (`product_name_length`, `product_description_length`, `product_photos_qty`, `product_weight_g`, `product_length_cm`, `product_height_cm`, `product_width_cm`) are nullable. `SAFE_CAST` in `stg_products` returns NULL for rows where the source CSV field is blank.
- **Column renames**: Source misspellings `product_name_lenght` → `product_name_length`, `product_description_lenght` → `product_description_length`. Fixed in `stg_products`.
- **Dual-source staging model**: `stg_products` is the only staging model joining two raw tables (`olist_products_dataset` + `product_category_name_translation`). Both referenced via `{{ source() }}` directly (not via `ref('stg_product_category_name_translation')`) and declared in `sources.yml` for full lineage visibility in the dbt DAG.

#### `dim_sellers` — PK: `seller_id`
- **Geolocation enrichment**: Same pattern as `dim_customers` — lat/lng from `stg_geolocation` by zip code prefix, nullable.

#### `dim_date` — PK: `date_key` (DATE)
- **Generated dimension**: No raw data source. Produced by `dbt_utils.date_spine(datepart="day", start_date="cast('2016-01-01' as date)", end_date="cast('2018-12-31' as date)")`.
- **DATE type**: Native output of `date_spine` — no casting needed. Fact tables derive `date_key` via staging models: `stg_orders` uses `DATE(SAFE_CAST(order_purchase_timestamp AS TIMESTAMP))`, `stg_reviews` uses `DATE(CAST(review_creation_date AS TIMESTAMP))`. See ADR-001.
- **Range**: 2016-01-01 to 2018-12-31, providing buffer beyond the data window (first order 2016-09-04, last 2018-10-17).

### 3.4 Staging Layer Design Principles

The staging layer (`stg_*` models, materialised as views) enforces three responsibilities:

1. **Type casting**: All columns arrive from Meltano as STRING. Staging models cast to appropriate BigQuery types (`INT64`, `FLOAT64`, `TIMESTAMP`, `DATE`) using `CAST()` and `SAFE_CAST()` for nullable fields.
2. **Data defect correction**: Source-level data quality issues are fixed exactly once in staging:
   - `stg_reviews`: ROW_NUMBER deduplication (789 duplicate `review_id` values)
   - `stg_geolocation`: Brazil bounding-box filter (`lat BETWEEN -35 AND 5`, `lng BETWEEN -75 AND -34`) + AVG(lat, lng) per zip code (~1M → ~19k rows). Only 29 lat + 37 lng outlier rows in source — nearly all 19,015 distinct zip prefixes survive the filter intact. (Profile: `geolocation.distinct_zip_prefixes = 19,015`)
   - `stg_payments`: Filter `payment_type = 'not_defined'` (3 rows), clamp `payment_installments = 0 → 1` (2 rows)
   - `stg_products`: Column rename (misspelled `lenght` → `length`), category COALESCE
3. **Contract surface**: Staging models define the typed, cleaned interface that mart models consume via `ref()`. Raw tables are never referenced directly from marts.

### 3.5 Mart-Level Test Design

The mart layer has deliberate test coverage decisions that reflect data realities rather than mechanical FK enforcement:

| Test | Applied? | Rationale |
|---|---|---|
| `fct_sales` compound PK (`order_id` + `order_item_id`) | Yes — `unique_combination_of_columns` | Natural composite key; no surrogate |
| `fct_sales` 4 FK relationships (dims) | Yes — `relationships` tests | All FKs are NOT NULL and must resolve |
| `fct_sales` row count (110k–120k) | Yes — `expect_table_row_count_to_be_between` | Guards against fan-out (duplicates) and empty materialisation |
| `fct_reviews` PK (`review_id`) | Yes — `unique` + `not_null` | Dedup in staging guarantees uniqueness |
| `fct_reviews.order_id` FK → `stg_orders` | Yes — `relationships` | Cross-boundary FK; targets staging, not `fct_sales` |
| `fct_reviews.date_key` FK → `dim_date` | Yes — via `assert_date_key_range.sql` singular test | Range-checked across all 3 facts |
| `fct_payments` compound PK (`order_id` + `payment_sequential`) | Yes — `unique_combination_of_columns` | Compound natural key |
| `fct_payments.date_key` FK → `dim_date` | **No** — intentionally omitted | LEFT JOIN produces NULL `date_key` for orphan payments; a `relationships` test fails on every NULL row. The `assert_date_key_range.sql` singular test guards non-null values. |
| `fct_payments.date_key` `not_null` | **No** — intentionally omitted | NULL is legitimate (orphan payments with no matching order) |

**Row count guards** on all 3 facts serve a dual purpose: they catch fan-out bugs (duplicate joins inflating rows) and detect empty materialisation (raw data not loaded, views resolve to 0 rows). A reconciliation test that JOINs empty facts passes vacuously — row count tests catch the root cause first.

### 3.6 Architecture Decision Records

| ADR | Decision | Key Rationale |
|---|---|---|
| ADR-001 | `date_key` type: DATE (not INTEGER YYYYMMDD) | `dbt_utils.date_spine` natively produces DATE; INTEGER adds unnecessary casting in every model |
| ADR-002 | Dataset names: `olist_raw` / `olist_analytics` (not `raw` / `analytics`) | `raw` is a BigQuery SQL reserved word — requires backtick-quoting; adapter handling is version-dependent |
| ADR-003 | `fct_reviews.order_id` FK → `stg_orders` (not `fct_sales`) | 756 itemless orders have reviews but no `fct_sales` rows; FK to `fct_sales` would orphan those reviews |
| ADR-004 | Meltano extractor: `tap-csv` | Streaming file reads (safe for 1M-row geolocation); community-maintained with active support |

---

## 4. Development Environment

| Component | Version | Notes |
|---|---|---|
| Python | 3.11.15 | Conda environment `assignment2` |
| dbt-core | 1.11.7 | With dbt-bigquery 1.11.1 |
| Dagster | 1.12.18 | With dagster-dbt 0.28.18 |
| Meltano | 4.1.2 | Plugin venvs under `.meltano/` |
| Streamlit | 1.55.0 | Multi-page architecture |
| Plotly | 6.5.0 | All analytical + dashboard charts |
| pandas | 2.3.3 | Data manipulation |
| google-cloud-bigquery | 3.40.1 | BigQuery Python client (used by all notebooks + `generate_parquet.py`) |

**Credentials and configuration**: All tools read from the repo root `.env` file:
- `GOOGLE_APPLICATION_CREDENTIALS` — path to GCP service account key file
- `GCP_PROJECT_ID` — BigQuery project identifier
- `BIGQUERY_ANALYTICS_DATASET` — dbt target dataset (default: `olist_analytics`)
- `BIGQUERY_RAW_DATASET` — Meltano target dataset / dbt source schema (default: `olist_raw`)

---

## 5. References

- Architecture Decision Records: `docs/decisions/ADR-001` through `ADR-004`
- Source data profile: `docs/data_profile.json`
- Star schema ERD: `docs/diagrams/star_schema.png` (Graphviz) + `docs/star_schema.dbml` (dbdiagram.io) + `docs/star_schema.dot` (Graphviz source)
- Data lineage: `docs/diagrams/data_lineage.png` (Graphviz) + `docs/data_lineage.dot` (Graphviz source)
- Pipeline architecture: `docs/diagrams/pipeline_architecture_detailed_2.png` (Graphviz)
- BRD: `docs/requirements/BRD_Olist_Assignment_v5.0.md`
