/**
 * 订单管理 API
 */
import { apiGet, apiPost } from './client';
import { OrderInfo, OrderStatistics, PaginatedResponse } from './types';

// 获取今日订单列表
export const getTodayOrders = async () => {
  return apiGet<OrderInfo[]>('/orders/today');
};

// 获取待成交订单列表
export const getPendingOrders = async () => {
  return apiGet<OrderInfo[]>('/orders/pending');
};

// 获取历史订单列表
export const getHistoryOrders = async (page: number = 1, pageSize: number = 20) => {
  return apiGet<PaginatedResponse<OrderInfo>>(
    '/orders/history',
    { params: { page, page_size: pageSize } }
  );
};

// 获取订单统计信息
export const getOrderStatistics = async () => {
  return apiGet<OrderStatistics>('/orders/statistics');
};

// 取消订单
export const cancelOrder = async (orderId: string) => {
  return apiPost<void>('/orders/cancel', { order_id: orderId });
};

// 搜索订单
export const searchOrders = async (keyword: string) => {
  return apiGet<OrderInfo[]>(
    '/orders/search',
    { params: { keyword } }
  );
};
