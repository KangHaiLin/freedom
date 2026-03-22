import { Card } from "./ui/card";
import { ArrowUpRight, ArrowDownRight, TrendingUp, Activity, DollarSign, Target } from "lucide-react";
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";

const accountData = [
  { name: "账户总值", value: "¥2,456,789", change: "+12.5%", trend: "up", icon: DollarSign },
  { name: "今日收益", value: "¥15,234", change: "+2.3%", trend: "up", icon: TrendingUp },
  { name: "持仓市值", value: "¥1,987,654", change: "-0.8%", trend: "down", icon: Activity },
  { name: "可用资金", value: "¥469,135", change: "0%", trend: "neutral", icon: Target },
];

const equityCurve = [
  { date: "01/01", value: 1000000 },
  { date: "01/08", value: 1050000 },
  { date: "01/15", value: 1120000 },
  { date: "01/22", value: 1080000 },
  { date: "01/29", value: 1150000 },
  { date: "02/05", value: 1200000 },
  { date: "02/12", value: 1280000 },
  { date: "02/19", value: 1350000 },
  { date: "02/26", value: 1420000 },
  { date: "03/05", value: 1480000 },
  { date: "03/12", value: 1520000 },
  { date: "03/17", value: 1587654 },
];

const profitData = [
  { date: "01/01", profit: 5000 },
  { date: "01/08", profit: 8000 },
  { date: "01/15", profit: -3000 },
  { date: "01/22", profit: 12000 },
  { date: "01/29", profit: 6000 },
  { date: "02/05", profit: 15000 },
  { date: "02/12", profit: -2000 },
  { date: "02/19", profit: 18000 },
  { date: "02/26", profit: 9000 },
  { date: "03/05", profit: 11000 },
  { date: "03/12", profit: 14000 },
  { date: "03/17", profit: 7000 },
];

const topHoldings = [
  { name: "贵州茅台", code: "600519", value: 285000, profit: "+15.2%", color: "#10b981" },
  { name: "宁德时代", code: "300750", value: 245000, profit: "+8.7%", color: "#3b82f6" },
  { name: "比亚迪", code: "002594", value: 198000, profit: "-2.3%", color: "#ef4444" },
  { name: "隆基绿能", code: "601012", value: 156000, profit: "+5.1%", color: "#f59e0b" },
  { name: "中国平安", code: "601318", value: 134000, profit: "+3.4%", color: "#8b5cf6" },
];

const strategyPerformance = [
  { name: "动量策略A", returns: "+28.5%", sharpe: "2.34", status: "运行中" },
  { name: "均值回归B", returns: "+15.2%", sharpe: "1.87", status: "运行中" },
  { name: "套利策略C", returns: "+9.8%", sharpe: "2.01", status: "暂停" },
  { name: "趋势跟踪D", returns: "+22.1%", sharpe: "2.15", status: "运行中" },
];

const pieData = [
  { name: "股票", value: 65, color: "#3b82f6" },
  { name: "现金", value: 20, color: "#10b981" },
  { name: "债券", value: 10, color: "#f59e0b" },
  { name: "其他", value: 5, color: "#8b5cf6" },
];

export default function Dashboard() {
  return (
    <div className="space-y-6">
      {/* 账户概览卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {accountData.map((item, index) => (
          <Card key={index} className="bg-[#0f0f14] border-gray-800 p-6">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="text-sm text-gray-300 mb-1">{item.name}</p>
                <p className="text-2xl font-bold mb-2">{item.value}</p>
                <div className="flex items-center gap-1">
                  {item.trend === "up" ? (
                    <ArrowUpRight className="h-4 w-4 text-red-400" />
                  ) : item.trend === "down" ? (
                    <ArrowDownRight className="h-4 w-4 text-green-400" />
                  ) : null}
                  <span
                    className={`text-sm ${
                      item.trend === "up"
                        ? "text-red-400"
                        : item.trend === "down"
                        ? "text-green-400"
                        : "text-gray-300"
                    }`}
                  >
                    {item.change}
                  </span>
                </div>
              </div>
              <div className="p-3 rounded-lg bg-blue-500/10">
                <item.icon className="h-6 w-6 text-blue-400" />
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* 权益曲线和每日收益 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 bg-[#0f0f14] border-gray-800 p-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-100">账户权益曲线</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={equityCurve}>
              <defs>
                <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="date" stroke="#9ca3af" style={{ fontSize: "12px" }} />
              <YAxis stroke="#9ca3af" style={{ fontSize: "12px" }} />
              <Tooltip
                contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #4b5563", borderRadius: "8px", color: "#e5e7eb" }}
                labelStyle={{ color: "#d1d5db" }}
              />
              <Area type="monotone" dataKey="value" stroke="#3b82f6" fillOpacity={1} fill="url(#colorValue)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        <Card className="bg-[#0f0f14] border-gray-800 p-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-100">资产配置</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={5}
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #4b5563", borderRadius: "8px", color: "#e5e7eb" }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="mt-4 space-y-2">
            {pieData.map((item, index) => (
              <div key={index} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full" style={{ backgroundColor: item.color }}></div>
                  <span className="text-gray-300">{item.name}</span>
                </div>
                <span className="font-semibold text-gray-100">{item.value}%</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* 每日盈亏 */}
      <Card className="bg-[#0f0f14] border-gray-800 p-6">
        <h3 className="text-lg font-semibold mb-4 text-gray-100">每日盈亏</h3>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={profitData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="date" stroke="#9ca3af" style={{ fontSize: "12px" }} />
            <YAxis stroke="#9ca3af" style={{ fontSize: "12px" }} />
            <Tooltip
              contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #4b5563", borderRadius: "8px", color: "#e5e7eb" }}
              labelStyle={{ color: "#d1d5db" }}
            />
            <Bar dataKey="profit" fill="#3b82f6" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      {/* 重仓持股和策略表现 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="bg-[#0f0f14] border-gray-800 p-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-100">重仓持股</h3>
          <div className="space-y-3">
            {topHoldings.map((stock, index) => (
              <div key={index} className="flex items-center justify-between p-3 rounded-lg bg-[#1a1a20] hover:bg-[#1f1f26] transition-colors">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-gray-100">{stock.name}</span>
                    <span className="text-xs text-gray-400">{stock.code}</span>
                  </div>
                  <p className="text-sm text-gray-300 mt-1">¥{stock.value.toLocaleString()}</p>
                </div>
                <div className="text-right">
                  <span
                    className={`text-sm font-semibold ${
                      stock.profit.startsWith("+") ? "text-red-400" : "text-green-400"
                    }`}
                  >
                    {stock.profit}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="bg-[#0f0f14] border-gray-800 p-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-100">策略表现</h3>
          <div className="space-y-3">
            {strategyPerformance.map((strategy, index) => (
              <div key={index} className="flex items-center justify-between p-3 rounded-lg bg-[#1a1a20] hover:bg-[#1f1f26] transition-colors">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-gray-100">{strategy.name}</span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded ${
                        strategy.status === "运行中"
                          ? "bg-blue-500/20 text-blue-400"
                          : "bg-gray-500/20 text-gray-300"
                      }`}
                    >
                      {strategy.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 mt-1">
                    <span className="text-sm text-gray-300">收益: {strategy.returns}</span>
                    <span className="text-sm text-gray-300">夏普: {strategy.sharpe}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
