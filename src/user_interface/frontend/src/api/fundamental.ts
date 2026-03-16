/**
 * 基本面数据 API
 */
import { apiGet } from './client';
import { StockBasic, FinancialReport, PaginatedResponse } from './types';

// 获取股票基本面信息
export const getStockBasic = async (code: string) => {
  return apiGet<StockBasic>(`/fundamental/basic/${code}`);
};

// 获取财务报告列表
export const getFinancialReports = async (
  code: string,
  page: number = 1,
  pageSize: number = 20
) => {
  return apiGet<PaginatedResponse<FinancialReport>>(
    `/fundamental/reports/${code}`,
    { params: { page, page_size: pageSize } }
  );
};
