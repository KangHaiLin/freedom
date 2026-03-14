# 数据库架构设计

## 1. 整体数据库架构
系统采用混合数据库架构，根据不同数据类型和使用场景选择最优数据库解决方案：

```
┌─────────────────────────────────────────────────────┐
│                    数据访问层                       │
└─────────────────┬─────────────────┬─────────────────┘
                  │                 │
┌─────────────────▼─┐ ┌─────────────▼────────────┐ ┌────────────────▼────────────────┐
│   PostgreSQL      │ │      ClickHouse集群       │ │       InfluxDB集群              │
│  (业务关系型数据) │ │  (历史数据分析/回测)      │ │    (实时时序数据存储)           │
└───────────────────┘ └──────────────────────────┘ └─────────────────────────────────┘
```

### 1.1 数据库选型对比
| 数据库 | 适用场景 | 优势 | 劣势 |
|--------|----------|------|------|
| **PostgreSQL 14+** | 用户数据、元数据、策略配置、交易记录等结构化业务数据 | ACID事务支持、SQL标准兼容、丰富的索引类型、扩展性强 | 时序数据写入性能一般 |
| **ClickHouse 23.3+** | 历史行情数据、大规模数据分析、回测数据存储 | 列式存储、超高压缩比、批量查询性能优异、支持SQL | 不支持事务、不适合高频小批量更新 |
| **InfluxDB 2.7+** | 实时行情数据、监控指标数据、高频时间序列数据 | 超高写入性能、时序数据查询优化、内置数据保留策略 | 存储成本较高、不适合复杂分析查询 |
| **Redis 7.0+** | 缓存、会话存储、实时行情快照、消息队列 | 内存级性能、丰富的数据结构、高并发支持 | 数据持久化成本高、存储容量有限 |

## 2. PostgreSQL设计
### 2.1 核心表结构
#### 用户与权限模块
```sql
-- 用户表
CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role_id INTEGER NOT NULL,
    status SMALLINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 角色表
CREATE TABLE roles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL,
    permissions JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 策略管理模块
```sql
-- 策略表
CREATE TABLE strategies (
    strategy_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    strategy_name VARCHAR(100) NOT NULL,
    strategy_code TEXT NOT NULL,
    strategy_type SMALLINT NOT NULL, -- 1:趋势 2:均值回归 3:套利 4:其他
    parameters JSONB NOT NULL,
    status SMALLINT DEFAULT 0, -- 0:草稿 1:测试中 2:已上线 3:已下线
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- 回测任务表
CREATE TABLE backtest_tasks (
    task_id BIGSERIAL PRIMARY KEY,
    strategy_id BIGINT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_capital DECIMAL(18,2) NOT NULL,
    parameters JSONB NOT NULL,
    status SMALLINT DEFAULT 0, -- 0:排队中 1:执行中 2:已完成 3:失败
    result JSONB,
    duration INTEGER, -- 执行时间(秒)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (strategy_id) REFERENCES strategies(strategy_id)
);
```

#### 交易管理模块
```sql
-- 订单表
CREATE TABLE orders (
    order_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    strategy_id BIGINT,
    stock_code VARCHAR(10) NOT NULL,
    order_type SMALLINT NOT NULL, -- 1:买入 2:卖出
    order_price DECIMAL(10,2) NOT NULL,
    order_quantity INTEGER NOT NULL,
    filled_quantity INTEGER DEFAULT 0,
    status SMALLINT DEFAULT 0, -- 0:未报 1:已报 2:部分成交 3:全部成交 4:已撤销 5:废单
    order_time TIMESTAMP NOT NULL,
    completed_time TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (strategy_id) REFERENCES strategies(strategy_id)
);

-- 持仓表
CREATE TABLE positions (
    position_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    stock_code VARCHAR(10) NOT NULL,
    quantity INTEGER NOT NULL,
    available_quantity INTEGER NOT NULL,
    average_cost DECIMAL(10,2) NOT NULL,
    market_value DECIMAL(18,2) NOT NULL,
    profit_loss DECIMAL(18,2) NOT NULL,
    profit_loss_ratio DECIMAL(8,4) NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, stock_code),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

## 3. ClickHouse设计
### 3.1 核心表结构
#### 日线行情表
```sql
CREATE TABLE stock_daily (
    trade_date Date,
    stock_code String,
    open Decimal(10,2),
    high Decimal(10,2),
    low Decimal(10,2),
    close Decimal(10,2),
    volume UInt64,
    amount Decimal(18,2),
    adjust_factor Decimal(8,4),
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(trade_date)
ORDER BY (trade_date, stock_code)
SETTINGS index_granularity = 8192;
```

#### 分钟线行情表
```sql
CREATE TABLE stock_minute (
    trade_time DateTime,
    stock_code String,
    open Decimal(10,2),
    high Decimal(10,2),
    low Decimal(10,2),
    close Decimal(10,2),
    volume UInt64,
    amount Decimal(18,2),
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(trade_time)
ORDER BY (trade_time, stock_code)
SETTINGS index_granularity = 8192;
```

#### Tick行情表
```sql
CREATE TABLE stock_tick (
    trade_time DateTime64(3),
    stock_code String,
    price Decimal(10,2),
    volume UInt32,
    amount Decimal(18,2),
    bid_price1 Decimal(10,2),
    bid_volume1 UInt32,
    ask_price1 Decimal(10,2),
    ask_volume1 UInt32,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(trade_time)
ORDER BY (trade_time, stock_code)
SETTINGS index_granularity = 8192;
```

### 3.2 集群配置
- 3节点ClickHouse集群，1个分片2个副本
- 采用分布式表引擎，支持跨节点查询
- 数据保留策略：Tick数据保留3年，分钟线保留5年，日线永久保留

## 4. InfluxDB设计
### 4.1 数据模型
#### 实时行情测量(measurement)
```
measurement: realtime_quote
tags:
  - stock_code: 股票代码
  - exchange: 交易所(SH/SZ)
fields:
  - price: 当前价格
  - open: 开盘价
  - high: 最高价
  - low: 最低价
  - volume: 成交量
  - amount: 成交额
  - bid_price1: 买一价
  - bid_volume1: 买一量
  - ask_price1: 卖一价
  - ask_volume1: 卖一量
timestamp: 交易时间(毫秒级)
```

#### 系统监控测量(measurement)
```
measurement: system_metrics
tags:
  - host: 主机名
  - service: 服务名
  - metric_type: 指标类型
fields:
  - value: 指标值
timestamp: 采集时间
```

### 4.2 保留策略
- 实时行情数据：保留7天，用于实时行情推送
- 监控指标数据：保留1年，用于系统性能分析
- 数据写入采用批量写入，每1000条批量写入一次，提升性能

## 5. 数据流转设计
```
┌───────────────┐     ┌───────┐     ┌──────────────┐     ┌────────────────┐
│ 数据源        │────▶│ Kafka │────▶│ 实时处理模块 │────▶│ InfluxDB(实时) │
└───────────────┘     └───┬───┘     └──────────────┘     └────────────────┘
                          │
                          ├─────────────────────────────────────────┐
                          ▼                                         ▼
                ┌─────────────────────┐                   ┌───────────────────┐
                │ 批量处理模块        │                   │ 持久化模块        │
                └─────────┬───────────┘                   └─────────┬─────────┘
                          │                                         │
                          ▼                                         ▼
                ┌─────────────────────┐                   ┌───────────────────┐
                │ ClickHouse(历史数据)│                   │ PostgreSQL(业务)  │
                └─────────────────────┘                   └───────────────────┘
```

### 5.1 数据同步策略
- 实时数据：先写入Kafka，然后实时消费写入InfluxDB，延迟<1秒
- 历史数据：T+1日批量将前一日数据从Kafka归档到ClickHouse，数据一致性校验通过后完成
- 业务数据：实时写入PostgreSQL，保证ACID特性
- 缓存策略：热点数据(如最新行情、用户持仓)写入Redis缓存，缓存过期时间根据数据特点设置1秒到5分钟不等

## 6. 备份与恢复
## 6. 数据分片方案
### 6.1 ClickHouse分片策略
采用按日期+股票代码哈希分片方案，支持线性扩展：
- 分片规则：按交易日期月份 + 股票代码前两位哈希值取模
- 分片数量：初始3个分片，每增加50亿条数据增加1个分片
- 副本数量：每个分片2个副本，分布在不同可用区
- 分布式表：采用分布式表引擎对外提供统一查询接口，查询自动路由到对应分片

### 6.2 PostgreSQL分片策略
- 订单表、交易记录表：按月份分表，每年的数据存在单独的分区表中
- 用户表、策略表：数据量较小，不做分片，采用主从复制提高性能
- 分片中间件：采用ShardingSphere-JDBC实现分库分表，对应用透明

### 6.3 扩展能力
- 支持在线扩容，扩容过程不影响业务正常运行
- 数据自动均衡，扩容后数据自动迁移到新分片
- 分片数量最大支持100个，可支持1000亿条以上数据存储

## 7. 冷热数据分层存储策略
### 7.1 数据分层标准
| 数据层级 | 定义 | 存储介质 | 访问性能 |
|----------|------|----------|----------|
| 热数据 | 最近3个月的数据，访问频率高 | 高性能SSD | 毫秒级响应 |
| 温数据 | 3个月-2年的数据，访问频率中等 | 普通SSD | 几十毫秒响应 |
| 冷数据 | 2年以上的数据，访问频率极低 | 低成本SATA HDD/对象存储 | 秒级响应 |

### 7.2 自动流转策略
- 数据写入3个月后，自动从热存储迁移到温存储
- 数据写入2年后，自动从温存储迁移到冷存储
- 冷数据按需加载，访问前自动迁回温存储
- 迁移过程透明，不影响业务查询

### 7.3 成本收益
- 存储成本降低60%以上，冷数据存储成本仅为热数据的1/5
- 热存储性能提升30%，减少冷数据占用高性能存储资源
- 数据生命周期自动化管理，无需人工干预

## 8. 备份与恢复
### 8.1 备份策略
- PostgreSQL：每日全量备份 + 实时WAL日志备份，备份保留30天
- ClickHouse：每周全量备份 + 每日增量备份，备份保留90天
- InfluxDB：实时数据不需要备份，历史数据已同步到ClickHouse
- Redis：持久化采用RDB+AOF混合模式，每日备份一次

### 8.2 恢复目标
- RPO(恢复点目标)：≤5分钟，最多丢失5分钟数据
- RTO(恢复时间目标)：≤4小时，系统可以在4小时内恢复服务

### 8.3 灾备切换验证方案
#### 定期演练
- 每季度进行一次灾备切换演练，验证灾备系统可用性
- 每年进行一次全面的灾难恢复演练，模拟真实故障场景

#### 验证流程
1. **准备阶段**：制定演练计划，通知相关人员，备份当前数据
2. **故障模拟**：模拟主数据中心故障，切断主中心网络
3. **切换操作**：启动灾备切换流程，将流量切换到灾备中心
4. **功能验证**：验证系统功能完整性、数据一致性、性能指标
5. **回切操作**：验证完成后将流量切回主中心，恢复正常运行
6. **总结改进**：编写演练报告，总结问题并优化切换流程

#### 验证指标
- 切换时间：≤4小时，符合RTO目标
- 数据丢失：≤5分钟，符合RPO目标
- 功能可用率：100%，核心功能全部正常
- 性能指标：不低于正常运行时的80%
