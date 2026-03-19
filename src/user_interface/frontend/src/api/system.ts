/**
 * 系统管理 API
 */
import { apiGet } from './client';
import { BacktestTask } from './types';

// 获取系统信息
export const getSystemInfo = async () => {
  return apiGet<{
    version: string;
    python_version: string;
    os: string;
    start_time: string;
    uptime_seconds: number;
  }>('/system/info');
};

// 获取回测任务列表
export const getBacktestTasks = async () => {
  return apiGet<BacktestTask[]>('/system/backtest-tasks');
};

// 获取回测任务详情
export const getBacktestTask = async (taskId: string) => {
  return apiGet<BacktestTask>(`/system/backtest-tasks/${taskId}`);
};

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

// 创建回测任务
export const createBacktestTask = async (name: string, strategyId: string) => {
  return apiGet<BacktestTask>(`/system/backtest-tasks?name=${name}&strategy_id=${strategyId}`);
};

// 触发系统诊断
export const runDiagnostic = async () => {
  return apiGet<{
    report_url: string;
    issues: number;
    recommendations: string[];
  }>('/system/diagnostic');
};
