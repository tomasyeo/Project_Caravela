# Progress Log — Project Caravela
# REQ-037.2: All implementation deviations must also be recorded in changelog.md.
# Update status at the start and end of each work session.
# Statuses: not started | in progress | complete | blocked

## How to use
- Set status to `in progress` when you begin work on a requirement.
- Set status to `complete` when the requirement passes its acceptance criteria (tests pass, deliverable committed).
- Set status to `blocked` and fill in the Blocked By column when a dependency or open question prevents progress.
- If implementation deviates from the BRD, mark Deviation = Yes and add an entry to `changelog.md`.
- Link ADRs in Notes for any requirement where a significant decision was made.

---

## Section 0 — Development Environment

| REQ-ID | Description | Owner | Status | Blocked By | Deviation | Notes |
|---|---|---|---|---|---|---|
| REQ-059.1 | Python 3.11, conda env `assignment2`, dependencies installed | Data Engineer | complete | — | — | Python 3.11.15 confirmed in `assignment2` env. dagster 1.12.18, dagster-dbt 0.28.18, dbt-core 1.11.7, meltano 4.1.2 all installed. |
| REQ-060.1 | macOS/Linux supported; Windows via WSL2 | Data Engineer | complete | — | — | Developed and validated on macOS Darwin 26.3.1. `launch_dagster.sh` uses `stat -f` (macOS) with `stat -c` Linux fallback. |

---

## Section 1 — Ingestion (Meltano)

| REQ-ID | Description | Owner | Status | Blocked By | Deviation | Notes |
|---|---|---|---|---|---|---|
| REQ-001.2 | Meltano pipeline configured: `tap-csv` → `target-bigquery` | Data Engineer | complete | — | Yes | Deviated from spec: `tap-csv` instead of `tap-spreadsheets-anywhere`; `batch_job` method; `_view` suffix on BQ table names. See changelog 2026-03-14 entries. |
| REQ-002.1 | All 9 source CSVs loaded to `olist_raw` | Data Engineer | complete | — | Yes | All 9 tables + 9 flat-column views in `olist_raw`. dbt must query `*_view` tables. See changelog. |
| REQ-003.1 | BigQuery datasets pre-created; `GOOGLE_APPLICATION_CREDENTIALS` provisioned | Platform Engineer | complete | — | — | `GOOGLE_APPLICATION_CREDENTIALS` and `GCP_PROJECT_ID` confirmed set in environment. Datasets (`olist_raw`, `olist_analytics`) exist and operational — confirmed by `dbt test` 76/76 PASS against live BigQuery 2026-03-18. `.env` auto-loading via `launch_dagster.sh` + `dagster/dagster_home/dagster.yaml` (EnvFileLoader) complete. |

---

## Section 2 — Data Warehouse Design (dbt Staging)

| REQ-ID | Description | Owner | Status | Blocked By | Deviation | Notes |
|---|---|---|---|---|---|---|
| REQ-004.1 | dbt project scaffolded; `packages.yml` with dbt-expectations + dbt_utils | Data Engineer | complete | — | Yes | `dbt_project.yml`, `packages.yml`, `profiles.yml` created. `dbt deps` installed dbt_utils 1.3.3, dbt-expectations v0.6.0 (metaplane fork — `git: https://github.com/metaplane/dbt-expectations`). Original calogica/dbt-expectations deprecated after v0.10.4; metaplane fork is the active continuation. `mostly` parameter not available in this fork. See changelog 2026-03-18. |
| REQ-011.1 | 9 staging models — all raw columns cast from STRING in staging | Data Engineer | complete | — | Yes | All 9 staging models created. `sources.yml` uses `_view` suffix (upstream deviation). `stg_products` uses `product_category_name_english` not `string_field_1`. See changelog 2026-03-14. |
| REQ-012.1 | dbt lineage complete — all 9 tables in `sources.yml` | Data Engineer | complete | — | Yes | 9 sources declared with `_view` suffix. `stg_products` dual-source (both `olist_products_dataset_view` and `product_category_name_translation_view`). `dbt parse` + `dbt compile` succeed (manifest.json generated). |

---

## Section 3 — Data Warehouse Design (dbt Marts)

| REQ-ID | Description | Owner | Status | Blocked By | Deviation | Notes |
|---|---|---|---|---|---|---|
| REQ-005.1 | `dim_customers` — PK: `customer_unique_id`; city, state, zip, lat, lng | Data Engineer | complete | — | — | lat/lng from `stg_geolocation`; nullable where no match. `dbt build` PASS. |
| REQ-006.1 | `dim_products` — PK: `product_id`; COALESCE English/Portuguese/uncategorized | Data Engineer | complete | — | Yes | Pass-through from `stg_products`. COALESCE dead-branch fixed. WHERE filter removed (was excluding 610 dim rows, breaking FK tests). `dbt build` PASS. **Analyst note:** use `product_category_name_english` for all analysis — `product_category_name` contains empty strings for 610 products. |
| REQ-007.1 | `dim_date` — PK: `date_key DATE`; generated via `dbt_utils.date_spine` | Data Engineer | complete | — | — | Range: 2016-01-01 to 2018-12-31. `dbt build` PASS. See ADR-001 |
| REQ-051.1 | `dim_sellers` — PK: `seller_id`; city, state, zip, lat, lng | Data Engineer | complete | — | — | lat/lng from `stg_geolocation`; nullable where no match. `dbt build` PASS. |
| REQ-008.1 | `fct_sales` — order-item granularity; FKs to all 4 dims | Data Engineer | complete | — | — | Three-source CTE (order_items → orders → customers). `dbt build` PASS. |
| REQ-052.1 | `fct_reviews` — deduplicated on `review_id`; FK: `order_id` → `stg_orders` | Data Engineer | complete | — | — | Pass-through from `stg_reviews` (already deduped). FK → stg_orders (not fct_sales). `dbt build` PASS. See ADR-003 |
| REQ-053.1 | `fct_payments` — compound key (`order_id`, `payment_sequential`) | Data Engineer | complete | — | — | `date_key` from `stg_orders` via explicit CTE. `dbt build` PASS. |
| REQ-054.1 | `stg_geolocation` — Brazil bounding-box filter; AVG() lat/lng per zip | Data Engineer | complete | — | — | Already implemented in staging by Agent 1b. Used by dim_customers and dim_sellers. `dbt build` PASS. |
| REQ-013.1 | `total_sale_amount` = price + freight_value (item-level derived column) | Data Engineer | complete | — | — | Computed in `fct_sales`. `order_payment_value` excluded. `dbt build` PASS. |

---

## Section 4 — Data Quality Testing

| REQ-ID | Description | Owner | Status | Blocked By | Deviation | Notes |
|---|---|---|---|---|---|---|
| REQ-015.1 | dbt-expectations generic tests in `schema.yml` | Data Engineer | complete | — | — | `dbt/models/staging/schema.yml` (10 models) + `dbt/models/marts/schema.yml` (7 models) created. Column ranges, accepted values, null thresholds, row counts declared. |
| REQ-016.1 | `relationships` tests for all FK columns across all fact tables | Data Engineer | complete | — | — | `fct_sales` 4 FKs (dim_customers, dim_products, dim_sellers, dim_date). `fct_reviews.order_id → stg_orders` (NOT fct_sales — 756 itemless orders). `fct_payments` compound PK only; no dim_date FK (date_key nullable via LEFT JOIN). |
| REQ-017.1 | Singular SQL tests in `tests/` for cross-table assertions | Data Engineer | complete | — | — | 3 tests: `assert_boleto_single_installment.sql`, `assert_payment_reconciliation.sql`, `assert_date_key_range.sql` |
| REQ-018.1 | Null threshold tests calibrated from `docs/data_profile.json` | Data Engineer | complete | — | Yes | Thresholds calibrated: `review_comment_title` fill=11.7% (mostly=0.08), `review_comment_message` fill=41.3% (mostly=0.40), `dim_customers`/`dim_sellers` lat/lng match=99.7%/99.8% (mostly=0.97). **Proportion tests NOT implemented** — metaplane/dbt-expectations v0.6.0 has no `mostly` parameter on any macro. Fill rates documented in column descriptions and `docs/data_profile.json` as calibration evidence. See changelog 2026-03-18. |
| REQ-019.1 | All data quality tests executable via single `dbt test` command | Data Engineer | complete | — | — | NFR satisfied — all tests in schema.yml + tests/ directory, run via `dbt test` or `dbt build` |

---

## Section 5 — Analysis and Dashboard

| REQ-ID | Description | Owner | Status | Blocked By | Deviation | Notes |
|---|---|---|---|---|---|---|
| REQ-020.2 | SQLAlchemy + BigQuery connector in notebooks | Data Analyst | complete | — | Yes | Used `google-cloud-bigquery` client directly instead of SQLAlchemy. Added `load_dotenv()` — dataset names read from `.env` (`BIGQUERY_ANALYTICS_DATASET`, `BIGQUERY_RAW_DATASET`) with fallback defaults. See changelog 2026-03-16. |
| REQ-021.1 | `00_eda.ipynb` — exploratory schema verification; no Parquet output | Data Analyst | complete | — | — | 27 cells (15 md + 12 code), 0 errors. Row counts, schemas, null distributions, distribution checks, data cut awareness. Data quality notes expanded to 7 items including `dim_date.date_key` DATETIME quirk. |
| REQ-022.1 | 11 confirmed metrics across 3 analytical notebooks | Data Analyst | complete | — | — | Metrics 1,2,6,7,8 in nb01; 3,5,9+delay×review in nb02; 4,10,11 in nb03. All charts use plotly.express. Additional deep-dives: freight analysis, Black Friday, cohort retention, delivery promise accuracy, category×region, seller quality tiers, Lorenz/Gini concentration analysis (seller 0.78, customer 0.48, category revenue 0.71), temporal Gini trend, category-level HHI. All insights quality-audited and validated against data. |
| REQ-023.1 | 4-notebook structure; exploratory/analytical separation | Data Analyst | complete | — | — | 4 notebooks, no cross-notebook variable dependencies. Each opens with markdown referencing EDA findings. |
| REQ-024.1 | Streamlit dashboard — 4 views; 4 global filters | Data Analyst | complete | — | Yes | 5 pages (4 analysis + Glossary), horizontal tab layout per page, extra charts (Lorenz, freight, quality tiers, Gini trend). Runtime smoke-tested 2026-03-17 — all pages load, all filters work, edge cases pass. See changelog 2026-03-16 Agent 4 entry. |
| REQ-025.1 | Parquet files in `data/`; committed to repo | Data Analyst | complete | — | Yes | 6 files exported: sales_orders (112,279), customer_rfm (95,420), satisfaction_summary (97,379), geo_delivery (533), seller_performance (3,068), concentration_metrics (83). New `concentration_metrics.parquet` added for Lorenz/Gini/HHI dashboard KPIs. See changelog 2026-03-16. |
| REQ-055.1 | RFM segmentation — hardcoded ref date 2018-08-31; 6 segments | Data Analyst | complete | — | — | Reference date hardcoded. 3-tier F (F1/F2/F3). 6 segments assigned via RF-only. Repeat rate: ~3.1%. |
| REQ-056.1 | Delivery performance — on-time rate + avg delay; notebook 3 | Data Analyst | complete | — | Yes | COUNT(DISTINCT order_id) used. Min 30 orders threshold. geo_delivery.parquet has year/month cols. Seller cancellation_rate bug fixed (COUNTIF→COUNT DISTINCT CASE). See changelog 2026-03-16. |
| REQ-057.1 | Review/satisfaction analysis; delay×review correlation | Data Analyst | complete | — | — | 5 delay bins (early/on-time/1-3d/4-7d/7+d). NPS proxy scoring. Box plot + bar chart. |
| REQ-058.1 | Payment method distribution + installment behaviour | Data Analyst | complete | — | — | payment_sequential=1 for primary payment. Donut + histogram. Credit card ~77% of orders. |
| *(no REQ-ID)* | `notebooks/utils.py` — REGION_MAP, SEGMENT_COLOURS, REGION_COLOURS, STATUS_COLOURS, `add_region()`, `lorenz_curve()`, `gini_coefficient()`, `hhi()`, `concentration_summary()` | Data Analyst | complete | — | Yes | Updated add_region: added default param + .copy() + dynamic output naming. Colour values kept as-is (Flat UI). Added numpy import + 4 concentration analysis helpers. See changelog 2026-03-16. |
| *(no REQ-ID)* | `scripts/generate_parquet.py` — optional quick-setup alternative to running all 3 analytical notebooks | Data Analyst | complete | — | Yes | Rewritten to use `google.cloud.bigquery.Client` (matching notebooks). All 6 Parquet schemas aligned exactly with notebook outputs. RFM date upper bound included. See changelog 2026-03-16. |

---

## Section 6 — Orchestration (Dagster)

| REQ-ID | Description | Owner | Status | Blocked By | Deviation | Notes |
|---|---|---|---|---|---|---|
| REQ-026.1 | Dagster project with `dagster-dbt`; Meltano shell asset; `dbt build` | Platform Engineer | complete | — | Yes | 5 files created and validated. 25 assets in correct topological order. `meltano_ingest` uses `@multi_asset(specs=...)` — confirmed PRODUCER of `olist_raw/*` (not consumer). Execution order enforced: meltano_ingest → olist_raw/* → stg_* → dim_*/fct_*. All paths `__file__`-relative. Live `dagster dev` validated 2026-03-18. |
| REQ-027.1 | Manual triggering via Dagster UI + CLI | Platform Engineer | complete | — | — | `full_pipeline_job` defined with `AssetSelection.all()`. Triggerable via UI Materialize button or `dagster job execute -j full_pipeline_job`. Confirmed visible in UI 2026-03-18. |
| REQ-028.2 | Daily 09:00 SGT schedule; `execution_timezone="Asia/Singapore"` | Platform Engineer | complete | — | Yes | `cron_schedule="0 9 * * *"`, `execution_timezone="Asia/Singapore"` confirmed. `job_name` string used instead of job object reference (avoids circular import). Schedule name: `full_pipeline_job_schedule`. Confirmed visible under Automation in UI 2026-03-18. |
| REQ-029.1 | Dagster UI accessible; asset materialisation state visible | Platform Engineer | complete | — | — | All 25 assets load cleanly. 4-layer topology confirmed in asset graph: meltano_ingest → olist_raw/* → stg_* → dim_*/fct_*. `full_pipeline_job_schedule` visible under Automation. Live validated 2026-03-18 via `./scripts/launch_dagster.sh`. |

---

## Section 7 — Documentation (Required)

| REQ-ID | Description | Owner | Status | Blocked By | Deviation | Notes |
|---|---|---|---|---|---|---|
| REQ-030.1 | Pipeline architecture diagram + architecture document | Orchestrator | complete | — | — | 3 Graphviz PNGs (`pipeline_architecture.png`, `pipeline_architecture_detailed.png`, `pipeline_architecture_detailed_2.png`) + 2 Mermaid `.md` files in `docs/diagrams/`. Final detailed version: TB layout, 3840×2160px, execution boundaries (Dagster-automated vs manual), `.env` credential flows, row counts, file locations. |
| REQ-031.1 | Data lineage diagram — must show cross-layer dependencies | Orchestrator | complete | — | — | `docs/diagrams/data_lineage.png` (3777×2160px) + `docs/data_lineage.md` (Mermaid). 3-layer LR layout (raw→staging→marts), 7 key lineage notes, cross-boundary FK annotated. |
| REQ-032.1 | Star schema ERD — must annotate `fct_reviews.order_id → stg_orders` | Orchestrator | complete | — | — | `docs/diagrams/star_schema.png` (3797×2160px) + `docs/diagrams/star_schema.dbml` + `docs/diagrams/star_schema.dot`. 3-column layout: satellite facts, fct_sales (center), dims. All columns from actual dbt SQL. User-refined: nullable markers, composite PKs, FK edges to dim_date from all facts. |
| REQ-033.1 | Technical report — tool selection rationale + schema justification | Orchestrator + Agent 3 | complete | — | — | `docs/technical_report.md`. Orchestrator: §1 intro, §2.1–2.4 + §2.6 tool rationale, §3 schema justification (3.1–3.6), §4 dev environment. Agent 3: §2.5 analysis rationale, §5 analytical methodology. Agent 2: Dagster expansion. User-refined: batch_job rationale, env_var interpolation, mart-level test design table (§3.5). |
| REQ-035.1 | Project implementation document | Data Engineer | not started | post-implementation | — | — |
| REQ-036.1 | Local run setup document | Platform Engineer | complete | — | — | Created `docs/local_run_setup.md` — 10-step guide from fresh clone to running dashboard. Covers one-time setup, manifest generation, Dagster launch, pipeline execution, notebooks, dashboard. References `scripts/launch_dagster.sh` and `docs/troubleshooting.md`. |
| REQ-037.2 | `changelog.md` — all ad hoc deviations logged | All | complete | — | — | 42 entries as of 2026-03-18. Covers all Meltano, dbt, Dagster, notebook, dashboard, and documentation deviations. |
| REQ-045.1 | `README.md` at repo root with deployment URL placeholder | Agent 3 + Orchestrator | complete | — | — | Agent 3: architecture overview, quickstart (dashboard-only + generate_parquet.py), notebook inventory, Parquet file inventory, utils.py API, data quality notes, env vars, docs index. Deployment URL placeholder present. `README.md` exists at repo root. |
| REQ-046.1 | dbt `schema.yml` descriptions for all models + columns | Data Engineer | complete | — | — | `dbt/models/staging/schema.yml` + `dbt/models/marts/schema.yml` created with model and column descriptions for all 10 staging + 7 mart models. |
| REQ-047.1 | `.env.example` with all required env vars | Data Engineer | complete | — | — | File created at repo root |
| REQ-048.1 | Dagster asset descriptions in UI | Platform Engineer | complete | — | — | `@dbt_assets` auto-inherits descriptions from dbt `schema.yml`. `meltano_ingest` description set on `@multi_asset` decorator. |
| REQ-049.1 | All docs in `docs/`; diagrams in `docs/diagrams/` | All | complete | — | — | Verified: all `.dot`, `.dbml`, `.png` diagram files in `docs/diagrams/`. All markdown docs in `docs/`. ADRs in `docs/decisions/`. Executive deliverables in `docs/executive/`. BRD + requirements in `docs/requirements/`. |
| REQ-050.1 | Dashboard user guide — 4 views, 4 filters documented | Dash Engineer + Data Analyst | complete | — | — | Final merged guide at `docs/dashboard_user_guide.md`. Covers: getting started, layout/navigation, filter mechanics, per-page interpretation, glossary usage, 8 data quality notes. Analyst draft (`docs/dashboard_user_guide_analyst_draft.md`) retained as source. |
| REQ-061.1 | ADRs in `docs/decisions/` — minimum 3 pre-populated | Platform Engineer / Data Engineer | complete | — | — | 4 ADRs created: ADR-001 (date_key type), ADR-002 (dataset rename), ADR-003 (fct_reviews FK target), ADR-004 (tap selection). Exceeds minimum of 3. |
| REQ-065.1 | `progress.md` — REQ-level implementation status tracker | Platform Engineer | complete | — | — | This file |

---

## Section 7 — Documentation (Optional — REQ-062.1 to REQ-064.1)

| REQ-ID | Description | Owner | Status | Blocked By | Deviation | Notes |
|---|---|---|---|---|---|---|
| REQ-062.1 | `docs/troubleshooting.md` | Data Engineer + Platform Engineer | complete | — | — | 44 entries across Meltano (8), dbt staging (9), dbt marts (18), Dagster (9). Dagster section (entries #36–44) added by Agent 2 covering: manifest.json missing, module not found, schedule not firing, wrong dependency direction, env var errors, meltano subprocess failure, job validation error, circular import, AssetKey mismatch. |
| REQ-063.1 | `docs/data_dictionary.md` | Data Engineer + Data Analyst | complete | — | — | Data Analyst draft (Parquet schemas, metrics, utils API) + Data Engineer additions (raw source layer 9 tables, staging transformations, column type reference). `docs/data_profile.json` used as evidence base. |
| REQ-064.1 | `docs/testing_guide.md` | Data Engineer | complete | — | Yes | Created at `docs/testing_guide.md`. Covers all 10 staging + 7 mart models with per-column test evidence from `docs/data_profile.json`. Singular test calibration rationale. Known omissions (mostly unavailable, 2 pair tests removed). Failure interpretation guide. Deviation: proportion tests omitted (metaplane fork constraint — see changelog 2026-03-18). |

---

## Section 8 — Executive Stakeholder Presentation

| REQ-ID | Description | Owner | Status | Blocked By | Deviation | Notes |
|---|---|---|---|---|---|---|
| REQ-066.1 | `docs/executive_brief.md` — narrative source for NotebookLM slide generation | Data Scientist | complete | — | — | 2,177 words. All 11 metrics referenced with specific figures from Parquet-verified data. 9 sections, 5 strategic recommendations, 3 risks (1 technical + 2 business). |
| REQ-038.1 | Executive slide deck (Google Slides → `.pptx` in `docs/`) | Agent 5 | complete | — | — | `docs/executive/executive_slides.pptx` + `docs/executive/executive_slides.pdf`. Generated via `scripts/generate_slides.py`. 11 slide assets in `docs/executive/slides_assets/`. Speaker notes in `docs/executive/Speaker Notes.pdf`. |
| REQ-039.1 | Executive summary slide (≤3 min) | Agent 5 | complete | — | — | Included in executive slide deck. |
| REQ-040.1 | Technical solution overview slide | Agent 5 | complete | — | — | Included in executive slide deck. References pipeline architecture diagram. |
| REQ-041.1 | Risk and mitigation section — at least 1 technical risk + mitigation strategy | Agent 5 | complete | — | — | Included in executive slide deck. Brief (REQ-066.1) provides supporting narrative with 3 risks (1 technical + 2 business). |
| REQ-042.1 | Interactive aid during presentation — Streamlit dashboard satisfies AC | Agent 5 | complete | — | — | Streamlit dashboard operational (REQ-024.1 complete). Dashboard serves as interactive aid during presentation. |
| REQ-043.1 | Presentation quality and delivery (10 min + 5 min Q&A) | Agent 5 | complete | — | — | Slide deck + speaker notes prepared. All team members present. |
| REQ-044.1 | Business value proposition slide | Agent 5 | complete | — | — | Included in executive slide deck. 5 strategic recommendations in executive brief. |
