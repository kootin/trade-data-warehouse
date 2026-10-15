INSERT INTO marts.dim_date
SELECT CAST(strftime(d, '%Y%m%d') AS INTEGER), d::DATE, year(d), quarter(d), month(d),
       dayname(d), dayofweek(d) IN (0, 6)
FROM range(DATE '2026-01-01', DATE '2027-12-31', INTERVAL 1 DAY) t(d)
ON CONFLICT DO NOTHING;
