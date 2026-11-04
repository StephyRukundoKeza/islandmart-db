    # IslandMart pipeline shortcuts. Run from the project root, e.g. `make all`.
.PHONY: help up down load dbt test docs dashboard airflow-build airflow-up airflow-down all

help:
	@echo "make up             start the IslandMart Postgres database"
	@echo "make load           load the DummyJSON API and Postgres into DuckDB (dlt)"
	@echo "make dbt            build and test all dbt models"
	@echo "make test           run dbt tests only"
	@echo "make docs           generate and open the dbt docs"
	@echo "make dashboard      open the Streamlit dashboard"
	@echo "make airflow-build  build the custom Airflow image"
	@echo "make airflow-up     start Airflow (http://localhost:8080)"
	@echo "make airflow-down   stop Airflow"
	@echo "make all            start Postgres, load, then build with dbt"

up:
	docker compose up -d

down:
	docker compose down

load:
	uv run python/dlt_dummyjson.py
	uv run python/dlt_islandmart_postgres.py

dbt:
	cd islandmart_dbt && dbt build

test:
	cd islandmart_dbt && dbt test

docs:
	cd islandmart_dbt && dbt docs generate && dbt docs serve

dashboard:
	uv run streamlit run python/dashboard.py

airflow-build:
	cd airflow && docker compose build

airflow-up:
	cd airflow && docker compose up -d

airflow-down:
	cd airflow && docker compose down

all: up load dbt