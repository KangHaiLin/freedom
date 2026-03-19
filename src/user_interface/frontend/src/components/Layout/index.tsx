/**
 * 主布局组件
 * 完全模仿example设计：顶部header + 左侧侧边栏 + 主内容区
 */
import React from 'react';
import { useLocation, Link } from 'react-router-dom';
import { Bell, Settings, LayoutDashboard, TrendingUp, Brain, Settings as SettingsIcon } from 'lucide-react';
import { MENU_ITEMS } from '@/utils/constants';
import './index.css';

// 主要指数数据
const marketIndices = [
  { name: '上证指数', value: '3245.67', change: '+1.23%', trend: 'up' },
  { name: '深证成指', value: '10876.54', change: '-0.45%', trend: 'down' },
  { name: '创业板指', value: '2234.89', change: '+0.87%', trend: 'up' },
];

// 图标映射
const iconMap: Record<string, React.ComponentType<any>> = {
  dashboard: LayoutDashboard,
  stock: TrendingUp,
  strategy: Brain,
  setting: SettingsIcon,
};

interface AppLayoutProps {
  children: React.ReactNode;
}

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const location = useLocation();

  return (
    <div className="app-root">
      {/* 顶部导航栏 - 完全模仿example */}
      <header className="app-header">
        <div className="header-container">
          <div className="header-left">
            <div className="logo-section">
              <div className="logo-icon">
                <span className="logo-text">Q</span>
              </div>
              <h1 className="logo-title">量化交易系统</h1>
            </div>
            <div className="market-indices">
              {marketIndices.map((index, idx) => (
                <div key={idx} className="market-index">
                  <span className="index-name">{index.name}</span>
                  <span className={`index-value ${index.trend}`}>
                    {index.value}
                  </span>
                  <span className={`index-change ${index.trend}`}>
                    {index.change}
                  </span>
                </div>
              ))}
            </div>
          </div>
          <div className="header-right">
            <button className="header-btn">
              <Bell className="bell-icon" />
              <span className="notification-dot"></span>
            </button>
            <button className="header-btn">
              <Settings className="settings-icon" />
            </button>
            <div className="user-section">
              <div className="user-avatar"></div>
              <span className="user-name">用户</span>
            </div>
          </div>
        </div>
      </header>

      {/* 主体内容 */}
      <div className="main-container">
        {/* 侧边导航栏 - 完全模仿example */}
        <aside className="sidebar">
          <nav className="sidebar-nav">
            {MENU_ITEMS.map((item) => {
              const isActive = location.pathname === item.key;
              const Icon = iconMap[item.icon];
              return (
                <Link
                  key={item.key}
                  to={item.key}
                  className={`sidebar-item ${isActive ? 'active' : ''}`}
                >
                  {Icon && <Icon className="sidebar-icon" />}
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </aside>

        {/* 主内容区 */}
        <main className="main-content">
          {children}
        </main>
      </div>
    </div>
  );
};

export default AppLayout;
