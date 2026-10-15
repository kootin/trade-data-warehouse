"""Run the analytics queries in sql/analytics against the warehouse."""
import argparse

import duckdb

from warehouse.loader import SQL_DIR


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", default="warehouse.duckdb")
    a = p.parse_args()
    con = duckdb.connect(a.db, read_only=True)
    for f in sorted((SQL_DIR / "analytics").glob("*.sql")):
        print(f"\n== {f.stem} ==")
        con.sql(f.read_text()).show(max_rows=12)
    print("\n== dim_instrument history (SCD2) ==")
    con.sql("SELECT symbol, sector, valid_from, valid_to, is_current FROM marts.dim_instrument "
            "WHERE symbol IN (SELECT symbol FROM marts.dim_instrument GROUP BY 1 HAVING count(*) > 1)").show()


if __name__ == "__main__":
    main()
