/**
 * 投资组合/账户 API
 */
import { apiGet } from './client';
import {
  AccountSummary,
  PositionInfo,
  AssetAllocation,
  EquityCurvePoint,
  PortfolioDashboard,
} from './types';

// 获取仪表盘数据（账户汇总、资产配置、重仓持股、权益曲线）
export const getPortfolioDashboard = async () => {
  return apiGet<PortfolioDashboard>('/portfolio/dashboard');
};

// 获取账户汇总信息
export const getAccountSummary = async () => {
  return apiGet<AccountSummary>('/portfolio/summary');
};

// 获取资产配置数据
export const getAssetAllocation = async () => {
  return apiGet<AssetAllocation[]>('/portfolio/asset-allocation');
};

// 获取权益曲线历史数据
export const getEquityCurve = async (days: number = 90) => {
  return apiGet<EquityCurvePoint[]>(
    '/portfolio/equity-curve',
    { params: { days } }
  );
};

// 获取所有持仓列表
export const getTopHoldings = async (limit: number = 10) => {
  return apiGet<PositionInfo[]>(
    '/portfolio/top-holdings',
    { params: { limit } }
  );
};
