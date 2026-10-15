-- SCD Type 2: expire current rows whose attributes changed, then insert new versions.
-- $batch_date is bound by the loader.
UPDATE marts.dim_instrument d
SET valid_to = $batch_date - INTERVAL 1 DAY, is_current = FALSE
FROM staging.instruments s
WHERE d.symbol = s.symbol AND d.is_current
  AND d.row_hash <> md5(concat_ws('|', s.name, s.sector, s.asset_class));

INSERT INTO marts.dim_instrument (symbol, name, sector, asset_class, valid_from, row_hash)
SELECT s.symbol, s.name, s.sector, s.asset_class, $batch_date,
       md5(concat_ws('|', s.name, s.sector, s.asset_class))
FROM staging.instruments s
LEFT JOIN marts.dim_instrument d ON d.symbol = s.symbol AND d.is_current
WHERE d.symbol IS NULL;
