-- Idempotent incremental load: re-running a batch never duplicates trades.
-- Dimension lookups are point-in-time, so a trade keeps the attributes valid when it executed.
INSERT INTO marts.fact_trade
SELECT t.trade_id,
       CAST(strftime(t.executed_at, '%Y%m%d') AS INTEGER),
       i.instrument_sk, a.account_sk, t.side, t.quantity, t.price,
       round(t.price * t.quantity, 2), t.fees, t.executed_at, now()
FROM staging.trades t
JOIN marts.dim_instrument i ON i.symbol = t.symbol
     AND t.executed_at::DATE BETWEEN i.valid_from AND i.valid_to
JOIN marts.dim_account a ON a.account_id = t.account_id
     AND t.executed_at::DATE BETWEEN a.valid_from AND a.valid_to
ON CONFLICT (trade_id) DO NOTHING;
