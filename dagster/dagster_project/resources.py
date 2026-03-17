from dagster_dbt import DbtCliResource
from pathlib import Path

dbt_resource = DbtCliResource(
    project_dir=str(Path(__file__).parent.parent.parent / "dbt"),
)
