"""Dagster: the IslandMart dlt + dbt pipeline as software-defined assets."""
import os
import sys
from pathlib import Path

import dagster as dg
import dlt
from dagster_dbt import DbtCliResource, dbt_assets
from dagster_dlt import DagsterDltResource, DagsterDltTranslator, dlt_assets
from dagster_dlt.translator import DltResourceTranslatorData

sys.path.insert(0, str(Path(__file__).parent))   # so we can import the existing dlt script
from dlt_islandmart_postgres import DUCKDB_PATH, islandmart_source

DBT_PROJECT_DIR = Path(__file__).parent.parent / "islandmart_dbt"


class IslandmartDltTranslator(DagsterDltTranslator):
    """Name dlt's assets like dbt's sources (islandmart/products, ...), so Dagster can link them."""

    def get_asset_spec(self, data: DltResourceTranslatorData) -> dg.AssetSpec:
        spec = super().get_asset_spec(data)
        return spec.replace_attributes(key=dg.AssetKey(["islandmart", data.resource.name]))


@dlt_assets(
    dlt_source=islandmart_source(),
    dlt_pipeline=dlt.pipeline(
        pipeline_name="islandmart_postgres",
        destination=dlt.destinations.duckdb(DUCKDB_PATH),
        dataset_name="raw_islandmart",
    ),
    name="islandmart_postgres",
    group_name="ingestion",
    dagster_dlt_translator=IslandmartDltTranslator(),
)
def islandmart_dlt_assets(context: dg.AssetExecutionContext, dlt: DagsterDltResource):
    yield from dlt.run(context=context)


@dbt_assets(manifest=DBT_PROJECT_DIR / "target" / "manifest.json")
def islandmart_dbt_assets(context: dg.AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build", "--exclude-resource-type", "unit_test"], context=context).stream()

daily_job = dg.define_asset_job("islandmart_daily", selection=dg.AssetSelection.all())

defs = dg.Definitions(
    assets=[islandmart_dlt_assets, islandmart_dbt_assets],
    jobs=[daily_job],
    schedules=[dg.ScheduleDefinition(job=daily_job, cron_schedule="0 0 * * *")],
    resources={
        "dlt": DagsterDltResource(),
        "dbt": DbtCliResource(
            project_dir=str(DBT_PROJECT_DIR),
            profiles_dir=str(DBT_PROJECT_DIR),
            dbt_executable=os.getenv("DBT_EXECUTABLE", "dbt"),
        ),
    },
)