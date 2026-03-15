-- PostgreSQL测试库初始化脚本

-- 实时行情表
CREATE TABLE IF NOT EXISTS market_realtime_quote (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(20) NOT NULL,
    time TIMESTAMP NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    open NUMERIC(10, 2),
    high NUMERIC(10, 2),
    low NUMERIC(10, 2),
    volume BIGINT,
    amount NUMERIC(16, 2),
    bid_price1 NUMERIC(10, 2),
    bid_volume1 BIGINT,
    ask_price1 NUMERIC(10, 2),
    ask_volume1 BIGINT,
    source VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_code, time)
);

CREATE INDEX IF NOT EXISTS idx_realtime_stock_time ON market_realtime_quote(stock_code, time DESC);
CREATE INDEX IF NOT EXISTS idx_realtime_time ON market_realtime_quote(time DESC);

-- 日线行情表
CREATE TABLE IF NOT EXISTS market_daily_quote (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    open NUMERIC(10, 2) NOT NULL,
    high NUMERIC(10, 2) NOT NULL,
    low NUMERIC(10, 2) NOT NULL,
    close NUMERIC(10, 2) NOT NULL,
    volume BIGINT NOT NULL,
    amount NUMERIC(16, 2),
    adjust_factor NUMERIC(10, 4) DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_code, trade_date)
);

CREATE INDEX IF NOT EXISTS idx_daily_stock_date ON market_daily_quote(stock_code, trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_date ON market_daily_quote(trade_date DESC);

-- 财务数据表
CREATE TABLE IF NOT EXISTS financial_statement (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(20) NOT NULL,
    report_date DATE NOT NULL,
    report_type VARCHAR(20) NOT NULL,
    revenue NUMERIC(20, 2),
    net_profit NUMERIC(20, 2),
    eps NUMERIC(10, 4),
    roe NUMERIC(10, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_code, report_date, report_type)
);

-- 测试数据插入
INSERT INTO market_realtime_quote (stock_code, time, price, open, high, low, volume) VALUES
('000001.SZ', '2023-01-01 09:30:00', 10.0, 9.8, 10.1, 9.7, 100000),
('600000.SH', '2023-01-01 09:30:00', 15.0, 14.8, 15.2, 14.7, 200000)
ON CONFLICT DO NOTHING;

INSERT INTO market_daily_quote (stock_code, trade_date, open, high, low, close, volume) VALUES
('000001.SZ', '2023-01-01', 9.8, 10.5, 9.7, 10.2, 1000000),
('000001.SZ', '2023-01-02', 10.2, 10.8, 10.0, 10.5, 1200000),
('000001.SZ', '2023-01-03', 10.5, 11.0, 10.3, 10.8, 1500000),
('000001.SZ', '2023-01-04', 10.8, 11.2, 10.6, 11.0, 1300000),
('000001.SZ', '2023-01-05', 11.0, 11.5, 10.8, 11.3, 1800000)
ON CONFLICT DO NOTHING;
