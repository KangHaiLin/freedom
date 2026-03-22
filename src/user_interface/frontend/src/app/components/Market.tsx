import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Search, Star } from "lucide-react";
import { LineChart, Line, ResponsiveContainer } from "recharts";
import { useState } from "react";

const generateMiniChart = () => {
  return Array.from({ length: 20 }, () => ({
    value: Math.random() * 100 + 50,
  }));
};

const marketData = [
  { name: "贵州茅台", code: "600519", price: 1845.67, change: 2.34, changePercent: "+1.28%", volume: "12.5万手", turnover: "23.1亿", trend: "up", chart: generateMiniChart() },
  { name: "宁德时代", code: "300750", price: 234.56, change: -3.45, changePercent: "-1.45%", volume: "89.3万手", turnover: "20.9亿", trend: "down", chart: generateMiniChart() },
  { name: "比亚迪", code: "002594", price: 287.89, change: 5.67, changePercent: "+2.01%", volume: "156.7万手", turnover: "45.2亿", trend: "up", chart: generateMiniChart() },
  { name: "隆基绿能", code: "601012", price: 32.45, change: -0.56, changePercent: "-1.70%", volume: "234.5万手", turnover: "7.6亿", trend: "down", chart: generateMiniChart() },
  { name: "中国平安", code: "601318", price: 56.78, change: 0.89, changePercent: "+1.59%", volume: "178.9万手", turnover: "10.2亿", trend: "up", chart: generateMiniChart() },
  { name: "招商银行", code: "600036", price: 38.92, change: -0.23, changePercent: "-0.59%", volume: "123.4万手", turnover: "4.8亿", trend: "down", chart: generateMiniChart() },
  { name: "五粮液", code: "000858", price: 178.34, change: 1.23, changePercent: "+0.69%", volume: "45.6万手", turnover: "8.1亿", trend: "up", chart: generateMiniChart() },
  { name: "立讯精密", code: "002475", price: 34.56, change: -1.12, changePercent: "-3.14%", volume: "267.8万手", turnover: "9.3亿", trend: "down", chart: generateMiniChart() },
  { name: "海天味业", code: "603288", price: 92.45, change: 0.67, changePercent: "+0.73%", volume: "34.5万手", turnover: "3.2亿", trend: "up", chart: generateMiniChart() },
  { name: "恒瑞医药", code: "600276", price: 67.89, change: -0.45, changePercent: "-0.66%", volume: "56.7万手", turnover: "3.8亿", trend: "down", chart: generateMiniChart() },
];

const indices = [
  { name: "上证指数", code: "000001", value: "3245.67", change: "+39.87", changePercent: "+1.23%" },
  { name: "深证成指", code: "399001", value: "10876.54", change: "-49.12", changePercent: "-0.45%" },
  { name: "创业板指", code: "399006", value: "2234.89", change: "+19.23", changePercent: "+0.87%" },
  { name: "科创50", code: "000688", value: "1056.34", change: "+8.56", changePercent: "+0.82%" },
];

const sectors = [
  { name: "半导体", change: "+2.87%", trend: "up" },
  { name: "新能源车", change: "+1.45%", trend: "up" },
  { name: "白酒", change: "+0.98%", trend: "up" },
  { name: "医药", change: "-0.34%", trend: "down" },
  { name: "房地产", change: "-1.23%", trend: "down" },
  { name: "银行", change: "-0.56%", trend: "down" },
];

export default function Market() {
  const [searchTerm, setSearchTerm] = useState("");

  const filteredData = marketData.filter(
    (stock) =>
      stock.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      stock.code.includes(searchTerm)
  );

  return (
    <div className="space-y-6">
      {/* 指数行情 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {indices.map((index, idx) => (
          <Card key={idx} className="bg-[#0f0f14] border-gray-800 p-5">
            <div className="flex items-start justify-between mb-2">
              <div>
                <p className="text-sm text-gray-300">{index.name}</p>
                <p className="text-xs text-gray-400 mt-0.5">{index.code}</p>
              </div>
              <Star className="h-4 w-4 text-gray-500 hover:text-yellow-400 cursor-pointer transition-colors" />
            </div>
            <p className="text-2xl font-bold mb-1 text-gray-100">{index.value}</p>
            <div className="flex items-center gap-2">
              <span
                className={`text-sm font-semibold ${
                  index.change.startsWith("+") ? "text-red-400" : "text-green-400"
                }`}
              >
                {index.change}
              </span>
              <span
                className={`text-sm ${
                  index.changePercent.startsWith("+") ? "text-red-400" : "text-green-400"
                }`}
              >
                {index.changePercent}
              </span>
            </div>
          </Card>
        ))}
      </div>

      {/* 板块涨跌 */}
      <Card className="bg-[#0f0f14] border-gray-800 p-6">
        <h3 className="text-lg font-semibold mb-4 text-gray-100">板块涨跌榜</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {sectors.map((sector, idx) => (
            <div
              key={idx}
              className={`p-3 rounded-lg border ${
                sector.trend === "up"
                  ? "bg-red-500/10 border-red-500/30"
                  : "bg-green-500/10 border-green-500/30"
              }`}
            >
              <p className="text-sm text-gray-200 mb-1">{sector.name}</p>
              <p
                className={`text-base font-semibold ${
                  sector.trend === "up" ? "text-red-400" : "text-green-400"
                }`}
              >
                {sector.change}
              </p>
            </div>
          ))}
        </div>
      </Card>

      {/* 个股行情 */}
      <Card className="bg-[#0f0f14] border-gray-800 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-100">个股行情</h3>
          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="搜索股票代码或名称..."
              className="pl-9 bg-[#1a1a20] border-gray-700 text-gray-100"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-300">股票名称</th>
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-300">代码</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-300">最新价</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-300">涨跌额</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-300">涨跌幅</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-300">成交量</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-300">成交额</th>
                <th className="text-center py-3 px-4 text-sm font-medium text-gray-300">走势</th>
                <th className="text-center py-3 px-4 text-sm font-medium text-gray-300">操作</th>
              </tr>
            </thead>
            <tbody>
              {filteredData.map((stock, idx) => (
                <tr
                  key={idx}
                  className="border-b border-gray-800/50 hover:bg-[#1a1a20] transition-colors"
                >
                  <td className="py-3 px-4">
                    <div className="flex items-center gap-2">
                      <Star className="h-4 w-4 text-gray-500 hover:text-yellow-400 cursor-pointer transition-colors" />
                      <span className="font-medium text-gray-100">{stock.name}</span>
                    </div>
                  </td>
                  <td className="py-3 px-4 text-gray-300">{stock.code}</td>
                  <td className="py-3 px-4 text-right font-semibold text-gray-100">{stock.price}</td>
                  <td
                    className={`py-3 px-4 text-right font-medium ${
                      stock.trend === "up" ? "text-red-400" : "text-green-400"
                    }`}
                  >
                    {stock.change > 0 ? "+" : ""}
                    {stock.change.toFixed(2)}
                  </td>
                  <td
                    className={`py-3 px-4 text-right font-medium ${
                      stock.trend === "up" ? "text-red-400" : "text-green-400"
                    }`}
                  >
                    {stock.changePercent}
                  </td>
                  <td className="py-3 px-4 text-right text-gray-300">{stock.volume}</td>
                  <td className="py-3 px-4 text-right text-gray-300">{stock.turnover}</td>
                  <td className="py-3 px-4">
                    <ResponsiveContainer width={80} height={30}>
                      <LineChart data={stock.chart}>
                        <Line
                          type="monotone"
                          dataKey="value"
                          stroke={stock.trend === "up" ? "#f87171" : "#4ade80"}
                          strokeWidth={1.5}
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </td>
                  <td className="py-3 px-4">
                    <div className="flex items-center justify-center gap-2">
                      <button className="px-3 py-1 text-xs bg-red-500/20 text-red-400 rounded hover:bg-red-500/30 transition-colors">
                        买入
                      </button>
                      <button className="px-3 py-1 text-xs bg-green-500/20 text-green-400 rounded hover:bg-green-500/30 transition-colors">
                        卖出
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
