# Local Run Setup — Project Caravela

> REQ-036.1 — Step-by-step guide for a fresh clone through to a running dashboard.

---

## Prerequisites

Before starting, confirm the following are available:

| Requirement | Notes |
|---|---|
| GCP service account key (`.json`) | Requires BigQuery Editor role on the target project |
| BigQuery datasets pre-created | `olist_raw` and `olist_analytics` must exist — see Step 2 |
| `conda` installed | Miniconda or Anaconda; `assignment2` env must be created |
| `git` installed | Standard system git |

---

## Step 1 — Clone and activate the environment

```bash
git clone <repo-url>
cd Project_Caravela

conda activate assignment2
```

Verify the environment is active and key tools are available:
```bash
python --version        # 3.11.x
dagster --version       # 1.12.x
dbt --version           # Core: 1.11.x
meltano --version       # 4.x
```

---

## Step 2 — Create BigQuery datasets (one-time per GCP project)

```bash
bq mk --dataset <your-gcp-project>:olist_raw
bq mk --dataset <your-gcp-project>:olist_analytics
```

These datasets must exist before the first pipeline run. Meltano writes to `olist_raw`; dbt writes to `olist_analytics`.

---

## Step 3 — Configure credentials

```bash
cp .env.example .env
```

Edit `.env` and fill in all four values:

```bash
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account-key.json
GCP_PROJECT_ID=your-gcp-project-id
BIGQUERY_RAW_DATASET=olist_raw
BIGQUERY_ANALYTICS_DATASET=olist_analytics
```

Verify credentials resolve correctly:
```bash
echo $GOOGLE_APPLICATION_CREDENTIALS   # should return the key file path
echo $GCP_PROJECT_ID                   # should return the project ID
```

> **Note:** `DAGSTER_HOME` is managed automatically by `scripts/launch_dagster.sh` — do not set it manually unless running `dagster dev` directly.

---

## Step 4 — Install Meltano plugin virtual environments (one-time)

```bash
cd meltano
meltano install
cd ..
```

This creates isolated venvs under `meltano/.meltano/` for `tap-csv` and `target-bigquery`. Required on every fresh clone. Re-run if `.meltano/` is deleted.

**Known issue:** `setuptools>=81` breaks plugin installation. Both plugins pin `setuptools<70` in their `pip_url` — this is already configured in `meltano.yml`. If installation fails with `ModuleNotFoundError: No module named 'pkg_resources'`, see `docs/troubleshooting.md` entry #1.

---

## Step 5 — Install dbt packages (one-time)

```bash
cd dbt
dbt deps
cd ..
```

Installs `dbt-utils` and `dbt-expectations` into `dbt/dbt_packages/`. Required on every fresh clone.

---

## Step 6 — Generate dbt manifest (required before Dagster)

```bash
cd dbt
dbt parse
cd ..
```

`dagster-dbt` reads `manifest.json` at Python import time — it must exist before `dagster dev` starts. `dbt parse` generates `dbt/target/manifest.json` without connecting to BigQuery.

**Known issue:** dbt 1.11.7 exits with code 1 due to a protobuf bug (see `docs/troubleshooting.md` entry #9). This is expected — check that the file was created:
```bash
ls -la dbt/target/manifest.json   # should exist with a recent timestamp
```

Regenerate after any changes to dbt models, sources, or `schema.yml`.

---

## Step 7 — Launch Dagster

```bash
./scripts/launch_dagster.sh
```

The script runs 7 pre-flight checks (credentials, manifest, binaries), sources `.env`, sets `DAGSTER_HOME`, then starts `dagster dev`.

The Dagster UI is available at: **http://127.0.0.1:3000**

**Options:**
```bash
./scripts/launch_dagster.sh --parse          # regenerate manifest.json first
./scripts/launch_dagster.sh --port 3001      # use a different port
./scripts/launch_dagster.sh --help           # full usage
```

**What you should see in the UI:**
- **Asset graph**: 25 assets in 4 layers — `meltano_ingest` → 9 `olist_raw/*` → 10 `stg_*` → 6 mart models + `dim_date`
- **Automation**: `full_pipeline_job_schedule` — daily 09:00 SGT (`0 9 * * *`, `Asia/Singapore`)
- **Jobs**: `full_pipeline_job` — selects all assets

---

## Step 8 — Run the pipeline

### Via Dagster UI (recommended)
1. Open http://127.0.0.1:3000
2. Navigate to **Assets** → **View global asset lineage**
3. Click **Materialize all** to run the full pipeline
4. Monitor progress in the **Runs** tab — Meltano stdout/stderr is forwarded to Dagster logs

### Via CLI
```bash
# Full pipeline
dagster job execute -j full_pipeline_job -d dagster/

# Individual asset (e.g. re-run dbt only after a model change)
dagster asset materialize --select '*' -d dagster/

# Meltano only
dagster asset materialize --select meltano_ingest -d dagster/
```

### Via Meltano directly (ingestion only)
```bash
cd meltano
./launch_meltano.sh run
```

### Via dbt directly (transformation only, after Meltano has run)
```bash
cd dbt
dbt build    # runs all models + tests interleaved
```

> **Warning:** Running the pipeline (any method above) will execute `WRITE_TRUNCATE` on all `olist_raw` tables and rebuild all `olist_analytics` tables. This is safe — the dataset is fixed/historical and full refresh is always correct.

---

## Step 9 — Run analytical notebooks

Prerequisites: pipeline must have run successfully (BigQuery `olist_analytics` populated).

```bash
jupyter notebook
```

Run in order:
1. `notebooks/00_eda.ipynb` — exploratory only, no output required
2. `notebooks/01_sales_analysis.ipynb` → exports `data/sales_orders.parquet`
3. `notebooks/02_customer_analysis.ipynb` → exports `data/customer_rfm.parquet`, `data/satisfaction_summary.parquet`
4. `notebooks/03_geo_seller_analysis.ipynb` → exports `data/geo_delivery.parquet`, `data/seller_performance.parquet`, `data/concentration_metrics.parquet`

**Quick setup alternative** (skips notebooks, generates all 6 Parquet files directly):
```bash
python scripts/generate_parquet.py
```

---

## Step 10 — Run the dashboard

Prerequisites: all 6 Parquet files must exist in `data/`. No BigQuery connection required.

```bash
streamlit run dashboard.py
```

Dashboard opens at: **http://localhost:8501**

Four analysis views: Executive Overview, Product Performance, Geographic Analysis, Customer Analysis. Global filters: Date Range, Product Category, Customer State, Customer Region.

---

## Optional — Browse dbt documentation

```bash
cd dbt
dbt docs generate   # compiles catalog.json + manifest.json
dbt docs serve      # starts interactive schema browser at http://localhost:8080
```

Shows an interactive DAG and data dictionary. Not committed to git (`dbt/target/` is gitignored).

---

## Full sequence summary

```bash
# One-time setup (fresh clone)
conda activate assignment2
cp .env.example .env              # fill in credentials
bq mk --dataset <project>:olist_raw
bq mk --dataset <project>:olist_analytics
cd meltano && meltano install && cd ..
cd dbt && dbt deps && cd ..

# Every session
conda activate assignment2
./scripts/launch_dagster.sh       # runs pre-flight checks, starts UI at :3000
# → Materialize in UI, or run notebooks, or streamlit run dashboard.py
```

---

## Troubleshooting

See `docs/troubleshooting.md` for common failure modes across all pipeline layers.

Key entries for first-time setup:
- **#1** — `meltano install` fails (`pkg_resources` error)
- **#9** — dbt protobuf exit crash (expected, not a problem)
- **#36** — `dagster dev` fails at startup (`manifest.json` missing)
- **#37** — `dagster dev` module not found (wrong working directory)
- **#40** — `dbt build` env var errors in Dagster (credentials not injected)
