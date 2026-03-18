import subprocess
from pathlib import Path

from dagster import AssetExecutionContext, AssetKey, AssetSpec, multi_asset
from dagster_dbt import DbtCliResource, dbt_assets

DBT_MANIFEST_PATH = (
    Path(__file__).parent.parent.parent / "dbt" / "target" / "manifest.json"
)

# AssetSpec objects declare meltano_ingest as the PRODUCER of each olist_raw table.
# This makes olist_raw/* executable (not external) so Dagster enforces:
#   meltano_ingest → olist_raw/* → stg_* → dim_*/fct_*
# Names use _view suffix to match target-bigquery's denormalized=false output —
# sources.yml and manifest.json reference the flat-column views, not the base tables.
# (Deviation from spec — see changelog 2026-03-14 _view suffix entry.)
RAW_TABLE_SPECS = [
    AssetSpec(AssetKey(["olist_raw", "olist_customers_dataset_view"])),
    AssetSpec(AssetKey(["olist_raw", "olist_orders_dataset_view"])),
    AssetSpec(AssetKey(["olist_raw", "olist_order_items_dataset_view"])),
    AssetSpec(AssetKey(["olist_raw", "olist_order_payments_dataset_view"])),
    AssetSpec(AssetKey(["olist_raw", "olist_order_reviews_dataset_view"])),
    AssetSpec(AssetKey(["olist_raw", "olist_products_dataset_view"])),
    AssetSpec(AssetKey(["olist_raw", "olist_sellers_dataset_view"])),
    AssetSpec(AssetKey(["olist_raw", "olist_geolocation_dataset_view"])),
    AssetSpec(AssetKey(["olist_raw", "product_category_name_translation_view"])),
]


@multi_asset(
    specs=RAW_TABLE_SPECS,
    name="meltano_ingest",
    description=(
        "Runs Meltano ingestion: tap-csv → target-bigquery. "
        "Loads all 9 Olist CSV source files into BigQuery olist_raw dataset. "
        "Write disposition: WRITE_TRUNCATE (full refresh on every run). "
        "Note: geolocation file has 1M rows — expect several minutes with no visible progress."
    ),
)
def meltano_ingest(context: AssetExecutionContext):
    # tap-csv used instead of tap-spreadsheets-anywhere — see changelog 2026-03-14.
    # --env-file ../.env loads repo-root .env directly so BIGQUERY_RAW_DATASET and
    # other vars are available regardless of how Dagster was started (with or without
    # launch_dagster.sh). cwd is meltano/, so ../ resolves to repo root.
    result = subprocess.run(
        ["meltano", "--env-file", "../.env", "run", "tap-csv", "target-bigquery"],
        cwd=Path(__file__).parent.parent.parent / "meltano",
        capture_output=True,
        text=True,
    )
    if result.stdout:
        context.log.info(result.stdout)
    # Log stderr unconditionally — meltano writes progress info to stderr by convention.
    if result.stderr:
        if result.returncode != 0:
            context.log.error(result.stderr)
        else:
            context.log.info(result.stderr)
    if result.returncode != 0:
        raise Exception(f"meltano run failed:\n{result.stderr}")


@dbt_assets(manifest=DBT_MANIFEST_PATH)
def caravela_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()
