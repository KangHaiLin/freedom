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

// 触发系统诊断
export const runDiagnostic = async () => {
  return apiGet<{
    report_url: string;
    issues: number;
    recommendations: string[];
  }>('/system/diagnostic');
};
