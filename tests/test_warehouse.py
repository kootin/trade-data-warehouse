from datetime import date

import pytest

from warehouse.loader import connect, export_parquet, load_batch


@pytest.fixture
def con():
    c = connect(":memory:")
    yield c
    c.close()


def load_days(con, *days):
    return [load_batch(con, date(2026, 10, d), n_trades=50) for d in days]


def test_scd2_creates_new_version_and_expires_old(con):
    load_days(con, 5, 6, 7)
    rows = con.execute(
        "SELECT sector, valid_from, valid_to, is_current FROM marts.dim_instrument "
        "WHERE symbol = 'META' ORDER BY valid_from"
    ).fetchall()
    assert rows == [
        ("Technology", date(2026, 10, 5), date(2026, 10, 6), False),
        ("Communication Services", date(2026, 10, 7), date(9999, 12, 31), True),
    ]
    # Exactly one current row per natural key.
    assert con.execute(
        "SELECT max(c) FROM (SELECT count(*) c FROM marts.dim_instrument WHERE is_current GROUP BY symbol)"
    ).fetchone()[0] == 1


def test_facts_join_point_in_time_dimension_version(con):
    load_days(con, 5, 6, 7, 8)
    bad = con.execute("""
        SELECT count(*) FROM marts.fact_trade f JOIN marts.dim_instrument i USING (instrument_sk)
        WHERE f.executed_at::DATE NOT BETWEEN i.valid_from AND i.valid_to
    """).fetchone()[0]
    assert bad == 0
    tiers = con.execute("""
        SELECT DISTINCT f.executed_at::DATE < DATE '2026-10-08' AS before_change, a.risk_tier
        FROM marts.fact_trade f JOIN marts.dim_account a USING (account_sk)
        WHERE a.account_id = 'ACC-002' ORDER BY 1
    """).fetchall()
    assert tiers == [(False, "MEDIUM"), (True, "HIGH")]


def test_reloading_a_batch_is_idempotent(con):
    load_days(con, 5)
    first = con.execute("SELECT count(*), sum(gross_amount) FROM marts.fact_trade").fetchone()
    load_days(con, 5)
    assert con.execute("SELECT count(*), sum(gross_amount) FROM marts.fact_trade").fetchone() == first
    assert con.execute("SELECT count(*) FROM marts.dim_instrument").fetchone()[0] == 5


def test_change_counts_logged(con):
    stats = load_days(con, 5, 6, 7, 8)
    assert [s["instruments_changed"] for s in stats] == [0, 0, 1, 0]
    assert [s["accounts_changed"] for s in stats] == [0, 0, 0, 1]


def test_position_snapshot_reconciles_to_facts(con):
    load_days(con, 5, 6)
    snap = con.execute("SELECT sum(net_quantity) FROM marts.fact_position_daily WHERE date_sk = 20261006").fetchone()[0]
    facts = con.execute(
        "SELECT sum(CASE side WHEN 'BUY' THEN quantity ELSE -quantity END) FROM marts.fact_trade"
    ).fetchone()[0]
    assert snap == facts


def test_export_parquet(con, tmp_path):
    load_days(con, 5)
    export_parquet(con, str(tmp_path))
    assert (tmp_path / "fact_trade" / "data.parquet").exists()
    n = con.execute(f"SELECT count(*) FROM '{tmp_path}/fact_trade/data.parquet'").fetchone()[0]
    assert n == 50


def test_analytics_queries_run(con):
    from warehouse.loader import SQL_DIR

    load_days(con, 5, 6, 7, 8)
    for f in sorted((SQL_DIR / "analytics").glob("*.sql")):
        assert con.sql(f.read_text()).fetchall(), f.name
