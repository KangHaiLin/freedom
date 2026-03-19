import { Card } from "./ui/card";
import { Button } from "./ui/button";
import { TrendingUp, PieChart as PieChartIcon } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";

const holdings = [
  {
    name: "贵州茅台",
    code: "600519",
    quantity: 200,
    avgCost: 1678.00,
    currentPrice: 1845.67,
    marketValue: 369134,
    profit: 33534,
    profitPercent: 9.99,
    weight: 18.5,
  },
  {
    name: "宁德时代",
    code: "300750",
    quantity: 1000,
    avgCost: 221.30,
    currentPrice: 234.56,
    marketValue: 234560,
    profit: 13260,
    profitPercent: 5.99,
    weight: 11.8,
  },
  {
    name: "比亚迪",
    code: "002594",
    quantity: 800,
    avgCost: 276.80,
    currentPrice: 287.89,
    marketValue: 230312,
    profit: 8872,
    profitPercent: 4.01,
    weight: 11.6,
  },
  {
    name: "隆基绿能",
    code: "601012",
    quantity: 5000,
    avgCost: 31.20,
    currentPrice: 32.45,
    marketValue: 162250,
    profit: 6250,
    profitPercent: 4.01,
    weight: 8.2,
  },
  {
    name: "中国平安",
    code: "601318",
    quantity: 2500,
    avgCost: 54.60,
    currentPrice: 56.78,
    marketValue: 141950,
    profit: 5450,
    profitPercent: 3.99,
    weight: 7.1,
  },
  {
    name: "招商银行",
    code: "600036",
    quantity: 3000,
    avgCost: 38.20,
    currentPrice: 38.92,
    marketValue: 116760,
    profit: 2160,
    profitPercent: 1.88,
    weight: 5.9,
  },
  {
    name: "五粮液",
    code: "000858",
    quantity: 600,
    avgCost: 175.60,
    currentPrice: 178.34,
    marketValue: 107004,
    profit: 1644,
    profitPercent: 1.56,
    weight: 5.4,
  },
  {
    name: "立讯精密",
    code: "002475",
    quantity: 2800,
    avgCost: 35.80,
    currentPrice: 34.56,
    marketValue: 96768,
    profit: -3472,
    profitPercent: -3.46,
    weight: 4.9,
  },
];

const sectorDistribution = [
  { name: "消费", value: 25.4, color: "#3b82f6" },
  { name: "新能源", value: 22.3, color: "#10b981" },
  { name: "金融", value: 18.7, color: "#f59e0b" },
  { name: "科技", value: 15.2, color: "#8b5cf6" },
  { name: "医药", value: 10.1, color: "#ef4444" },
  { name: "其他", value: 8.3, color: "#6b7280" },
];

const riskMetrics = [
  { name: "组合Beta", value: "0.92", status: "良好" },
  { name: "波动率", value: "18.5%", status: "中等" },
  { name: "相关系数", value: "0.85", status: "正常" },
  { name: "信息比率", value: "1.23", status: "优秀" },
];

export default function Portfolio() {
  const totalMarketValue = holdings.reduce((sum, h) => sum + h.marketValue, 0);
  const totalProfit = holdings.reduce((sum, h) => sum + h.profit, 0);
  const totalProfitPercent = (totalProfit / (totalMarketValue - totalProfit)) * 100;

  return (
    <div className="space-y-6">
      {/* 页头 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-100">持仓管理</h2>
          <p className="text-gray-300 mt-1">查看和管理您的投资组合</p>
        </div>
        <Button className="bg-blue-600 hover:bg-blue-700">
          <PieChartIcon className="h-4 w-4 mr-2" />
          持仓分析
        </Button>
      </div>

      {/* 持仓概览 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-[#0f0f14] border-gray-800 p-6">
          <p className="text-sm text-gray-300 mb-1">总持仓市值</p>
          <p className="text-2xl font-bold text-gray-100">¥{totalMarketValue.toLocaleString()}</p>
          <div className="flex items-center gap-1 mt-2">
            <TrendingUp className="h-4 w-4 text-red-400" />
            <span className="text-sm text-red-400">+5.2% 本周</span>
          </div>
        </Card>
        <Card className="bg-[#0f0f14] border-gray-800 p-6">
          <p className="text-sm text-gray-300 mb-1">总盈亏</p>
          <p className="text-2xl font-bold text-red-400">¥{totalProfit.toLocaleString()}</p>
          <div className="flex items-center gap-1 mt-2">
            <span className="text-sm text-gray-300">盈利比例</span>
            <span className="text-sm text-red-400">87.5%</span>
          </div>
        </Card>
        <Card className="bg-[#0f0f14] border-gray-800 p-6">
          <p className="text-sm text-gray-300 mb-1">持仓收益率</p>
          <p className="text-2xl font-bold text-red-400">+{totalProfitPercent.toFixed(2)}%</p>
          <div className="flex items-center gap-1 mt-2">
            <TrendingUp className="h-4 w-4 text-red-400" />
            <span className="text-sm text-red-400">跑赢大盘2.5%</span>
          </div>
        </Card>
        <Card className="bg-[#0f0f14] border-gray-800 p-6">
          <p className="text-sm text-gray-300 mb-1">持仓股票数</p>
          <p className="text-2xl font-bold text-gray-100">{holdings.length}</p>
          <div className="flex items-center gap-1 mt-2">
            <span className="text-sm text-gray-300">集中度</span>
            <span className="text-sm text-gray-100">适中</span>
          </div>
        </Card>
      </div>

      {/* 行业分布和风险指标 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 bg-[#0f0f14] border-gray-800 p-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-100">行业分布</h3>
          <div className="flex items-center gap-8">
            <ResponsiveContainer width={250} height={250}>
              <PieChart>
                <Pie
                  data={sectorDistribution}
                  cx="50%"
                  cy="50%"
                  innerRadius={70}
                  outerRadius={100}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {sectorDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1f2937",
                    border: "1px solid #4b5563",
                    borderRadius: "8px",
                    color: "#e5e7eb"
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex-1 space-y-3">
              {sectorDistribution.map((sector, idx) => (
                <div key={idx} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div
                      className="h-3 w-3 rounded-full"
                      style={{ backgroundColor: sector.color }}
                    ></div>
                    <span className="text-sm text-gray-200">{sector.name}</span>
                  </div>
                  <span className="text-sm font-semibold text-gray-100">{sector.value}%</span>
                </div>
              ))}
            </div>
          </div>
        </Card>

        <Card className="bg-[#0f0f14] border-gray-800 p-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-100">风险指标</h3>
          <div className="space-y-4">
            {riskMetrics.map((metric, idx) => (
              <div key={idx} className="p-3 rounded-lg bg-[#1a1a20]">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-gray-300">{metric.name}</span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded ${
                      metric.status === "优秀"
                        ? "bg-green-500/20 text-green-400"
                        : metric.status === "良好" || metric.status === "正常"
                        ? "bg-blue-500/20 text-blue-400"
                        : "bg-yellow-500/20 text-yellow-400"
                    }`}
                  >
                    {metric.status}
                  </span>
                </div>
                <p className="text-lg font-semibold text-gray-100">{metric.value}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* 持仓明细 */}
      <Card className="bg-[#0f0f14] border-gray-800 p-6">
        <h3 className="text-lg font-semibold mb-4 text-gray-100">持仓明细</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-300">股票名称</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-300">代码</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-300">持仓数量</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-300">成本价</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-300">现价</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-300">市值</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-300">盈亏</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-300">盈亏比例</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-300">仓位占比</th>
                <th className="text-center py-3 px-4 text-sm font-medium text-gray-300">操作</th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((holding, idx) => (
                <tr
                  key={idx}
                  className="border-b border-gray-800/50 hover:bg-[#1a1a20] transition-colors"
                >
                  <td className="py-3 px-4 font-medium text-gray-100">{holding.name}</td>
                  <td className="py-3 px-4 text-gray-300">{holding.code}</td>
                  <td className="py-3 px-4 text-right text-gray-100">{holding.quantity.toLocaleString()}</td>
                  <td className="py-3 px-4 text-right text-gray-300">
                    {holding.avgCost.toFixed(2)}
                  </td>
                  <td className="py-3 px-4 text-right font-semibold text-gray-100">
                    {holding.currentPrice.toFixed(2)}
                  </td>
                  <td className="py-3 px-4 text-right text-gray-100">
                    ¥{holding.marketValue.toLocaleString()}
                  </td>
                  <td
                    className={`py-3 px-4 text-right font-semibold ${
                      holding.profit > 0 ? "text-red-400" : "text-green-400"
                    }`}
                  >
                    {holding.profit > 0 ? "+" : ""}¥{holding.profit.toLocaleString()}
                  </td>
                  <td
                    className={`py-3 px-4 text-right font-semibold ${
                      holding.profitPercent > 0 ? "text-red-400" : "text-green-400"
                    }`}
                  >
                    {holding.profitPercent > 0 ? "+" : ""}
                    {holding.profitPercent.toFixed(2)}%
                  </td>
                  <td className="py-3 px-4 text-right text-gray-300">{holding.weight}%</td>
                  <td className="py-3 px-4">
                    <div className="flex items-center justify-center gap-2">
                      <button className="px-2 py-1 text-xs bg-blue-500/20 text-blue-400 rounded hover:bg-blue-500/30 transition-colors">
                        调仓
                      </button>
                      <button className="px-2 py-1 text-xs bg-red-500/20 text-red-400 rounded hover:bg-red-500/30 transition-colors">
                        清仓
                      </button>
                    </div>
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