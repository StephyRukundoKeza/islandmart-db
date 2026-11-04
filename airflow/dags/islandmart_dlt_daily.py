"""Daily DAG: load IslandMart's Postgres data into the DuckDB warehouse with dlt."""
from datetime import datetime, timedelta

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag

PROJECT_DIR = "/opt/islandmart"


@dag(
    schedule="@daily",
    start_date=datetime(2026, 11, 1),
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=2)},
    tags=["islandmart", "dlt"],
)
def islandmart_dlt_daily():
    BashOperator(
        task_id="load_postgres_to_duckdb",
        bash_command=f"cd {PROJECT_DIR} && python python/dlt_islandmart_postgres.py",
        env={"DB_HOST": "host.docker.internal", "DB_PORT": "5433"},
        append_env=True,
    )


islandmart_dlt_daily()