CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS candles (
    time        TIMESTAMPTZ NOT NULL,
    open        FLOAT8,
    high        FLOAT8,
    low         FLOAT8,
    close       FLOAT8,
    volume      FLOAT8
);
SELECT create_hypertable('candles', 'time', if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS decisions (
    time              TIMESTAMPTZ NOT NULL,
    regime            TEXT,
    buy_score         FLOAT8,
    sell_score        FLOAT8,
    trigger_fired     BOOLEAN,
    ai_action         TEXT,
    ai_confidence     FLOAT8,
    ai_sl             FLOAT8,
    ai_tp             FLOAT8,
    risk_block_reason TEXT
);
SELECT create_hypertable('decisions', 'time', if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS trades (
    id          SERIAL PRIMARY KEY,
    open_time   TIMESTAMPTZ,
    close_time  TIMESTAMPTZ,
    direction   TEXT,
    lot_size    FLOAT8,
    open_price  FLOAT8,
    close_price FLOAT8,
    sl          FLOAT8,
    tp          FLOAT8,
    pnl         FLOAT8,
    result      TEXT
);

CREATE TABLE IF NOT EXISTS system_state (
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO system_state (key, value) VALUES
    ('kill_switch_active', 'false'),
    ('kill_switch_date', ''),
    ('daily_start_balance', '0'),
    ('daily_start_date', '')
ON CONFLICT (key) DO NOTHING;
