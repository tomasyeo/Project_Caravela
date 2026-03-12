# Business Requirements Document
## Project Caravela — Olist E-Commerce Analytics Pipeline
The caravel — caravela in Portuguese — was the sailing vessel that carried Portugal and Brazil into the Age of Discovery. We are doing the same with Brazilian commerce data. The name is earned. (Claude)

| Field | Value |
|---|---|
| Version | 4.0 |
| Status | Draft |
| Prepared by | Patrick — Requirements Analyst; Claude — AI Pipeline Architect |
| Primary Source | `requirements.md` |
| Supplementary Sources | `README.md` (anticipated — not yet in repository), `technical_report.md` (anticipated — not yet in repository), `olist_profile.txt` |
| Date | 2026-03-11 |

---

## Foreword

This document is addressed to the **Platform Engineer** as the primary implementation lead for Project Caravela — the Olist E-Commerce Analytics Pipeline.

The confirmed implementation team consists of five agents. Implementation authority is delegated per section as follows:

| Agent | Scope | Sections |
|---|---|---|
| **Platform Engineer** | Overall pipeline architecture, infrastructure, orchestration (Dagster + Meltano), tooling recommendations, and documentation structure | 0, 6, 7 |
| **Data Engineer** | Schema design, ELT pipeline (dbt staging + marts), and data quality implementation | 2, 3, 4 |
| **Data Analyst** | Analysis layer, key metrics, EDA, and notebook implementation | 5 (analysis) |
| **Dash Engineer** | Streamlit dashboard — all four views, filter logic, Parquet integration | 5 (dashboard) |
| **Data Scientist** | Executive brief, stakeholder slide deck, business narrative and recommendations | 8 |

Full discretion is delegated to each agent within their section scope. Cross-section dependencies must be coordinated explicitly — agents must not modify deliverables outside their delegated scope without logging the change in `changelog.md` per REQ-037.2.

**Note on BRD role names:** Prior to v3.4, this document used "AI Pipeline Architect" for the Platform Engineer role. All prior references to "AI Pipeline Architect" should be read as "Platform Engineer".

Each section is self-contained. Requirements within each section must be read in conjunction with the assumptions (ASMP entries) that support them. All ad hoc changes and deviations to the implementation plan must be recorded in the changelog document per REQ-037.2.

---

## Assumptions Register

| ID | Statement | Supported REQ-IDs | Source |
|---|---|---|---|
| ASMP-001 | Meltano is selected as the ingestion tool. Source data is provided as CSV files directly — not retrieved from Kaggle. **Confirmed plugins: `tap-spreadsheets-anywhere` (extractor) and `target-bigquery` official Meltano plugin (loader).** `tap-spreadsheets-anywhere` is selected over `tap-csv` because it streams file contents (safe for the 1M-row geolocation file) and supports configurable per-file encoding (resolves UTF-8 BOM on `product_category_name_translation.csv`). `target-bigquery` official is selected for batch Load Jobs (free in BigQuery), `WRITE_TRUNCATE` write disposition support, and Meltano maintenance. **Meltano invocation:** `meltano run tap-spreadsheets-anywhere target-bigquery`. **`write_disposition`: `WRITE_TRUNCATE`** — required for idempotent daily Dagster runs on a fixed historical dataset; `WRITE_APPEND` would duplicate rows on every run. **BigQuery table naming convention:** each stream in `meltano.yml` uses an explicit `table_name` field set to the source filename minus extension, lowercased (e.g., `olist_customers_dataset.csv` → `olist_customers_dataset`). This naming convention is the contract for `sources.yml` in dbt — the data engineer must not deviate without updating `sources.yml`. Full table name mapping: `olist_customers_dataset`, `olist_orders_dataset`, `olist_order_items_dataset`, `olist_order_payments_dataset`, `olist_order_reviews_dataset`, `olist_products_dataset`, `olist_sellers_dataset`, `olist_geolocation_dataset`, `product_category_name_translation`. **`raw_data/` path:** configured in `meltano.yml` as a relative path from the Meltano project root (e.g., `../raw_data/` if Meltano lives in `meltano/`). Absolute paths must not be used — they break reproducibility across machines (REQ-036.1). **BigQuery dataset names: `olist_raw` (ingestion target) and `olist_analytics` (transformation target).** The name `raw` was rejected because it is a reserved word in BigQuery standard SQL — using it as a dataset name requires backtick-quoting in every query and its handling by dbt's BigQuery adapter is version-dependent; renaming avoids the ambiguity entirely. See changelog entry 2026-03-11. | REQ-001.2; REQ-012.1 | User confirmation; BRD review 2026-03-11 |
| ASMP-028 | **`tap-spreadsheets-anywhere` loads all columns as STRING into BigQuery `olist_raw`.** Type inference is not performed at ingestion — every column in every raw table is STRING regardless of its semantic type (timestamps, floats, integers). All type casts are the responsibility of the dbt staging layer: `order_purchase_timestamp` and all other timestamps must be cast using `CAST(col AS TIMESTAMP)` in `stg_orders` — Olist timestamps are well-formatted per `docs/data_profile.json`; `SAFE.PARSE_TIMESTAMP()` is not needed and introduces format string risk. Use `SAFE.PARSE_TIMESTAMP` only if a specific column is confirmed to have format variations. Preferred pattern: `DATE(CAST(col AS TIMESTAMP))` for date_key derivation (consistent with the confirmed `date_key DATE` type); `price`, `freight_value`, `payment_value`, `geolocation_lat/lng` cast as FLOAT64; `order_item_id`, `payment_sequential`, `payment_installments`, `review_score` cast as INT64. Failure to cast in staging will cause dbt-expectations pair tests (e.g., `order_approved_at ≥ order_purchase_timestamp`) to compare strings rather than timestamps, producing incorrect results without an explicit error. | REQ-011.1 | BRD review 2026-03-11 |
| ASMP-002 | Google BigQuery is the sole data warehouse and ingestion target for this project. | REQ-001.2, REQ-003.1, REQ-008.1, REQ-009.1 | User confirmation |
| ASMP-003 | dbt is selected as the ELT transformation tool targeting Google BigQuery. | REQ-008.1, REQ-009.1, REQ-010.1, REQ-014.1 | User confirmation |
| ASMP-004 | Data engineer has full discretion to modify schema detail as required during implementation. Schema defined in this BRD is based on dataset analysis and is subject to change. Note: In the Olist dataset, `customer_id` in `olist_orders_dataset.csv` is order-scoped — one customer may have multiple `customer_id` values across orders. `customer_unique_id` is the true customer identifier. All customer-level joins and keys must use `customer_unique_id`. | REQ-005.1, REQ-006.1, REQ-007.1, REQ-008.1, REQ-012.1, REQ-013.1, REQ-051.1, REQ-052.1, REQ-053.1 | User confirmation |
| ASMP-005 | Derived column implementation is at data engineer discretion. Confirmed derived column: `total_sale_amount` (price + freight_value, item-level) for product revenue attribution. `order_payment_value` has been removed from `fct_sales` — it is an order-level aggregate on an item-level fact table; in multi-item orders it repeats the same value across all item rows, causing silent double-counting on SUM(). Payment totals per order are obtained by querying `fct_payments` directly. | REQ-013.1 | BRD review |
| ASMP-006 | Null value and duplicate test implementation is deferred to data engineer discretion. | REQ-018.1 | User confirmation |
| ASMP-007 | Business logic tests are in scope for data quality testing. Specific rules are deferred to data engineer discretion. | REQ-017.1 | User confirmation |
| ASMP-008 | Key metrics confirmed in scope — six mandated metrics: (1) monthly sales trends, (2) top-selling products by revenue, (3) RFM customer segmentation, (4) delivery performance (on-time rate and average delay), (5) review/satisfaction analysis, (6) payment method distribution. Five additional metrics confirmed in scope per data analyst review: (7) Average Order Value (AOV) trend, (8) fulfilment/cancellation rate by status, (9) NPS proxy (review score rebucketed: 1–2 = detractor, 3 = passive, 4–5 = promoter), (10) seller performance summary (GMV + average review score + cancellation rate per seller), (11) regional e-commerce penetration (customer/seller metrics segmented by Brazil's 5 official regions: North, Northeast, Central-West, Southeast, South). Notebook organisation: four notebooks — `00_eda.ipynb` (exploratory, free-form analytics schema verification; not a deliverable metric source), `01_sales_analysis.ipynb`, `02_customer_analysis.ipynb`, `03_geo_seller_analysis.ipynb` (analytical deliverables, each exporting Parquet). Exploratory and analytical notebooks are fully separated: analytical notebooks are self-contained and reference `00_eda.ipynb` findings via markdown only. State-to-region mapping: North (AM, AC, RO, RR, AP, PA, TO), Northeast (MA, PI, CE, RN, PB, PE, AL, SE, BA), Central-West (MT, MS, GO, DF), Southeast (MG, ES, RJ, SP), South (PR, SC, RS). Implementation details per REQ-022.1 and REQ-055.1 through REQ-058.1. | REQ-022.1, REQ-055.1, REQ-056.1, REQ-057.1, REQ-058.1 | User confirmation |
| ASMP-009 | "Top-selling products" means highest revenue generated, derived from `total_sale_amount`. | REQ-022.1 | User confirmation |
| ASMP-010 | Dagster is selected as the orchestration tool. Pipeline execution supports both manual triggering and a daily scheduled run at 09:00. | REQ-026.1, REQ-027.1, REQ-028.2 | User confirmation |
| ASMP-011 | REQ-030.1 (pipeline architecture diagram) and REQ-034.1 (AI pipeline architecture document) are merged into a single deliverable produced by the Platform Engineer. The deliverable consists of one architecture document (written) and one architecture diagram (visual). | REQ-030.1 | User confirmation |
| ASMP-012 | Project implementation documentation and local run setup documentation are required deliverables. | REQ-035.1, REQ-036.1 | User confirmation |
| ASMP-013 | Data Scientist is a confirmed implementation team member with full discretion over Section 8 executive presentation content and delivery, including the executive brief (`docs/executive_brief.md` per REQ-066.1), slide deck, and business narrative. The Data Scientist takes analytical outputs from the Data Analyst (Sections 3–5) and translates them into stakeholder-facing deliverables. | REQ-038.1 through REQ-044.1; REQ-066.1 | User confirmation 2026-03-11 |
| ASMP-014 | BRD foreword delegation model confirmed. Five-agent team: Platform Engineer (primary lead — Sections 0, 6, 7), Data Engineer (Sections 2, 3, 4), Data Analyst (Section 5 analysis), Dash Engineer (Section 5 dashboard), Data Scientist (Section 8). Prior BRD versions used "AI Pipeline Architect" for Platform Engineer — all such references should be read as "Platform Engineer" per the v3.4 foreword note. | All | User confirmation 2026-03-11 |
| ASMP-015 | API keys for Google Cloud BigQuery connection will be provided to the data engineer before implementation begins. Credential format: service account JSON key file. Required environment variable: `GOOGLE_APPLICATION_CREDENTIALS`. Responsible party and provisioning timeline: to be confirmed with team. | REQ-003.1, REQ-059.1 | User confirmation |
| ASMP-016 | Parquet files committed to the repository are the final feature datasets produced by the analysis layer. They represent the output of the analysis notebooks and are the data source for the Streamlit dashboard deployment on Streamlit Community Cloud. | REQ-025.1 | User confirmation |
| ASMP-017 | A changelog document is required to log all ad hoc changes and deviations to the implementation plan during implementation. | REQ-037.2 | User confirmation |
| ASMP-018 | Pipeline orchestration was upgraded from optional (as stated in `requirements.md` §6) to required scope (P1). Scheduled runs, originally recommended in `requirements.md` §6, were temporarily descoped in v1.0 and are reinstated in v2.0 as a daily 09:00 Dagster schedule. These deviations from `requirements.md` are recorded here as the baseline. The changelog (REQ-037.2) does not require further entries for these specific decisions. | REQ-026.1, REQ-027.1, REQ-028.2 | User confirmation |
| ASMP-019 | Streamlit interactive dashboard (REQ-024.1) is confirmed in scope. Source `README.md` is anticipated but not yet in repository. | REQ-024.1 | User confirmation |
| ASMP-020 | All 9 Olist source CSV files are in scope for the dbt lineage. The omission of 4 tables (`olist_order_payments_dataset.csv`, `olist_order_reviews_dataset.csv`, `olist_sellers_dataset.csv`, `olist_geolocation_dataset.csv`) from v1.0 was a BA oversight — not a deliberate design decision. All 9 tables are confirmed in scope. | REQ-011.1, REQ-012.1 | User confirmation |
| ASMP-021 | `fct_payments` is implemented as a separate fact table (Option B). Payment method analysis (payment type distribution, installment behaviour) is confirmed in scope for the analysis layer. | REQ-053.1, REQ-058.1 | User confirmation |
| ASMP-022 | RFM (Recency, Frequency, Monetary) segmentation is the confirmed customer segmentation method. Full specification — **Reference date:** `2018-08-31` (last day of August 2018, the last complete month; August has 6,512 orders consistent with the stable plateau; September 2018 drops to 16 orders due to data cut artefact — see ASMP-025). **Observation window for trend analyses:** `2017-01-01` to `2018-08-31`; full dataset retained in customer purchase history for Recency calculation. **Scoring:** Recency — quintile-based (1–5), lower days-since-last-purchase = higher score. Frequency — 3-tier (F1 = 1 order, F2 = 2 orders, F3 = 3+ orders); standard quintile scoring not used because ~96.9% of customers have exactly 1 order (source data: 93,099 of 96,096 distinct customers). Monetary — quintile-based (1–5), higher `SUM(total_sale_amount)` = higher score. **Named segments (RF-only assignment):** Champions (R4–5, F3), Loyal (R3–5, F2–3), Promising (R4–5, F1), At Risk (R1–2, F2–3), High Value Lost (R1–2, F3 — high frequency, dormant), Hibernating (R1–3, F1 — dominant bucket; ~96.9% of customers). Segment assignment uses R_score and F_tier only — all 15 RF combinations are covered with no gaps. **Monetary is scored (M_score, quintile 1–5) and stored in `customer_rfm.parquet` as a display attribute** — it is visualised as one of three bars in the avg R/F/M grouped bar chart per segment, but does not drive segment assignment. M-inclusive assignment was considered but produces non-exhaustive rules given the RF distribution (96.9% F1 makes M thresholds within F1 the only meaningful distinction, which adds complexity without interpretive value). **Standalone metric required:** repeat purchase rate (% of `customer_unique_id` with exactly 1 order — expected ~96.9%; surfaces marketplace channel stickiness). | REQ-055.1 | User confirmation |
| ASMP-023 | Python 3.11 is the confirmed development Python version. The project uses a conda environment named `assignment2`. Conda is the preferred package manager; pip is used as fallback where conda packages are unavailable. Meltano manages its own plugin virtual environments internally under `.meltano/` — this is Meltano's default behaviour and does not require manual intervention. | REQ-059.1, REQ-060.1 | User confirmation |
| ASMP-024 | The `dbt-expectations` package (by Calogica) is declared in `packages.yml` and installed via `dbt deps`. It is used for generic tests declared in `schema.yml` at the column and table level. `dbt-expectations` is a direct port of the Great Expectations test library into dbt's native testing framework — its inclusion satisfies the Great Expectations mention in `requirements.md` §4 while remaining entirely within the dbt toolchain. Generic tests (dbt-expectations) and singular tests (`tests/*.sql`) are complementary mechanisms; both execute under `dbt test`. | REQ-015.1, REQ-017.1, REQ-018.1 | BRD review |
| ASMP-026 | **Visualization library:** `plotly.express` is the confirmed visualization library for all three analytical notebooks (`01_sales_analysis.ipynb`, `02_customer_analysis.ipynb`, `03_geo_seller_analysis.ipynb`) and `dashboard.py`. The exploratory notebook (`00_eda.ipynb`) may use seaborn/matplotlib as these charts are not reused in the dashboard. Plotly figures are rendered in Jupyter via the default renderer and in Streamlit via `st.plotly_chart(fig, use_container_width=True)`. Colour palettes for RFM segments, Brazil regions, and order statuses are defined in `notebooks/utils.py` and imported consistently across all notebooks and `dashboard.py`. The Brazil choropleth map requires `data/brazil_states.geojson` committed to the repository — do not fetch at runtime. File confirmed present; `featureidkey="properties.sigla"` confirmed. | REQ-024.1, REQ-022.1 | BRD review 2026-03-10 |
| ASMP-027 | **Dashboard architecture.** `dashboard.py` is a thin entry point (page config + `st.navigation()` only — no charts, no data loading). The four views are implemented as separate page files in `pages/`: `1_Executive.py`, `2_Products.py`, `3_Geographic.py`, `4_Customers.py`. A shared `dashboard_utils.py` at project root provides `@st.cache_data` Parquet loaders and `init_filters()` — separating Streamlit-specific code from `notebooks/utils.py` (pure Python, no Streamlit import). Cross-page filter state persists via `st.session_state` (keys: `date_start`, `date_end`, `category_filter`, `state_filter`, `region_filter`; initialised by `init_filters()` on every page load). Empty multi-select = show all (do not require explicit "All" selection). **Filter applicability per view:** Executive Overview (all 4 filters apply). Product Performance (all 4 apply). Geographic Analysis (Date Range and State/Region apply to `geo_delivery.parquet`; Product Category not applicable; `seller_performance.parquet` is full-period only — static label "Jan 2017 – Aug 2018" displayed above seller section via `st.caption()`). Customer Analysis (`customer_rfm.parquet`: Date Range and Product Category do not apply — fixed reference date 2018-08-31; display `st.caption()` note on RFM section; `satisfaction_summary.parquet`: all 4 filters apply). `data/brazil_states.geojson` is loaded via `@st.cache_data` from disk — not fetched at runtime. **Pre-implementation check (D-05):** before writing the choropleth, open `brazil_states.geojson` and verify the `featureidkey` path to the 2-letter state code field (commonly `properties.sigla` or `properties.SIGLA`). | REQ-024.1 | BRD review 2026-03-10 |
| ASMP-025 | **Source data temporal observations** (confirmed from `docs/data_profile.json` monthly distribution query, 2026-03-10). (1) **Tail sparsity:** September 2018 has 16 orders and October 2018 has 4 orders — a >99% drop from the stable August 2018 plateau of 6,512 orders. These are data cut artefacts, not real activity. `MAX(order_purchase_timestamp)` = 2018-10-17 is misleading as a reference date. (2) **Head sparsity:** November 2016 has zero orders — a complete gap at platform launch. September 2016 (4 orders) and December 2016 (1 order) are also non-representative. (3) **Stable plateau:** January 2018 through August 2018 averages ~6,748 orders/month. The platform reached operating scale from January 2017. (4) **Peak:** November 2017 (7,544 orders) reflects Brazilian Black Friday. (5) **Meaningful observation window:** `2017-01-01` to `2018-08-31` (20 months). Exclude 2018-09 and 2018-10 from all trend analyses. Include 2016 orders in customer purchase history only (for RFM Recency — a customer who last bought in October 2016 correctly scores R1). Exclude 2016 from any seasonality or trend line analysis. | REQ-022.1, REQ-055.1 | BRD review |

---

## Section 0 — Development Environment

---

**REQ-059.1**
Type: CON
Priority: P0
Section: Development Environment
Statement: The project must be developed within a conda environment named `assignment2` using Python 3.11. Conda is the preferred package manager; pip is used as fallback where conda packages are unavailable. All project dependencies must be reproducible via a committed dependency file.
Rationale: A shared, reproducible environment prevents version incompatibilities across the toolchain (Meltano, dbt-bigquery, Dagster, Streamlit, SQLAlchemy, pandas) and ensures consistent behaviour across developer machines.
Acceptance Criteria: A `requirements.txt` or `environment.yml` file exists in the repository listing all project dependencies with pinned versions. The conda environment `assignment2` with Python 3.11 can be created and all dependencies installed by following the local run setup document (REQ-036.1). The environment successfully runs all pipeline stages end-to-end.
Dependencies: NONE
Source: ASMP-023; DE-Q1 user confirmation
Open Items: Agent has full discretion to select and install any Python modules required for the project.

---

**REQ-060.1**
Type: CON
Priority: P1
Section: Development Environment
Statement: The development environment must support macOS and Linux. Windows support is provided via WSL2 only.
Rationale: The toolchain (Meltano, Dagster) has known friction on native Windows. Standardising on macOS/Linux avoids platform-specific issues and simplifies the local run setup document.
Acceptance Criteria: The local run setup document (REQ-036.1) provides instructions for macOS and Linux. Windows users are directed to use WSL2. No platform-specific workarounds are required for macOS or Linux users.
Dependencies: REQ-059.1
Source: DE-Q2 user confirmation; ASMP-023
Open Items: NONE

---

## Section 1 — Data Ingestion

---

**REQ-001.2**
Type: FR
Priority: P0
Section: Data Ingestion
Statement: The system must ingest all 9 Olist CSV source files into Google BigQuery using Meltano as the ingestion tool.
Rationale: Raw source data must be loaded into the data warehouse before any transformation or analysis can occur. All 9 source files are confirmed in scope per ASMP-020.
Acceptance Criteria: All 9 Olist CSV source files are successfully loaded into the BigQuery `olist_raw` dataset. Meltano is used as the ingestion tool. No source files are missing from the raw dataset upon completion of ingestion. The 9 source files are: `olist_customers_dataset.csv`, `olist_orders_dataset.csv`, `olist_order_items_dataset.csv`, `olist_order_payments_dataset.csv`, `olist_order_reviews_dataset.csv`, `olist_products_dataset.csv`, `olist_sellers_dataset.csv`, `olist_geolocation_dataset.csv`, `product_category_name_translation.csv`.
Dependencies: NONE
Source: `requirements.md` §1; ASMP-001; ASMP-002; ASMP-020
Open Items: (1) ~~UTF-8 BOM on `product_category_name_translation.csv`~~ — resolved by `tap-spreadsheets-anywhere` selection (ASMP-001); configure `encoding: utf-8-sig` for that file in `meltano.yml`. (2) ~~Geolocation 1M rows memory concern~~ — resolved by `tap-spreadsheets-anywhere` streaming behaviour (ASMP-001). (3) ~~BigQuery table names produced by Meltano must be documented before `sources.yml` is written~~ — resolved by ASMP-001; full 9-table name mapping confirmed. (4) ~~`write_disposition` must be set to `WRITE_TRUNCATE` in `target-bigquery` config~~ — resolved by ASMP-001; `WRITE_TRUNCATE` confirmed and mandated.

---

**REQ-002.1**
Type: CON
Priority: P0
Section: Data Ingestion
Statement: The ingestion layer must use Meltano as the sole ingestion tool. This constraint applies exclusively to scripts whose primary purpose is loading the raw Olist CSV source files into BigQuery. Utility scripts for credential validation, BigQuery dataset setup, or CI tooling are not in scope of this constraint.
Rationale: Meltano was confirmed as the ingestion tool replacing the original Python/SQL script approach.
Acceptance Criteria: No ingestion scripts other than Meltano pipelines are present in the repository for the purpose of loading source data into BigQuery.
Dependencies: REQ-001.2
Source: ASMP-001
Open Items: NONE

---

**REQ-003.1**
Type: CON
Priority: P0
Section: Data Ingestion
Statement: The ingestion target must be Google BigQuery.
Rationale: BigQuery is the confirmed data warehouse for this project.
Acceptance Criteria: All raw source data is verifiably present in the Google BigQuery `olist_raw` dataset upon completion of ingestion. Credentials are configured via the `GOOGLE_APPLICATION_CREDENTIALS` environment variable per ASMP-015.
Dependencies: REQ-001.2
Source: ASMP-002; ASMP-015
Open Items: (1) Responsible party and timeline for credential provisioning — **Owner: Platform Engineer** to coordinate with team before implementation begins. This is a pre-implementation blocker for REQ-001.2 and REQ-011.1. Until `GOOGLE_APPLICATION_CREDENTIALS` is provisioned and set, no pipeline stage can run. (2) ~~BigQuery dataset naming — resolved. Dataset names confirmed as `olist_raw` and `olist_analytics`. `raw` was rejected as a BigQuery SQL reserved keyword; renaming was recorded in `changelog.md` per REQ-037.2. See ASMP-001.~~ Closed 2026-03-11.

---

## Section 2 — Data Warehouse Design

---

**REQ-004.1**
Type: FR
Priority: P0
Section: Data Warehouse Design
Statement: The data warehouse must implement a star schema in Google BigQuery consisting of three fact tables and four dimension tables.
Rationale: A star schema enables efficient analytical querying for BI and reporting use cases. Three fact tables capture distinct event granularities (sales transactions, payment records, and customer reviews). Four dimension tables cover the key analytical dimensions (customer, product, seller, and date).
Acceptance Criteria: The BigQuery `olist_analytics` dataset contains `fct_sales`, `fct_reviews`, and `fct_payments` as fact tables, and `dim_customers`, `dim_products`, `dim_sellers`, and `dim_date` as dimension tables. Each dimension table has a defined primary key. `fct_sales` contains foreign keys referencing `dim_customers`, `dim_products`, `dim_sellers`, and `dim_date`. Data engineer may modify schema detail as required per ASMP-004.
Dependencies: REQ-003.1
Source: `requirements.md` §2; ASMP-004; ASMP-020; ASMP-021
Open Items: NONE

---

**REQ-005.1**
Type: FR
Priority: P0
Section: Data Warehouse Design
Statement: The data warehouse must implement a `dim_customers` dimension table containing at minimum customer unique identifier, city, state, zip code prefix, and geolocation coordinates.
Rationale: Customer attributes are required to support geographic filtering, customer-level analysis, and map-based dashboard views. Note: `customer_unique_id` must be used as the primary key, not `customer_id`. See ASMP-004 for the distinction.
Acceptance Criteria: `dim_customers` exists in the BigQuery `olist_analytics` dataset with `customer_unique_id` as primary key and columns for `customer_city`, `customer_state`, `customer_zip_code_prefix`, `geolocation_lat`, and `geolocation_lng` (the latter two sourced from stg_geolocation per REQ-054.1, nullable where no geolocation match exists). Data engineer may modify schema detail as required per ASMP-004.
Dependencies: REQ-004.1; REQ-054.1
Source: `technical_report.md` §Schema Design; ASMP-004; ASMP-020
Open Items: NONE

---

**REQ-006.1**
Type: FR
Priority: P0
Section: Data Warehouse Design
Statement: The data warehouse must implement a `dim_products` dimension table containing at minimum product identifier and English product category name.
Rationale: Product attributes are required to support product-level filtering and category analysis. Note: Source data contains misspelled column names `product_name_lenght` and `product_description_lenght` in `olist_products_dataset.csv` — staging model must correct these.
Acceptance Criteria: `dim_products` exists in the BigQuery `olist_analytics` dataset with `product_id` as primary key and a `product_category` column containing the English translation from `product_category_name_translation.csv`. Corrected column names are used (e.g., `product_name_length`). `stg_products` must apply a `COALESCE` fallback for `product_category`: (1) English translation where available, (2) original Portuguese name as fallback for the 2 untranslated categories (`pc_gamer`, `portateis_cozinha_e_preparadores_de_alimentos`), (3) `'uncategorized'` for the 610 products with a null source category. This ensures `product_category` is never null in `dim_products` and the REQ-018.1 `not_null` test passes. Data engineer may modify schema detail as required per ASMP-004.
Dependencies: REQ-004.1
Source: `technical_report.md` §Schema Design; ASMP-004
Open Items: 2 product categories in the source data have no entry in `product_category_name_translation.csv`: `pc_gamer` and `portateis_cozinha_e_preparadores_de_alimentos`. The translation file also has no entry for the 610 products with a null `product_category_name`. The COALESCE fallback strategy defined in Acceptance Criteria handles all three cases. Data engineer may override with a different strategy if preferred.

---

**REQ-007.1**
Type: FR
Priority: P0
Section: Data Warehouse Design
Statement: The data warehouse must implement a `dim_date` dimension table containing at minimum date key, year, month, day, day of week, and quarter attributes, covering the full Olist dataset date range.
Rationale: Date attributes are required to support time-based filtering and trend analysis.
Acceptance Criteria: `dim_date` exists in the BigQuery `olist_analytics` dataset with `date_key` as primary key and columns for `year`, `month`, `day`, `day_of_week`, and `quarter`. The table covers at minimum the full Olist order date range (2016–2018). Data engineer may modify schema detail as required per ASMP-004.
Dependencies: REQ-004.1
Source: `technical_report.md` §Schema Design; ASMP-004
Open Items: NONE

---

**REQ-008.1**
Type: FR
Priority: P0
Section: Data Warehouse Design
Statement: The data warehouse must implement a `fct_sales` fact table at order item granularity, containing at minimum order identifier, order item identifier, customer unique identifier, product identifier, seller identifier, date key, order status, price, freight value, the derived column `total_sale_amount`, and the delivery timestamp columns `order_delivered_customer_date` and `order_estimated_delivery_date`.
Rationale: Transaction-level data at order item granularity is required to support product-level sales analysis and reporting. Delivery timestamps are promoted from `stg_orders` into `fct_sales` to keep the analytics layer self-sufficient — notebooks must not query staging models for delivery analysis. `order_payment_value` has been removed from `fct_sales` — see Open Items.
Acceptance Criteria: `fct_sales` exists in the BigQuery `olist_analytics` dataset with foreign keys referencing `dim_customers` (via `customer_unique_id`), `dim_products` (via `product_id`), `dim_sellers` (via `seller_id`), and `dim_date` (via `date_key`). All listed columns are present. `date_key` is derived from `order_purchase_timestamp` per ASMP-022 note — see Open Items. `total_sale_amount` = price + freight_value (item-level). `order_delivered_customer_date` and `order_estimated_delivery_date` are NULLABLE TIMESTAMP columns sourced from `stg_orders` — null for non-delivered orders. **These are order-level attributes on an item-level fact table; they repeat across all item rows for the same order_id. Any delivery metric query must use `COUNT(DISTINCT order_id)` — not `COUNT(*)` — to avoid double-counting multi-item orders.** **`customer_unique_id` in `fct_sales` is resolved by joining `stg_orders.customer_id` → `stg_customers.customer_unique_id`** — do not pass `customer_id` through directly; `stg_orders` carries the order-scoped `customer_id`, which has no FK relationship to `dim_customers`. Data engineer may modify schema detail as required per ASMP-004.
Dependencies: REQ-004.1; REQ-005.1; REQ-006.1; REQ-007.1; REQ-051.1
Source: `technical_report.md` §Schema Design; ASMP-003; ASMP-004; ASMP-005
Open Items: (1) `date_key` in `fct_sales` is derived from `order_purchase_timestamp` — the only timestamp guaranteed non-null across all order statuses and representing the moment the business transaction was committed. This decision is recorded here. Data engineer may override with documented rationale per ASMP-004. (2) `order_payment_value` has been removed from `fct_sales`. It was defined as SUM(payment_value) per order_id from fct_payments — an order-level aggregate on an item-level fact table. In a 9,803 multi-item orders dataset this produces repeated order-level values across item rows, causing silent double/triple-counting if any analyst runs SUM(order_payment_value). Payment totals per order are available by querying `fct_payments` directly. This decision is intentional and final; document in `changelog.md` as a deviation from the initial design. (3) ~~**[BLOCKING — DE DECISION REQUIRED]** `date_key` data type — resolved. Confirmed type: **`DATE`** (e.g., `2017-01-15`). Rationale: `dbt_utils.date_spine` produces a `date_day` column of type DATE natively — no casting required in `dim_date`. Staging models derive `date_key` via `DATE(CAST(timestamp AS TIMESTAMP))`. FK joins across all three fact tables work natively with same-type comparison. INTEGER (YYYYMMDD) would require additional casting in both `dim_date` and all staging models with no analytical benefit in BigQuery. STRING discarded — no semantic value, unreliable range comparisons. REQ-017.1 `date_key` range test unblocked — see REQ-017.1.~~ Closed 2026-03-11.

---

**REQ-009.1**
Type: CON
Priority: P0
Section: Data Warehouse Design
Statement: The star schema must be implemented in Google BigQuery via dbt models.
Rationale: dbt is the confirmed transformation tool for producing the star schema from raw source data.
Acceptance Criteria: All star schema tables (`fct_sales`, `fct_reviews`, `fct_payments`, `dim_customers`, `dim_products`, `dim_sellers`, `dim_date`) are produced by dbt models targeting the BigQuery `olist_analytics` dataset. No manual SQL scripts are used to produce the final schema.
Dependencies: REQ-004.1
Source: ASMP-002; ASMP-003
Open Items: NONE

---

**REQ-051.1**
Type: FR
Priority: P0
Section: Data Warehouse Design
Statement: The data warehouse must implement a `dim_sellers` dimension table containing at minimum seller identifier, zip code prefix, city, state, and geolocation coordinates.
Rationale: Seller attributes are required to support seller-level analysis, geographic seller distribution, and seller performance metrics. `seller_id` is present in `fct_sales` and requires a corresponding dimension table for referential integrity and analytical joins.
Acceptance Criteria: `dim_sellers` exists in the BigQuery `olist_analytics` dataset with `seller_id` as primary key and columns for `seller_zip_code_prefix`, `seller_city`, `seller_state`, `geolocation_lat`, and `geolocation_lng` (the latter two sourced from stg_geolocation per REQ-054.1, nullable where no geolocation match exists). Data engineer may modify schema detail as required per ASMP-004.
Dependencies: REQ-004.1; REQ-054.1
Source: ASMP-020; user confirmation (CRIT-02 resolution)
Open Items: NONE

---

**REQ-052.1**
Type: FR
Priority: P0
Section: Data Warehouse Design
Statement: The data warehouse must implement a `fct_reviews` fact table at review granularity, containing at minimum review identifier, order identifier, review score, review comment fields, review creation date, and date key.
Rationale: Customer review data is required to support satisfaction analysis and the delivery time vs. review score correlation metric confirmed in scope per ASMP-008.
Acceptance Criteria: `fct_reviews` exists in the BigQuery `olist_analytics` dataset with `review_id` as primary key. `order_id` links to `stg_orders` (not `fct_sales` — 756 of the 775 itemless orders have review records; these orders do not appear in `fct_sales` because `fct_sales` is at order-item granularity). `date_key` is derived from `review_creation_date` referencing `dim_date`. `review_score` (integer 1–5), `review_comment_title` (nullable), and `review_comment_message` (nullable) are present. **`stg_reviews` must deduplicate on `review_id` before `fct_reviews` is built** — the source `olist_order_reviews_dataset.csv` contains 789 duplicate `review_id` values. Deduplication strategy: retain the row with the latest `review_answer_timestamp` per `review_id` (using `ROW_NUMBER() OVER (PARTITION BY review_id ORDER BY review_answer_timestamp DESC)`). Without this deduplication the dbt `unique` test on `fct_reviews.review_id` will fail. Data engineer may modify schema detail as required per ASMP-004.
Dependencies: REQ-004.1; REQ-007.1
Source: ASMP-020; ASMP-021; EDA-Q4 user confirmation
Open Items: 789 duplicate `review_id` values confirmed in source data (profiled against raw_data/). 547 orders have multiple review records (max 3 reviews per order). Deduplication in `stg_reviews` is mandatory before `fct_reviews` is built.

---

**REQ-053.1**
Type: FR
Priority: P0
Section: Data Warehouse Design
Statement: The data warehouse must implement a `fct_payments` fact table at payment-method granularity, containing at minimum order identifier, payment sequential number, payment type, payment installments, payment value, and date key.
Rationale: Payment method data is required to support payment method distribution analysis and installment behaviour analysis confirmed in scope per ASMP-008 and ASMP-021.
Acceptance Criteria: `fct_payments` exists in the BigQuery `olist_analytics` dataset. The compound key is (`order_id`, `payment_sequential`). `date_key` is derived by joining to `stg_orders` on `order_id` to obtain `order_purchase_timestamp`, then referencing `dim_date`. `payment_type`, `payment_installments`, and `payment_value` are present. Data engineer may modify schema detail as required per ASMP-004.
Dependencies: REQ-004.1; REQ-007.1
Source: ASMP-020; ASMP-021; CL-4 user confirmation
Open Items: NONE

---

## Section 3 — ELT Pipeline

---

**REQ-010.1**
Type: FR
Priority: P0
Section: ELT Pipeline
Statement: The ELT pipeline must transform raw source data from the BigQuery `olist_raw` dataset into the star schema in the BigQuery `olist_analytics` dataset using dbt.
Rationale: Raw data must be cleaned, structured, and loaded into the star schema before analysis can occur.
Acceptance Criteria: All 9 raw source tables in the BigQuery `olist_raw` dataset have defined lineage paths per REQ-012.1 and are transformed via dbt models. No raw tables are directly referenced in downstream analysis or reporting.
Dependencies: REQ-001.2; REQ-004.1; REQ-009.1
Source: `requirements.md` §3; ASMP-003; ASMP-020
Open Items: NONE

---

**REQ-011.1**
Type: FR
Priority: P0
Section: ELT Pipeline
Statement: The ELT pipeline must implement a staging layer consisting of dbt staging models that clean and validate raw source data prior to final schema production. Staging models must exist for each raw source table included in the defined lineage (REQ-012.1).
Rationale: A staging layer ensures data quality and consistency before raw data is loaded into the star schema.
Acceptance Criteria: dbt staging models exist for all 9 raw source tables per REQ-012.1. Staging models perform at minimum column renaming, type casting, and null handling. Final star schema tables are produced from staging models, not directly from raw tables. **All columns arrive from BigQuery `olist_raw` as STRING per ASMP-028 — explicit type casts are mandatory in every staging model for timestamps, floats, and integers; no column type can be assumed from the raw layer.**
Dependencies: REQ-010.1
Source: ASMP-003; ASMP-020
Open Items: 775 orders in `olist_orders_dataset.csv` have no corresponding rows in `olist_order_items_dataset.csv` (603 `unavailable`, 164 `canceled`, 5 `created`, 2 `invoiced`, 1 `shipped`). Since `fct_sales` is at order-item granularity, these 775 orders will not appear in `fct_sales` — this is correct and expected behaviour. Document this in the `stg_orders` model description so the team understands the intentional row count gap between total orders (99,441) and `fct_sales` records.

---

**REQ-012.1**
Type: FR
Priority: P0
Section: ELT Pipeline
Statement: The ELT pipeline must implement the following complete data lineage path:

- `olist_raw.customers` → `stg_customers` → `dim_customers`
- `olist_raw.products` + `olist_raw.product_category_name_translation` → `stg_products` → `dim_products`
- `olist_raw.sellers` → `stg_sellers` → `dim_sellers`
- `olist_raw.geolocation` → `stg_geolocation` → `dim_customers` (lat/lng enrichment), `dim_sellers` (lat/lng enrichment)
- `olist_raw.orders` → `stg_orders` → `fct_sales`
- `olist_raw.order_items` → `stg_order_items` → `fct_sales`
- `stg_customers` → `fct_sales` (resolves `customer_unique_id` via `stg_orders.customer_id` → `stg_customers.customer_unique_id`)
- `olist_raw.order_payments` → `stg_payments` → `fct_payments`
- `stg_orders` → `fct_payments` (provides `date_key` via `order_purchase_timestamp`)
- `olist_raw.order_reviews` → `stg_reviews` → `fct_reviews`
- (generated via `GENERATE_DATE_ARRAY()` or `dbt_utils.date_spine`, covering 2016–2018) → `dim_date`

Rationale: Documented lineage ensures complete traceability from all 9 source tables to the final schema and supports data quality verification.
Acceptance Criteria: All lineage paths listed in the statement are implemented as dbt model dependencies. The dbt lineage graph reflects the documented path without gaps or untracked transformations. `stg_geolocation` produces one row per zip_code_prefix with averaged lat/lng coordinates; enrichment joins into `dim_customers` and `dim_sellers` are LEFT JOINs (nullable where no match exists). Data engineer may modify lineage as required upon actual dataset analysis per ASMP-004.
Dependencies: REQ-010.1; REQ-011.1
Source: ASMP-003; ASMP-004; ASMP-020
Open Items: (1) ~~dim_date generation method — resolved. Confirmed: `dbt_utils.date_spine(datepart="day", start_date="cast('2016-01-01' as date)", end_date="cast('2018-12-31' as date)")`. Range covers first order (2016-09-04) through last (2018-10-17) with buffer; review and delivery dates may extend beyond the last order date. `dbt_utils` is already a declared package dependency. DE may override with documented rationale per ASMP-004.~~ Closed 2026-03-11. (2) `sources.yml` must reference BigQuery `olist_raw` table names exactly as produced by Meltano per ASMP-001 naming convention — verify table names exist in BigQuery `olist_raw` before running `dbt build`.

---

**REQ-013.1**
Type: FR
Priority: P1
Section: ELT Pipeline
Statement: The ELT pipeline must implement `total_sale_amount` as a derived column in `fct_sales` per ASMP-005.
Rationale: `total_sale_amount` (price + freight_value at item level) is required for product revenue attribution and top-selling product analysis (REQ-022.1, ASMP-009). It is the primary revenue metric in this pipeline.
Acceptance Criteria: `total_sale_amount` = price + freight_value is present in `fct_sales`, produced by a dbt model, and documented in `schema.yml`. Data engineer may add additional derived columns at discretion.
Dependencies: REQ-010.1; REQ-011.1
Source: `requirements.md` §3; ASMP-005
Open Items: `order_payment_value` has been removed from scope per REQ-008.1 Open Items. Order-level payment totals are available directly from `fct_payments` — no derived column in `fct_sales` is needed.

---

**REQ-014.1**
Type: CON
Priority: P0
Section: ELT Pipeline
Statement: The ELT pipeline must use dbt as the sole transformation tool targeting Google BigQuery.
Rationale: dbt was confirmed as the transformation tool for this project.
Acceptance Criteria: All transformation logic is implemented as dbt models. No custom SQL transformation scripts outside of dbt are present in the repository.
Dependencies: REQ-010.1
Source: ASMP-003
Open Items: NONE

---

**REQ-054.1**
Type: FR
Priority: P1
Section: ELT Pipeline
Statement: The ELT pipeline must implement geolocation enrichment by joining averaged lat/lng coordinates from `stg_geolocation` into `dim_customers` and `dim_sellers` via zip code prefix.
Rationale: Lat/lng coordinates are required for map-based geographic analysis in the Streamlit dashboard (Geographic Analysis view, REQ-024.1). Customer and seller geographic data without coordinates cannot support precise map rendering.
Acceptance Criteria: `stg_geolocation` produces one row per `geolocation_zip_code_prefix` with `avg_lat` and `avg_lng` (averaged across all rows per prefix). **Before aggregating, `stg_geolocation` must filter source rows to Brazil's bounding box (`geolocation_lat BETWEEN -35 AND 5` AND `geolocation_lng BETWEEN -75 AND -34`)** — the source data contains 29–37 coordinate outliers with values as far as +45° lat (France) and +121° lng (China); including these in the AVG() would produce wrong coordinates for affected zip prefixes and corrupt map rendering in the Streamlit dashboard. `dim_customers` contains `geolocation_lat` and `geolocation_lng` joined via `customer_zip_code_prefix` (LEFT JOIN — nullable). `dim_sellers` contains `geolocation_lat` and `geolocation_lng` joined via `seller_zip_code_prefix` (LEFT JOIN — nullable).
Dependencies: REQ-011.1; REQ-012.1; REQ-005.1; REQ-051.1
Source: ASMP-020; geographic analysis scope
Open Items: 29–37 coordinate outliers confirmed in `olist_geolocation_dataset.csv` (profiled against raw_data/). Pre-aggregation bounding-box filter is mandatory.

---

## Section 4 — Data Quality Testing

---

**REQ-015.1**
Type: FR
Priority: P0
Section: Data Quality Testing
Statement: The pipeline must implement data quality tests using two complementary dbt mechanisms: (1) dbt-expectations generic tests declared in `schema.yml` for column-level and table-level validations, and (2) dbt singular tests (custom SQL files in `tests/`) for conditional logic and cross-table assertions. Both mechanisms target the BigQuery `olist_analytics` dataset.
Rationale: Generic tests (dbt-expectations) co-locate validations with model documentation and use a declarative syntax for common patterns. Singular tests retain full SQL expressiveness for conditional and cross-table rules. Together they provide complete coverage. Both execute under `dbt test`, satisfying REQ-019.1 without a separate test runner. The inclusion of dbt-expectations satisfies the Great Expectations requirement in `requirements.md` §4 per ASMP-024.
Acceptance Criteria: dbt-expectations is declared in `packages.yml` and installed. Generic tests are declared in `schema.yml` files for all analytics schema models. Singular test SQL files exist in `tests/` for cross-table and conditional assertions. All tests execute via `dbt test` and produce a pass/fail result. No untested tables exist in the `olist_analytics` dataset.
Dependencies: REQ-010.1; REQ-011.1; ASMP-024
Source: `requirements.md` §4; ASMP-002; ASMP-024
Open Items: NONE

---

**REQ-016.1**
Type: FR
Priority: P0
Section: Data Quality Testing
Statement: The pipeline must implement referential integrity tests verifying that all foreign key values in `fct_sales` exist in their respective dimension tables, using two mechanisms: dbt built-in `relationships` tests for existence checks, and dbt singular tests for quantified violation counts.
Rationale: The dbt `relationships` generic test confirms existence of FK values in the target dimension but does not quantify violations. Singular SQL tests are required to produce a count of violations, enabling prioritisation and downstream debugging. Both mechanisms are needed for complete FK integrity assurance.
Acceptance Criteria: dbt `relationships` generic tests are declared in `schema.yml` for all FK columns across all fact tables: `fct_sales` — `customer_unique_id` → `dim_customers`, `product_id` → `dim_products`, `seller_id` → `dim_sellers`, `date_key` → `dim_date`; `fct_payments` — `date_key` → `dim_date`. Note: `fct_reviews.order_id → stg_orders` is a cross-layer FK handled as a `relationships` test in `fct_reviews` schema.yml targeting `ref('stg_orders')` per REQ-017.1 — it is not included here because it targets a staging model, not a mart. Corresponding singular SQL tests produce a quantified count of integrity violations per FK for `fct_sales`. Zero violations is the passing condition for all FK tests.
Dependencies: REQ-015.1; REQ-004.1; REQ-051.1
Source: ASMP-002; CRIT-02 resolution
Open Items: NONE

---

**REQ-017.1**
Type: FR
Priority: P0
Section: Data Quality Testing
Statement: The pipeline must implement business logic tests against the BigQuery `olist_analytics` dataset. Column-level rules are implemented as dbt-expectations generic tests in `schema.yml`. Conditional and cross-table rules are implemented as dbt singular tests in `tests/`.
Rationale: Business logic tests verify that data conforms to expected domain rules beyond structural integrity. dbt-expectations generic tests are the recommended mechanism for column-level rules — they are declarative, co-located with model documentation, and self-documenting. Singular SQL tests handle rules that require conditional logic (e.g., boleto installments) or cross-table joins (e.g., financial reconciliation).
Acceptance Criteria: The following confirmed business logic tests are implemented. Data engineer may add additional tests at their discretion.

**`stg_orders` (staging layer — temporal logic)**
- `order_status` in `['delivered','shipped','canceled','unavailable','invoiced','processing','approved','created']` — dbt-expectations generic
- `order_purchase_timestamp` not null — dbt built-in
- `order_approved_at` ≥ `order_purchase_timestamp` (where not null) — dbt-expectations pair test
- `order_delivered_carrier_date` ≥ `order_purchase_timestamp` (where not null) — dbt-expectations pair test
- `order_delivered_customer_date` ≥ `order_delivered_carrier_date` (where both not null) — dbt-expectations pair test
- `order_estimated_delivery_date` ≥ `order_purchase_timestamp` — dbt-expectations pair test

**`fct_sales`**
- `price` > 0 — dbt-expectations generic
- `freight_value` ≥ 0 — dbt-expectations generic
- `total_sale_amount` > 0 — dbt-expectations generic
- `total_sale_amount` = `price` + `freight_value` within tolerance 0.01 — singular SQL
- `order_item_id` ≥ 1 — dbt-expectations generic
- `order_status` in confirmed set — dbt-expectations generic
- Row count between 90,000 and 200,000 — dbt-expectations table-level

**`fct_reviews`**
- `review_score` between 1 and 5 — dbt-expectations generic
- `review_answer_timestamp` ≥ `review_creation_date` — dbt-expectations pair test
- Every `order_id` in `fct_reviews` exists in `stg_orders` — singular SQL (note: `fct_sales` cannot be the FK target because 756 itemless orders have reviews but no `fct_sales` rows)
- Row count between 95,000 and 100,000 — dbt-expectations table-level (`expect_table_row_count_to_be_between`). Source has 99,224 reviews; after dedup of 789 duplicate `review_id` values expected output is ~98,435. Lower bound of 95,000 catches over-aggressive dedup logic (e.g., partitioning on `order_id` instead of `review_id`).

**`fct_payments`**
- `payment_value` ≥ 0 — dbt-expectations generic (zero is valid for secondary voucher payments on multi-payment orders; 6 such records confirmed in source data; no negative values exist)
- `payment_type` in `['credit_card','boleto','voucher','debit_card']` — dbt-expectations generic
- `payment_installments` between 1 and 24 — dbt-expectations generic
- `payment_sequential` ≥ 1 — dbt-expectations generic
- `boleto` payment type always has `payment_installments` = 1 — singular SQL
- SUM(`payment_value`) per `order_id` reconciles to order-level total within R$1.00 tolerance — singular SQL

Note: `stg_payments` must apply two source data corrections before `fct_payments` is built: (1) Filter rows where `payment_type = 'not_defined'` — 3 such rows exist in source data, all with `payment_value = 0.00`; they are error/test records with no business value. (2) Clamp `payment_installments = 0` to `1` via `GREATEST(payment_installments, 1)` — 2 credit_card rows in source data carry 0 installments, which is semantically invalid. These staging fixes ensure the `payment_type` accepted-values test and `payment_installments ≥ 1` test reflect genuine business violations rather than known source defects.

**`dim_customers` / `dim_sellers`**
- `customer_state` / `seller_state` in 27 valid Brazilian state codes — dbt-expectations generic
- `customer_zip_code_prefix` / `seller_zip_code_prefix` matches `^[0-9]{5}$` — dbt-expectations generic
- `geolocation_lat` between -35 and 5 — dbt-expectations generic
- `geolocation_lng` between -75 and -34 — dbt-expectations generic

**`dim_products`**
- `product_category` not null (confirms COALESCE fallback in stg_products produced a value for every product) — dbt built-in
- `product_name_length` not null — dbt built-in (confirms DEF-009 rename from `product_name_lenght` was applied in `stg_products`)
- `product_description_length` not null — dbt built-in (confirms DEF-009 rename from `product_description_lenght` was applied in `stg_products`)

**`dim_date`**
- `month` between 1 and 12, `day` between 1 and 31, `day_of_week` between 1 and 7, `quarter` between 1 and 4 — dbt-expectations generic

Dependencies: REQ-015.1; ASMP-024
Source: `requirements.md` §4; ASMP-007; ASMP-024
Open Items: ~~`date_key` range test deferred pending type confirmation — unblocked. Confirmed type: DATE. Test implementation: `expect_column_values_to_be_between(column_name='date_key', min_value='2016-01-01', max_value='2018-12-31')` in `dim_date` schema.yml. All three fact table `date_key` FK columns are DATE type — consistent with `dim_date.date_key`.~~ Closed 2026-03-11.

---

**REQ-018.1**
Type: FR
Priority: P1
Section: Data Quality Testing
Statement: The pipeline must implement null value and duplicate tests against the BigQuery `olist_analytics` dataset. PK and FK columns use binary `not_null` and `unique` tests. Known sparse columns use dbt-expectations `expect_column_values_to_not_be_null` with a `mostly` threshold to avoid false positives.
Rationale: Binary `not_null` tests are appropriate for structural columns (PKs, FKs, mandatory fields) where any null is a data quality failure. Sparse columns with legitimately nullable data (e.g., review comments, geolocation coordinates from a LEFT JOIN) require threshold-based null testing — a binary `not_null` test would produce constant false positives for these columns.
Acceptance Criteria: All PK columns have `unique` + `not_null` tests. All FK columns have `not_null` tests. The following sparse columns use `expect_column_values_to_not_be_null` with the specified `mostly` thresholds: `fct_reviews.review_comment_title` (0.08), `fct_reviews.review_comment_message` (0.40), `dim_customers.geolocation_lat` and `geolocation_lng` (0.97), `dim_sellers.geolocation_lat` and `geolocation_lng` (0.97). Thresholds may be adjusted by data engineer after profiling actual data distribution. All tests execute via `dbt test`. **Threshold calibration evidence (from `docs/data_profile.json` test_thresholds section):** `review_comment_title` is 88.3% null (11.7% non-null) → threshold 0.08 catches genuine degradation with margin; `review_comment_message` is 58.7% null (41.3% non-null) → threshold 0.40 matches actual fill rate; geolocation row-level match is 99.7% for customers and 99.8% for sellers → threshold 0.97 gives meaningful signal on join quality degradation.
Dependencies: REQ-015.1; ASMP-024
Source: `requirements.md` §4; ASMP-006; ASMP-024
Open Items: NONE — thresholds calibrated from `docs/data_profile.json` test_thresholds section.

---

**REQ-019.1**
Type: NFR
Priority: P1
Section: Data Quality Testing
Statement: All data quality tests must be executable via the single command `dbt test` from the dbt project directory.
Rationale: A single executable command ensures tests can be run consistently by any team member without manual coordination.
Acceptance Criteria: Running `dbt test` from the dbt project directory executes all data quality tests in sequence and produces a consolidated pass/fail report. All tests complete without manual intervention.
Dependencies: REQ-015.1
Source: `requirements.md` §4; SIG-05 resolution
Open Items: NONE

---

## Section 5 — Data Analysis with Python

---

**REQ-020.2**
Type: FR
Priority: P0
Section: Data Analysis with Python
Statement: The Jupyter notebook analysis layer must use SQLAlchemy as the connector to Google BigQuery for all data retrieval operations. The Streamlit dashboard is exempt from this requirement — it retrieves data from persisted Parquet files per REQ-025.1.
Rationale: SQLAlchemy is the confirmed connector method between the Python analysis layer and BigQuery. Streamlit reads from Parquet files to decouple the dashboard from live BigQuery queries.
Acceptance Criteria: All data retrieval in Jupyter notebooks uses SQLAlchemy as the BigQuery connector. Connection is verified by successfully executing at least one query against the `olist_analytics` dataset. Streamlit dashboard reads exclusively from Parquet files.
Dependencies: REQ-003.1; REQ-008.1
Source: `requirements.md` §5; CRIT-03 resolution
Open Items: NONE

---

**REQ-021.1**
Type: FR
Priority: P0
Section: Data Analysis with Python
Statement: The analysis layer must perform exploratory data analysis using pandas against data retrieved from Google BigQuery.
Rationale: pandas is explicitly named in the project brief as the required tool for exploratory data analysis.
Acceptance Criteria: A Jupyter notebook exists in the repository containing pandas-based EDA. EDA must include at minimum descriptive statistics and at least one data visualisation per analytical area. All data is retrieved from the BigQuery `olist_analytics` dataset via SQLAlchemy per REQ-020.2.
Dependencies: REQ-020.2
Source: `requirements.md` §5
Open Items: NONE

---

**REQ-022.1**
Type: FR
Priority: P0
Section: Data Analysis with Python
Statement: The analysis layer must calculate and present eleven business metrics across three analytical notebooks. Six mandated metrics: (1) monthly sales trends, (2) top-selling products by revenue, (3) RFM customer segmentation, (4) delivery performance, (5) review/satisfaction analysis, (6) payment method analysis. Five additional confirmed metrics: (7) Average Order Value (AOV) trend, (8) fulfilment/cancellation rate by status, (9) NPS proxy, (10) seller performance summary, (11) regional e-commerce penetration. All metrics derived from the BigQuery `olist_analytics` dataset.
Rationale: Eleven metrics covering growth, efficiency, quality, and retention KPIs provide complete business intelligence coverage of the Olist dataset. Regional analysis leverages Brazil's 5 official regional divisions to identify penetration gaps and growth opportunities. Per ASMP-008 and ASMP-025.
Acceptance Criteria: All eleven metrics are calculated and documented across three analytical notebooks as follows — `01_sales_analysis.ipynb`: metrics 1, 2, 6, 7, 8. `02_customer_analysis.ipynb`: metrics 3, 5, 9, plus delay × review score correlation (REQ-057.1). `03_geo_seller_analysis.ipynb`: metrics 4 (all delivery KPIs — on-time rate, avg delay, regional breakdown), 10, 11. Delivery performance is consolidated entirely in notebook 3; notebook 2 uses per-order delivery delay data only for the correlation analysis, not as a KPI output. Trend analyses use observation window `2017-01-01` to `2018-08-31` per ASMP-025 — exclude September and October 2018 data cut artefacts. All data retrieved from the BigQuery `olist_analytics` dataset mart tables via SQLAlchemy per REQ-020.2 — staging models are not queried from notebooks. Implementation details per REQ-055.1 through REQ-058.1.
Dependencies: REQ-021.1; ASMP-025
Source: `requirements.md` §5; ASMP-008; ASMP-009
Open Items: NONE

---

**REQ-023.1**
Type: FR
Priority: P0
Section: Data Analysis with Python
Statement: The repository must contain Jupyter notebooks with analysis performed against the BigQuery `olist_analytics` dataset.
Rationale: Jupyter notebooks are an explicitly required deliverable in the project brief.
Acceptance Criteria: Four Jupyter notebooks exist in the repository. (1) `00_eda.ipynb` — exploratory notebook; free-form analytics schema verification and distribution checks against the Gold layer; informs analytical choices documented in notebooks 1–3; not required to produce Parquet output. (2–4) `01_sales_analysis.ipynb`, `02_customer_analysis.ipynb`, `03_geo_seller_analysis.ipynb` — analytical notebooks; each is fully self-contained (no cross-notebook variable dependencies); each connects to BigQuery via SQLAlchemy per REQ-020.2, calculates its assigned metrics per REQ-022.1, and exports at least one Parquet file per REQ-025.1. Each analytical notebook opens with a markdown cell referencing the relevant `00_eda.ipynb` findings that informed its design. All three analytical notebooks run end-to-end without errors against the `olist_analytics` dataset. `notebooks/utils.py` exists at the `notebooks/` directory and imports cleanly with no Streamlit dependency — it must provide: `REGION_MAP` (27 states + DF mapped to 5 regions), `SEGMENT_COLOURS` (6 RFM segment colours), `REGION_COLOURS` (5 region colours), `STATUS_COLOURS` (8 order status colours), and `add_region(df, state_col)` helper. All three analytical notebooks, `scripts/generate_parquet.py` (if committed), and `dashboard_utils.py` import from this module — import failure cascades to all downstream consumers.
Dependencies: REQ-020.2; REQ-021.1; REQ-022.1
Source: `requirements.md` Deliverables
Open Items: Notebook execution requires active BigQuery credentials configured per ASMP-015. The local run setup document (REQ-036.1) must include credential setup instructions. Evaluators are assumed to have access to the shared service account key.

---

**REQ-024.1**
Type: FR
Priority: P1
Section: Data Analysis with Python
Statement: The analysis layer must include an interactive Streamlit dashboard providing four views — Executive Overview, Product Performance, Geographic Analysis, and Customer Analysis — with global filters for Date Range, Product Category, Customer State, and Customer Region.
Rationale: An interactive dashboard makes analytical findings accessible to business and technical stakeholders beyond static notebook outputs, and supports deployment on Streamlit Community Cloud. Customer Region (Brazil's 5 official regions) is added as a fourth global filter to support the regional e-commerce penetration analysis (metric 11, REQ-022.1) — Customer State alone produces an unwieldy 27-item dropdown and does not support region-level business questions.
Acceptance Criteria: `dashboard.py` exists at the repository root and runs without errors via `streamlit run dashboard.py`. Dashboard uses Streamlit multi-page architecture per ASMP-027: `dashboard.py` is a thin entry point; four page files exist at `pages/1_Executive.py`, `pages/2_Products.py`, `pages/3_Geographic.py`, `pages/4_Customers.py`; `dashboard_utils.py` at project root provides `@st.cache_data` Parquet loader functions for all 5 Parquet files and `init_filters()` which initialises `st.session_state` keys per ASMP-027 — all four page files call `init_filters()` at the top; if this file is missing or broken all four pages fail. The four views are named: Executive Overview, Product Performance, Geographic Analysis, and Customer Analysis. Global filters for Date Range, Product Category, Customer State, and Customer Region are functional in the sidebar and persist across page navigation via `st.session_state`. Filter applicability per view follows ASMP-027 — inapplicable filters show `st.caption()` notes rather than being hidden. Empty multi-select filter = show all. All data sourced from persisted Parquet files per REQ-025.1. Headline KPI metrics displayed via `st.metric()` at the top of each view. Charts rendered via `st.plotly_chart(fig, use_container_width=True)`. A dashboard user guide per REQ-050.1 documents each view and filter behaviour.
Dependencies: REQ-022.1; REQ-025.1; REQ-055.1; REQ-056.1; REQ-057.1; REQ-058.1
Source: ASMP-019; ASMP-027; EDA-Q2 user confirmation; BRD review 2026-03-10
Open Items: NONE

---

**REQ-025.1**
Type: FR
Priority: P0
Section: Data Analysis with Python
Statement: The analysis layer must persist final feature datasets as five Parquet files committed to the `data/` directory in the repository root for use by the Streamlit dashboard on Streamlit Community Cloud.
Rationale: Parquet files committed to the repository are the data source for Streamlit Community Cloud deployment, which cannot rely on live BigQuery queries. The files represent the final datasets produced by the analysis layer per ASMP-016. A single `data/` path convention ensures notebooks (export) and `dashboard.py` (import) reference the same location without path mismatches.
Acceptance Criteria: Five Parquet files and one GeoJSON file are committed to `data/` in the repository root. The GeoJSON file `data/brazil_states.geojson` contains Brazilian state boundaries with feature IDs matching two-letter state codes (e.g., `"SP"`) for use in `px.choropleth`. Five Parquet files are committed to `data/` in the repository root: (1) `data/sales_orders.parquet` — order-item granularity (~112k rows); columns include year, month, product_category, customer_state, customer_region, total_sale_amount, order_status, primary_payment_type, primary_payment_installments; produced by `01_sales_analysis.ipynb`. (2) `data/customer_rfm.parquet` — customer granularity (~96k rows); RFM scores, named segment, customer_state, customer_region; produced by `02_customer_analysis.ipynb`. (3) `data/satisfaction_summary.parquet` — order granularity (~97k rows); review_score, nps_bucket, delay_days, is_on_time, primary_product_category, customer_state, customer_region, year, month; produced by `02_customer_analysis.ipynb`. (4) `data/geo_delivery.parquet` — customer_state × month granularity (~540 rows); on_time_rate, avg_delay_days, customer_region, year, month; produced by `03_geo_seller_analysis.ipynb`. (5) `data/seller_performance.parquet` — seller granularity (~3k rows); gmv, order_count, cancellation_rate, avg_review_score, seller_state, seller_region; produced by `03_geo_seller_analysis.ipynb`. Total estimated size ~15MB — Git LFS not required. `primary_payment_type` uses `payment_sequential = 1` per order (approximation for 2,961 split-payment orders, ~3% of total — documented in dashboard user guide). `primary_product_category` is the category of the highest-revenue item per order. `customer_region` and `seller_region` derived from `notebooks/utils.py` REGION_MAP — single canonical source used by all notebooks and `dashboard.py`. All notebooks export to `data/` using relative paths. `dashboard.py` reads from `data/` using relative paths. Parquet files must be committed — do not add to `.gitignore`.
Dependencies: REQ-022.1; REQ-024.1
Source: ASMP-016; ASMP-027; CL-4 resolution; user confirmation; BRD review 2026-03-10
Open Items: `data/brazil_states.geojson` source is codeforamerica/click_that_hood (27 features; 2-letter state code in `properties.sigla`). File must be downloaded and committed to the repository — do not fetch at runtime. `featureidkey` confirmed as `properties.sigla` — verified against `data/brazil_states.geojson` (field: `"sigla": "AC"` for Acre). Use `featureidkey="properties.sigla"` in all `px.choropleth` calls. A convenience script `scripts/generate_parquet.py` may be provided by the Data Analyst as an alternative Parquet generation path for quick setup (usage: `python scripts/generate_parquet.py --project <gcp_project_id>`). If committed, it must produce output identical to running `01_sales_analysis.ipynb`, `02_customer_analysis.ipynb`, and `03_geo_seller_analysis.ipynb` in sequence. The local run setup document (REQ-036.1) must document this as the alternative to full notebook execution.

---

**REQ-055.1**
Type: FR
Priority: P0
Section: Data Analysis with Python
Statement: The analysis layer must implement RFM (Recency, Frequency, Monetary) customer segmentation using `customer_unique_id` as the customer identifier, following the full specification in ASMP-022.
Rationale: RFM segmentation is the industry-standard e-commerce customer segmentation method and is directly calculable from the Olist dataset. It produces business-actionable segments for the executive presentation. The reference date and scoring methodology are fixed to ensure reproducibility — see ASMP-022 and ASMP-025.
Acceptance Criteria: (1) RFM reference date is hardcoded as `2018-08-31` per ASMP-022 — not derived from `CURRENT_DATE` or `MAX(order_purchase_timestamp)`. (2) Recency scored as quintiles (1–5); lower days = higher score. (3) Frequency scored as 3-tier: F1 = 1 order, F2 = 2 orders, F3 = 3+ orders. (4) Monetary scored as quintiles (1–5). (5) Customers assigned to named segments: Champions, Loyal, Promising, At Risk, High Value Lost, Hibernating per ASMP-022 definitions. (6) Repeat purchase rate (% of customers with exactly 1 order) is surfaced as a standalone metric. (7) RFM segment distribution and repeat purchase rate are visualised in `02_customer_analysis.ipynb` and surfaced in the Customer Analysis dashboard view (REQ-024.1). (8) Notebook documents the reference date, observation window, and Frequency tier rationale as inline commentary.
Dependencies: REQ-022.1; ASMP-022; ASMP-025
Source: ASMP-022; EDA-Q1 user confirmation; BRD review 2026-03-10
Open Items: NONE

---

**REQ-056.1**
Type: FR
Priority: P0
Section: Data Analysis with Python
Statement: The analysis layer must implement delivery performance metrics covering on-time delivery rate and average delivery delay.
Rationale: Delivery performance is a primary operational KPI for an e-commerce business and a strong insight for the executive presentation audience.
Acceptance Criteria: All delivery performance metrics are implemented in `03_geo_seller_analysis.ipynb`. On-time delivery rate is calculated as the percentage of orders where `order_delivered_customer_date` ≤ `order_estimated_delivery_date`, restricted to `order_status = 'delivered'`. Average delivery delay is calculated as AVG(`order_delivered_customer_date` - `order_estimated_delivery_date`) for delivered orders. Both headline metrics and regional breakdown (by customer_state mapped to Brazil's 5 regions per ASMP-008) are produced in this notebook. Delivery timestamps are sourced from `fct_sales` per REQ-008.1 — use `COUNT(DISTINCT order_id)` for all delivery rate calculations. Regional breakdown applies a minimum 30-order threshold — state × month combinations with fewer than 30 delivered orders are suppressed in the heatmap visualisation to avoid statistically misleading rates. Both metrics are visualised in `03_geo_seller_analysis.ipynb` and surfaced in the Geographic Analysis dashboard view.
Dependencies: REQ-022.1; REQ-008.1
Source: EDA-Q3 user confirmation; ASMP-008; BRD review 2026-03-10
Open Items: NONE

---

**REQ-057.1**
Type: FR
Priority: P0
Section: Data Analysis with Python
Statement: The analysis layer must implement review and satisfaction metrics in both the Jupyter notebook and the Streamlit dashboard.
Rationale: `fct_reviews` is a confirmed fact table in scope. Excluding review data from the analysis layer would leave an entire fact table with no downstream analytical use.
Acceptance Criteria: Review analysis includes at minimum: average review score, review score distribution (1–5), and correlation between delivery delay and review score. All metrics are present in the Jupyter notebook and at least one review metric is surfaced in the Streamlit dashboard.
Dependencies: REQ-022.1; REQ-052.1
Source: EDA-Q4 user confirmation; ASMP-008
Open Items: NONE. Dashboard view: Customer Analysis page per ASMP-027. `satisfaction_summary.parquet` is the data source for all review and NPS metrics in that view.

---

**REQ-058.1**
Type: FR
Priority: P0
Section: Data Analysis with Python
Statement: The analysis layer must implement payment method analysis metrics covering payment type distribution and installment behaviour.
Rationale: Payment method analysis is confirmed in scope per ASMP-021. `fct_payments` is a confirmed fact table specifically to support this analysis.
Acceptance Criteria: Payment analysis includes at minimum: distribution of orders by `payment_type` (credit card, boleto, voucher, debit), average number of installments for instalment purchases, and revenue breakdown by payment type. All metrics are present in the Jupyter notebook and surfaced in the appropriate Streamlit dashboard view.
Dependencies: REQ-022.1; REQ-053.1
Source: ASMP-021; CL-4 resolution; ASMP-008
Open Items: NONE. Dashboard view: Executive Overview per ASMP-027. Source: `sales_orders.parquet` columns `primary_payment_type` and `primary_payment_installments` (payment_sequential = 1 per order).

---

## Section 6 — Pipeline Orchestration

---

**REQ-026.1**
Type: FR
Priority: P1
Section: Pipeline Orchestration
Statement: The pipeline must implement Dagster as the orchestration tool to coordinate execution of the ingestion, transformation, and data quality stages. The dbt integration must use the `dagster-dbt` library. The Meltano integration uses a shell command asset invoking `meltano run`.
Rationale: Dagster was confirmed as the orchestration tool for this project per ASMP-010. `dagster-dbt` auto-generates one Dagster asset per dbt model from `manifest.json`, providing granular visibility and native dependency tracking. No official Dagster-Meltano integration exists; shell invocation is the accepted approach.
Acceptance Criteria: A Dagster project exists in the repository. `dagster-dbt` is installed and configured. dbt models are represented as individual Dagster assets auto-generated via `@dbt_assets`. A Meltano ingestion asset is defined that executes `meltano run` and is wired as an upstream dependency of the dbt source assets via declared `AssetKey` specs — the key prefix must match the source name in `sources.yml` (`olist_raw`). A `define_asset_job` wrapping both Meltano and dbt assets exists and is referenced by the schedule — the schedule cannot trigger without an associated job. The dbt profile uses `env_var()` interpolation for `GCP_PROJECT_ID` and `GOOGLE_APPLICATION_CREDENTIALS` — no hardcoded paths. The recommended dbt execution mode is `dbt build` (interleaved model materialisation and test execution in topological order) — this ensures a staging model that fails its tests blocks dependent mart models from running. No partition strategy is used — this is a full-refresh pipeline with `WRITE_TRUNCATE`. All stages are executable via Dagster without manual script invocation.
Dependencies: REQ-001.2; REQ-010.1; REQ-015.1
Source: ASMP-010; ASMP-018
Open Items: NONE

---

**REQ-027.1**
Type: FR
Priority: P1
Section: Pipeline Orchestration
Statement: The pipeline must support both manual execution and daily scheduled execution of all orchestrated stages via Dagster.
Rationale: Manual execution provides on-demand flexibility. The daily schedule reinstates the regular run capability specified in `requirements.md` §6 per ASMP-018.
Acceptance Criteria: All Dagster jobs and assets are executable on demand via the Dagster UI or CLI. A daily schedule at 09:00 is implemented per REQ-028.2. Pipeline completes all stages end-to-end under both execution modes.
Dependencies: REQ-026.1; REQ-028.2
Source: ASMP-010; ASMP-018
Open Items: NONE

---

**REQ-028.1**
*Superseded in v2.0. The constraint prohibiting scheduled runs is removed. See REQ-028.2 and ASMP-018.*

---

**REQ-028.2**
Type: FR
Priority: P1
Section: Pipeline Orchestration
Statement: The pipeline must implement a Dagster schedule that triggers all orchestrated stages daily at 09:00.
Rationale: Regular scheduled runs align with `requirements.md` §6 guidance and ensure the analytics dataset is refreshed daily without manual intervention.
Acceptance Criteria: A Dagster schedule is defined in the repository and triggers the full pipeline job daily at 09:00. The schedule is visible in the Dagster UI. No additional infrastructure beyond Dagster is required to activate the schedule.
Dependencies: REQ-026.1; REQ-027.1
Source: ASMP-010; ASMP-018; Q4 user confirmation
Open Items: Timezone confirmed: `Asia/Singapore` (UTC+8). The Dagster schedule triggers daily at 09:00 SGT. Implementation: `ScheduleDefinition(cron_schedule="0 9 * * *", execution_timezone="Asia/Singapore")` — use `execution_timezone` directly; do not manually convert to UTC. **Schedule execution note:** `dagster dev` starts both webserver and daemon — schedule fires correctly in development. For production-like deployments, both `dagster-webserver` and `dagster-daemon run` must be running; the schedule is visible in the UI if only the webserver runs, but will not trigger without the daemon.

---

**REQ-029.1**
Type: NFR
Priority: P1
Section: Pipeline Orchestration
Statement: The Dagster orchestration layer must provide visibility into pipeline execution status for all orchestrated stages.
Rationale: Execution visibility enables the team to identify and diagnose pipeline failures without inspecting raw logs.
Acceptance Criteria: Dagster UI is accessible during pipeline execution and displays run status, asset materialisation state, and error messages for each stage. All pipeline stages are represented as named assets or jobs with human-readable descriptions in the Dagster UI per REQ-048.1.
Dependencies: REQ-026.1; REQ-048.1
Source: `requirements.md` §6
Open Items: NONE

---

## Section 7 — Documentation

---

**REQ-030.1**
Type: FR
Priority: P0
Section: Documentation
Statement: The repository must contain a pipeline architecture document and a pipeline architecture diagram, both produced by the Platform Engineer. The architecture document provides written justification for the system design. The architecture diagram provides a visual representation of the end-to-end data pipeline, illustrating the flow of data through Meltano, BigQuery, dbt, Dagster, and Streamlit.
Rationale: This merged deliverable (formerly REQ-030.1 and REQ-034.1) captures both the visual system map and the architect's written design recommendations in a single coherent deliverable.
Acceptance Criteria: One architecture document (written) and one architecture diagram (visual) both exist in the `docs/` directory per REQ-049.1. The diagram shows: source CSVs → Meltano → BigQuery `olist_raw` dataset → dbt → BigQuery `olist_analytics` dataset → Jupyter/pandas → Parquet files → Streamlit, with Dagster orchestrating the pipeline stages. The written document covers component interaction design, recommended project structure, integration patterns, and architectural decisions. Both are committed to the main branch.
Dependencies: REQ-001.2; REQ-009.1; REQ-014.1; REQ-026.1
Source: `requirements.md` §7; ASMP-011; CL-1 resolution
Open Items: NONE

---

*REQ-034.1 — Merged into REQ-030.1 in v2.0 per ASMP-011 and CL-1 resolution.*

---

**REQ-031.1**
Type: FR
Priority: P0
Section: Documentation
Statement: The repository must contain a data lineage diagram illustrating the flow of data from all 9 raw source tables through staging models to the final star schema.
Rationale: A data lineage diagram supports traceability and audit of data transformations across all source tables.
Acceptance Criteria: A data lineage diagram exists in `docs/diagrams/` per REQ-049.1. The diagram reflects all lineage paths per REQ-012.1, including the two cross-dependencies that are easy to omit: `stg_customers → fct_sales` (customer_unique_id resolution via stg_orders.customer_id) and `stg_orders → fct_payments` (date_key derivation). Recommended format: Mermaid diagram embedded in `docs/data_lineage.md` — renders natively in GitHub, version-controlled as text, no external tool dependency. The diagram is committed to the main branch.
Dependencies: REQ-012.1; REQ-049.1
Source: `requirements.md` §7
Open Items: NONE

---

**REQ-032.1**
Type: FR
Priority: P0
Section: Documentation
Statement: The repository must contain a star schema diagram illustrating the structure of the `olist_analytics` dataset including all tables, columns, primary keys, and foreign keys.
Rationale: A star schema diagram enables data engineers and analysts to understand the data model without inspecting the database directly.
Acceptance Criteria: A star schema diagram exists in `docs/diagrams/` per REQ-049.1. The diagram reflects the full confirmed schema: `fct_sales`, `fct_reviews`, `fct_payments`, `dim_customers`, `dim_products`, `dim_sellers`, `dim_date`. All PKs and FKs are shown. **Special note:** `fct_reviews.order_id` FK points to `stg_orders` (not a mart table) — the diagram must show this FK with a clear annotation; standard ERD tools assume all FKs stay within the mart layer and will omit or misdirect this edge without explicit handling. Recommended tool: dbdiagram.io (DBML source committed alongside the exported image for diffability). The diagram is committed to the main branch.
Dependencies: REQ-004.1 through REQ-008.1; REQ-051.1; REQ-052.1; REQ-053.1; REQ-049.1
Source: `requirements.md` §7
Open Items: NONE

---

**REQ-033.1**
Type: FR
Priority: P0
Section: Documentation
Statement: The repository must contain a technical report documenting tool selection rationale and schema design justification.
Rationale: A technical report satisfies the `requirements.md` §7 requirement to explain why tools and schema designs were chosen. It is distinct from REQ-030.1 (the architecture document): REQ-030.1 covers *what the system does and how it is structured* (component interactions, data flow, integration patterns); REQ-033.1 covers *why these choices were made* (tool selection rationale over alternatives, schema design justification). The two documents are complementary — REQ-030.1 is system-facing, REQ-033.1 is decision-facing.
Acceptance Criteria: A technical report exists in `docs/` per REQ-049.1. The report documents: (1) tool selection rationale — for each of Meltano, BigQuery, dbt, Dagster, and Streamlit, why it was chosen over named alternatives; (2) schema design justification — why the star schema with three fact tables (`fct_sales`, `fct_reviews`, `fct_payments`) and four dimension tables supports efficient querying for the confirmed 11 metrics. The report does NOT duplicate the system architecture diagram or component interaction design from REQ-030.1. The report is committed to the main branch.
Dependencies: REQ-030.1; REQ-049.1
Source: `requirements.md` §7
Open Items: NONE

---

**REQ-035.1**
Type: FR
Priority: P0
Section: Documentation
Statement: The repository must contain a project implementation document describing how each pipeline component was built.
Rationale: Project implementation documentation enables team members and reviewers to understand the build process without prior context. It answers "how was this built?" — distinct from REQ-036.1 which answers "how do I run it?"
Acceptance Criteria: A project implementation document exists in `docs/` per REQ-049.1. The document covers: Meltano configuration (tap, target, schema mapping); dbt project structure (model layers, key transformations); Dagster setup (asset definitions, integrations); analysis layer structure (notebook organisation, Parquet export); and any implementation deviations from the plan. The document is committed to the main branch.
Dependencies: REQ-049.1
Source: ASMP-012
Open Items: NONE

---

**REQ-036.1**
Type: FR
Priority: P0
Section: Documentation
Statement: The repository must contain a local run setup document providing step-by-step instructions to execute the pipeline on a local machine, including credential configuration and dashboard setup.
Rationale: Local run setup documentation enables any team member to reproduce the pipeline without prior knowledge of the implementation.
Acceptance Criteria: A local run setup document exists in `docs/` per REQ-049.1. Instructions cover: (0) BigQuery dataset pre-creation — both `olist_raw` and `olist_analytics` datasets must be created before any pipeline stage runs; create via `bq mk --dataset <project>:olist_raw` and `bq mk --dataset <project>:olist_analytics`, or via the BigQuery Console; this step is a prerequisite for Meltano and dbt and is not automated by either tool. (1) conda environment creation (`assignment2`, Python 3.11); (2) dependency installation; (3) `GOOGLE_APPLICATION_CREDENTIALS` environment variable configuration; (4) Meltano ingestion execution; (5) dbt transformation and test execution; (6) Dagster UI launch and pipeline triggering; (7) Parquet file generation; (8) `streamlit run dashboard.py`. A person with no prior context must be able to execute the pipeline end-to-end by following the document alone. macOS and Linux instructions are provided. Windows users are directed to WSL2. The document is committed to the main branch. **Run order must be explicitly documented:** (0.5) `cd dbt && dbt deps` — installs `dbt-expectations` and `dbt_utils` from `packages.yml`; mandatory on any fresh clone; without it `dbt_utils.date_spine` and all dbt-expectations tests fail. (0.6) `dbt parse` — generates `target/manifest.json` required by `dagster-dbt` at import time; must run after `dbt deps` and before `dagster dev`; no BigQuery connection required. (1) `dbt build` (populates BigQuery olist_analytics dataset); (2a) Run analytical notebooks in order — `01_sales_analysis.ipynb`, `02_customer_analysis.ipynb`, `03_geo_seller_analysis.ipynb` — each exports its Parquet files to `data/`; (2b) Alternatively, run `python scripts/generate_parquet.py --project <gcp_project_id>` for quick Parquet generation without running full notebooks; (3) `streamlit run dashboard.py`. `00_eda.ipynb` is exploratory and produces no Parquet output — it may be run independently at any time. **`notebooks/utils.py` note (A-06):** `notebooks/utils.py` is the single canonical source for REGION_MAP, colour palettes, and `add_region()`. It is imported by all 3 analytical notebooks, `scripts/generate_parquet.py`, and `dashboard_utils.py`. If `utils.py` fails to import (syntax error, missing dependency), all downstream consumers fail. The local run setup document must verify that `notebooks/utils.py` imports cleanly as a standalone check before running notebooks or the dashboard.
Dependencies: REQ-026.1; REQ-027.1; REQ-059.1; REQ-060.1; REQ-049.1
Source: ASMP-012; ASMP-023
Open Items: NONE

---

**REQ-037.2**
Type: FR
Priority: P0
Section: Documentation
Statement: The repository must contain a changelog document that records all ad hoc changes and deviations to the implementation plan made during implementation.
Rationale: A changelog ensures traceability between the agreed implementation plan and the as-built system.
Acceptance Criteria: A changelog document exists in the repository root or `docs/`. Each entry records at minimum the date, the affected component, a description of the change or deviation, and the reason for the change. The changelog is updated at the time each deviation occurs — not retrospectively at project completion. The document is committed to the main branch.
Dependencies: NONE
Source: ASMP-017
Open Items: NONE

---

**REQ-045.1**
Type: FR
Priority: P0
Section: Documentation
Statement: The repository must contain a `README.md` at the repository root serving as the project entry point.
Rationale: README.md is the first document any reviewer or evaluator encounters. It is cited as a supplementary source for multiple requirements and must exist as a formal deliverable.
Acceptance Criteria: `README.md` exists at the repository root. It contains at minimum: project title and overview; repository structure; links to all documentation deliverables in `docs/`; instructions to get started (referencing REQ-036.1); and confirmation of the Streamlit dashboard deployment URL. **Note:** the deployment URL is a post-implementation placeholder — it can only be added after deploying to Streamlit Community Cloud. The README.md stub must include a clearly marked `TODO: add deployment URL after Streamlit Cloud deployment` placeholder. The file is committed to the main branch.
Dependencies: REQ-049.1
Source: SIG-03 resolution; ASMP-019
Open Items: NONE

---

**REQ-046.1**
Type: FR
Priority: P1
Section: Documentation
Statement: All dbt models and columns must have descriptions in `schema.yml`. The dbt documentation site must be generatable via `dbt docs generate`.
Rationale: dbt documentation is industry-standard practice and provides the data dictionary for the analytics schema (addressing documentation Gap 3). Evaluators familiar with dbt will expect it.
Acceptance Criteria: All dbt models in the staging and marts layers have a `description` field in `schema.yml`. All columns in the star schema tables have descriptions. `dbt docs generate` runs without errors. **The generated documentation site is NOT committed to the repository** — `target/` is large and rebuilds in seconds; `target/` must be listed in `.gitignore`. The local run setup document (REQ-036.1) must include `dbt docs generate && dbt docs serve` as an optional step for browsing the interactive schema and lineage documentation locally.
Dependencies: REQ-009.1
Source: DOC-Q1 user confirmation
Open Items: NONE

---

**REQ-047.1**
Type: FR
Priority: P0
Section: Documentation
Statement: The repository must contain a `.env.example` file listing all required environment variables with descriptions and placeholder values.
Rationale: Environment variable documentation is a prerequisite for local execution (REQ-036.1) and a standard repository practice. Without it, the pipeline cannot be reproduced by anyone not already familiar with the configuration.
Acceptance Criteria: `.env.example` exists at the repository root. It lists at minimum: `GOOGLE_APPLICATION_CREDENTIALS` (path to service account JSON key), `GCP_PROJECT_ID` (GCP project ID — required by `dbt/profiles.yml` via `env_var()` and `scripts/generate_parquet.py`), BigQuery dataset names (`olist_raw`, `olist_analytics`), and `DAGSTER_HOME` (project-local Dagster state directory). Placeholder values are provided for all variables. The file is committed to the main branch. The actual `.env` file (with real credentials) is listed in `.gitignore` using the precise pattern `.env` — not `.env*` (which would incorrectly exclude `.env.example` from the repository).
Dependencies: REQ-059.1
Source: SIG-06 resolution; documentation Gap 5
Open Items: NONE

---

**REQ-048.1**
Type: FR
Priority: P1
Section: Documentation
Statement: All Dagster assets must have human-readable descriptions visible in the Dagster UI.
Rationale: Without descriptions, the Dagster UI presents a list of unlabelled nodes, making it inaccessible to team members unfamiliar with the implementation.
Acceptance Criteria: Every Dagster asset defined in the project has a `description` parameter. Descriptions are visible in the Dagster UI asset catalogue. Descriptions explain what the asset does, what it produces, and its dependencies in plain language. Note: `dagster-dbt` assets auto-generated via `@dbt_assets` inherit their descriptions from the dbt `schema.yml` model descriptions — no separate Dagster description is needed for these assets provided the dbt model descriptions are complete.
Dependencies: REQ-026.1
Source: documentation Gap 4
Open Items: NONE

---

**REQ-049.1**
Type: FR
Priority: P1
Section: Documentation
Statement: All documentation deliverables must be located in a `docs/` directory. Diagrams must be located in `docs/diagrams/`.
Rationale: A consistent documentation directory structure prevents documentation from being scattered across the repository root and makes deliverables easy to locate for reviewers and evaluators.
Acceptance Criteria: A `docs/` directory exists in the repository. All documentation deliverables (technical report, implementation document, local run setup, README links to docs/) are located within `docs/`. All diagrams (pipeline architecture, data lineage, star schema) are located in `docs/diagrams/`. The dbt documentation site output is NOT committed to the repository per REQ-046.1 — `target/` is in `.gitignore`.
Dependencies: NONE
Source: DOC-Q2 user confirmation
Open Items: NONE

---

**REQ-050.1**
Type: FR
Priority: P1
Section: Documentation
Statement: The repository must contain a dashboard user guide providing description of each view and each analysis within the Streamlit dashboard.
Rationale: The dashboard is a key presentation deliverable. Without a user guide, stakeholders cannot understand what each view shows or how to interact with the filters effectively.
Acceptance Criteria: A dashboard user guide exists in `docs/` per REQ-049.1. The guide documents: how to run the dashboard (`streamlit run dashboard.py`); how to regenerate Parquet data files; and for each of the four views (Executive Overview, Product Performance, Geographic Analysis, Customer Analysis) — a description of every analysis, chart, and metric presented, and how all four global filters (Date Range, Product Category, Customer State, **Customer Region**) affect each view per the ASMP-027 filter applicability matrix.
Dependencies: REQ-024.1; REQ-049.1
Source: DOC-Q3 user confirmation
Open Items: NONE

---

**REQ-061.1**
Type: FR
Priority: P1
Section: Documentation
Statement: Architecture Decision Records (ADRs) must be maintained for all non-obvious architectural and schema decisions made during implementation.
Rationale: Decisions made under time pressure or incomplete information are frequently revisited. Without a written record of *why* a decision was made, future maintainers (including the same team) re-debate resolved issues or unknowingly reverse decisions that had important reasons. ADRs are the industry-standard mechanism for capturing this context.
Acceptance Criteria: ADR files exist in `docs/decisions/` using the naming convention `ADR-NNN-short-title.md`. Each ADR documents: context (what situation prompted the decision), options considered, decision made, and consequences. Minimum required ADRs for Project Caravela (decisions already made): ADR-001 (`date_key` type — DATE vs INTEGER), ADR-002 (dataset rename — `raw`→`olist_raw`, `analytics`→`olist_analytics`), ADR-003 (`fct_reviews.order_id` FK target — `stg_orders` vs `fct_sales`). Additional ADRs should be created as new significant decisions arise during implementation.
Owner: Platform Engineer (architecture decisions); Data Engineer (schema and implementation decisions)
Timing: Written at the moment of decision — not retrospectively. ADRs written after the fact lose the context that made them valuable.
Dependencies: REQ-049.1
Source: Documentation stack review v3.0
Open Items: NONE

---

**REQ-062.1**
Type: FR
Priority: P2 (Optional — recommended)
Section: Documentation
Statement: A troubleshooting guide must document common failure modes and their resolutions for the Project Caravela pipeline.
Rationale: The pipeline spans five tools (Meltano, dbt, Dagster, BigQuery, Streamlit) and multiple environment dependencies. Non-obvious failures at environment setup and first run are certain — without documented resolutions, the same errors will be investigated repeatedly.
Acceptance Criteria: `docs/troubleshooting.md` exists and documents at minimum: missing or stale `target/manifest.json` (symptom: Dagster import error; fix: `dbt parse`); incorrect `GOOGLE_APPLICATION_CREDENTIALS` (symptom: BigQuery auth error; fix: verify env var and key file path); BigQuery dataset not pre-created (symptom: dbt build 404; fix: `bq mk`); Meltano venv not initialised (symptom: `meltano run` command not found; fix: `meltano install`); dbt packages not installed (symptom: `dbt build` fails on missing macros; fix: `dbt deps`). New entries added as issues are encountered during implementation.
Owner: Data Engineer (primary author); any team member may add entries
Timing: Updated throughout implementation as issues are encountered; final review after first successful end-to-end run
Dependencies: REQ-049.1; REQ-036.1
Source: Documentation stack review v3.0
Open Items: NONE

---

**REQ-063.1**
Type: FR
Priority: P2 (Optional — recommended)
Section: Documentation
Statement: A data dictionary must document column-level business definitions for all star schema tables beyond the dbt `schema.yml` descriptions.
Rationale: dbt descriptions are implementation-facing (what the column is). A data dictionary is business-facing (what the column means to a stakeholder, acceptable values, business rules). The two serve different audiences and are complementary.
Acceptance Criteria: `docs/data_dictionary.md` exists and documents for each star schema table (`fct_sales`, `fct_reviews`, `fct_payments`, `dim_customers`, `dim_products`, `dim_sellers`, `dim_date`): column name, type, business definition, acceptable values or range, and any known data quality notes (e.g., nullable columns, COALESCE fallbacks, dedup behaviour). Cross-references `docs/data_profile.json` for threshold evidence.
Owner: Data Engineer (column definitions and data quality notes); Data Analyst (business meaning and metric usage notes)
Timing: Written after dbt models are stable (post successful `dbt build`); use `dbt docs generate` output as the starting draft
Dependencies: REQ-049.1; REQ-046.1
Source: Documentation stack review v3.0
Open Items: NONE

---

**REQ-064.1**
Type: FR
Priority: P2 (Optional — recommended)
Section: Documentation
Statement: A testing guide must document the data quality test architecture, threshold decisions, and evidence base for all dbt tests.
Rationale: dbt test thresholds (e.g., `mostly=0.97` for geolocation nulls) are calibrated from source data analysis. Without documentation, these values appear arbitrary to reviewers and cannot be adjusted confidently in future data refreshes.
Acceptance Criteria: `docs/testing_guide.md` exists and documents: the two-mechanism test architecture (dbt-expectations generic tests in `schema.yml` + singular SQL tests in `tests/`); for each key threshold — the calibrated value, the source data evidence (row counts, null rates), and the `docs/data_profile.json` reference. Covers at minimum: `review_comment_title` null (`mostly=0.08`), `review_comment_message` null (`mostly=0.40`), `geolocation_lat/lng` null (`mostly=0.97`), `payment_value ≥ 0` (zero-value voucher rationale), `stg_reviews` dedup (789 duplicate `review_id` values). Notes which singular tests enforce cross-table FK assertions.
Owner: Data Engineer
Timing: Written alongside dbt test implementation; updated if thresholds are recalibrated during implementation
Dependencies: REQ-049.1; REQ-015.1; REQ-017.1; REQ-018.1
Source: Documentation stack review v3.0
Open Items: NONE

---

**REQ-065.1**
Type: FR
Priority: P1
Section: Documentation
Statement: A `progress.md` file must be maintained at the repository root tracking implementation status for every BRD requirement.
Rationale: The project spans 60+ requirements across 8 sections and 4 domain roles. Without a structured tracker, implementation status is invisible across sessions and between agents — blockers go unnoticed, completed items get re-examined, and deviations from the BRD are not surfaced until late.
Acceptance Criteria: `progress.md` exists at the repository root. It contains one row per BRD requirement, organised by section. Each row records: REQ-ID, description, owner, status (`not started` / `in progress` / `complete` / `blocked`), blocked-by (REQ-ID of dependency if blocked), deviation flag (Yes/No), and notes. Status is updated at the start and end of each implementation work session. Any deviation from BRD acceptance criteria is flagged in the Deviation column and cross-referenced with a `changelog.md` entry. The file is committed to the main branch and updated throughout implementation.
Owner: Platform Engineer (maintains structure and ensures completeness); domain agents (Data Engineer, Data Analyst, Dash Engineer, Data Scientist) update their own rows during implementation.
Timing: Created before implementation begins (pre-implementation); updated continuously throughout implementation; final review at project completion.
Dependencies: NONE
Source: Documentation stack review v3.2
Open Items: NONE

---

## Section 8 — Executive Stakeholder Presentation

---

**REQ-038.1**
Type: FR
Priority: P0
Section: Executive Stakeholder Presentation
Statement: The project must produce a slide deck presenting the pipeline architecture, key findings, and business recommendations to a mixed audience of technical and business executives.
Rationale: A slide deck is an explicitly required deliverable in the project brief.
Acceptance Criteria: A slide deck exists in the repository committed to the main branch. The deck contains at minimum an executive summary, business value proposition, technical solution overview, business recommendations, and risk and mitigation sections. The deck is accessible without specialist software. Data scientist has full discretion over content and delivery per ASMP-013.
Dependencies: REQ-033.1; REQ-066.1
Source: `requirements.md` Deliverables; ASMP-013
Open Items: Slide deck production is user-handled via the NotebookLM workflow documented in REQ-066.1. The Data Scientist agent's Section 8 deliverable is REQ-066.1 (`docs/executive_brief.md`) only. REQ-038.1 through REQ-044.1 serve as the user's slide content checklist.

---

**REQ-039.1**
Type: FR
Priority: P0
Section: Executive Stakeholder Presentation
Statement: The presentation must include an executive summary providing a concise overview of the problem, solution, and business impact within a maximum of 3 minutes of presentation time.
Rationale: An executive summary is an explicitly recommended component of the presentation in the project brief.
Acceptance Criteria: The slide deck contains a clearly labelled executive summary section deliverable within 3 minutes of presentation time. Data scientist has full discretion over content per ASMP-013.
Dependencies: REQ-038.1
Source: `requirements.md` §8; ASMP-013
Open Items: NONE

---

**REQ-040.1**
Type: FR
Priority: P0
Section: Executive Stakeholder Presentation
Statement: The presentation must include a technical solution overview providing a high-level description of the pipeline architecture without overwhelming technical detail.
Rationale: Technical executives require sufficient technical depth to evaluate the solution without alienating business executives.
Acceptance Criteria: The slide deck contains a clearly labelled technical solution overview section referencing the confirmed tooling: Meltano, BigQuery, dbt, Dagster, and Streamlit. Architecture diagrams per REQ-030.1 are referenced or embedded. Data scientist has full discretion over content per ASMP-013.
Dependencies: REQ-038.1; REQ-030.1
Source: `requirements.md` §8; ASMP-013
Open Items: NONE

---

**REQ-041.1**
Type: FR
Priority: P1
Section: Executive Stakeholder Presentation
Statement: The presentation must include an honest assessment of technical risks, limitations, and mitigation strategies relevant to the pipeline implementation.
Rationale: Risk and mitigation is an explicitly recommended component of the presentation in the project brief.
Acceptance Criteria: The slide deck contains a clearly labelled risk and mitigation section with at least one technical risk identified and a corresponding mitigation strategy. Data scientist has full discretion over content per ASMP-013.
Dependencies: REQ-038.1
Source: `requirements.md` §8; ASMP-013
Open Items: NONE

---

**REQ-042.1**
Type: FR
Priority: P0
Section: Executive Stakeholder Presentation
Statement: The presentation must include at minimum one interactive aid supporting delivery of findings to the mixed executive audience.
Rationale: Interactive aids enhance stakeholder engagement and comprehension of analytical findings.
Acceptance Criteria: At minimum the Streamlit dashboard per REQ-024.1 is available and functional during the presentation. Data scientist has full discretion over additional interactive aids per ASMP-013.
Dependencies: REQ-024.1; REQ-038.1
Source: `requirements.md` §8; ASMP-013
Open Items: NONE. Streamlit dashboard per REQ-024.1 satisfies the interactive aid requirement. Additional interactive aids remain at Data Scientist discretion per ASMP-013.

---

**REQ-043.1**
Type: NFR
Priority: P0
Section: Executive Stakeholder Presentation
Statement: The presentation must be deliverable within a total duration of 15 minutes — 10 minutes presentation and 5 minutes Q&A.
Rationale: Duration is explicitly specified in the project brief.
Acceptance Criteria: The presentation is completed within 10 minutes. A Q&A period of 5 minutes follows. All team members are present and prepared to answer questions from both technical and business executives.
Dependencies: REQ-038.1
Source: `requirements.md` §8
Open Items: NONE

---

**REQ-044.1**
Type: FR
Priority: P1
Section: Executive Stakeholder Presentation
Statement: The presentation must include a business value proposition section articulating the business value and strategic impact of the pipeline, driven by data and insights.
Rationale: Business Value Proposition is an explicitly recommended component of the presentation in `requirements.md` §8. It was absent from BRD v1.0.
Acceptance Criteria: The slide deck contains a clearly labelled business value proposition section. The section articulates at minimum: the business problem addressed, measurable efficiency improvements enabled by the pipeline, and at least one data-driven strategic recommendation. Data scientist has full discretion over content per ASMP-013.
Dependencies: REQ-038.1; REQ-022.1
Source: `requirements.md` §8; SIG-07 resolution; ASMP-013
Open Items: NONE

---

**REQ-066.1**
Type: FR
Priority: P1
Section: Executive Stakeholder Presentation
Statement: The Data Scientist must produce an Executive Brief document (`docs/executive_brief.md`) serving as the primary narrative source for the slide deck and for Google NotebookLM slide generation.
Rationale: The executive brief captures the complete presentation narrative in structured prose — a format that (1) serves as a standalone written deliverable, (2) feeds Google NotebookLM to auto-generate the Google Slides deck, and (3) is version-controlled in the repository. Writing prose first forces a coherent narrative before visual design begins.
Acceptance Criteria: `docs/executive_brief.md` exists, committed to the main branch. The document is structured with H1/H2/H3 headings so that heading hierarchy is preserved when pasted into a Google Doc for NotebookLM upload. It covers at minimum: Business Context (why this matters), Solution Overview (pipeline architecture in plain language), Key Finding — Sales & Revenue (metrics 1, 2, 7 with specific numbers), Key Finding — Customer Behaviour (RFM segments, repeat purchase rate, NPS proxy), Key Finding — Operational Performance (delivery performance, seller performance), Business Recommendations (3–4 data-driven actions with supporting numbers from the analysis), and Risks & Limitations (data cut artefacts, geolocation coverage, 96.9% single-purchase rate). Word count: 1,500–2,500 words. All specific numbers cited must be sourced from the Parquet feature files produced by the analytical notebooks. **NotebookLM workflow:** Google Doc (paste from Markdown) → NotebookLM → Google Slides → polish → export `.pptx` committed to `docs/`.
Owner: Data Scientist
Timing: Written after all three analytical notebooks are complete and Parquet files are exported; before slide deck production begins.
Dependencies: REQ-022.1; REQ-055.1; REQ-056.1; REQ-057.1; REQ-058.1; REQ-049.1
Source: Documentation stack review v3.4; user confirmation 2026-03-11
Open Items: NONE

---

## Requirements Index

| REQ-ID | Type | Priority | Section |
|---|---|---|---|
| REQ-059.1 | CON | P0 | Development Environment |
| REQ-060.1 | CON | P1 | Development Environment |
| REQ-001.2 | FR | P0 | Data Ingestion |
| REQ-002.1 | CON | P0 | Data Ingestion |
| REQ-003.1 | CON | P0 | Data Ingestion |
| REQ-004.1 | FR | P0 | Data Warehouse Design |
| REQ-005.1 | FR | P0 | Data Warehouse Design |
| REQ-006.1 | FR | P0 | Data Warehouse Design |
| REQ-007.1 | FR | P0 | Data Warehouse Design |
| REQ-008.1 | FR | P0 | Data Warehouse Design |
| REQ-009.1 | CON | P0 | Data Warehouse Design |
| REQ-051.1 | FR | P0 | Data Warehouse Design |
| REQ-052.1 | FR | P0 | Data Warehouse Design |
| REQ-053.1 | FR | P0 | Data Warehouse Design |
| REQ-010.1 | FR | P0 | ELT Pipeline |
| REQ-011.1 | FR | P0 | ELT Pipeline |
| REQ-012.1 | FR | P0 | ELT Pipeline |
| REQ-013.1 | FR | P1 | ELT Pipeline |
| REQ-014.1 | CON | P0 | ELT Pipeline |
| REQ-054.1 | FR | P1 | ELT Pipeline |
| REQ-015.1 | FR | P0 | Data Quality Testing |
| REQ-016.1 | FR | P0 | Data Quality Testing |
| REQ-017.1 | FR | P0 | Data Quality Testing |
| REQ-018.1 | FR | P1 | Data Quality Testing |
| REQ-019.1 | NFR | P1 | Data Quality Testing |
| REQ-020.2 | FR | P0 | Data Analysis with Python |
| REQ-021.1 | FR | P0 | Data Analysis with Python |
| REQ-022.1 | FR | P0 | Data Analysis with Python |
| REQ-023.1 | FR | P0 | Data Analysis with Python |
| REQ-024.1 | FR | P1 | Data Analysis with Python |
| REQ-025.1 | FR | P0 | Data Analysis with Python |
| REQ-055.1 | FR | P0 | Data Analysis with Python |
| REQ-056.1 | FR | P0 | Data Analysis with Python |
| REQ-057.1 | FR | P0 | Data Analysis with Python |
| REQ-058.1 | FR | P0 | Data Analysis with Python |
| REQ-026.1 | FR | P1 | Pipeline Orchestration |
| REQ-027.1 | FR | P1 | Pipeline Orchestration |
| REQ-028.1 | — | — | Superseded in v2.0 |
| REQ-028.2 | FR | P1 | Pipeline Orchestration |
| REQ-029.1 | NFR | P1 | Pipeline Orchestration |
| REQ-030.1 | FR | P0 | Documentation |
| REQ-031.1 | FR | P0 | Documentation |
| REQ-032.1 | FR | P0 | Documentation |
| REQ-033.1 | FR | P0 | Documentation |
| REQ-034.1 | — | — | Merged into REQ-030.1 in v2.0 |
| REQ-035.1 | FR | P0 | Documentation |
| REQ-036.1 | FR | P0 | Documentation |
| REQ-037.2 | FR | P0 | Documentation |
| REQ-045.1 | FR | P0 | Documentation |
| REQ-046.1 | FR | P1 | Documentation |
| REQ-047.1 | FR | P0 | Documentation |
| REQ-048.1 | FR | P1 | Documentation |
| REQ-049.1 | FR | P1 | Documentation |
| REQ-050.1 | FR | P1 | Documentation |
| REQ-061.1 | FR | P1 | Documentation |
| REQ-062.1 | FR | P2 (Optional) | Documentation |
| REQ-063.1 | FR | P2 (Optional) | Documentation |
| REQ-064.1 | FR | P2 (Optional) | Documentation |
| REQ-065.1 | FR | P1 | Documentation |
| REQ-038.1 | FR | P0 | Executive Stakeholder Presentation |
| REQ-039.1 | FR | P0 | Executive Stakeholder Presentation |
| REQ-040.1 | FR | P0 | Executive Stakeholder Presentation |
| REQ-041.1 | FR | P1 | Executive Stakeholder Presentation |
| REQ-042.1 | FR | P0 | Executive Stakeholder Presentation |
| REQ-043.1 | NFR | P0 | Executive Stakeholder Presentation |
| REQ-044.1 | FR | P1 | Executive Stakeholder Presentation |
| REQ-066.1 | FR | P1 | Executive Stakeholder Presentation |

---

## Completeness Summary

| Requirement Type | Count | Sections Present |
|---|---|---|
| FR (Functional) | 47 | 0, 1, 2, 3, 4, 5, 6, 7, 8 |
| NFR (Non-Functional) | 3 | 4, 6, 8 |
| CON (Constraint) | 7 | 0, 1, 2, 3 |
| ASMP (Assumption) | 23 | All |

**Priority distribution (active requirements only):**
- P0: 38 requirements
- P1: 19 requirements
- P2: 0 requirements

**Superseded / merged in v2.0:**
- REQ-028.1 (CON, P1): Superseded by REQ-028.2
- REQ-034.1 (FR, P0): Merged into REQ-030.1

**Flagged gaps (no source material — not invented):**
- NFRs absent from Sections 0, 2, 5, and 7 — source material contains no performance, availability, or latency requirements for these sections.
- CONs absent from Sections 4, 7, and 8 — source material contains no technology, budget, or regulatory constraints specific to these sections.

---

## BRD Revision History

| Version | Date | Authors | Key Changes |
|---|---|---|---|
| 1.0 | 2026-03-08 | Patrick — Requirements Analyst | Initial draft. 43 requirements across Sections 1–8. |
| 2.0 | 2026-03-08 | Patrick — Requirements Analyst; Claude — AI Pipeline Architect | Added Section 0 (Development Environment). Expanded star schema from 1 fact + 3 dim to 3 fact + 4 dim (added fct_reviews, fct_payments, dim_sellers). All 9 source tables added to lineage (ASMP-020). Geolocation enrichment added (REQ-054.1). order_purchase_timestamp confirmed as date_key source. Daily 09:00 Dagster schedule reinstated (REQ-028.2; REQ-028.1 superseded). RFM segmentation formalised (REQ-055.1). Delivery performance, review/satisfaction, and payment analysis added as required metrics (REQ-056.1–058.1). 4th Customer Analysis Streamlit view added (REQ-024.1). REQ-030.1 and REQ-034.1 merged per ASMP-011. Six documentation gaps addressed (REQ-045.1–050.1). BigQuery "schema" corrected to "dataset" throughout. REQ-020.2 scoped to Jupyter notebooks only; Streamlit exempted. 23 ASMPs (up from 17). REQ-001.2 and REQ-037.2 version suffix .2 noted — these reflect revisions made during v1.0 authoring before the document was formally versioned. |
| 2.1 | 2026-03-09 | Patrick — Requirements Analyst; Claude — AI Pipeline Architect | Data engineer review applied. ASMP-024 added (dbt-expectations). Section 4 (Data Quality Testing): REQ-015.1 expanded to two-mechanism test architecture; REQ-016.1 clarified (relationships + singular SQL); REQ-017.1 replaced DE-discretion language with full confirmed test inventory per table; REQ-018.1 threshold-aware null tests with calibrated mostly values. Source data profiling findings applied: REQ-052.1 mandates stg_reviews deduplication on review_id (789 duplicates confirmed); REQ-054.1 mandates stg_geolocation bounding-box filter before AVG() (coordinate outliers confirmed); REQ-006.1 mandates COALESCE fallback for 2 untranslated product categories + 610 null-category products; REQ-017.1 notes stg_payments must filter not_defined rows and clamp 0-installment records; REQ-018.1 thresholds recalibrated from source data (geolocation 0.85→0.97, review_comment_title 0.15→0.08); REQ-001.2 open items added (BOM in translation file, geolocation 1M rows performance risk); REQ-003.1 open item added (raw dataset naming/reserved keyword note); REQ-011.1 open item added (775 itemless orders expected behaviour documented). REQ-008.1 updated: customer_unique_id resolution via stg_customers join mandated explicitly; order_payment_value removed from fct_sales (order-level aggregate on item-level fact — silent double-count risk in multi-item orders). ASMP-005 and REQ-013.1 updated accordingly. 24 ASMPs. |
| 2.2 | 2026-03-09 | Patrick — Requirements Analyst; Claude — AI Pipeline Architect | Consistency audit and Dagster review applied. AUDIT-01 (critical): REQ-052.1 fct_reviews.order_id FK target changed from fct_sales to stg_orders — 756 itemless orders have reviews but no fct_sales rows; REQ-017.1 cross-table test updated accordingly. AUDIT-02: REQ-017.1 payment_value test changed from >0 to ≥0 — 6 legitimate zero-value voucher payments confirmed. AUDIT-03: REQ-012.1 lineage updated — added stg_customers→fct_sales (customer_unique_id resolution) and stg_orders→fct_payments (date_key derivation). AUDIT-05: REQ-008.1 stale REQ-053.1 dependency removed. AUDIT-06: REQ-017.1 product_category test description updated for COALESCE accuracy. Section 6 (Dagster): REQ-026.1 expanded — dagster-dbt mandatory integration, dbt build as execution mode, Meltano shell asset; REQ-048.1 notes dagster-dbt inherits descriptions from schema.yml; REQ-028.2 timezone closed (Asia/Singapore). |
| 2.3 | 2026-03-10 | Patrick — Requirements Analyst; Claude — AI Data Analyst | Section 5 (Analysis + Dashboard) data analyst review applied. ASMP-008 expanded: 11 confirmed metrics (6 mandated + 5 additional); 4-notebook structure; state-to-region mapping for Brazil's 5 IBGE regions. ASMP-022 updated: full RFM specification — reference date 2018-08-31, 3-tier Frequency (96.9% single-purchase rate confirmed), quintile R/M, 6 named segments, repeat purchase rate as standalone metric. ASMP-025 added: source data temporal observations confirmed from monthly distribution query — tail sparsity (Sep/Oct 2018 artefacts), Nov 2016 gap, observation window 2017-01-01 to 2018-08-31. REQ-008.1 updated: order_delivered_customer_date and order_estimated_delivery_date added as nullable timestamps in fct_sales (delivery timestamps promoted from stg_orders to keep analytics layer self-sufficient; COUNT(DISTINCT order_id) mandated for delivery rate calculations). REQ-022.1 updated: 11 metrics, 4-notebook structure, delivery consolidated to notebook 3, staging models excluded from notebook queries. REQ-023.1 updated: 4-notebook structure; exploratory/analytical full separation formalised; 00_eda.ipynb defined. REQ-024.1 updated: Customer Region added as 4th global dashboard filter. REQ-055.1 updated: full RFM implementation spec, hardcoded reference date, no open items. REQ-056.1 updated: delivery performance consolidated to 03_geo_seller_analysis.ipynb. |
| 4.0 | 2026-03-11 | Patrick — Requirements Analyst; Claude — Platform Engineer | Executive Presentation stack review — 5 issues resolved. E-01: REQ-038.1 dependency updated — REQ-066.1 added (brief must exist before slides can be produced). REQ-038.1 Open Items updated: slide deck production is user-handled via NotebookLM; Data Scientist agent deliverable is REQ-066.1 only. E-02: REQ-066.1 dependency corrected — REQ-038.1 removed (brief precedes deck; Timing field and Dependencies field were contradicting each other). E-03: REQ-038.1 AC updated — "risk and mitigation" added to required sections list (REQ-041.1 P1 requires this section; it was absent from parent REQ AC). E-04: REQ-042.1 Open Item closed — Streamlit dashboard satisfies interactive aid requirement; `presentation.html` note was redundant given ASMP-013 discretion. E-05: progress.md REQ-041.1 corrected (was "Key findings slides" — BRD says risk/mitigation); REQ-042.1 corrected (was "Business recommendations slide" — BRD says interactive aid). |
| 3.9 | 2026-03-11 | Patrick — Requirements Analyst; Claude — Platform Engineer | Dashboard stack review — 6 issues resolved. D-01: REQ-024.1 AC expanded — `dashboard_utils.py` interface specified (`init_filters()`, `@st.cache_data` loaders, cascade failure noted). D-02: REQ-050.1 owner updated to joint Dash Engineer + Data Analyst in progress.md — Dash Engineer owns technical operation; Data Analyst owns metric interpretation. D-03: REQ-025.1 Open Items updated — `data/brazil_states.geojson` source documented (codeforamerica/click_that_hood). D-04: CLAUDE.md three stale `dashboard.py` references corrected — Parquet Inventory (reads → `dashboard_utils.py`), Visualization (+ `pages/*.py`, note `dashboard.py` has no charts), checklist (imported by `dashboard_utils.py` not `dashboard.py`). D-05: CLAUDE.md run order restructured with per-agent labels — Platform Engineer (step 0), Data Engineer (steps 1–3), Data Analyst (step 4), Dash Engineer (step 5); clarifies that Data Analyst does not run dbt and Dash Engineer does not need BigQuery access. D-06: CLAUDE.md deliverables checklist expanded — `dashboard.py` (thin entry point), `dashboard_utils.py` (loaders + filter init), `pages/` (four view files) each listed separately. |
| 3.8 | 2026-03-11 | Patrick — Requirements Analyst; Claude — Platform Engineer | Analysis stack review — 6 issues resolved. A-01: REQ-020.2 dependency corrected — REQ-004.1 (dbt scaffold) replaced with REQ-008.1 (fct_sales); notebooks require analytics data to exist, not just the project to be scaffolded. A-02: REQ-057.1 Open Item closed — review metrics dashboard placement already decided in ASMP-027 (Customer Analysis view, satisfaction_summary.parquet). A-03: REQ-058.1 Open Item closed — payment metrics dashboard placement already decided in ASMP-027 (Executive Overview, sales_orders.parquet). A-04: REQ-056.1 AC updated — 30-order minimum threshold added for regional delivery breakdown heatmap (suppress sparse cells to avoid misleading rates). A-05: REQ-025.1 Open Items updated — scripts/generate_parquet.py formalised as optional Data Analyst convenience script; must produce output identical to notebooks; REQ-036.1 must document as alternative quick-start. A-06: REQ-023.1 AC updated — notebooks/utils.py explicitly required as importable module; contents (REGION_MAP, SEGMENT_COLOURS, REGION_COLOURS, STATUS_COLOURS, add_region) mandated; cascade failure risk documented. |
| 3.7 | 2026-03-11 | Patrick — Requirements Analyst; Claude — Platform Engineer | Data Quality Testing stack review — 6 issues resolved. DQ-01: DEF-009 column renames (`product_name_lenght` → `product_name_length`, `product_description_lenght` → `product_description_length`) added to CLAUDE.md `stg_products` notes and to REQ-017.1 `dim_products` test block. DQ-02: REQ-016.1 Acceptance Criteria expanded to include `fct_payments.date_key → dim_date` FK test; `fct_reviews` cross-layer FK cross-referenced to REQ-017.1. DQ-03: REQ-018.1 threshold calibration rationale moved into Acceptance Criteria; Open Items closed. DQ-04: CLAUDE.md Data Quality Testing section expanded with pair test function name, NULL handling behaviour, boleto singular test pattern, financial reconciliation pattern, fct_reviews dedup guard note. DQ-05: `fct_reviews` row count test added to REQ-017.1 (`expect_table_row_count_to_be_between` min=95000, max=100000). DQ-06: REQ-019.1 corrected in progress.md — moved from Section 5 to Section 4 with correct description (NFR: `dbt test` single command); `notebooks/utils.py` entry in Section 5 corrected to show no REQ-ID. |
| 3.6 | 2026-03-11 | Patrick — Requirements Analyst; Claude — Platform Engineer | Ingestion stack review — 8 issues resolved. I-01: CLAUDE.md BOM note updated to confirmed `encoding: utf-8-sig` pattern. I-02/I-03: REQ-001.2 Open Items (3) and (4) closed — resolved by ASMP-001. I-04: REQ-003.1 Open Item (1) assigned to Platform Engineer as pre-implementation blocker; progress.md updated with blocker flag. I-05: CLAUDE.md Meltano Configuration section added (stream naming contract, BOM encoding, relative path, WRITE_TRUNCATE, STRING schema, geolocation note). I-06: Geolocation performance/hang warning added to CLAUDE.md. I-07: ADR-004 created — `tap-spreadsheets-anywhere` vs `tap-csv` selection. I-08: ASMP-028 clarified — `CAST(col AS TIMESTAMP)` preferred; `SAFE.PARSE_TIMESTAMP` reserved for known format-variation columns only. |
| 3.5 | 2026-03-11 | Patrick — Requirements Analyst; Claude — Platform Engineer | Documentation stack review — 7 issues resolved. D-R01: REQ-061.1 Owner updated to Platform Engineer. D-R02: REQ-065.1 Owner updated to Platform Engineer; Dash Engineer added to agent list in Acceptance Criteria. D-R03: ASMP-011 updated to Platform Engineer. D-R04: REQ-030.1 Statement updated to Platform Engineer. D-R05: REQ-049.1 "if committed" dbt docs clause removed — replaced with explicit NOT committed reference to REQ-046.1. D-R06: progress.md REQ-065.1 moved from Optional to Required section; REQ-061.1 owner updated to Platform Engineer. D-R07: REQ-033.1 Statement and Acceptance Criteria sharpened — boundary with REQ-030.1 now explicit (REQ-030.1 = system design/how; REQ-033.1 = decisions/why). |
| 3.4 | 2026-03-11 | Patrick — Requirements Analyst; Claude — Platform Engineer | Team composition confirmed and formalised: Platform Engineer (formerly "AI Pipeline Architect"), Data Engineer, Data Analyst, Dash Engineer, Data Scientist. BRD foreword delegation table updated to 5-agent model with section ownership. ASMP-013 updated: Data Scientist confirmed as team member, scope expanded to include REQ-066.1. ASMP-014 updated: five-agent team confirmed; "AI Pipeline Architect" → "Platform Engineer" mapping noted for prior BRD versions. REQ-066.1 added (P1): `docs/executive_brief.md` — structured narrative document for NotebookLM slide generation workflow; owned by Data Scientist; post-analysis timing. Traceability matrix, CLAUDE.md checklist, and progress.md Section 8 updated. |
| 3.3 | 2026-03-11 | Patrick — Requirements Analyst; Claude — AI Pipeline Architect | REQ-065.1 added (P1): `progress.md` formalised as a required deliverable. Owner: AI Pipeline Architect (structure); domain agents update own rows. Traceability matrix, CLAUDE.md checklist, and progress.md self-entry updated. |
| 3.2 | 2026-03-11 | Patrick — Requirements Analyst; Claude — AI Pipeline Architect | REQ-061.1 priority upgraded P2→P1 (required): ADRs document decisions already made — not discretionary. REQ-062.1 to REQ-064.1 remain P2 Optional — depend on implementation findings. Traceability matrix, CLAUDE.md checklist, and progress.md updated accordingly. |
| 3.1 | 2026-03-11 | Patrick — Requirements Analyst; Claude — AI Pipeline Architect | Optional documentation requirements added (REQ-061.1 to REQ-064.1): ADRs, troubleshooting guide, data dictionary, testing guide. Each requirement specifies owner and implementation timing. Requirements Traceability Matrix updated. `progress.md` implementation status tracker created (full REQ-level tracking table, all sections). Three ADRs pre-populated in `docs/decisions/`: ADR-001 (`date_key` type), ADR-002 (dataset rename), ADR-003 (`fct_reviews` FK target). ADR template committed as `ADR-000-template.md`. CLAUDE.md Required Deliverables Checklist updated with all optional items. |
| 3.0 | 2026-03-11 | Patrick — Requirements Analyst; Claude — AI Pipeline Architect | Documentation stack review applied (D-01 to D-10). REQ-047.1 updated: `.env.example` template committed with `GOOGLE_APPLICATION_CREDENTIALS`, `GCP_PROJECT_ID`, `BIGQUERY_RAW_DATASET=olist_raw`, `BIGQUERY_ANALYTICS_DATASET=olist_analytics`, `DAGSTER_HOME`; `.gitignore` entry note added. REQ-036.1 updated: `dbt deps` added as step 0.5 (mandatory on fresh clone); `dbt parse` moved to step 0.6 (must follow `dbt deps`). REQ-050.1 updated: Customer Region confirmed as fourth global dashboard filter; dashboard user guide updated. REQ-046.1 resolved: dbt docs NOT committed to repo; `target/` covered by `.gitignore`; `dbt docs generate && dbt docs serve` added as optional diagnostic step in local run setup. REQ-031.1 updated: data lineage diagram must call out cross-layer dependencies (`stg_customers→fct_sales`, `stg_orders→fct_payments`); Mermaid recommended as format. REQ-032.1 updated: star schema ERD must annotate `fct_reviews.order_id → stg_orders` FK as cross-layer dependency; dbdiagram.io + DBML source recommended. REQ-045.1 updated: architecture document deployment URL is a post-implementation placeholder. CLAUDE.md updated: Documentation section added with diagramming tools table (draw.io / Mermaid / dbdiagram.io), dbt docs generate/serve note, optional documentation recommendations (ADRs, troubleshooting guide, data dictionary, testing guide). `.env.example` file created at repo root. | 2.9 | 2026-03-11 | Patrick — Requirements Analyst; Claude — AI Pipeline Architect | Dagster stack second-pass review. REQ-026.1 acceptance criteria updated: job definition requirement added (O-09), AssetSpec key naming constraint added (O-12), dbt profile env_var mandate added (O-08), no-partition-strategy stated (O-15). REQ-028.2 updated: `execution_timezone="Asia/Singapore"` pattern confirmed (O-10). CLAUDE.md updated: profiles.yml env_var pattern (O-08); manifest path __file__-relative resolution (O-11); all 9 AssetKey specs listed explicitly (O-12); Meltano subprocess log forwarding added (O-13); job definition + Definitions object pattern added (O-09); ScheduleDefinition with execution_timezone (O-10); version compatibility pins (O-14); no-partition statement (O-15). |
| 2.8 | 2026-03-11 | Patrick — Requirements Analyst; Claude — AI Pipeline Architect | Orchestration (Dagster) stack review applied. CLAUDE.md updated: Dagster project file structure documented (O-03); `DbtCliResource` + `dbt.cli(["build"])` pattern mandated (O-05); Meltano asset upstream wiring pattern with `AssetSpec` declaration documented (O-02); `meltano run` must set `cwd` to `meltano/` directory (O-04); `dbt parse` added as pre-start requirement for `manifest.json` generation (O-01); `GOOGLE_APPLICATION_CREDENTIALS` propagation note added (O-06); `dagster dev` vs `dagster-daemon` clarification added (O-07). REQ-036.1 updated: `dbt parse` added as step 0.5 in run order; dataset names corrected in step 0. REQ-028.2 updated: daemon requirement for scheduled runs documented. |
| 2.7 | 2026-03-11 | Patrick — Requirements Analyst; Claude — AI Pipeline Architect | `date_key` type confirmed as DATE. REQ-008.1 Open Item (3) closed — blocking flag removed. REQ-017.1 open item closed — `date_key` range test unblocked; confirmed implementation: `expect_column_values_to_be_between` with `min_value='2016-01-01'`, `max_value='2018-12-31'`. CLAUDE.md updated with `date_key` type and staging cast pattern. Changelog updated. |
| 2.6 | 2026-03-11 | Patrick — Requirements Analyst; Claude — AI Pipeline Architect | dbt stack review (T-01). BigQuery dataset names renamed: `raw` → `olist_raw`, `analytics` → `olist_analytics`. `raw` is a reserved word in BigQuery standard SQL — relying on implicit adapter quoting introduces version-dependent behaviour risk; renaming eliminates the ambiguity at zero migration cost pre-implementation. All 35 affected references updated across Assumptions Register, Sections 2–7, and Revision History. ASMP-001 updated with dataset name rationale. REQ-003.1 Open Item 2 closed. Changelog entry added. |
| 2.5 | 2026-03-11 | Patrick — Requirements Analyst; Claude — AI Pipeline Architect | Ingestion stack review applied. ASMP-001 updated: `tap-spreadsheets-anywhere` and `target-bigquery` confirmed; `WRITE_TRUNCATE` write disposition mandated; BigQuery table naming convention documented (filename minus extension); `raw_data/` relative path convention specified; `meltano run` command confirmed. ASMP-028 added: all-STRING schema inference from tap — all type casts mandatory in dbt staging layer. REQ-001.2 open items (1) and (2) resolved by plugin selection. REQ-011.1 updated: ASMP-028 mandatory cast requirement added. REQ-012.1 open item added: `sources.yml` table name verification step. REQ-036.1 updated: BigQuery dataset pre-creation added as step 0. |
| 2.4 | 2026-03-10 | Patrick — Requirements Analyst; Claude — AI Dashboard Architect | Dashboard stack review applied. ASMP-027 added: full dashboard architecture — multi-page app (Approach 3); `dashboard.py` thin entry point; `pages/` directory with 4 page files; `dashboard_utils.py` for Streamlit-specific cached loaders and filter initialisation; cross-page filter state via `st.session_state`; filter applicability matrix per view; empty multi-select = show all; `st.caption()` notes for inapplicable filters; D-05 pre-implementation check for GeoJSON `featureidkey`. REQ-024.1 updated: multi-page architecture and ASMP-027 referenced in acceptance criteria. REQ-025.1 open item added: D-05 featureidkey pre-implementation check. REQ-036.1 updated: explicit run-order documentation mandated (dbt build → notebooks or generate_parquet.py → streamlit); A-06 utils.py single-point-of-failure noted with import verification step. REQ-008.1 open item (3) added: date_key type decision flagged as blocking for notebook implementation — DE decision required. REQ-017.1 open item updated: date_key range test flagged as blocking DE decision. |

---

*End of Document — BRD Project Caravela — Olist E-Commerce Analytics Pipeline v3.7*
