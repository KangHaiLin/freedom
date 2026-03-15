-- ClickHouse测试库初始化脚本

CREATE DATABASE IF NOT EXISTS stock_test;
USE stock_test;

-- 分钟线行情表
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
ORDER BY (stock_code, trade_time)
TTL trade_time + INTERVAL 1 YEAR;

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
ORDER BY (stock_code, trade_time)
TTL trade_time + INTERVAL 3 MONTH;

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

-- 测试数据插入
INSERT INTO market_minute_quote (stock_code, trade_time, open, high, low, close, volume, amount) VALUES
('000001.SZ', '2023-01-01 09:30:00', 10.0, 10.1, 9.9, 10.0, 10000, 100000),
('000001.SZ', '2023-01-01 09:31:00', 10.0, 10.2, 10.0, 10.1, 12000, 121200),
('000001.SZ', '2023-01-01 09:32:00', 10.1, 10.3, 10.1, 10.2, 15000, 153000);
