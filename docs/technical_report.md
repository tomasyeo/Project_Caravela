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
- **`@multi_asset(specs=...)` producer pattern**: The Meltano asset uses `@multi_asset(specs=RAW_TABLE_SPECS)` rather than `@asset(deps=RAW_TABLES)`. The `deps=` pattern would declare `meltano_ingest` as a *consumer* of `olist_raw/*` (i.e. downstream), making the raw tables external assets that Dagster treats as always-available. The `specs=` pattern correctly declares `meltano_ingest` as the *producer* of all 9 `olist_raw/*` assets — the topological order then enforces `meltano_ingest` first, with all dbt assets blocked until ingestion completes.
- **`dagster-dbt` integration**: The `@dbt_assets` decorator reads `manifest.json` at import time and generates one asset per dbt model. `dbt.cli(["build"])` runs models and tests interleaved — a failing staging test halts the build before dependent marts materialise. The `manifest.json` path uses `Path(__file__)`-relative resolution so `dagster dev` works correctly regardless of the launch working directory.
- **Credential injection chain**: All credentials flow from a single `.env` at repo root into the Dagster process via a three-stage chain: (1) `scripts/launch_dagster.sh` sources `.env` and exports `DAGSTER_HOME=<repo>/dagster/dagster_home` before Dagster starts; (2) Dagster finds `dagster/dagster_home/dagster.yaml` and activates the `EnvFileLoader`, which injects all `.env` vars into the process environment; (3) `dbt.cli(["build"])` inherits those vars — `profiles.yml` reads `GCP_PROJECT_ID`, `GOOGLE_APPLICATION_CREDENTIALS`, and `BIGQUERY_ANALYTICS_DATASET` via `env_var()`. The Meltano subprocess receives `--env-file ../.env` directly so it is self-sufficient regardless of how Dagster was launched.
- **Schedule**: `ScheduleDefinition` with `cron_schedule="0 9 * * *"` and `execution_timezone="Asia/Singapore"` — no manual UTC conversion required. `job_name="full_pipeline_job"` (string reference) is used instead of importing the job object into `schedules.py`, which would create a circular import with `__init__.py`.
- **UI observability**: The Dagster web UI shows asset materialisation status, run history, logs (Meltano stdout/stderr forwarded via `context.log`), and schedule status. `dagster dev` starts both webserver and daemon for development.
- **Manifest pre-generation**: `dbt parse` must run before `dagster dev` on fresh clones — `dagster-dbt` reads `manifest.json` at Python import time, not at execution time. The `scripts/launch_dagster.sh` script supports a `--parse` flag to regenerate the manifest automatically.

### 2.5 Analysis — Jupyter Notebooks + google-cloud-bigquery

| Criterion | Decision |
|---|---|
| **Selected** | Jupyter notebooks with `google-cloud-bigquery` Python client |
| **Alternatives considered** | Python scripts, dbt metrics layer, BigQuery console, SQLAlchemy + `sqlalchemy-bigquery` |
| **Decision** | Notebooks — exploratory + reproducible analytical workflow |

**Rationale:**
- **Separation of concerns**: Four notebooks serve distinct purposes — `00_eda.ipynb` (exploratory, no output), `01_sales_analysis.ipynb`, `02_customer_analysis.ipynb`, `03_geo_seller_analysis.ipynb` (each exports Parquet files). Notebooks are self-contained with no cross-notebook variable dependencies. Each analytical notebook opens with a markdown cell referencing relevant EDA findings, creating a narrative chain without variable coupling.
- **BigQuery connection**: `google.cloud.bigquery.Client` via `GOOGLE_APPLICATION_CREDENTIALS` environment variable. Queries target the `olist_analytics` mart tables (star schema), not raw or staging tables. `sqlalchemy-bigquery` was considered but the native client offers a simpler API (`client.query(sql).to_dataframe()`) with fewer dependencies and no SQLAlchemy dialect version conflicts.
- **Parquet-as-contract**: Each analytical notebook exports pre-computed DataFrames to `data/*.parquet`. This decouples the dashboard from BigQuery entirely — the Streamlit dashboard reads committed Parquet files and requires no GCP credentials. The 6 Parquet schemas form a versioned downstream contract for the dashboard engineer (see Section 5.5).
- **`generate_parquet.py` fallback**: `scripts/generate_parquet.py` replicates all 6 Parquet exports without requiring Jupyter. This enables grader setup in a single command (`python scripts/generate_parquet.py --project <gcp_project_id>`) without opening notebooks. All schemas are kept in sync with notebook outputs.
- **Observation window**: All trend analyses use Jan 2017 – Aug 2018 (20 months). 2016-11/12 (0–1 orders) and 2018-09/10 (16/4 orders) are excluded as data cut artefacts. 2016 orders are retained only in RFM customer history to correctly compute Recency for customers who last purchased in 2016.
- **Visualisation**: Plotly Express for all analytical notebooks and dashboard pages — interactive charts render natively in Jupyter and in Streamlit via `st.plotly_chart()`. Seaborn/matplotlib used only in `00_eda.ipynb` for exploratory distribution plots (histograms, heatmaps) where interactivity is not required.

### 2.6 Dashboard — Streamlit

| Criterion | Decision |
|---|---|
| **Selected** | Streamlit 1.55 with multi-page `st.navigation()` architecture |
| **Alternatives considered** | Looker, Metabase, Dash (Plotly), custom React app |
| **Decision** | Streamlit — Python-native, rapid prototyping, zero frontend build step |

**Rationale:**
- **No credentials required**: The dashboard reads committed Parquet files from `streamlit/data/` — no BigQuery connection, no GCP credentials. Any machine with Python can run it. This was a deliberate architectural constraint that drove the Parquet export design in the analytical notebooks.
- **Streamlit Cloud deployment**: All dashboard files are co-located under `streamlit/` (entry point, utilities, pages, data). `streamlit/dashboard.py` is the Cloud app entry point. Path resolution uses `Path(__file__).parent` for data files and `Path(__file__).parent.parent` for `notebooks/utils.py` (repo root) — relative to the source file, not the launch directory.

**File structure:**

```
streamlit/
  dashboard.py          ← thin entry point: page config + st.navigation() only
  dashboard_utils.py    ← @st.cache_data loaders + filter helpers + sidebar renderer
  requirements.txt      ← pinned dependencies for Streamlit Cloud
  data/
    *.parquet           ← 6 Parquet files (copied from repo root data/)
    brazil_states.geojson
  pages/
    1_Executive.py      ← Executive Overview (4 tabs)
    2_Products.py       ← Product Performance (3 tabs)
    3_Geographic.py     ← Geographic Analysis (3 tabs)
    4_Customers.py      ← Customer Analysis (4 tabs)
    5_Glossary.py       ← Searchable glossary (17 terms, no charts)
```

**Architecture patterns:**

- **Thin entry point**: `dashboard.py` contains only `st.set_page_config()` and `st.navigation()`. No data loading, no charts, no imports beyond `streamlit`. This prevents the entry point from becoming a maintenance surface as pages evolve.
- **Shared loaders with caching**: `dashboard_utils.py` exposes 6 `@st.cache_data` loaders (one per Parquet file + GeoJSON). Cache persists across page navigations within a session — each Parquet file is read from disk exactly once.
- **Constant imports from `notebooks/utils.py`**: Colour palettes (`REGION_COLOURS`, `SEGMENT_COLOURS`, `STATUS_COLOURS`) and the `add_region()` helper are imported from the single canonical source. This prevents colour drift between notebooks and dashboard — a change to `notebooks/utils.py` propagates everywhere.
- **Tab layout**: Each analysis page uses `st.tabs()` with one focused narrative per tab. Tabs share the same filtered dataset; switching tabs does not re-apply or reset filters. This pattern avoids the cognitive load of a single page with too many unrelated charts.

**Filter design — 4 global filters in sidebar:**

| Filter | Session State Key | Default | Widget type |
|---|---|---|---|
| Date Range | `date_start`, `date_end` | Jan 2017 – Aug 2018 | `st.date_input` |
| Product Category | `category_filter` | `[]` (all) | `st.multiselect` |
| State | `state_filter` | `[]` (all) | `st.multiselect` |
| Region | `region_filter` | `[]` (all) | `st.multiselect` |

`init_filters()` is called at the top of every page to initialise session state keys before any widget reads them. Empty list = show all — this is the semantic contract enforced by the `apply_filters()` helper.

**Filter applicability per section — inapplicable filters remain visible with `st.caption()` notes:**

| Filter | Executive | Products | Geo (delivery) | Geo (sellers) | Customers (RFM) | Customers (satisfaction) |
|---|---|---|---|---|---|---|
| Date Range | ✓ | ✓ | ✓ | ✗ full period | ✗ fixed ref date | ✓ |
| Product Category | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ approx |
| State | ✓ | ✓ | ✓ | ✓ seller home | ✓ | ✓ |
| Region | ✓ | ✓ | ✓ | ✓ seller home | ✓ | ✓ |

Hiding inapplicable filters was rejected — it creates surprising behaviour when a user sets a filter, navigates, and the filter silently disappears. Caption notes explain the constraint without removing the control.

**Non-obvious implementation decisions:**

1. **Item-granularity deduplication**: `sales_orders.parquet` is at order-item grain (~112k rows). Computing order-level metrics (AOV, on-time rate, payment distribution) requires `drop_duplicates("order_id")` before aggregation. Without this, an order with 3 items is counted 3 times — inflating AOV and distorting payment type shares. Every page that uses `sales_orders` makes this deduplication explicit at load time.

2. **`geo_delivery.parquet` column naming**: The delivery Parquet uses column `region` (not `customer_region`). A dedicated `apply_geo_filters()` function handles this difference and also performs date filtering via integer year-month comparison (`year * 100 + month`) rather than a `date_key` column (which `geo_delivery` does not have).

3. **Plotly categorical axis annotation**: `fig.add_vline(x="2017-11", annotation_text=...)` fails with `TypeError: unsupported operand type(s) for +: 'int' and 'str'` when the x-axis is categorical strings. Plotly internally computes `sum(x_values) / len(x_values)` to position the annotation; `sum(["2017-01", ...])` starts with `0 + "2017-01"` which raises the error. Fix: replaced with `fig.add_shape(type="line", xref="x", ...)` + `fig.add_annotation(xref="x", ...)` which accept string x-values directly. Applied to the Black Friday 2017 annotation on the Sales Trend tab.

4. **Multiselect session state ownership**: Using both `default=st.session_state.key` and `st.session_state.key = st.multiselect(...)` creates a double-rerun bug where the second click in a multiselect is silently dropped (Streamlit re-renders the widget with the stale default before the new value is written back). Fix: use `key=` parameter only — Streamlit manages the session state sync automatically. The `default=` parameter is never set.

5. **Reset button callback order**: Directly assigning `st.session_state.category_filter = []` in the script body after a keyed multiselect is instantiated raises `StreamlitAPIException` — keyed widgets own their session state key and block external mutation after rendering. Fix: use `on_click=_reset` callback, which executes in the pre-script phase before widget instantiation.

6. **RFM heatmap reindex ordering**: Building the pivot with `.reindex(index=[5,4,3,2,1], columns=["F1","F2","F3"])` must happen *before* `.fillna(0).astype(int)`. If reindex follows fillna/astype, reindex reintroduces NaN into an int64 array, which silently downcasts to float64 and renders as "nan" in the cell text.

7. **NaN guard on NPS metric**: When the filtered dataset is too small to compute NPS, `nps_score` is `float("nan")`. The conditional `nps_score >= 0` evaluates `False` for NaN, falling to the else branch and rendering `"nan"` as a string. Fix: `pd.isna(nps_score)` guard before the comparison.

8. **Simpson's Paradox on on-time rate**: On-time rate is computed as `sum(on_time_orders) / sum(total_orders)` across filtered `geo_delivery` rows — not as an average of pre-computed per-state rates. Averaging pre-computed rates without weighting by volume gives disproportionate influence to states with few orders. The weighted aggregate is the correct denominator.

9. **`st.plotly_chart` width**: `use_container_width=True` was deprecated in Streamlit 1.55 in favour of `width="stretch"`. All 30 `st.plotly_chart` calls across the 4 analysis pages use `width="stretch"`.

**Choropleth map:**
- GeoJSON: `data/brazil_states.geojson` — committed to repo, loaded once via `@st.cache_data` as a Python dict.
- `featureidkey="properties.sigla"` — confirmed against the GeoJSON feature properties; matches the 2-letter state codes (`"SP"`, `"RJ"`, etc.) in all Parquet files.
- No runtime HTTP fetch — the file is local, ensuring the map renders without network access.

**Page content summary:**

| Page | Tabs | Key charts |
|---|---|---|
| Executive Overview | Sales Trend · Revenue & AOV · Payment Mix · Order Health | GMV area + order count bar (stacked panels); AOV line + payment type bar; payment type donut + instalment histogram; cancellation rate line + order status donut |
| Product Performance | Revenue Rankings · Category Concentration · Freight Impact | Horizontal bar + treemap (top-N slider); Lorenz curve + Gini/HHI/CR4/CR10 KPI cards; freight-to-price ratio bar |
| Geographic Analysis | Market Map · Delivery Performance · Seller Analysis | Choropleth (GMV by state) + region bar; on-time rate bar + delay bar + region×month heatmap; scatter (GMV vs score) + Pareto curve + quality tier treemap + monthly Gini trend |
| Customer Analysis | RFM Segments · Segment Playbook · Satisfaction & NPS · Delivery Impact | Grouped bar (avg R/F/M per segment) + RFM heatmap; segment action cards; review score bar + avg score line + NPS stacked bar + NPS trend line; delay-bin bar + box plot |
| Glossary | — | Searchable expanders (17 terms across 7 categories); no charts |

**Lorenz curve and concentration metrics** (Product Performance — Category Concentration tab): `lorenz_curve()` and `gini_coefficient()` are imported directly from `notebooks/utils.py` and applied to the filtered revenue series. The Gini and HHI interpretive caption is dynamic — it adjusts its language based on whether HHI is above or below the 1,500 competitive-concentration threshold.

**Seller quality tiers** (Geographic Analysis — Seller Analysis tab): Quality tier classification (`Premium`, `Good`, `Average`, `At Risk`) is applied at render time using a row-wise function on the filtered seller DataFrame, using thresholds from the BRD (≥10 orders; score ≥ 4.0 + cancel ≤ 2% for Premium, etc.). This avoids pre-computing tiers in the Parquet file, keeping tier definitions in one place.

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
| numpy | 2.2.5 | Concentration analysis helpers in `notebooks/utils.py` (Lorenz curve, Gini, HHI) |
| google-cloud-bigquery | 3.40.1 | BigQuery Python client (used by all notebooks + `generate_parquet.py`) |

**Credentials and configuration**: All tools read from the repo root `.env` file, but via different mechanisms — each tool has its own loading path:

| Tool | Loading mechanism |
|---|---|
| Meltano | `meltano --env-file ../.env` flag (passed by `launch_meltano.sh` and the Dagster `meltano_ingest` subprocess) |
| dbt | `env_var()` in `profiles.yml` — reads from process environment at compile time |
| Dagster | `DAGSTER_HOME` → `dagster/dagster_home/dagster.yaml` → `EnvFileLoader` — injects `.env` into the Dagster process at startup |
| Jupyter notebooks | `load_dotenv()` via `python-dotenv` at the top of each notebook |
| Streamlit dashboard | No credentials needed — reads committed Parquet files only |

The four `.env` variables:
- `GOOGLE_APPLICATION_CREDENTIALS` — path to GCP service account key file
- `GCP_PROJECT_ID` — BigQuery project identifier
- `BIGQUERY_ANALYTICS_DATASET` — dbt target dataset (default: `olist_analytics`)
- `BIGQUERY_RAW_DATASET` — Meltano target dataset / dbt source schema (default: `olist_raw`)

**`DAGSTER_HOME` bootstrap constraint**: Dagster requires `DAGSTER_HOME` to be set in the process environment *before* it starts — it uses this to locate `dagster.yaml` which activates the `EnvFileLoader`. This creates a circular dependency: Dagster cannot load `.env` to discover its home directory. `scripts/launch_dagster.sh` resolves this by sourcing `.env` and exporting `DAGSTER_HOME` as an absolute path before calling `dagster dev`.

---

## 5. Analytical Methodology

This section documents the key analytical design decisions made during notebook implementation. These decisions are not derivable from the dbt schema alone — they represent explicit choices about how to interpret, segment, and present the data for stakeholder consumption.

### 5.1 Observation Window — Jan 2017 to Aug 2018

**Decision**: All trend analyses (GMV, NPS, cancellation rate, delivery performance) are scoped to 2017-01 through 2018-08 inclusive.

**Rationale:**

| Period | Orders | Reason excluded |
|---|---|---|
| 2016-11 | 0 | Data cut artefact — no orders |
| 2016-12 | 1 | Insufficient volume; distorts seasonality |
| 2018-09 | 16 | Data cut artefact — pipeline cut mid-month |
| 2018-10 | 4 | Data cut artefact — pipeline cut early |

Including these edge periods would produce spurious troughs and peaks at the boundaries of every trend chart. The observation window is applied consistently via a SQL `WHERE` clause in each notebook query — not as a post-hoc filter on the exported Parquet.

**Exception — RFM Recency**: 2016 orders are retained in customer history. A customer whose last purchase was in 2016 has a legitimately high Recency value (many days since last order) and should be assigned a low R-score. Excluding 2016 entirely would misclassify these customers as new rather than lapsed.

### 5.2 RFM Segmentation Design

**Reference date**: `2018-08-31` — hardcoded, not `CURRENT_DATE` or `MAX(order_purchase_timestamp)`. Using `CURRENT_DATE` would change segment assignments every time the notebook is re-run. Using `MAX(timestamp)` would shift the reference point if the data cut changes. A fixed date produces reproducible, comparable results across runs and reviewers.

**Frequency tier design**: 3 tiers (F1=1 order, F2=2 orders, F3=3+ orders) instead of quintiles.

Quintile scoring collapses when the distribution is highly skewed. In this dataset, 96.9% of customers have exactly 1 order. A quintile-based F-score would assign F1 to all single-order customers regardless of percentile rank, and F2–F5 would cover the remaining 3.1% — producing a 5-tier scale that is functionally a 2-tier scale with arbitrary internal boundaries. Three explicit tiers reflect the actual business reality (one-time, repeat, loyal) without false precision.

**Segment assignment (RF-only)**:

| Segment | R-score | F-tier | Business interpretation |
|---|---|---|---|
| Champions | 4–5 | F3 | Recent + frequent — highest-value active customers |
| Loyal | 3–5 | F2–F3 | Returning customers with good recency |
| Promising | 4–5 | F1 | Recent first-time buyers — nurture for repeat purchase |
| At Risk | 1–2 | F2–F3 | Previously frequent, now lapsed — win-back candidates |
| High Value Lost | 1–2 | F3 | High-frequency, long-absent — priority win-back |
| Hibernating | 1–3 | F1 | Distant single-purchase — low re-engagement probability |

Monetary score (M-score, quintile 1–5) is stored in `customer_rfm.parquet` as a display attribute for the grouped bar chart but does not drive segment assignment. RF-only assignment produces segments that are collectively exhaustive — every R/F combination is covered by exactly one segment when priority ordering is applied: more specific segments (Champions, High Value Lost) take precedence over their broader parent definitions (Loyal, At Risk). For example, a customer with R=5 and F-tier=F3 satisfies both Champions (R4–5, F3) and Loyal (R3–5, F2–F3); they are assigned Champions. This priority is implemented as a SQL `CASE WHEN` ordered from most-specific to least-specific.

**Repeat purchase rate**: Computed as the share of `customer_unique_id` values with `frequency >= 2`. Expected value ~3.1% — confirming the marketplace's single-purchase dominant behaviour (ASMP-022). Displayed as a `st.metric()` KPI card in the dashboard.

### 5.3 NPS Proxy and Review Analysis

**NPS proxy scoring**:
- Detractor: review_score 1–2
- Passive: review_score 3
- Promoter: review_score 4–5
- NPS = (% promoters) − (% detractors)

This mapping approximates the standard Net Promoter Score methodology using the 1–5 ordinal scale available in the dataset. It is a proxy — no explicit "would recommend" survey question was asked. The NPS trend line complements the raw score distribution bar chart by reducing 5 categories to a single scalar for stakeholders who are familiar with NPS benchmarks.

**Delay×review correlation — 5 bins**:

| Bin | Definition | Purpose |
|---|---|---|
| `early` | delivered < estimated | Captures positive surprise effect — early delivery correlates with higher scores |
| `on-time` | delivered = estimated (0 days late) | Baseline |
| `1–3d late` | 1–3 days past estimate | Mild delay |
| `4–7d late` | 4–7 days past estimate | Moderate delay |
| `7+d late` | >7 days past estimate | Severe delay |

The `early` bin is deliberately included. An analysis starting from "on-time or late" would miss the insight that customers receiving orders before the estimated date give materially higher scores — a finding with direct operational value (tighter delivery estimates → more early deliveries → better NPS).

### 5.4 Concentration Analysis (Lorenz / Gini / HHI)

Beyond the 11 core BRD metrics, the notebooks compute revenue concentration metrics to quantify market structure:

| Metric | Scope | Finding |
|---|---|---|
| Gini coefficient | Seller GMV distribution | ~0.78 — high concentration; top 20% of sellers generate ~80% of GMV |
| Gini coefficient | Seller GMV by month (temporal) | Tracks whether seller concentration increases or decreases over time |
| Gini coefficient | Customer monetary spend | ~0.48 — moderate concentration |
| Gini coefficient | Category revenue | ~0.71 — top categories disproportionately dominate revenue |
| HHI (Herfindahl-Hirschman Index) | Seller GMV, customer spend, category revenue | Sum of squared market share fractions; complements Gini with a single-number market concentration measure |
| CR4 / CR10 | All dimensions | Cumulative revenue share of top 4 and top 10 entities |

These metrics are exported to `data/concentration_metrics.parquet` (83 rows). The file has a `dimension × group_key` structure: each row represents one dimension (e.g., `seller_gmv`, `seller_gmv_monthly`, `customer_monetary`, `category_revenue`, `category_seller_gmv`) at one aggregation level (e.g., `overall`, `2017-01`, a specific category name). Lorenz curves in the dashboard plot the cumulative share of entities (x-axis) against cumulative value share (y-axis), with the 45° equality line as reference — one curve per dimension.

**Rationale for inclusion**: The 80/20 seller concentration finding is a high-signal insight for marketplace operators — it determines seller acquisition strategy and risk exposure. Standard bar charts (top N sellers) convey ranking but not structural inequality. A Gini coefficient and Lorenz curve communicate the full distribution shape in a single number and plot.

### 5.5 Parquet Schema Contract

The 6 Parquet files exported by the analytical notebooks form a versioned contract for the dashboard layer. Schema stability is enforced by keeping `generate_parquet.py` in sync with notebook exports. The contract is summarised below for downstream reference:

| File | Granularity | Rows (est.) | Key columns |
|---|---|---|---|
| `sales_orders.parquet` | Order-item | ~112k | `order_id`, `order_item_id`, `product_category_name_english`, `date_key`, `year`, `month`, `order_status`, `total_sale_amount`, `primary_payment_type`, `primary_payment_installments`, `customer_region` |
| `customer_rfm.parquet` | Customer | ~96k | `customer_unique_id`, `customer_state`, `customer_region`, `recency_days`, `frequency`, `monetary_value`, `r_score`, `f_tier`, `m_score`, `segment` |
| `satisfaction_summary.parquet` | Order | ~97k | `order_id`, `review_score`, `nps_category`, `delivery_delay_days`, `delay_bin`, `year`, `month`, `customer_region`, `primary_product_category` |
| `geo_delivery.parquet` | State × month | ~535 | `customer_state`, `region`, `year`, `month`, `total_orders`, `on_time_orders`, `on_time_rate`, `avg_delay_days` |
| `seller_performance.parquet` | Seller | ~3k | `seller_id`, `seller_state`, `seller_region`, `gmv`, `order_count`, `avg_review_score`, `cancellation_rate` |
| `concentration_metrics.parquet` | Dimension × group | 83 | `dimension`, `group_key`, `gini`, `cr4`, `cr10`, `hhi`, `n_entities`, `top_20pct_share` |

**Design notes**:
- `primary_payment_type` and `primary_payment_installments` in `sales_orders.parquet` use `payment_sequential=1` per order. ~3% of orders use split payments — this is an acceptable approximation for payment distribution analysis.
- `primary_product_category` in `satisfaction_summary.parquet` is the category of the highest-revenue item per order. Approximate for ~10% multi-item orders.
- `geo_delivery.parquet` includes `year` and `month` columns — required for the Date Range filter on the Geographic dashboard page.
- `seller_performance.parquet` has no date dimension — full-period aggregation only. The dashboard displays a static "Jan 2017 – Aug 2018" label above the seller section.
- All `*_region` columns are derived from `notebooks/utils.py:REGION_MAP` — single source of truth, no drift between files.

---

## 6. References

- Architecture Decision Records: `docs/decisions/ADR-001` through `ADR-004`
- Source data profile: `docs/data_profile.json`
- Star schema ERD: `docs/diagrams/star_schema.png` (Graphviz) + `docs/star_schema.dbml` (dbdiagram.io) + `docs/star_schema.dot` (Graphviz source)
- Data lineage: `docs/diagrams/data_lineage.png` (Graphviz) + `docs/data_lineage.dot` (Graphviz source)
- Pipeline architecture: `docs/diagrams/pipeline_architecture_detailed_2.png` (Graphviz)
- Local run setup guide: `docs/local_run_setup.md`
- Troubleshooting guide: `docs/troubleshooting.md`
- BRD: `docs/requirements/BRD_Olist_Assignment_v5.0.md`
