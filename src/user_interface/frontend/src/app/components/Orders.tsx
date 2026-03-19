import { Card } from "./ui/card";
import { Badge } from "./ui/badge";
import { Input } from "./ui/input";
import { Search } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";

const todayOrders = [
  {
    time: "14:32:15",
    stock: "贵州茅台",
    code: "600519",
    type: "买入",
    price: 1845.67,
    quantity: 100,
    amount: 184567,
    status: "已成交",
    commission: 18.46,
  },
  {
    time: "13:45:23",
    stock: "宁德时代",
    code: "300750",
    type: "卖出",
    price: 234.56,
    quantity: 500,
    amount: 117280,
    status: "已成交",
    commission: 11.73,
  },
  {
    time: "11:23:45",
    stock: "比亚迪",
    code: "002594",
    type: "买入",
    price: 287.89,
    quantity: 300,
    amount: 86367,
    status: "已成交",
    commission: 8.64,
  },
  {
    time: "10:15:32",
    stock: "隆基绿能",
    code: "601012",
    type: "买入",
    price: 32.45,
    quantity: 1000,
    amount: 32450,
    status: "部分成交",
    commission: 3.25,
  },
  {
    time: "09:35:18",
    stock: "中国平安",
    code: "601318",
    type: "卖出",
    price: 56.78,
    quantity: 800,
    amount: 45424,
    status: "已撤单",
    commission: 0,
  },
];

const pendingOrders = [
  {
    time: "14:55:32",
    stock: "招商银行",
    code: "600036",
    type: "买入",
    price: 38.92,
    quantity: 1000,
    amount: 38920,
    status: "待成交",
  },
  {
    time: "13:20:15",
    stock: "五粮液",
    code: "000858",
    type: "卖出",
    price: 178.34,
    quantity: 200,
    amount: 35668,
    status: "待成交",
  },
];

const historyOrders = [
  {
    date: "2024-03-16",
    stock: "立讯精密",
    code: "002475",
    type: "买入",
    price: 34.56,
    quantity: 1000,
    amount: 34560,
    status: "已成交",
    commission: 3.46,
  },
  {
    date: "2024-03-15",
    stock: "海天味业",
    code: "603288",
    type: "卖出",
    price: 92.45,
    quantity: 500,
    amount: 46225,
    status: "已成交",
    commission: 4.62,
  },
  {
    date: "2024-03-14",
    stock: "恒瑞医药",
    code: "600276",
    type: "买入",
    price: 67.89,
    quantity: 600,
    amount: 40734,
    status: "已成交",
    commission: 4.07,
  },
  {
    date: "2024-03-13",
    stock: "贵州茅台",
    code: "600519",
    type: "买入",
    price: 1812.34,
    quantity: 100,
    amount: 181234,
    status: "已成交",
    commission: 18.12,
  },
  {
    date: "2024-03-12",
    stock: "宁德时代",
    code: "300750",
    type: "卖出",
    price: 241.23,
    quantity: 500,
    amount: 120615,
    status: "已成交",
    commission: 12.06,
  },
];

export default function Orders() {
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
          <p className="text-3xl font-bold text-gray-100">{todayOrders.length}</p>
          <p className="text-xs text-gray-300 mt-1">成交 {todayOrders.filter(o => o.status === "已成交").length} 笔</p>
        </Card>
        <Card className="bg-[#0f0f14] border-gray-800 p-5">
          <p className="text-sm text-gray-300 mb-1">待成交订单</p>
          <p className="text-3xl font-bold text-yellow-400">{pendingOrders.length}</p>
          <p className="text-xs text-gray-300 mt-1">等待处理中</p>
        </Card>
        <Card className="bg-[#0f0f14] border-gray-800 p-5">
          <p className="text-sm text-gray-300 mb-1">今日成交额</p>
          <p className="text-3xl font-bold text-gray-100">¥466.2K</p>
          <p className="text-xs text-green-400 mt-1">+15.2% vs 昨日</p>
        </Card>
        <Card className="bg-[#0f0f14] border-gray-800 p-5">
          <p className="text-sm text-gray-300 mb-1">今日手续费</p>
          <p className="text-3xl font-bold text-gray-100">¥42.08</p>
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
                  {todayOrders.map((order, idx) => (
                    <tr
                      key={idx}
                      className="border-b border-gray-800/50 hover:bg-[#1a1a20] transition-colors"
                    >
                      <td className="py-3 px-4 text-gray-300">{order.time}</td>
                      <td className="py-3 px-4 font-medium text-gray-100">{order.stock}</td>
                      <td className="py-3 px-4 text-gray-300">{order.code}</td>
                      <td className="py-3 px-4 text-center">
                        <span
                          className={`px-2 py-1 text-xs rounded ${
                            order.type === "买入"
                              ? "bg-red-500/20 text-red-400"
                              : "bg-green-500/20 text-green-400"
                          }`}
                        >
                          {order.type}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right text-gray-100">{order.price.toFixed(2)}</td>
                      <td className="py-3 px-4 text-right text-gray-100">{order.quantity.toLocaleString()}</td>
                      <td className="py-3 px-4 text-right text-gray-100">¥{order.amount.toLocaleString()}</td>
                      <td className="py-3 px-4 text-right text-gray-300">
                        ¥{order.commission.toFixed(2)}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <Badge
                          className={
                            order.status === "已成交"
                              ? "bg-green-500/20 text-green-400"
                              : order.status === "部分成交"
                              ? "bg-yellow-500/20 text-yellow-400"
                              : "bg-gray-500/20 text-gray-300"
                          }
                        >
                          {order.status}
                        </Badge>
                      </td>
                    </tr>
                  ))}
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
                  {pendingOrders.map((order, idx) => (
                    <tr
                      key={idx}
                      className="border-b border-gray-800/50 hover:bg-[#1a1a20] transition-colors"
                    >
                      <td className="py-3 px-4 text-gray-300">{order.time}</td>
                      <td className="py-3 px-4 font-medium text-gray-100">{order.stock}</td>
                      <td className="py-3 px-4 text-gray-300">{order.code}</td>
                      <td className="py-3 px-4 text-center">
                        <span
                          className={`px-2 py-1 text-xs rounded ${
                            order.type === "买入"
                              ? "bg-red-500/20 text-red-400"
                              : "bg-green-500/20 text-green-400"
                          }`}
                        >
                          {order.type}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right text-gray-100">{order.price.toFixed(2)}</td>
                      <td className="py-3 px-4 text-right text-gray-100">{order.quantity.toLocaleString()}</td>
                      <td className="py-3 px-4 text-right text-gray-100">¥{order.amount.toLocaleString()}</td>
                      <td className="py-3 px-4 text-center">
                        <Badge className="bg-yellow-500/20 text-yellow-400">{order.status}</Badge>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <button className="px-3 py-1 text-xs bg-red-500/20 text-red-400 rounded hover:bg-red-500/30 transition-colors">
                          撤单
                        </button>
                      </td>
                    </tr>
                  ))}
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
                  {historyOrders.map((order, idx) => (
                    <tr
                      key={idx}
                      className="border-b border-gray-800/50 hover:bg-[#1a1a20] transition-colors"
                    >
                      <td className="py-3 px-4 text-gray-300">{order.date}</td>
                      <td className="py-3 px-4 font-medium text-gray-100">{order.stock}</td>
                      <td className="py-3 px-4 text-gray-300">{order.code}</td>
                      <td className="py-3 px-4 text-center">
                        <span
                          className={`px-2 py-1 text-xs rounded ${
                            order.type === "买入"
                              ? "bg-red-500/20 text-red-400"
                              : "bg-green-500/20 text-green-400"
                          }`}
                        >
                          {order.type}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right text-gray-100">{order.price.toFixed(2)}</td>
                      <td className="py-3 px-4 text-right text-gray-100">{order.quantity.toLocaleString()}</td>
                      <td className="py-3 px-4 text-right text-gray-100">¥{order.amount.toLocaleString()}</td>
                      <td className="py-3 px-4 text-right text-gray-300">
                        ¥{order.commission.toFixed(2)}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <Badge className="bg-blue-500/20 text-blue-400">{order.status}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </TabsContent>
        </Tabs>
      </Card>
    </div>
  );
}