-- Exposure by the account's risk tier *as of each trade*, with a running total.
SELECT d.full_date, a.risk_tier, sum(f.gross_amount) AS daily_notional,
       sum(sum(f.gross_amount)) OVER (PARTITION BY a.risk_tier ORDER BY d.full_date) AS running_notional
FROM marts.fact_trade f
JOIN marts.dim_account a USING (account_sk)
JOIN marts.dim_date d USING (date_sk)
GROUP BY d.full_date, a.risk_tier ORDER BY d.full_date, a.risk_tier;
