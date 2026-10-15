.PHONY: install load report trino test clean
install:
	pip install -e ".[dev]"
load:
	python -m warehouse.loader --db warehouse.duckdb --days 5 --export exports
report:
	python -m warehouse.report --db warehouse.duckdb
trino:
	docker compose -f trino/docker-compose.yml up -d
test:
	pytest -q
clean:
	rm -rf warehouse.duckdb* exports
