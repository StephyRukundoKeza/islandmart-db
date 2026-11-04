"""Daily IslandMart ELT: load the API and the app database with dlt, then build and test with dbt."""
import logging
from datetime import datetime, timedelta
from pathlib import Path

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import dag

PROJECT_DIR = "/opt/islandmart"
DBT_DIR = f"{PROJECT_DIR}/islandmart_dbt"
ALERT_LOG = Path(PROJECT_DIR) / "logs" / "airflow_alerts.log"
PG_ENV = {"DB_HOST": "host.docker.internal", "DB_PORT": "5433"}

log = logging.getLogger(__name__)


def alert_on_failure(context):
    """Runs when a task has failed for the last time (after all its retries)."""
    ti = context["ti"]
    message = (
        f"{datetime.now():%Y-%m-%d %H:%M:%S} FAILED: dag={ti.dag_id} task={ti.task_id} "
        f"run={ti.run_id} error={context.get('exception')}"
    )
    log.error(message)
    ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with ALERT_LOG.open("a", encoding="utf-8") as f:
        f.write(message + "\n")


@dag(
    dag_id="islandmart_elt_daily",
    schedule="@daily",
    start_date=datetime(2026, 11, 1),
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=2),
        "on_failure_callback": alert_on_failure,
    },
    tags=["islandmart", "dlt", "dbt"],
)
def islandmart_elt_daily():
    load_api = BashOperator(
        task_id="load_dummyjson_api",
        bash_command=f"cd {PROJECT_DIR} && python python/dlt_dummyjson.py",
    )

    load_postgres = BashOperator(
        task_id="load_postgres_to_duckdb",
        bash_command=f"cd {PROJECT_DIR} && python python/dlt_islandmart_postgres.py",
        env=PG_ENV,
        append_env=True,
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=(
            f"cd {DBT_DIR} && dbt build "
            "--exclude-resource-type test --exclude-resource-type unit_test"
        ),
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_DIR} && dbt test",
    )

    load_api >> load_postgres >> dbt_build >> dbt_test


islandmart_elt_daily()