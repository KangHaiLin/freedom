import { useState, useEffect } from "react";
import { Card } from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Play, RotateCcw, Download } from "lucide-react";
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { getStrategies, createBacktestTask, getBacktestResult, exportBacktestReport, resetBacktestConfig, saveBacktestConfig, loadBacktestConfig } from "@/api/backtest";
import type { StrategyInfo, BacktestResultDetail } from "@/api/backtest";
import { toast } from "sonner";

// 默认模拟数据（当没有回测结果时使用）
const defaultBacktestResults = [
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

const defaultDrawdownData = [
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

const defaultMonthlyReturns = [
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

const defaultTradeHistory = [
  { date: "2024-03-15", stock: "贵州茅台", action: "买入", price: 1678.00, quantity: 100, profit: "+15,234" },
  { date: "2024-03-14", stock: "宁德时代", action: "卖出", price: 245.60, quantity: 500, profit: "-2,340" },
  { date: "2024-03-13", stock: "比亚迪", action: "买入", price: 276.80, quantity: 300, profit: "+8,760" },
  { date: "2024-03-12", stock: "隆基绿能", action: "卖出", price: 33.20, quantity: 1000, profit: "+4,560" },
  { date: "2024-03-11", stock: "中国平安", action: "买入", price: 55.40, quantity: 800, profit: "+6,780" },
];

export default function Backtest() {
  // 状态管理
  const [strategies, setStrategies] = useState<StrategyInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedStrategy, setSelectedStrategy] = useState("");
  const [startDate, setStartDate] = useState("2023-01-01");
  const [endDate, setEndDate] = useState("2024-03-17");
  const [initialCapital, setInitialCapital] = useState("1000000");

  // 结果数据
  const [result, setResult] = useState<BacktestResultDetail | null>(null);
  const [backtestResults, setBacktestResults] = useState(defaultBacktestResults);
  const [drawdownData, setDrawdownData] = useState(defaultDrawdownData);
  const [monthlyReturns, setMonthlyReturns] = useState(defaultMonthlyReturns);
  const [tradeHistory, setTradeHistory] = useState(defaultTradeHistory);

  // 统计数据（计算显示值）
  const totalReturn = result ? (result.total_return * 100).toFixed(1) + "%" : "+72.0%";
  const annualReturn = result ? (result.annual_return * 100).toFixed(1) + "%" : "+48.3%";
  const sharpeRatio = result ? result.sharpe_ratio.toFixed(2) : "2.45";
  const maxDrawdown = result ? (result.max_drawdown * 100).toFixed(1) + "%" : "-3.6%";
  const winRate = result ? (result.win_rate * 100).toFixed(1) + "%" : "73.5%";
  const tradeCount = result ? result.trade_count.toString() : "156";

  // 组件加载时获取策略列表并恢复保存的配置
  useEffect(() => {
    const loadStrategies = async () => {
      try {
        const data = await getStrategies();
        setStrategies(data);
        if (data.length > 0) {
          setSelectedStrategy(data[0].id);
        }
      } catch (error) {
        console.error("Failed to load strategies:", error);
        // 如果API失败，使用默认选项
        setStrategies([
          { id: "1", name: "动量策略A", type: "momentum", status: "active", returns: "+0.0%", sharpe: "0.00", max_drawdown: "0.0%", winRate: "0.0%", positions: 0, performance: [] },
          { id: "2", name: "均值回归B", type: "mean_reversion", status: "active", returns: "+0.0%", sharpe: "0.00", max_drawdown: "0.0%", winRate: "0.0%", positions: 0, performance: [] },
          { id: "3", name: "套利策略C", type: "arbitrage", status: "active", returns: "+0.0%", sharpe: "0.00", max_drawdown: "0.0%", winRate: "0.0%", positions: 0, performance: [] },
          { id: "4", name: "趋势跟踪D", type: "trend", status: "active", returns: "+0.0%", sharpe: "0.00", max_drawdown: "0.0%", winRate: "0.0%", positions: 0, performance: [] },
        ]);
        setSelectedStrategy("1");
      }
    };

    loadStrategies();

    // 恢复上次保存的配置
    const savedConfig = loadBacktestConfig();
    if (savedConfig) {
      setSelectedStrategy(savedConfig.strategy_id);
      setStartDate(savedConfig.start_date);
      setEndDate(savedConfig.end_date);
      setInitialCapital(savedConfig.initial_capital.toString());
    }
  }, []);

  // 开始回测
  const handleStartBacktest = async () => {
    if (!selectedStrategy) {
      toast.error("请选择策略");
      return;
    }

    const capital = parseFloat(initialCapital.replace(/,/g, ""));
    if (isNaN(capital) || capital <= 0) {
      toast.error("请输入有效的初始资金");
      return;
    }

    setLoading(true);
    try {
      // 保存配置到本地
      saveBacktestConfig({
        name: `${strategies.find(s => s.id === selectedStrategy)?.name || "策略"}回测`,
        strategy_id: selectedStrategy,
        start_date: startDate,
        end_date: endDate,
        initial_capital: capital,
      });

      // 创建回测任务
      const task = await createBacktestTask({
        name: `${strategies.find(s => s.id === selectedStrategy)?.name || "策略"}回测`,
        strategy_id: selectedStrategy,
        start_date: startDate,
        end_date: endDate,
        initial_capital: capital,
      });

      // 获取回测结果详情（实际生产环境这里应该轮询等待完成）
      const resultData = await getBacktestResult(task.id);
      setResult(resultData);

      // 更新图表数据
      if (resultData.equity_curve && resultData.equity_curve.length > 0) {
        setBacktestResults(resultData.equity_curve);
      }
      if (resultData.drawdown_curve && resultData.drawdown_curve.length > 0) {
        setDrawdownData(resultData.drawdown_curve);
      }
      if (resultData.monthly_returns && resultData.monthly_returns.length > 0) {
        setMonthlyReturns(resultData.monthly_returns);
      }
      if (resultData.trade_history && resultData.trade_history.length > 0) {
        setTradeHistory(resultData.trade_history);
      }

      toast.success("回测完成");
    } catch (error) {
      console.error("Backtest failed:", error);
      toast.error("回测失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  // 重置配置
  const handleReset = () => {
    setSelectedStrategy(strategies[0]?.id || "");
    setStartDate("2023-01-01");
    setEndDate("2024-03-17");
    setInitialCapital("1000000");
    resetBacktestConfig();
    setResult(null);
    setBacktestResults(defaultBacktestResults);
    setDrawdownData(defaultDrawdownData);
    setMonthlyReturns(defaultMonthlyReturns);
    setTradeHistory(defaultTradeHistory);
    toast.info("已重置配置");
  };

  // 导出报告
  const handleExport = async () => {
    if (!result) {
      toast.error("请先运行回测");
      return;
    }
    try {
      // 获取导出链接，实际这里会打开下载
      await exportBacktestReport("latest");
      toast.success("报告导出成功");
    } catch (error) {
      console.error("Export failed:", error);
      toast.error("导出失败");
    }
  };

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
              value={selectedStrategy}
              onChange={(e) => setSelectedStrategy(e.target.value)}
              className="w-full px-3 py-2 bg-[#1a1a20] border border-gray-700 rounded-lg text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {strategies.map((strategy) => (
                <option key={strategy.id} value={strategy.id}>
                  {strategy.name}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="start-date" className="text-gray-300">开始日期</Label>
            <Input
              id="start-date"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="bg-[#1a1a20] border-gray-700 text-gray-100"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="end-date" className="text-gray-300">结束日期</Label>
            <Input
              id="end-date"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="bg-[#1a1a20] border-gray-700 text-gray-100"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="capital" className="text-gray-300">初始资金</Label>
            <Input
              id="capital"
              type="text"
              value={initialCapital}
              onChange={(e) => setInitialCapital(e.target.value)}
              className="bg-[#1a1a20] border-gray-700 text-gray-100"
            />
          </div>
        </div>
        <div className="flex items-center gap-3 mt-6">
          <Button
            className="bg-blue-600 hover:bg-blue-700"
            onClick={handleStartBacktest}
            disabled={loading}
          >
            <Play className="h-4 w-4 mr-2" />
            {loading ? "运行中..." : "开始回测"}
          </Button>
          <Button variant="outline" className="border-gray-700" onClick={handleReset}>
            <RotateCcw className="h-4 w-4 mr-2" />
            重置
          </Button>
          <Button variant="outline" className="border-gray-700" onClick={handleExport}>
            <Download className="h-4 w-4 mr-2" />
            导出报告
          </Button>
        </div>
      </Card>

      {/* 回测统计 */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <Card className="bg-[#0f0f14] border-gray-800 p-4">
          <p className="text-xs text-gray-300 mb-1">总收益率</p>
          <p className="text-xl font-bold text-red-400">{totalReturn}</p>
        </Card>
        <Card className="bg-[#0f0f14] border-gray-800 p-4">
          <p className="text-xs text-gray-300 mb-1">年化收益</p>
          <p className="text-xl font-bold text-gray-100">{annualReturn}</p>
        </Card>
        <Card className="bg-[#0f0f14] border-gray-800 p-4">
          <p className="text-xs text-gray-300 mb-1">夏普比率</p>
          <p className="text-xl font-bold text-gray-100">{sharpeRatio}</p>
        </Card>
        <Card className="bg-[#0f0f14] border-gray-800 p-4">
          <p className="text-xs text-gray-300 mb-1">最大回撤</p>
          <p className="text-xl font-bold text-green-400">{maxDrawdown}</p>
        </Card>
        <Card className="bg-[#0f0f14] border-gray-800 p-4">
          <p className="text-xs text-gray-300 mb-1">胜率</p>
          <p className="text-xl font-bold text-gray-100">{winRate}</p>
        </Card>
        <Card className="bg-[#0f0f14] border-gray-800 p-4">
          <p className="text-xs text-gray-300 mb-1">交易次数</p>
          <p className="text-xl font-bold text-gray-100">{tradeCount}</p>
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
                  <td className="py-3 px-4 text-right text-gray-100">{typeof trade.price === 'number' ? trade.price.toFixed(2) : trade.price}</td>
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
