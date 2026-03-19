/**
 * 系统监控 API
 */
import { apiGet } from './client';
import {
  SystemMetrics,
  ApplicationMetrics,
  HealthStatus,
  DataSourceStatus,
  AlertRecord,
  MonitorDashboard,
} from './types';

// 获取系统指标快照
export const getSystemMetrics = async () => {
  return apiGet<SystemMetrics>('/monitor/system');
};

// 获取应用指标
export const getApplicationMetrics = async () => {
  return apiGet<ApplicationMetrics>('/monitor/application');
};

// 获取完整健康检查
export const getHealthStatus = async () => {
  return apiGet<HealthStatus>('/monitor/health');
};

// 获取数据源状态列表
export const getDataSourceStatus = async () => {
  return apiGet<DataSourceStatus[]>('/monitor/data-sources');
};

// 获取指标历史数据
export const getMetricsHistory = async (minutes: number = 60) => {
  return apiGet<SystemMetrics[]>(
    '/monitor/history',
    { params: { minutes } }
  );
};

// 获取监控面板数据（包含最近告警统计）
export const getMonitorDashboard = async () => {
  return apiGet<MonitorDashboard>('/monitor/dashboard');
};

// 获取最近告警记录
export const getRecentAlerts = async (
  limit: number = 20,
  level?: string
) => {
  return apiGet<AlertRecord[]>(
    '/monitor/alerts',
    { params: { limit, ...(level && { level }) } }
  );
};
