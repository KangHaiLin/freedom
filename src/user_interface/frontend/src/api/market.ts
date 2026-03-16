/**
 * 行情数据 API
 */
import { apiGet } from './client';
import {
  RealtimeQuote,
  DailyKline,
  MinuteKline,
  StockBasic,
  KlineQueryParams,
  StockSearchParams,
  PaginatedResponse,
} from './types';

// 搜索股票
export const searchStocks = async (params: StockSearchParams) => {
  return apiGet<PaginatedResponse<StockBasic>>(
    '/market/search',
    { params }
  );
};

// 获取股票列表
export const getStockList = async (page: number = 1, pageSize: number = 100) => {
  return apiGet<PaginatedResponse<StockBasic>>(
    '/market/stocks',
    { params: { page, page_size: pageSize } }
  );
};

// 获取日K线数据
export const getDailyKline = async (params: KlineQueryParams) => {
  return apiGet<DailyKline[]>('/market/kline/daily', { params });
};

// 获取分钟K线数据
export const getMinuteKline = async (params: KlineQueryParams) => {
  return apiGet<MinuteKline[]>('/market/kline/minute', { params });
};

// 获取实时行情
export const getRealtimeQuotes = async (codes: string[]) => {
  return apiGet<RealtimeQuote[]>(
    '/market/quotes',
    { params: { codes: codes.join(',') } }
  );
};

// 获取单只股票实时行情
export const getRealtimeQuote = async (code: string) => {
  return apiGet<RealtimeQuote>(`/market/quote/${code}`);
};
