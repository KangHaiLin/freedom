/**
 * 回测相关 API
 */
import { apiGet, apiPost } from './client';
import { BacktestTask, BacktestResult } from './types';

// 获取策略列表
export interface StrategyInfo {
  id: string;
  name: string;
  type: string;
  status: string;
  returns: string;
  sharpe: string;
  max_drawdown: string;
  winRate: string;
  positions: number;
  performance: Array<{ date: string; value: number }>;
}

export const getStrategies = async () => {
  return apiGet<StrategyInfo[]>('/system/strategies');
};

// 获取回测任务列表
export const getBacktestTasks = async () => {
  return apiGet<BacktestTask[]>('/system/backtest-tasks');
};

// 获取回测任务详情
export const getBacktestTask = async (taskId: string) => {
  return apiGet<BacktestTask>(`/system/backtest-tasks/${taskId}`);
};

// 创建回测任务
export interface CreateBacktestRequest {
  name: string;
  strategy_id: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
}

export const createBacktestTask = async (params: CreateBacktestRequest) => {
  return apiPost<BacktestTask>('/system/backtest-tasks', params);
};

// 获取回测结果详情（包含详细曲线数据）
export interface BacktestResultDetail extends BacktestResult {
  equity_curve: Array<{ date: string; portfolio: number; benchmark: number }>;
  drawdown_curve: Array<{ date: string; drawdown: number }>;
  monthly_returns: Array<{ month: string; returns: number }>;
  trade_history: Array<{
    date: string;
    stock: string;
    action: string;
    price: number;
    quantity: number;
    profit: string;
  }>;
}

export const getBacktestResult = async (taskId: string) => {
  return apiGet<BacktestResultDetail>(`/system/backtest-tasks/${taskId}/result`);
};

// 导出回测报告
export const exportBacktestReport = async (taskId: string) => {
  return apiGet<{ report_url: string }>(`/system/backtest-tasks/${taskId}/export`);
};

// 重置回测配置
export const resetBacktestConfig = () => {
  // 清除本地存储的配置
  localStorage.removeItem('backtest_config');
};

// 保存回测配置到本地
export const saveBacktestConfig = (config: CreateBacktestRequest) => {
  localStorage.setItem('backtest_config', JSON.stringify(config));
};

// 从本地加载回测配置
export const loadBacktestConfig = (): CreateBacktestRequest | null => {
  const saved = localStorage.getItem('backtest_config');
  if (saved) {
    try {
      return JSON.parse(saved);
    } catch {
      return null;
    }
  }
  return null;
};
