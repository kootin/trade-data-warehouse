-- SCD Type 2: expire current rows whose attributes changed, then insert new versions.
-- $batch_date is bound by the loader.
UPDATE marts.dim_account d
SET valid_to = $batch_date - INTERVAL 1 DAY, is_current = FALSE
FROM staging.accounts s
WHERE d.account_id = s.account_id AND d.is_current
  AND d.row_hash <> md5(concat_ws('|', s.account_name, s.segment, s.risk_tier));

INSERT INTO marts.dim_account (account_id, account_name, segment, risk_tier, valid_from, row_hash)
SELECT s.account_id, s.account_name, s.segment, s.risk_tier, $batch_date,
       md5(concat_ws('|', s.account_name, s.segment, s.risk_tier))
FROM staging.accounts s
LEFT JOIN marts.dim_account d ON d.account_id = s.account_id AND d.is_current
WHERE d.account_id IS NULL;
