-- Kimball star schema. Surrogate keys on every dimension, SCD Type 2 where history matters.
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;

CREATE SEQUENCE IF NOT EXISTS marts.seq_instrument_sk START 1;
CREATE SEQUENCE IF NOT EXISTS marts.seq_account_sk START 1;

CREATE TABLE IF NOT EXISTS marts.dim_date (
    date_sk      INTEGER PRIMARY KEY,         -- yyyymmdd
    full_date    DATE NOT NULL UNIQUE,
    year         SMALLINT, quarter SMALLINT, month SMALLINT, day_of_week VARCHAR,
    is_weekend   BOOLEAN
);

CREATE TABLE IF NOT EXISTS marts.dim_instrument (       -- SCD Type 2
    instrument_sk BIGINT PRIMARY KEY DEFAULT nextval('marts.seq_instrument_sk'),
    symbol        VARCHAR NOT NULL,               -- natural key
    name          VARCHAR, sector VARCHAR, asset_class VARCHAR,
    valid_from    DATE NOT NULL,
    valid_to      DATE NOT NULL DEFAULT DATE '9999-12-31',
    is_current    BOOLEAN NOT NULL DEFAULT TRUE,
    row_hash      VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS marts.dim_account (          -- SCD Type 2
    account_sk    BIGINT PRIMARY KEY DEFAULT nextval('marts.seq_account_sk'),
    account_id    VARCHAR NOT NULL,
    account_name  VARCHAR, segment VARCHAR, risk_tier VARCHAR,
    valid_from    DATE NOT NULL,
    valid_to      DATE NOT NULL DEFAULT DATE '9999-12-31',
    is_current    BOOLEAN NOT NULL DEFAULT TRUE,
    row_hash      VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS marts.fact_trade (           -- transaction grain: one row per trade
    trade_id      VARCHAR PRIMARY KEY,
    date_sk       INTEGER NOT NULL REFERENCES marts.dim_date(date_sk),
    instrument_sk BIGINT NOT NULL REFERENCES marts.dim_instrument(instrument_sk),
    account_sk    BIGINT NOT NULL REFERENCES marts.dim_account(account_sk),
    side          VARCHAR NOT NULL,
    quantity      INTEGER NOT NULL,
    price         DECIMAL(18,4) NOT NULL,
    gross_amount  DECIMAL(18,2) NOT NULL,
    fees          DECIMAL(18,2) NOT NULL,
    executed_at   TIMESTAMP NOT NULL,
    loaded_at     TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS marts.fact_position_daily (  -- periodic snapshot grain: account x instrument x day
    date_sk       INTEGER NOT NULL,
    account_id    VARCHAR NOT NULL,
    symbol        VARCHAR NOT NULL,
    net_quantity  BIGINT NOT NULL,
    cost_basis    DECIMAL(18,2) NOT NULL,
    PRIMARY KEY (date_sk, account_id, symbol)
);

CREATE TABLE IF NOT EXISTS marts.etl_batch_log (
    batch_date DATE PRIMARY KEY, trades_loaded INTEGER, instruments_changed INTEGER,
    accounts_changed INTEGER, finished_at TIMESTAMP
);
