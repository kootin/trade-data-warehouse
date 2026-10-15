-- Rebuild the snapshot for this batch date from all trades to date (cumulative).
DELETE FROM marts.fact_position_daily WHERE date_sk = CAST(strftime($batch_date, '%Y%m%d') AS INTEGER);

INSERT INTO marts.fact_position_daily
SELECT CAST(strftime($batch_date, '%Y%m%d') AS INTEGER), a.account_id, i.symbol,
       sum(CASE f.side WHEN 'BUY' THEN f.quantity ELSE -f.quantity END),
       sum(CASE f.side WHEN 'BUY' THEN f.gross_amount ELSE -f.gross_amount END)
FROM marts.fact_trade f
JOIN marts.dim_instrument i USING (instrument_sk)
JOIN marts.dim_account a USING (account_sk)
WHERE f.executed_at::DATE <= $batch_date
GROUP BY ALL;
