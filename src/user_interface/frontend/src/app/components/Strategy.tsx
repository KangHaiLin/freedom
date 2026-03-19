import { Card } from "./ui/card";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Play, Pause, Settings, Plus, TrendingUp, Brain, Zap } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

const strategies = [
  {
    id: 1,
    name: "动量策略A",
    type: "趋势跟踪",
    status: "运行中",
    returns: "+28.5%",
    sharpe: "2.34",
    maxDrawdown: "-8.2%",
    winRate: "68.5%",
    positions: 8,
    icon: TrendingUp,
    color: "blue",
    performance: [
      { date: "01/01", value: 100 },
      { date: "01/15", value: 105 },
      { date: "02/01", value: 110 },
      { date: "02/15", value: 115 },
      { date: "03/01", value: 122 },
      { date: "03/17", value: 128.5 },
    ],
  },
  {
    id: 2,
    name: "均值回归B",
    type: "统计套利",
    status: "运行中",
    returns: "+15.2%",
    sharpe: "1.87",
    maxDrawdown: "-5.6%",
    winRate: "72.3%",
    positions: 12,
    icon: Brain,
    color: "purple",
    performance: [
      { date: "01/01", value: 100 },
      { date: "01/15", value: 103 },
      { date: "02/01", value: 107 },
      { date: "02/15", value: 110 },
      { date: "03/01", value: 113 },
      { date: "03/17", value: 115.2 },
    ],
  },
  {
    id: 3,
    name: "套利策略C",
    type: "市场中性",
    status: "暂停",
    returns: "+9.8%",
    sharpe: "2.01",
    maxDrawdown: "-3.2%",
    winRate: "81.2%",
    positions: 0,
    icon: Zap,
    color: "green",
    performance: [
      { date: "01/01", value: 100 },
      { date: "01/15", value: 102 },
      { date: "02/01", value: 104 },
      { date: "02/15", value: 106 },
      { date: "03/01", value: 108 },
      { date: "03/17", value: 109.8 },
    ],
  },
  {
    id: 4,
    name: "趋势跟踪D",
    type: "趋势跟踪",
    status: "运行中",
    returns: "+22.1%",
    sharpe: "2.15",
    maxDrawdown: "-6.8%",
    winRate: "65.7%",
    positions: 6,
    icon: TrendingUp,
    color: "orange",
    performance: [
      { date: "01/01", value: 100 },
      { date: "01/15", value: 104 },
      { date: "02/01", value: 109 },
      { date: "02/15", value: 114 },
      { date: "03/01", value: 119 },
      { date: "03/17", value: 122.1 },
    ],
  },
];

const strategyTemplates = [
  { name: "双均线策略", description: "经典趋势跟踪策略", difficulty: "简单" },
  { name: "MACD金叉策略", description: "技术指标策略", difficulty: "简单" },
  { name: "布林带突破", description: "波动性突破策略", difficulty: "中等" },
  { name: "网格交易", description: "震荡市场策略", difficulty: "中等" },
  { name: "多因子选股", description: "量化选股策略", difficulty: "复杂" },
  { name: "配对交易", description: "统计套利策略", difficulty: "复杂" },
];

export default function Strategy() {
  return (
    <div className="space-y-6">
      {/* 页头 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-100">策略管理</h2>
          <p className="text-gray-300 mt-1">管理和监控您的量化交易策略</p>
        </div>
        <Button className="bg-blue-600 hover:bg-blue-700">
          <Plus className="h-4 w-4 mr-2" />
          创建新策略
        </Button>
      </div>

      {/* 策略统计 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-[#0f0f14] border-gray-800 p-5">
          <p className="text-sm text-gray-300 mb-1">运行中策略</p>
          <p className="text-3xl font-bold text-gray-100">3</p>
          <p className="text-xs text-green-400 mt-1">+1 本周</p>
        </Card>
        <Card className="bg-[#0f0f14] border-gray-800 p-5">
          <p className="text-sm text-gray-300 mb-1">总收益率</p>
          <p className="text-3xl font-bold text-red-400">+21.9%</p>
          <p className="text-xs text-gray-300 mt-1">本年度</p>
        </Card>
        <Card className="bg-[#0f0f14] border-gray-800 p-5">
          <p className="text-sm text-gray-300 mb-1">平均夏普比率</p>
          <p className="text-3xl font-bold text-gray-100">2.09</p>
          <p className="text-xs text-gray-300 mt-1">所有策略</p>
        </Card>
        <Card className="bg-[#0f0f14] border-gray-800 p-5">
          <p className="text-sm text-gray-300 mb-1">持仓数量</p>
          <p className="text-3xl font-bold text-gray-100">26</p>
          <p className="text-xs text-gray-300 mt-1">当前活跃</p>
        </Card>
      </div>

      {/* 运行中的策略 */}
      <div>
        <h3 className="text-lg font-semibold mb-4 text-gray-100">运行中的策略</h3>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {strategies.map((strategy) => (
            <Card key={strategy.id} className="bg-[#0f0f14] border-gray-800 p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-start gap-3">
                  <div
                    className={`p-2 rounded-lg ${
                      strategy.color === "blue"
                        ? "bg-blue-500/10"
                        : strategy.color === "purple"
                        ? "bg-purple-500/10"
                        : strategy.color === "green"
                        ? "bg-green-500/10"
                        : "bg-orange-500/10"
                    }`}
                  >
                    <strategy.icon
                      className={`h-5 w-5 ${
                        strategy.color === "blue"
                          ? "text-blue-400"
                          : strategy.color === "purple"
                          ? "text-purple-400"
                          : strategy.color === "green"
                          ? "text-green-400"
                          : "text-orange-400"
                      }`}
                    />
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-100">{strategy.name}</h4>
                    <p className="text-sm text-gray-300">{strategy.type}</p>
                  </div>
                </div>
                <Badge
                  className={
                    strategy.status === "运行中"
                      ? "bg-blue-500/20 text-blue-400"
                      : "bg-gray-500/20 text-gray-300"
                  }
                >
                  {strategy.status}
                </Badge>
              </div>

              <div className="grid grid-cols-4 gap-3 mb-4">
                <div>
                  <p className="text-xs text-gray-300">收益率</p>
                  <p className="text-sm font-semibold text-green-400">{strategy.returns}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-300">夏普比率</p>
                  <p className="text-sm font-semibold text-gray-100">{strategy.sharpe}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-300">最大回撤</p>
                  <p className="text-sm font-semibold text-red-400">{strategy.maxDrawdown}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-300">胜率</p>
                  <p className="text-sm font-semibold text-gray-100">{strategy.winRate}</p>
                </div>
              </div>

              <ResponsiveContainer width="100%" height={120}>
                <LineChart data={strategy.performance}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="date" stroke="#9ca3af" style={{ fontSize: "10px" }} />
                  <YAxis stroke="#9ca3af" style={{ fontSize: "10px" }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#1f2937",
                      border: "1px solid #4b5563",
                      borderRadius: "8px",
                      color: "#e5e7eb"
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>

              <div className="flex items-center gap-2 mt-4 pt-4 border-t border-gray-800">
                <Button
                  size="sm"
                  variant={strategy.status === "运行中" ? "outline" : "default"}
                  className={
                    strategy.status === "运行中"
                      ? "flex-1 border-gray-700"
                      : "flex-1 bg-green-600 hover:bg-green-700"
                  }
                >
                  {strategy.status === "运行中" ? (
                    <>
                      <Pause className="h-4 w-4 mr-1" />
                      暂停
                    </>
                  ) : (
                    <>
                      <Play className="h-4 w-4 mr-1" />
                      启动
                    </>
                  )}
                </Button>
                <Button size="sm" variant="outline" className="border-gray-700">
                  <Settings className="h-4 w-4" />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </div>

      {/* 策略模板 */}
      <div>
        <h3 className="text-lg font-semibold mb-4 text-gray-100">策略模板库</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {strategyTemplates.map((template, idx) => (
            <Card
              key={idx}
              className="bg-[#0f0f14] border-gray-800 p-5 hover:border-blue-500/50 transition-colors cursor-pointer"
            >
              <div className="flex items-start justify-between mb-3">
                <h4 className="font-semibold text-gray-100">{template.name}</h4>
                <Badge
                  variant="outline"
                  className={
                    template.difficulty === "简单"
                      ? "border-green-500/30 text-green-400"
                      : template.difficulty === "中等"
                      ? "border-yellow-500/30 text-yellow-400"
                      : "border-red-500/30 text-red-400"
                  }
                >
                  {template.difficulty}
                </Badge>
              </div>
              <p className="text-sm text-gray-300 mb-4">{template.description}</p>
              <Button size="sm" variant="outline" className="w-full border-gray-700">
                使用模板
              </Button>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}