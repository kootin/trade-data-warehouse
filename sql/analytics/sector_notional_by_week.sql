-- Point-in-time attribution: META trades before 2026-10-07 stay in Technology.
SELECT i.sector, d.year, weekofyear(d.full_date) AS week, sum(f.gross_amount) AS notional
FROM marts.fact_trade f
JOIN marts.dim_instrument i USING (instrument_sk)
JOIN marts.dim_date d USING (date_sk)
GROUP BY ALL ORDER BY week, notional DESC;
