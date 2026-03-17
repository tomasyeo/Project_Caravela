from dagster import AssetSelection, Definitions, define_asset_job

from .assets import caravela_dbt_assets, meltano_ingest
from .resources import dbt_resource
from .schedules import full_pipeline_schedule

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
