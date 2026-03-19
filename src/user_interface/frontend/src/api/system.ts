/**
 * 系统管理 API
 */
import { apiGet } from './client';
import { BacktestTask, SystemStatus, UserInfo } from './types';

// 获取系统状态
export const getSystemStatus = async () => {
  return apiGet<SystemStatus>('/system/status');
};

// 获取系统配置
export const getSystemConfig = async () => {
  return apiGet<Record<string, any>>('/system/config');
};

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

// 获取存储健康状态
export const getStorageHealth = async () => {
  return apiGet<Record<string, any>>('/system/storage_health');
};

// 获取数据源健康状态
export const getDataSourceHealth = async () => {
  return apiGet<Record<string, any>>('/system/data_source_health');
};

// 获取当前用户信息
// 注意：当前系统使用API Key认证，这里从本地存储获取用户名信息
export const getCurrentUserInfo = async (): Promise<UserInfo> => {
  // 实际项目中应从后端验证获取用户信息
  // 这里我们基于API Key的存在性返回
  const apiKey = localStorage.getItem('quant_api_key');
  return {
    username: localStorage.getItem('quant_username') || '用户',
    role: localStorage.getItem('quant_user_role') || 'user',
    api_key_valid: !!apiKey,
  };
};

// 保存用户信息到本地（登录后调用）
export const saveUserInfo = (username: string, role: string = 'user') => {
  localStorage.setItem('quant_username', username);
  localStorage.setItem('quant_user_role', role);
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
