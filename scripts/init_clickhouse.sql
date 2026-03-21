-- ClickHouse测试库初始化脚本

CREATE DATABASE IF NOT EXISTS stock_test;
USE stock_test;

-- 日线行情表
CREATE TABLE IF NOT EXISTS daily_market_data
(
    trade_date Date,
    stock_code String,
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    volume UInt64,
    amount Float64,
    adjust_factor Float64,
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(trade_date)
ORDER BY (trade_date, stock_code)
SETTINGS index_granularity = 8192;

-- 1分钟线行情表
CREATE TABLE IF NOT EXISTS minute1_market_data
(
    trade_time DateTime,
    stock_code String,
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    volume UInt64,
    amount Float64,
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(trade_time)
ORDER BY (trade_time, stock_code)
SETTINGS index_granularity = 8192;

-- 5分钟线行情表
CREATE TABLE IF NOT EXISTS minute5_market_data
(
    trade_time DateTime,
    stock_code String,
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    volume UInt64,
    amount Float64,
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(trade_time)
ORDER BY (trade_time, stock_code)
SETTINGS index_granularity = 8192;

-- 15分钟线行情表
CREATE TABLE IF NOT EXISTS minute15_market_data
(
    trade_time DateTime,
    stock_code String,
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    volume UInt64,
    amount Float64,
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(trade_time)
ORDER BY (trade_time, stock_code)
SETTINGS index_granularity = 8192;

-- 30分钟线行情表
CREATE TABLE IF NOT EXISTS minute30_market_data
(
    trade_time DateTime,
    stock_code String,
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    volume UInt64,
    amount Float64,
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(trade_time)
ORDER BY (trade_time, stock_code)
SETTINGS index_granularity = 8192;

-- 60分钟线行情表
CREATE TABLE IF NOT EXISTS minute60_market_data
(
    trade_time DateTime,
    stock_code String,
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    volume UInt64,
    amount Float64,
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(trade_time)
ORDER BY (trade_time, stock_code)
SETTINGS index_granularity = 8192;

-- Tick行情表
CREATE TABLE IF NOT EXISTS tick_market_data
(
    trade_time DateTime64(3),
    stock_code String,
    price Float64,
    volume Int64,
    amount Float64,
    bid_price1 Float64,
    bid_volume1 Int64,
    ask_price1 Float64,
    ask_volume1 Int64,
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(trade_time)
ORDER BY (trade_time, stock_code)
SETTINGS index_granularity = 8192;

-- 旧版分钟线行情表（保留用于兼容）
CREATE TABLE IF NOT EXISTS market_minute_quote
(
    stock_code String,
    trade_time DateTime,
    open Float64,
    high Float64,
    low Float64,
    close Float64,
    volume Int64,
    amount Float64
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(trade_time)
ORDER BY (stock_code, trade_time);

-- Tick行情表
CREATE TABLE IF NOT EXISTS market_tick_quote
(
    stock_code String,
    trade_time DateTime64(3),
    price Float64,
    volume Int64,
    amount Float64,
    bid_price1 Float64,
    bid_volume1 Int64,
    ask_price1 Float64,
    ask_volume1 Int64
)
ENGINE = MergeTree
PARTITION BY toYYYYMMDD(trade_time)
ORDER BY (stock_code, trade_time);

-- 采集日志表
CREATE TABLE IF NOT EXISTS collection_log
(
    id String,
    source String,
    stock_code String,
    data_type String,
    status String,
    error_msg String,
    response_time Int64,
    create_time DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(create_time)
ORDER BY (source, create_time);
