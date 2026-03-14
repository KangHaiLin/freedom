# 接口规范设计

## 1. 接口总体规范
### 1.1 设计原则
- **RESTful风格**：所有对外API遵循RESTful设计规范，语义清晰
- **版本控制**：API地址包含版本号，如`/api/v1/...`
- **统一返回格式**：所有接口返回统一的JSON格式，包含状态码、消息、数据
- **安全认证**：所有接口需要身份认证，采用JWT Token机制
- **限流机制**：根据用户等级和接口重要性设置不同的限流策略
- **幂等性**：所有写操作接口保证幂等性，重复调用不会产生副作用

### 1.2 统一返回格式
```json
{
  "code": 200,          // 状态码，200表示成功，其他表示错误
  "message": "success", // 提示信息
  "data": {},           // 返回数据，成功时返回，失败时可返回null
  "request_id": "xxx",  // 请求ID，用于问题排查
  "timestamp": 1234567890 // 时间戳
}
```

### 1.3 错误码规范
| 错误码 | 含义 | 说明 |
|--------|------|------|
| 200 | 成功 | 请求处理成功 |
| 400 | 请求参数错误 | 参数缺失、格式错误等 |
| 401 | 未认证 | 未登录或Token过期 |
| 403 | 无权限 | 权限不足，无法访问该资源 |
| 404 | 资源不存在 | 请求的资源不存在 |
| 429 | 请求过于频繁 | 触发限流机制 |
| 500 | 服务器内部错误 | 服务器处理异常 |
| 503 | 服务不可用 | 服务维护或过载 |

### 1.4 认证机制
1. 客户端通过登录接口获取JWT Token
2. 后续所有请求在Header中携带`Authorization: Bearer {token}`
3. Token有效期为2小时，过期后需要使用Refresh Token刷新
4. 关键操作（如下单、修改策略）需要二次验证，采用动态验证码或UKey

### 1.5 签名验证机制
为防止数据篡改和重放攻击，所有敏感接口（交易、资金、策略修改）必须进行签名验证：

#### 签名算法
1. 所有请求参数按字典序排序，拼接成字符串
2. 加上时间戳（timestamp，精确到秒）和随机数（nonce）
3. 使用分配给用户的Secret Key进行HMAC-SHA256签名
4. 签名结果放在请求Header的`X-Signature`字段中

#### 验证规则
1. 时间戳有效期为5分钟，超过5分钟的请求直接拒绝
2. 随机数10分钟内不可重复，防止重放攻击
3. 服务端重新计算签名，与客户端传的签名比对，不一致则拒绝请求

#### 签名示例
```python
import hmac
import hashlib
import time
import random

def generate_signature(params, secret_key):
    # 1. 参数按字典序排序
    sorted_params = sorted(params.items(), key=lambda x: x[0])
    # 2. 拼接参数
    param_str = '&'.join([f"{k}={v}" for k, v in sorted_params])
    # 3. 加时间戳和随机数
    timestamp = str(int(time.time()))
    nonce = str(random.randint(100000, 999999))
    sign_str = f"{param_str}&timestamp={timestamp}&nonce={nonce}"
    # 4. HMAC-SHA256签名
    signature = hmac.new(secret_key.encode(), sign_str.encode(), hashlib.sha256).hexdigest()
    return signature, timestamp, nonce
```

### 1.6 限流降级策略
#### 限流规则
采用令牌桶算法实现限流，根据用户等级设置不同阈值：
| 用户等级 | 接口类型 | 限流阈值 |
|----------|----------|----------|
| 普通用户 | 查询类接口 | 100次/分钟 |
| 普通用户 | 操作类接口 | 20次/分钟 |
| VIP用户 | 查询类接口 | 1000次/分钟 |
| VIP用户 | 操作类接口 | 200次/分钟 |
| 机构用户 | 查询类接口 | 10000次/分钟 |
| 机构用户 | 操作类接口 | 2000次/分钟 |

#### 降级策略
系统负载过高时，按优先级自动降级非核心接口：
1. 一级降级（CPU>70%）：禁用回测历史数据导出功能
2. 二级降级（CPU>80%）：禁用非实时行情查询，仅保留最新行情
3. 三级降级（CPU>90%）：禁用策略回测功能，保障实盘交易
4. 四级降级（CPU>95%）：仅保留核心交易功能，其他全部降级

#### 限流响应
触发限流时返回429状态码，响应格式：
```json
{
  "code": 429,
  "message": "请求过于频繁，请稍后再试",
  "data": {
    "retry_after": 60 // 60秒后重试
  },
  "request_id": "xxx",
  "timestamp": 1710000000
}
```

## 2. 对外REST API规范
### 2.1 用户管理接口
| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 用户登录 | POST | /api/v1/auth/login | 用户登录获取Token |
| 用户登出 | POST | /api/v1/auth/logout | 用户登出 |
| 刷新Token | POST | /api/v1/auth/refresh | 刷新访问Token |
| 获取用户信息 | GET | /api/v1/user/info | 获取当前用户信息 |
| 修改用户密码 | PUT | /api/v1/user/password | 修改用户密码 |

#### 登录接口示例
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "test_user",
  "password": "password123"
}

Response:
{
  "code": 200,
  "message": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 7200,
    "user_info": {
      "user_id": 1001,
      "username": "test_user",
      "role": "quant_researcher"
    }
  },
  "request_id": "req-123456",
  "timestamp": 1710000000
}
```

### 2.2 行情数据接口
| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 获取最新行情 | GET | /api/v1/market/realtime/{stock_code} | 获取单只股票最新行情 |
| 批量获取行情 | POST | /api/v1/market/realtime/batch | 批量获取多只股票最新行情 |
| 获取历史日线 | GET | /api/v1/market/daily/{stock_code} | 获取股票历史日线数据 |
| 获取历史分钟线 | GET | /api/v1/market/minute/{stock_code} | 获取股票历史分钟线数据 |
| 获取K线数据 | GET | /api/v1/market/kline/{stock_code} | 获取不同周期的K线数据 |

### 2.3 策略管理接口
| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 获取策略列表 | GET | /api/v1/strategy/list | 获取当前用户的策略列表 |
| 创建策略 | POST | /api/v1/strategy/create | 创建新策略 |
| 获取策略详情 | GET | /api/v1/strategy/{strategy_id} | 获取策略详细信息 |
| 修改策略 | PUT | /api/v1/strategy/{strategy_id} | 修改策略代码和参数 |
| 删除策略 | DELETE | /api/v1/strategy/{strategy_id} | 删除策略 |
| 运行回测 | POST | /api/v1/strategy/{strategy_id}/backtest | 提交回测任务 |
| 获取回测结果 | GET | /api/v1/backtest/{task_id}/result | 获取回测任务结果 |

### 2.4 交易管理接口
| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 下单 | POST | /api/v1/trade/order | 创建新订单 |
| 撤单 | DELETE | /api/v1/trade/order/{order_id} | 撤销未成交订单 |
| 获取订单列表 | GET | /api/v1/trade/orders | 获取订单列表 |
| 获取订单详情 | GET | /api/v1/trade/order/{order_id} | 获取订单详细信息 |
| 获取持仓列表 | GET | /api/v1/trade/positions | 获取当前持仓列表 |
| 获取资金账户 | GET | /api/v1/trade/account | 获取资金账户信息 |
| 获取交易记录 | GET | /api/v1/trade/history | 获取历史交易记录 |

## 3. WebSocket API规范
### 3.1 连接地址
- 生产环境：`wss://api.quant.com/ws/v1`
- 测试环境：`wss://test-api.quant.com/ws/v1`

### 3.2 消息格式
所有消息采用JSON格式，包含消息类型、数据字段：
```json
{
  "type": "message_type",
  "data": {},
  "request_id": "xxx"
}
```

### 3.3 消息类型
| 消息类型 | 方向 | 说明 |
|----------|------|------|
| auth | 客户端→服务端 | 认证消息，携带Token |
| subscribe | 客户端→服务端 | 订阅消息，指定订阅主题 |
| unsubscribe | 客户端→服务端 | 取消订阅消息 |
| ping | 双向 | 心跳检测 |
| pong | 双向 | 心跳响应 |
| quote | 服务端→客户端 | 行情推送消息 |
| order_update | 服务端→客户端 | 订单状态更新消息 |
| alert | 服务端→客户端 | 告警通知消息 |

#### 订阅行情示例
```json
// 客户端发送订阅请求
{
  "type": "subscribe",
  "data": {
    "topic": "quote",
    "symbols": ["600000.SH", "000001.SZ"]
  },
  "request_id": "sub-123456"
}

// 服务端推送行情
{
  "type": "quote",
  "data": {
    "stock_code": "600000.SH",
    "price": 12.34,
    "volume": 123456,
    "timestamp": 1710000000000
  },
  "request_id": "sub-123456"
}
```

### 3.4 连接管理
- 心跳间隔：30秒，超过90秒没有心跳自动断开连接
- 断开重连：客户端需要实现自动重连机制，重连后重新订阅主题
- 消息压缩：支持gzip压缩，减少网络传输量

## 4. 内部服务接口规范
### 4.1 通信协议
内部服务之间采用gRPC通信协议，Protocol Buffers v3作为接口定义语言。

### 4.2 服务定义示例
```proto
syntax = "proto3";

package datamanager;

service DataManager {
  // 获取实时行情
  rpc GetRealtimeQuote(GetRealtimeQuoteRequest) returns (GetRealtimeQuoteResponse);

  // 批量获取实时行情
  rpc BatchGetRealtimeQuote(BatchGetRealtimeQuoteRequest) returns (BatchGetRealtimeQuoteResponse);

  // 查询历史行情
  rpc QueryHistoryQuote(QueryHistoryQuoteRequest) returns (QueryHistoryQuoteResponse);
}

message GetRealtimeQuoteRequest {
  string stock_code = 1;
}

message GetRealtimeQuoteResponse {
  int32 code = 1;
  string message = 2;
  RealtimeQuote data = 3;
}

message RealtimeQuote {
  string stock_code = 1;
  double price = 2;
  double open = 3;
  double high = 4;
  double low = 5;
  int64 volume = 6;
  double amount = 7;
  int64 timestamp = 8;
}
```

### 4.3 服务间调用规范
- 超时设置：所有内部调用设置合理的超时时间，默认5秒，最长不超过30秒
- 重试机制：幂等接口支持重试，非幂等接口禁止重试
- 熔断降级：采用Hystrix实现服务熔断和降级，防止雪崩效应
- 链路追踪：所有调用携带Trace ID，实现全链路追踪

## 5. 对接外部接口规范
### 5.1 市场数据接口
- Wind API：用于获取高质量的基本面数据和历史行情
- Tushare API：用于补充获取行情和财务数据
- 交易所行情接口：用于获取实时Level-2行情数据

### 5.2 券商交易接口
- CTP接口：对接期货公司和证券公司的CTP系统
- PB接口：对接券商的PB系统，实现机构交易
- 券商开放API：对接中小券商的开放交易接口

### 5.3 监管报送接口
- CSRC报送接口：按照监管要求报送交易数据和风控数据
- 交易所报送接口：报送异常交易和大额交易数据

## 6. 接口版本管理
- 新功能开发保持接口向后兼容，旧版本接口至少保留6个月过渡期
- 废弃接口在文档中明确标注废弃时间和替代接口
- 重大版本升级提前3个月通知用户，提供迁移指南
