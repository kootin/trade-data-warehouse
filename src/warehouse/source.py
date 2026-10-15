"""Simulated operational (OLTP) source system.

Each call to `extract(batch_date)` returns that day's changes the way a CDC or
nightly extract would: new trades, plus instrument and account master-data rows
that may have changed attributes (sector reclassifications, risk tier changes).
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta

import pandas as pd

INSTRUMENTS = {
    "AAPL": ("Apple Inc", "Technology", "Equity"),
    "JPM": ("JPMorgan Chase & Co", "Financials", "Equity"),
    "XOM": ("Exxon Mobil Corp", "Energy", "Equity"),
    "UST10Y": ("US Treasury 10Y", "Government", "Bond"),
    "META": ("Meta Platforms", "Technology", "Equity"),
}
ACCOUNTS = {
    "ACC-001": ("Northwind Pension Fund", "Institutional", "LOW"),
    "ACC-002": ("Contoso Capital", "Hedge Fund", "HIGH"),
    "ACC-003": ("Fabrikam Family Office", "Private Wealth", "MEDIUM"),
}
PRICES = {"AAPL": 190.0, "JPM": 200.0, "XOM": 115.0, "UST10Y": 98.5, "META": 560.0}

# Master-data changes that land on specific batch dates, to exercise SCD Type 2.
CHANGES = {
    date(2026, 10, 7): {"instrument": {"META": ("Meta Platforms", "Communication Services", "Equity")}},
    date(2026, 10, 8): {"account": {"ACC-002": ("Contoso Capital", "Hedge Fund", "MEDIUM")}},
}


def extract(batch_date: date, n_trades: int = 200, seed: int | None = None) -> dict[str, pd.DataFrame]:
    rng = random.Random(seed if seed is not None else batch_date.toordinal())
    instruments = dict(INSTRUMENTS)
    accounts = dict(ACCOUNTS)
    for d, change in sorted(CHANGES.items()):
        if d <= batch_date:
            instruments.update(change.get("instrument", {}))
            accounts.update(change.get("account", {}))

    inst_df = pd.DataFrame(
        [(s, *v, batch_date) for s, v in instruments.items()],
        columns=["symbol", "name", "sector", "asset_class", "extracted_on"],
    )
    acct_df = pd.DataFrame(
        [(a, *v, batch_date) for a, v in accounts.items()],
        columns=["account_id", "account_name", "segment", "risk_tier", "extracted_on"],
    )
    start = datetime.combine(batch_date, datetime.min.time()) + timedelta(hours=13, minutes=30)
    rows = []
    for i in range(n_trades):
        sym = rng.choice(list(instruments))
        rows.append({
            "trade_id": f"{batch_date:%Y%m%d}-{i:05d}",
            "account_id": rng.choice(list(accounts)),
            "symbol": sym,
            "side": rng.choice(["BUY", "SELL"]),
            "quantity": rng.randint(1, 500),
            "price": round(PRICES[sym] * (1 + rng.gauss(0, 0.01)), 4),
            "fees": round(rng.uniform(0.5, 15), 2),
            "executed_at": start + timedelta(seconds=rng.randrange(6 * 3600 + 1800)),
        })
    return {"instruments": inst_df, "accounts": acct_df, "trades": pd.DataFrame(rows)}
