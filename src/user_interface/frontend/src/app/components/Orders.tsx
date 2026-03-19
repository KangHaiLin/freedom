import { Card } from "./ui/card";
import { Badge } from "./ui/badge";
import { Input } from "./ui/input";
import { Search } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import { useState, useEffect } from 'react';
import { message } from 'antd';
import { OrderInfo, OrderStatistics } from '@/api/types';
import {
  getTodayOrders,
  getPendingOrders,
  getHistoryOrders,
  getOrderStatistics,
  cancelOrder,
} from '@/api/orders';

// 映射后端side到前端显示类型
const mapSideToType = (side: string): string => {
  return side === 'BUY' ? '买入' : '卖出';
};

// 映射后端status到前端显示状态
const mapStatusToDisplay = (status: string): string => {
  const statusMap: Record<string, string> = {
    'PENDING': '待提交',
    'SUBMITTED': '待成交',
    'PARTIAL': '部分成交',
    'FILLED': '已成交',
    'CANCELLED': '已撤单',
    'REJECTED': '已拒绝',
  };
  return statusMap[status] || status;
};

export default function Orders() {
  const [todayOrders, setTodayOrders] = useState<OrderInfo[]>([]);
  const [pendingOrders, setPendingOrders] = useState<OrderInfo[]>([]);
  const [historyOrders, setHistoryOrders] = useState<OrderInfo[]>([]);
  const [statistics, setStatistics] = useState<OrderStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchKeyword, setSearchKeyword] = useState('');

  // 加载所有数据
  const loadAllData = async () => {
    try {
      setLoading(true);
      const [today, pending, historyStats, history] = await Promise.all([
        getTodayOrders(),
        getPendingOrders(),
        getOrderStatistics(),
        getHistoryOrders(1, 20),
      ]);
      setTodayOrders(today);
      setPendingOrders(pending);
      setHistoryOrders(history.items);
      setStatistics(historyStats);
    } catch (error) {
      console.error('加载订单数据失败', error);
      message.error('加载订单数据失败');
    } finally {
      setLoading(false);
    }
  };

  // 处理撤单
  const handleCancel = async (orderId: string) => {
    try {
      await cancelOrder(orderId);
      message.success('撤单成功');
      // 重新加载数据
      loadAllData();
    } catch (error) {
      console.error('撤单失败', error);
      // 错误已经在api拦截器处理了
    }
  };

  // 获取显示时间（从iso字符串提取时分秒）
  const getDisplayTime = (isoStr: string | null): string => {
    if (!isoStr) return '';
    const dt = new Date(isoStr);
    return dt.toTimeString().slice(0, 8);
  };

  // 获取显示日期
  const getDisplayDate = (isoStr: string | null): string => {
    if (!isoStr) return '';
    return isoStr.slice(0, 10);
  };

  // 计算今日成交额格式化
  const getFormattedTodayAmount = (): string => {
    if (!statistics) return '¥0';
    if (statistics.today_amount >= 1000000) {
      return `¥${(statistics.today_amount / 1000).toFixed(1)}K`;
    }
    return `¥${statistics.today_amount.toLocaleString()}`;
  };

  // 格式化佣金
  const getFormattedCommission = (): string => {
    if (!statistics) return '¥0';
    return `¥${statistics.today_commission.toFixed(2)}`;
  };

  useEffect(() => {
    loadAllData();
  }, []);

  return (
    <div className="space-y-6">
      {/* 页头 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-100">订单管理</h2>
          <p className="text-gray-300 mt-1">查看和管理您的交易订单</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="搜索订单..."
              className="pl-9 bg-[#1a1a20] border-gray-700 text-gray-100"
            />
          </div>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-[#0f0f14] border-gray-800 p-5">
          <p className="text-sm text-gray-300 mb-1">今日订单</p>
          <p className="text-3xl font-bold text-gray-100">{statistics?.today_total ?? todayOrders.length}</p>
          <p className="text-xs text-gray-300 mt-1">成交 {statistics?.today_filled ?? todayOrders.filter(o => mapStatusToDisplay(o.status) === "已成交").length} 笔</p>
        </Card>
        <Card className="bg-[#0f0f14] border-gray-800 p-5">
          <p className="text-sm text-gray-300 mb-1">待成交订单</p>
          <p className="text-3xl font-bold text-yellow-400">{statistics?.pending ?? pendingOrders.length}</p>
          <p className="text-xs text-gray-300 mt-1">等待处理中</p>
        </Card>
        <Card className="bg-[#0f0f14] border-gray-800 p-5">
          <p className="text-sm text-gray-300 mb-1">今日成交额</p>
          <p className="text-3xl font-bold text-gray-100">{getFormattedTodayAmount()}</p>
          <p className="text-xs text-green-400 mt-1">{/* +15.2% vs 昨日 留作日后实现 */}</p>
        </Card>
        <Card className="bg-[#0f0f14] border-gray-800 p-5">
          <p className="text-sm text-gray-300 mb-1">今日手续费</p>
          <p className="text-3xl font-bold text-gray-100">{getFormattedCommission()}</p>
          <p className="text-xs text-gray-300 mt-1">佣金率 0.009%</p>
        </Card>
      </div>

      {/* 订单列表 */}
      <Card className="bg-[#0f0f14] border-gray-800">
        <Tabs defaultValue="today" className="w-full">
          <div className="border-b border-gray-800 px-6 pt-6">
            <TabsList className="bg-transparent">
              <TabsTrigger 
                value="today" 
                className="data-[state=active]:bg-[#1a1a20] data-[state=active]:text-blue-400 text-gray-300"
              >
                今日订单
              </TabsTrigger>
              <TabsTrigger 
                value="pending" 
                className="data-[state=active]:bg-[#1a1a20] data-[state=active]:text-blue-400 text-gray-300"
              >
                待成交
              </TabsTrigger>
              <TabsTrigger 
                value="history" 
                className="data-[state=active]:bg-[#1a1a20] data-[state=active]:text-blue-400 text-gray-300"
              >
                历史订单
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="today" className="p-6">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-800">
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-300">时间</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-300">股票名称</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-300">代码</th>
                    <th className="text-center py-3 px-4 text-sm font-medium text-gray-300">类型</th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-gray-300">价格</th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-gray-300">数量</th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-gray-300">成交额</th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-gray-300">手续费</th>
                    <th className="text-center py-3 px-4 text-sm font-medium text-gray-300">状态</th>
                  </tr>
                </thead>
                <tbody>
                  {todayOrders.map((order) => (
                    <tr
                      key={order.order_id}
                      className="border-b border-gray-800/50 hover:bg-[#1a1a20] transition-colors"
                    >
                      <td className="py-3 px-4 text-gray-300">{getDisplayTime(order.created_at)}</td>
                      <td className="py-3 px-4 font-medium text-gray-100">{order.stock_name || '-'}</td>
                      <td className="py-3 px-4 text-gray-300">{order.ts_code}</td>
                      <td className="py-3 px-4 text-center">
                        <span
                          className={`px-2 py-1 text-xs rounded ${
                            mapSideToType(order.side) === "买入"
                              ? "bg-red-500/20 text-red-400"
                              : "bg-green-500/20 text-green-400"
                          }`}
                        >
                          {mapSideToType(order.side)}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right text-gray-100">{(order.filled_avg_price || order.price || 0).toFixed(2)}</td>
                      <td className="py-3 px-4 text-right text-gray-100">{order.filled_quantity.toLocaleString()}</td>
                      <td className="py-3 px-4 text-right text-gray-100">¥{order.filled_notional.toLocaleString()}</td>
                      <td className="py-3 px-4 text-right text-gray-300">
                        ¥{(order.commission || 0).toFixed(2)}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <Badge
                          className={
                            mapStatusToDisplay(order.status) === "已成交"
                              ? "bg-green-500/20 text-green-400"
                              : mapStatusToDisplay(order.status) === "部分成交"
                              ? "bg-yellow-500/20 text-yellow-400"
                              : "bg-gray-500/20 text-gray-300"
                          }
                        >
                          {mapStatusToDisplay(order.status)}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                  {todayOrders.length === 0 && (
                    <tr>
                      <td colSpan={9} className="text-center py-8 text-gray-400">
                        {loading ? '加载中...' : '暂无今日订单'}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </TabsContent>

          <TabsContent value="pending" className="p-6">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-800">
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-300">时间</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-300">股票名称</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-300">代码</th>
                    <th className="text-center py-3 px-4 text-sm font-medium text-gray-300">类型</th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-gray-300">价格</th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-gray-300">数量</th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-gray-300">委托额</th>
                    <th className="text-center py-3 px-4 text-sm font-medium text-gray-300">状态</th>
                    <th className="text-center py-3 px-4 text-sm font-medium text-gray-300">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {pendingOrders.map((order) => (
                    <tr
                      key={order.order_id}
                      className="border-b border-gray-800/50 hover:bg-[#1a1a20] transition-colors"
                    >
                      <td className="py-3 px-4 text-gray-300">{getDisplayTime(order.created_at)}</td>
                      <td className="py-3 px-4 font-medium text-gray-100">{order.stock_name || '-'}</td>
                      <td className="py-3 px-4 text-gray-300">{order.ts_code}</td>
                      <td className="py-3 px-4 text-center">
                        <span
                          className={`px-2 py-1 text-xs rounded ${
                            mapSideToType(order.side) === "买入"
                              ? "bg-red-500/20 text-red-400"
                              : "bg-green-500/20 text-green-400"
                          }`}
                        >
                          {mapSideToType(order.side)}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right text-gray-100">{(order.price || 0).toFixed(2)}</td>
                      <td className="py-3 px-4 text-right text-gray-100">{order.quantity.toLocaleString()}</td>
                      <td className="py-3 px-4 text-right text-gray-100">¥{order.notional.toLocaleString()}</td>
                      <td className="py-3 px-4 text-center">
                        <Badge className="bg-yellow-500/20 text-yellow-400">{mapStatusToDisplay(order.status)}</Badge>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <button
                          onClick={() => handleCancel(order.order_id)}
                          className="px-3 py-1 text-xs bg-red-500/20 text-red-400 rounded hover:bg-red-500/30 transition-colors"
                        >
                          撤单
                        </button>
                      </td>
                    </tr>
                  ))}
                  {pendingOrders.length === 0 && (
                    <tr>
                      <td colSpan={9} className="text-center py-8 text-gray-400">
                        {loading ? '加载中...' : '暂无待成交订单'}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </TabsContent>

          <TabsContent value="history" className="p-6">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-800">
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-300">日期</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-300">股票名称</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-300">代码</th>
                    <th className="text-center py-3 px-4 text-sm font-medium text-gray-300">类型</th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-gray-300">价格</th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-gray-300">数量</th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-gray-300">成交额</th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-gray-300">手续费</th>
                    <th className="text-center py-3 px-4 text-sm font-medium text-gray-300">状态</th>
                  </tr>
                </thead>
                <tbody>
                  {historyOrders.map((order) => (
                    <tr
                      key={order.order_id}
                      className="border-b border-gray-800/50 hover:bg-[#1a1a20] transition-colors"
                    >
                      <td className="py-3 px-4 text-gray-300">{getDisplayDate(order.created_at)}</td>
                      <td className="py-3 px-4 font-medium text-gray-100">{order.stock_name || '-'}</td>
                      <td className="py-3 px-4 text-gray-300">{order.ts_code}</td>
                      <td className="py-3 px-4 text-center">
                        <span
                          className={`px-2 py-1 text-xs rounded ${
                            mapSideToType(order.side) === "买入"
                              ? "bg-red-500/20 text-red-400"
                              : "bg-green-500/20 text-green-400"
                          }`}
                        >
                          {mapSideToType(order.side)}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right text-gray-100">{(order.filled_avg_price || order.price || 0).toFixed(2)}</td>
                      <td className="py-3 px-4 text-right text-gray-100">{order.filled_quantity.toLocaleString()}</td>
                      <td className="py-3 px-4 text-right text-gray-100">¥{order.filled_notional.toLocaleString()}</td>
                      <td className="py-3 px-4 text-right text-gray-300">
                        ¥{(order.commission || 0).toFixed(2)}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <Badge className="bg-blue-500/20 text-blue-400">{mapStatusToDisplay(order.status)}</Badge>
                      </td>
                    </tr>
                  ))}
                  {historyOrders.length === 0 && (
                    <tr>
                      <td colSpan={9} className="text-center py-8 text-gray-400">
                        {loading ? '加载中...' : '暂无历史订单'}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </TabsContent>
        </Tabs>
      </Card>
    </div>
  );
}