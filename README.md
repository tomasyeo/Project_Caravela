# Project Caravela — Olist E-Commerce Analytics Pipeline

End-to-end data pipeline for the [Brazilian E-Commerce Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (~100k orders, 2016–2018). Ingests 9 CSV source files into BigQuery, transforms them through a star-schema data warehouse with dbt, orchestrates execution with Dagster, analyses the data in Jupyter notebooks, and presents insights through a Streamlit dashboard.

**Live dashboard:** _[deployment URL — add after Streamlit Cloud deploy]_

---

## Architecture Overview

```
raw_data/ (9 CSVs)
    └── Meltano (tap-csv → target-bigquery)
            └── BigQuery olist_raw (9 tables)
                    └── dbt (staging → mart)
                            └── BigQuery olist_analytics (4 dims + 3 facts)
                                    └── Jupyter Notebooks (analysis + Parquet export)
                                                └── Streamlit Dashboard (reads Parquet)
```

Orchestrated end-to-end by Dagster with a daily 09:00 SGT schedule.

---

## Quickstart

### Prerequisites

```bash
# 1. Create conda environment
conda env create -f environment.yml
conda activate assignment2

# 2. Copy and fill in credentials
cp .env.example .env
# Edit .env: set GCP_PROJECT_ID and GOOGLE_APPLICATION_CREDENTIALS

# 3. Pre-create BigQuery datasets (one-time)
bq mk --dataset <project>:olist_raw
bq mk --dataset <project>:olist_analytics
```

<!-- AGENT 1 (Data Engineer): add Meltano + dbt quickstart steps here -->
<!-- AGENT 2 (Platform Engineer): add Dagster quickstart steps here -->

### Dashboard (no BigQuery required)

Parquet files are committed to `data/` — the dashboard runs from those directly:

```bash
streamlit run dashboard.py
```

### Regenerate Parquet files

If you want to rebuild the Parquet exports from BigQuery without running the notebooks:

```bash
python scripts/generate_parquet.py
# Or with explicit project:
python scripts/generate_parquet.py --project <gcp_project_id>
```

---

## Repository Structure

```
Project_Caravela/
├── raw_data/                    # 9 source CSVs (Olist dataset)
├── meltano/                     # Meltano ingestion config
├── dbt/                         # dbt staging + mart models, tests, schemas
├── dagster/                     # Dagster project (assets, schedules, resources)
├── notebooks/
│   ├── utils.py                 # Shared constants: REGION_MAP, colour palettes, helpers
│   ├── 00_eda.ipynb             # Exploratory analysis — schema verification, distributions
│   ├── 01_sales_analysis.ipynb  # Metrics 1, 2, 6, 7, 8 → sales_orders.parquet
│   ├── 02_customer_analysis.ipynb  # Metrics 3, 5, 9 → customer_rfm.parquet, satisfaction_summary.parquet
│   └── 03_geo_seller_analysis.ipynb # Metrics 4, 10, 11 → geo_delivery.parquet, seller_performance.parquet
├── data/
│   ├── sales_orders.parquet
│   ├── customer_rfm.parquet
│   ├── satisfaction_summary.parquet
│   ├── geo_delivery.parquet
│   ├── seller_performance.parquet
│   ├── concentration_metrics.parquet
│   └── brazil_states.geojson    # State boundaries for choropleth maps
├── scripts/
│   └── generate_parquet.py      # Rebuild all 6 Parquet files from BigQuery
├── pages/                       # Streamlit multi-page app
├── dashboard.py                 # Entry point (st.navigation only)
├── dashboard_utils.py           # Cached Parquet loaders + filter init
├── docs/                        # Technical report, data dictionary, ADRs, guides
├── .env.example                 # Environment variable template
└── progress.md                  # REQ-level implementation status
```

---

<!-- AGENT 1 (Data Engineer): add Ingestion section (Meltano) here -->

<!-- AGENT 1 (Data Engineer): add Transformation section (dbt) here -->

<!-- AGENT 2 (Platform Engineer): add Orchestration section (Dagster) here -->

---

## Analysis Notebooks

Four notebooks cover 11 confirmed metrics. Each analytical notebook is self-contained — no cross-notebook variable dependencies.

### Running the notebooks

```bash
# Ensure BigQuery credentials are set
source .env   # or export manually

jupyter lab
```

Run notebooks in order if regenerating Parquet exports:
1. `01_sales_analysis.ipynb`
2. `02_customer_analysis.ipynb`
3. `03_geo_seller_analysis.ipynb`

`00_eda.ipynb` is exploratory only — run independently at any time, no Parquet output.

### Notebook inventory

| Notebook | Metrics | Parquet exports |
|---|---|---|
| `00_eda.ipynb` | Schema verification, null distributions, data quality notes | None |
| `01_sales_analysis.ipynb` | Monthly GMV, top products, payment distribution, AOV, cancellation rate | `sales_orders.parquet` |
| `02_customer_analysis.ipynb` | RFM segmentation, NPS proxy, delay×review correlation | `customer_rfm.parquet`, `satisfaction_summary.parquet` |
| `03_geo_seller_analysis.ipynb` | Delivery performance, regional penetration, seller performance | `geo_delivery.parquet`, `seller_performance.parquet`, `concentration_metrics.parquet` |

### Parquet file inventory

All files committed to `data/` — the dashboard reads these directly (no live BigQuery connection required).

| File | Granularity | Rows | Description |
|---|---|---|---|
| `sales_orders.parquet` | Order-item | ~112k | Sales transactions with payment type, region, category |
| `customer_rfm.parquet` | Customer | ~96k | RFM scores and segment assignments (ref date: 2018-08-31) |
| `satisfaction_summary.parquet` | Order | ~97k | Review scores, NPS category, delivery delay bins |
| `geo_delivery.parquet` | State × month | ~535 | On-time rate and average delay by state and month |
| `seller_performance.parquet` | Seller | ~3k | GMV, review score, cancellation rate per seller |
| `concentration_metrics.parquet` | Dimension × group | 83 | Gini, HHI, CR4/CR10 for seller/customer/category dimensions |

### Shared utilities — `notebooks/utils.py`

Imported by all 3 analytical notebooks, `scripts/generate_parquet.py`, and `dashboard_utils.py`. **Do not redefine these constants in notebooks.**

| Export | Type | Description |
|---|---|---|
| `REGION_MAP` | `dict[str, str]` | Maps 27 state codes + DF to 5 Brazilian regions |
| `SEGMENT_COLOURS` | `dict[str, str]` | Hex colours for 6 RFM segments |
| `REGION_COLOURS` | `dict[str, str]` | Hex colours for 5 regions |
| `STATUS_COLOURS` | `dict[str, str]` | Hex colours for 8 order statuses |
| `add_region(df, state_col)` | function | Adds `region` column via `REGION_MAP` lookup |
| `gini_coefficient(values)` | function | Computes Gini coefficient from a 1-D array |
| `lorenz_curve(values)` | function | Returns (x, y) arrays for Lorenz curve plotting |
| `hhi(values)` | function | Herfindahl-Hirschman Index |
| `concentration_summary(values, name)` | function | Returns dict with gini, hhi, cr4, cr10, top_20pct_share |

---

<!-- AGENT 4 (Dashboard Engineer): add Dashboard section here -->

---

## Documentation

| Document | Location | Description |
|---|---|---|
| Technical report | `docs/technical_report.md` | Tool selection rationale + schema + analytical methodology |
| Data dictionary | `docs/data_dictionary.md` | Column-level definitions for all layers |
| Dashboard user guide | `docs/dashboard_user_guide.md` | Filter mechanics, per-page interpretation |
| Testing guide | `docs/testing_guide.md` | dbt test coverage, thresholds, known omissions |
| Troubleshooting | `docs/troubleshooting.md` | Common failure modes per pipeline layer |
| Architecture Decision Records | `docs/decisions/` | ADR-001 through ADR-004 |
| Star schema ERD | `docs/diagrams/` | DBML source + Graphviz PNG |
| Data lineage diagram | `docs/diagrams/` | Full pipeline lineage (Graphviz) |

---

## Data Quality Notes

- **Observation window**: Jan 2017 – Aug 2018 (20 months). 2016-11/12 (0–1 orders) and 2018-09/10 (16/4 orders) excluded as data cut artefacts in all trend analyses.
- **Product categories**: Always use `product_category_name_english` — `product_category_name` contains empty strings for 610 products.
- **Delivery metrics**: Use `COUNT(DISTINCT order_id)` — delivery timestamps are order-level attributes repeated across item rows in `fct_sales`.
- **RFM reference date**: Hardcoded `2018-08-31` for reproducibility — not `CURRENT_DATE`.

---

## Environment Variables

See `.env.example` for the full list. Required variables:

| Variable | Description |
|---|---|
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to GCP service account JSON key file |
| `GCP_PROJECT_ID` | BigQuery project ID |
| `BIGQUERY_ANALYTICS_DATASET` | dbt target dataset (default: `olist_analytics`) |
| `BIGQUERY_RAW_DATASET` | Meltano target / dbt source schema (default: `olist_raw`) |
