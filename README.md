# trade-data-warehouse

A Kimball-style dimensional warehouse for trading data, built with SQL on DuckDB and exportable to Parquet so Trino (Presto) can query it in place.

## Posting skills this demonstrates

From JPMorgan Chase's **Lead Data Engineer** posting:

| Posting asks for | Where it shows up here |
| --- | --- |
| In-depth knowledge of data warehousing solutions and ETL processes | A nightly ELT (`loader.py`): extract, land in `staging`, transform into `marts` inside one transaction |
| Strong experience with relational databases; strong database and data modeling skills | A star schema in `sql/schema.sql` with a transaction-grain fact, a periodic-snapshot fact, surrogate keys and a date dimension |
| Data lifecycle; data quality and integrity | SCD Type 2 history, point-in-time joins, idempotent re-runs, a batch audit log, and reconciliation tests |
| Experience with Trino / Presto | `trino/` contains a Hive connector catalog and DDL that query the exported Parquet marts |
| Parquet | `export_parquet()` writes every mart as zstd Parquet |
| Git and CI/CD | GitHub Actions runs the tests and a full 5-day load on every push |

## The model

```
                 dim_date
                    │
dim_account ──── fact_trade ──── dim_instrument        (transaction grain)
  (SCD2)            │               (SCD2)
                    └── fact_position_daily            (periodic snapshot: account × symbol × day)
```

* **SCD Type 2.** When an instrument's sector or an account's risk tier changes, the current row is expired and a new version is inserted. Changes are detected by comparing a hash of the attributes. The simulated source reclassifies META to Communication Services on 2026-10-07 and moves ACC-002 from HIGH to MEDIUM risk on 2026-10-08.
* **Point-in-time joins.** Each trade binds to the dimension version that was valid when it executed. Historical reports therefore don't change when master data does. The `sector_notional_by_week` query shows META's notional split across two sectors.
* **Idempotent loads.** `ON CONFLICT DO NOTHING` on the fact and delete-then-insert on the snapshot mean a re-run batch never double-counts.
* **Atomic batches.** Staging, dimensions, facts and the audit log commit together or not at all.

## Run it

```bash
pip install -e ".[dev]"
make load      # loads 5 nightly batches, exports Parquet to ./exports
make report    # runs sql/analytics/*.sql and shows SCD2 history
make test
```

```
{'batch_date': datetime.date(2026, 10, 7), 'trades_loaded': 200, 'instruments_changed': 1, 'accounts_changed': 0}
{'batch_date': datetime.date(2026, 10, 8), 'trades_loaded': 200, 'instruments_changed': 0, 'accounts_changed': 1}

== dim_instrument history (SCD2) ==
│ META    │ Technology             │ 2026-10-05 │ 2026-10-06 │ false      │
│ META    │ Communication Services │ 2026-10-07 │ 9999-12-31 │ true       │
```

### Query it with Trino

```bash
make load && make trino
docker exec -it trino trino -f /etc/trino/init.sql                    # registers the Parquet marts, runs a sample star-join
docker exec -it trino trino --catalog lake --schema marts
```

## Layout

```
sql/schema.sql            DDL for staging + marts
sql/marts/NN_*.sql        transforms, run in order for each batch ($batch_date is bound by the loader)
sql/analytics/*.sql       business queries over the star schema
src/warehouse/source.py   simulated OLTP source with master-data changes
src/warehouse/loader.py   ELT orchestration, audit log, Parquet export
trino/                    Trino catalog + external table DDL
```
