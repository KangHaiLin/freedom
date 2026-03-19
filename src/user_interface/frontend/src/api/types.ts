/**
 * API 类型定义
 * 严格匹配后端 Pydantic 模型
 */

// 通用响应格式
export interface BaseResponse<T> {
  code: number;
  message: string;
  data: T;
  success: boolean;
}

// 分页响应
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

// 实时行情
export interface RealtimeQuote {
  code: string;
  name: string;
  price: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  amount: number;
  change: number;
  change_pct: number;
  timestamp: string;
}

// K线数据
export interface DailyKline {
  code: string;
  trade_date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  amount: number;
  pct_change: number;
}

// 分钟K线数据
export interface MinuteKline {
  code: string;
  trade_time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  amount: number;
}

// 基本面数据
export interface StockBasic {
  code: string;
  name: string;
  industry: string;
  area: string;
  market: string;
  list_date: string;
}

export interface FinancialReport {
  code: string;
  report_date: string;
  net_profit: number;
  eps: number;
  roe: number;
  revenue: number;
  total_assets: number;
  debt_ratio: number;
}

// 系统监控指标
export interface SystemMetrics {
  cpu: {
    percent: number;
    count: number;
    per_cpu: number[];
  };
  memory: {
    total: number;
    used: number;
    percent: number;
    available: number;
  };
  disk: {
    total: number;
    used: number;
    percent: number;
  };
  network: {
    bytes_sent: number;
    bytes_recv: number;
    pack_sent: number;
    pack_recv: number;
  };
  timestamp: number;
}

export interface ApplicationMetrics {
  requests: {
    total: number;
    errors: number;
    qps: number;
    error_rate: number;
    latency_avg: number;
    latency_p95: number;
    latency_p99: number;
  };
}

export interface HealthStatus {
  status: 'ok' | 'warning' | 'critical';
  checks: Record<string, HealthCheck>;
  overall_healthy: boolean;
}

export interface HealthCheck {
  name: string;
  status: 'ok' | 'warning' | 'critical';
  message: string;
  last_check: string;
  details?: Record<string, any>;
}

// 数据源状态
export interface DataSourceStatus {
  name: string;
  available: boolean;
  last_update: string;
  latency_ms: number;
  message: string;
}

// 回测任务状态
export interface BacktestTask {
  id: string;
  name: string;
  strategy: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  start_time: string;
  end_time?: string;
  result?: BacktestResult;
}

export interface BacktestResult {
  total_return: number;
  annual_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  trade_count: number;
}

// WebSocket 消息类型
export interface WsMessage {
  type: string;
  data: any;
  timestamp: number;
}

export interface WsQuoteUpdate extends WsMessage {
  type: 'quote';
  data: RealtimeQuote;
}

export interface WsSubscribe {
  action: 'subscribe' | 'unsubscribe';
  codes: string[];
}

// 查询参数
export interface KlineQueryParams {
  code: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  freq?: '1d' | '1m' | '5m' | '15m';
}

export interface StockSearchParams {
  keyword: string;
  limit?: number;
}

// 投资组合/账户相关
export interface PositionInfo {
  ts_code: string;
  name?: string;
  quantity: number;
  avg_cost: number;
  last_price: number;
  market_value: number;
  cost: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  realized_pnl: number;
}

export interface AccountSummary {
  initial_cash: number;
  current_cash: number;
  total_asset: number;
  total_market_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  daily_pnl: number;
  daily_pnl_pct: number;
  position_count: number;
}

export interface AssetAllocation {
  name: string;
  value: number;
  color?: string;
}

export interface EquityCurvePoint {
  date: string;
  value: number;
}

export interface PortfolioDashboard {
  account_summary: AccountSummary;
  asset_allocation: AssetAllocation[];
  top_holdings: PositionInfo[];
  equity_curve: EquityCurvePoint[];
}
