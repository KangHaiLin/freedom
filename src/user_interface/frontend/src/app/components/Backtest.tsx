import { Card } from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Play, RotateCcw, Download } from "lucide-react";
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

const backtestResults = [
  { date: "2023-01", portfolio: 1000000, benchmark: 1000000 },
  { date: "2023-02", portfolio: 1050000, benchmark: 1020000 },
  { date: "2023-03", portfolio: 1120000, benchmark: 1050000 },
  { date: "2023-04", portfolio: 1080000, benchmark: 1030000 },
  { date: "2023-05", portfolio: 1150000, benchmark: 1070000 },
  { date: "2023-06", portfolio: 1230000, benchmark: 1100000 },
  { date: "2023-07", portfolio: 1280000, benchmark: 1140000 },
  { date: "2023-08", portfolio: 1250000, benchmark: 1120000 },
  { date: "2023-09", portfolio: 1320000, benchmark: 1160000 },
  { date: "2023-10", portfolio: 1380000, benchmark: 1190000 },
  { date: "2023-11", portfolio: 1450000, benchmark: 1230000 },
  { date: "2023-12", portfolio: 1520000, benchmark: 1270000 },
  { date: "2024-01", portfolio: 1580000, benchmark: 1300000 },
  { date: "2024-02", portfolio: 1640000, benchmark: 1340000 },
  { date: "2024-03", portfolio: 1720000, benchmark: 1380000 },
];

const drawdownData = [
  { date: "2023-01", drawdown: 0 },
  { date: "2023-02", drawdown: -2.5 },
  { date: "2023-03", drawdown: 0 },
  { date: "2023-04", drawdown: -3.6 },
  { date: "2023-05", drawdown: 0 },
  { date: "2023-06", drawdown: 0 },
  { date: "2023-07", drawdown: 0 },
  { date: "2023-08", drawdown: -2.3 },
  { date: "2023-09", drawdown: 0 },
  { date: "2023-10", drawdown: 0 },
  { date: "2023-11", drawdown: 0 },
  { date: "2023-12", drawdown: 0 },
  { date: "2024-01", drawdown: 0 },
  { date: "2024-02", drawdown: 0 },
  { date: "2024-03", drawdown: -1.2 },
];

const monthlyReturns = [
  { month: "01", returns: 5.0 },
  { month: "02", returns: 6.7 },
  { month: "03", returns: -3.6 },
  { month: "04", returns: 6.5 },
  { month: "05", returns: 7.0 },
  { month: "06", returns: 4.3 },
  { month: "07", returns: -2.3 },
  { month: "08", returns: 5.6 },
  { month: "09", returns: 4.5 },
  { month: "10", returns: 5.2 },
  { month: "11", returns: 4.8 },
  { month: "12", returns: 5.5 },
];

const tradeHistory = [
  { date: "2024-03-15", stock: "贵州茅台", action: "买入", price: 1678.00, quantity: 100, profit: "+15,234" },
  { date: "2024-03-14", stock: "宁德时代", action: "卖出", price: 245.60, quantity: 500, profit: "-2,340" },
  { date: "2024-03-13", stock: "比亚迪", action: "买入", price: 276.80, quantity: 300, profit: "+8,760" },
  { date: "2024-03-12", stock: "隆基绿能", action: "卖出", price: 33.20, quantity: 1000, profit: "+4,560" },
  { date: "2024-03-11", stock: "中国平安", action: "买入", price: 55.40, quantity: 800, profit: "+6,780" },
];

export default function Backtest() {
  return (
    <div className="space-y-6">
      {/* 页头 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-100">策略回测</h2>
          <p className="text-gray-300 mt-1">基于历史数据测试策略性能</p>
        </div>
      </div>

      {/* 回测配置 */}
      <Card className="bg-[#0f0f14] border-gray-800 p-6">
        <h3 className="text-lg font-semibold mb-4 text-gray-100">回测配置</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="space-y-2">
            <Label htmlFor="strategy" className="text-gray-300">策略选择</Label>
            <select
              id="strategy"
              className="w-full px-3 py-2 bg-[#1a1a20] border border-gray-700 rounded-lg text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option>动量策略A</option>
              <option>均值回归B</option>
              <option>套利策略C</option>
              <option>趋势跟踪D</option>
            </select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="start-date" className="text-gray-300">开始日期</Label>
            <Input
              id="start-date"
              type="date"
              defaultValue="2023-01-01"
              className="bg-[#1a1a20] border-gray-700 text-gray-100"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="end-date" className="text-gray-300">结束日期</Label>
            <Input
              id="end-date"
              type="date"
              defaultValue="2024-03-17"
              className="bg-[#1a1a20] border-gray-700 text-gray-100"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="capital" className="text-gray-300">初始资金</Label>
            <Input
              id="capital"
              type="text"
              defaultValue="1,000,000"
              className="bg-[#1a1a20] border-gray-700 text-gray-100"
            />
          </div>
        </div>
        <div className="flex items-center gap-3 mt-6">
          <Button className="bg-blue-600 hover:bg-blue-700">
            <Play className="h-4 w-4 mr-2" />
            开始回测
          </Button>
          <Button variant="outline" className="border-gray-700">
            <RotateCcw className="h-4 w-4 mr-2" />
            重置
          </Button>
          <Button variant="outline" className="border-gray-700">
            <Download className="h-4 w-4 mr-2" />
            导出报告
          </Button>
        </div>
      </Card>

      {/* 回测统计 */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <Card className="bg-[#0f0f14] border-gray-800 p-4">
          <p className="text-xs text-gray-300 mb-1">总收益率</p>
          <p className="text-xl font-bold text-red-400">+72.0%</p>
        </Card>
        <Card className="bg-[#0f0f14] border-gray-800 p-4">
          <p className="text-xs text-gray-300 mb-1">年化收益</p>
          <p className="text-xl font-bold text-gray-100">+48.3%</p>
        </Card>
        <Card className="bg-[#0f0f14] border-gray-800 p-4">
          <p className="text-xs text-gray-300 mb-1">夏普比率</p>
          <p className="text-xl font-bold text-gray-100">2.45</p>
        </Card>
        <Card className="bg-[#0f0f14] border-gray-800 p-4">
          <p className="text-xs text-gray-300 mb-1">最大回撤</p>
          <p className="text-xl font-bold text-green-400">-3.6%</p>
        </Card>
        <Card className="bg-[#0f0f14] border-gray-800 p-4">
          <p className="text-xs text-gray-300 mb-1">胜率</p>
          <p className="text-xl font-bold text-gray-100">73.5%</p>
        </Card>
        <Card className="bg-[#0f0f14] border-gray-800 p-4">
          <p className="text-xs text-gray-300 mb-1">交易次数</p>
          <p className="text-xl font-bold text-gray-100">156</p>
        </Card>
      </div>

      {/* 权益曲线对比 */}
      <Card className="bg-[#0f0f14] border-gray-800 p-6">
        <h3 className="text-lg font-semibold mb-4 text-gray-100">权益曲线对比</h3>
        <ResponsiveContainer width="100%" height={350}>
          <AreaChart data={backtestResults}>
            <defs>
              <linearGradient id="colorPortfolio" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorBenchmark" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6b7280" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#6b7280" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="date" stroke="#9ca3af" style={{ fontSize: "12px" }} />
            <YAxis stroke="#9ca3af" style={{ fontSize: "12px" }} />
            <Tooltip
              contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #4b5563", borderRadius: "8px", color: "#e5e7eb" }}
              labelStyle={{ color: "#d1d5db" }}
            />
            <Legend />
            <Area
              type="monotone"
              dataKey="portfolio"
              name="策略收益"
              stroke="#3b82f6"
              fillOpacity={1}
              fill="url(#colorPortfolio)"
              strokeWidth={2}
            />
            <Area
              type="monotone"
              dataKey="benchmark"
              name="基准收益"
              stroke="#6b7280"
              fillOpacity={1}
              fill="url(#colorBenchmark)"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </Card>

      {/* 回撤分析和月度收益 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="bg-[#0f0f14] border-gray-800 p-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-100">回撤分析</h3>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={drawdownData}>
              <defs>
                <linearGradient id="colorDrawdown" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="date" stroke="#9ca3af" style={{ fontSize: "12px" }} />
              <YAxis stroke="#9ca3af" style={{ fontSize: "12px" }} />
              <Tooltip
                contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #4b5563", borderRadius: "8px", color: "#e5e7eb" }}
              />
              <Area
                type="monotone"
                dataKey="drawdown"
                stroke="#ef4444"
                fillOpacity={1}
                fill="url(#colorDrawdown)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        <Card className="bg-[#0f0f14] border-gray-800 p-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-100">月度收益率</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={monthlyReturns}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="month" stroke="#9ca3af" style={{ fontSize: "12px" }} />
              <YAxis stroke="#9ca3af" style={{ fontSize: "12px" }} />
              <Tooltip
                contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #4b5563", borderRadius: "8px", color: "#e5e7eb" }}
              />
              <Bar dataKey="returns" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      {/* 交易记录 */}
      <Card className="bg-[#0f0f14] border-gray-800 p-6">
        <h3 className="text-lg font-semibold mb-4 text-gray-100">交易记录</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-300">日期</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-300">股票</th>
                <th className="text-center py-3 px-4 text-sm font-medium text-gray-300">操作</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-300">价格</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-300">数量</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-300">盈亏</th>
              </tr>
            </thead>
            <tbody>
              {tradeHistory.map((trade, idx) => (
                <tr key={idx} className="border-b border-gray-800/50 hover:bg-[#1a1a20] transition-colors">
                  <td className="py-3 px-4 text-gray-300">{trade.date}</td>
                  <td className="py-3 px-4 font-medium text-gray-100">{trade.stock}</td>
                  <td className="py-3 px-4 text-center">
                    <span
                      className={`px-2 py-1 text-xs rounded ${
                        trade.action === "买入"
                          ? "bg-red-500/20 text-red-400"
                          : "bg-green-500/20 text-green-400"
                      }`}
                    >
                      {trade.action}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right text-gray-100">{trade.price.toFixed(2)}</td>
                  <td className="py-3 px-4 text-right text-gray-100">{trade.quantity}</td>
                  <td
                    className={`py-3 px-4 text-right font-semibold ${
                      trade.profit.startsWith("+") ? "text-red-400" : "text-green-400"
                    }`}
                  >
                    {trade.profit}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}