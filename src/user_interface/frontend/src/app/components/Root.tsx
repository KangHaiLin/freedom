import { Outlet, Link, useLocation } from "react-router";
import { LayoutDashboard, TrendingUp, Brain, LineChart, Briefcase, FileText, Settings, Bell } from "lucide-react";
import { cn } from "./ui/utils";

const navigation = [
  { name: "总览", href: "/", icon: LayoutDashboard },
  { name: "行情", href: "/market", icon: TrendingUp },
  { name: "策略", href: "/strategy", icon: Brain },
  { name: "回测", href: "/backtest", icon: LineChart },
  { name: "持仓", href: "/portfolio", icon: Briefcase },
  { name: "订单", href: "/orders", icon: FileText },
];

export default function Root() {
  const location = useLocation();

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-gray-100">
      {/* 顶部导航栏 */}
      <header className="border-b border-gray-800 bg-[#0f0f14]">
        <div className="flex items-center justify-between px-6 py-3">
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                <span className="font-bold text-white">Q</span>
              </div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                量化交易系统
              </h1>
            </div>
            <div className="flex items-center gap-6 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-gray-300">上证指数</span>
                <span className="text-red-400">3245.67</span>
                <span className="text-red-400 text-xs">+1.23%</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-300">深证成指</span>
                <span className="text-green-400">10876.54</span>
                <span className="text-green-400 text-xs">-0.45%</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-300">创业板指</span>
                <span className="text-red-400">2234.89</span>
                <span className="text-red-400 text-xs">+0.87%</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <button className="relative p-2 rounded-lg hover:bg-gray-800 transition-colors">
              <Bell className="h-5 w-5 text-gray-300" />
              <span className="absolute top-1 right-1 h-2 w-2 bg-red-500 rounded-full"></span>
            </button>
            <button className="p-2 rounded-lg hover:bg-gray-800 transition-colors">
              <Settings className="h-5 w-5 text-gray-300" />
            </button>
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600"></div>
              <span className="text-sm text-gray-200">用户001</span>
            </div>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* 侧边导航栏 */}
        <aside className="w-64 min-h-[calc(100vh-57px)] border-r border-gray-800 bg-[#0f0f14]">
          <nav className="p-4 space-y-1">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={cn(
                    "flex items-center gap-3 px-4 py-3 rounded-lg transition-colors",
                    isActive
                      ? "bg-gradient-to-r from-blue-600/20 to-purple-600/20 text-blue-400 border border-blue-500/30"
                      : "text-gray-300 hover:bg-gray-800 hover:text-gray-100"
                  )}
                >
                  <item.icon className="h-5 w-5" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </aside>

        {/* 主内容区 */}
        <main className="flex-1 p-6 bg-[#0a0a0f]">
          <Outlet />
        </main>
      </div>
    </div>
  );
}