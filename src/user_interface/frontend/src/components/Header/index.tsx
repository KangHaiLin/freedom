/**
 * 顶部导航栏
 * 借鉴example设计：显示主要指数涨跌
 */
import React, { useEffect, useState } from 'react';
import { Layout, Button, Badge } from 'antd';
import { MenuOutlined, BellOutlined, SettingOutlined } from '@ant-design/icons';
import { useAppContext } from '@/context/AppContext';
import { getRealtimeQuotes } from '@/api/market';
import { getMonitorDashboard } from '@/api/monitor';
import { getCurrentUserInfo } from '@/api/system';
import { UserInfo } from '@/api/types';
import './index.css';

const { Header: AntHeader } = Layout;

// 主要指数配置
const MAJOR_INDICES = [
  { code: '000001.SH', name: '上证指数' },
  { code: '399001.SZ', name: '深证成指' },
  { code: '399006.SZ', name: '创业板指' },
];

// 格式化后的指数数据
interface MarketIndex {
  name: string;
  code: string;
  value: string;
  change: string;
  trend: 'up' | 'down';
}

const Header: React.FC = () => {
  const { toggleSidebar } = useAppContext();
  const [indices, setIndices] = useState<MarketIndex[]>([]);
  const [unreadAlertCount, setUnreadAlertCount] = useState<number>(0);
  const [userInfo, setUserInfo] = useState<UserInfo>({
    username: '用户',
    role: 'user',
    api_key_valid: true,
  });

  // 获取主要指数实时行情
  const fetchMajorIndices = async () => {
    try {
      const codes = MAJOR_INDICES.map(item => item.code);
      const quotes = await getRealtimeQuotes(codes);

      const formatted: MarketIndex[] = MAJOR_INDICES.map(config => {
        const quote = quotes.find(q => q.code === config.code);
        if (quote) {
          // 格式化数据
          const changePct = quote.change_pct;
          const prefix = changePct >= 0 ? '+' : '';
          return {
            name: config.name,
            code: config.code,
            value: quote.price.toFixed(2),
            change: `${prefix}${changePct.toFixed(2)}%`,
            trend: changePct >= 0 ? 'up' : 'down',
          };
        }
        // 如果没找到数据，返回默认值
        return {
          name: config.name,
          code: config.code,
          value: '--',
          change: '--',
          trend: 'up',
        };
      });

      setIndices(formatted);
    } catch (error) {
      console.error('获取指数行情失败:', error);
      // 如果获取失败，保持现有数据或显示占位符
      if (indices.length === 0) {
        // 初始加载失败时显示占位符
        setIndices(MAJOR_INDICES.map(config => ({
          name: config.name,
          code: config.code,
          value: '--',
          change: '--',
          trend: 'up',
        })));
      }
    }
  };

  // 获取监控仪表盘数据（统计告警）
  const fetchAlertStats = async () => {
    try {
      const dashboard = await getMonitorDashboard();
      // 统计未读告警（warning和error级别算作需要提示）
      const count = dashboard.warning_count + dashboard.error_count;
      setUnreadAlertCount(count);
    } catch (error) {
      console.error('获取告警统计失败:', error);
    }
  };

  // 获取当前用户信息
  const fetchUserInfo = async () => {
    try {
      const info = await getCurrentUserInfo();
      setUserInfo(info);
    } catch (error) {
      console.error('获取用户信息失败:', error);
    }
  };

  useEffect(() => {
    fetchMajorIndices();
    fetchAlertStats();
    fetchUserInfo();

    // 定时刷新：每30秒更新一次指数和告警
    const interval = setInterval(() => {
      fetchMajorIndices();
      fetchAlertStats();
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  // 如果还没有数据，显示占位符
  const displayIndices = indices.length > 0 ? indices : MAJOR_INDICES.map(config => ({
    name: config.name,
    code: config.code,
    value: '--',
    change: '--',
    trend: 'up' as const,
  }));

  return (
    <AntHeader className="app-header">
      <div className="header-left">
        <Button
          icon={<MenuOutlined />}
          onClick={toggleSidebar}
          type="text"
          className="menu-toggle"
        />
        <div className="logo">
          <div className="logo-icon">
            <span className="logo-text">Q</span>
          </div>
          <h1 className="logo-title">量化交易系统</h1>
        </div>
      </div>

      <div className="header-center">
        {displayIndices.map((index) => (
          <div key={index.code} className="market-index">
            <span className="index-name">{index.name}</span>
            <span className="index-value">{index.value}</span>
            <span className={`index-change ${index.trend}`}>
              {index.change}
            </span>
          </div>
        ))}
      </div>

      <div className="header-right">
        <button className="header-btn">
          <Badge count={unreadAlertCount} dot={unreadAlertCount > 0} offset={[2, 2]}>
            <BellOutlined />
          </Badge>
        </button>
        <button className="header-btn">
          <SettingOutlined />
        </button>
        <div className="user-info">
          <div className="user-avatar"></div>
          <span className="user-name">{userInfo.username}</span>
        </div>
      </div>
    </AntHeader>
  );
};

export default Header;
