"""Nightly ELT: extract from the source, land in staging, transform into the star schema."""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

import duckdb

from warehouse import source

SQL_DIR = Path(__file__).resolve().parents[2] / "sql"


def connect(db_path: str = "warehouse.duckdb") -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(db_path)
    con.execute((SQL_DIR / "schema.sql").read_text())
    return con


def _run_sql_file(con: duckdb.DuckDBPyConnection, path: Path, batch_date: date) -> None:
    for stmt in filter(str.strip, path.read_text().split(";")):
        params = {"batch_date": batch_date} if "$batch_date" in stmt else None
        con.execute(stmt, params)


def load_batch(con: duckdb.DuckDBPyConnection, batch_date: date, n_trades: int = 200) -> dict:
    extracted = source.extract(batch_date, n_trades)
    con.execute("BEGIN")
    try:
        for name, df in extracted.items():
            con.register(f"_{name}", df)
            con.execute(f"CREATE OR REPLACE TABLE staging.{name} AS SELECT * FROM _{name}")
            con.unregister(f"_{name}")
        before = _version_counts(con)
        for sql_file in sorted((SQL_DIR / "marts").glob("*.sql")):
            _run_sql_file(con, sql_file, batch_date)
        after = _version_counts(con)
        trades = con.execute(
            "SELECT count(*) FROM marts.fact_trade WHERE executed_at::DATE = ?", [batch_date]
        ).fetchone()[0]
        stats = {
            "batch_date": batch_date,
            "trades_loaded": trades,
            # On the first load every row is new; afterwards new versions == changed attributes.
            "instruments_changed": after[0] - before[0] if before[0] else 0,
            "accounts_changed": after[1] - before[1] if before[1] else 0,
        }
        con.execute(
            "INSERT OR REPLACE INTO marts.etl_batch_log VALUES (?, ?, ?, ?, now())",
            [batch_date, stats["trades_loaded"], stats["instruments_changed"], stats["accounts_changed"]],
        )
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return stats


def _version_counts(con) -> tuple[int, int]:
    return con.execute(
        "SELECT (SELECT count(*) FROM marts.dim_instrument), (SELECT count(*) FROM marts.dim_account)"
    ).fetchone()


def export_parquet(con: duckdb.DuckDBPyConnection, out_dir: str) -> None:
    """Export marts as Parquet so Trino (or Spark, Athena) can query them in place."""
    for (table,) in con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'marts'"
    ).fetchall():
        dest = Path(out_dir) / table
        dest.mkdir(parents=True, exist_ok=True)
        con.execute(f"COPY marts.{table} TO '{dest}/data.parquet' (FORMAT parquet, COMPRESSION zstd)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", default="warehouse.duckdb")
    p.add_argument("--start", type=date.fromisoformat, default=date(2026, 10, 5))
    p.add_argument("--days", type=int, default=5)
    p.add_argument("--export", default="exports", help="directory for Parquet exports ('' to skip)")
    a = p.parse_args()
    con = connect(a.db)
    for i in range(a.days):
        print(load_batch(con, a.start + timedelta(days=i)))
    if a.export:
        export_parquet(con, a.export)
        print(f"exported marts to {a.export}/")


if __name__ == "__main__":
    main()
