CREATE SCHEMA IF NOT EXISTS lake.marts;

CREATE TABLE IF NOT EXISTS lake.marts.fact_trade (
    trade_id VARCHAR, date_sk INTEGER, instrument_sk BIGINT, account_sk BIGINT, side VARCHAR,
    quantity INTEGER, price DECIMAL(18,4), gross_amount DECIMAL(18,2), fees DECIMAL(18,2),
    executed_at TIMESTAMP(6), loaded_at TIMESTAMP(6)
) WITH (format = 'PARQUET', external_location = 'local:///data/fact_trade');

CREATE TABLE IF NOT EXISTS lake.marts.dim_instrument (
    instrument_sk BIGINT, symbol VARCHAR, name VARCHAR, sector VARCHAR, asset_class VARCHAR,
    valid_from DATE, valid_to DATE, is_current BOOLEAN, row_hash VARCHAR
) WITH (format = 'PARQUET', external_location = 'local:///data/dim_instrument');

CREATE TABLE IF NOT EXISTS lake.marts.dim_account (
    account_sk BIGINT, account_id VARCHAR, account_name VARCHAR, segment VARCHAR, risk_tier VARCHAR,
    valid_from DATE, valid_to DATE, is_current BOOLEAN, row_hash VARCHAR
) WITH (format = 'PARQUET', external_location = 'local:///data/dim_account');

-- Same star-join, now through Trino:
SELECT i.sector, count(*) AS trades, sum(f.gross_amount) AS notional
FROM lake.marts.fact_trade f
JOIN lake.marts.dim_instrument i ON f.instrument_sk = i.instrument_sk
GROUP BY i.sector ORDER BY notional DESC;
