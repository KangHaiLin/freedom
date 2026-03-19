/**
 * 顶部导航栏
 * 借鉴example设计：显示主要指数涨跌
 */
import React from 'react';
import { Layout, Button } from 'antd';
import { MenuOutlined, BellOutlined, SettingOutlined } from '@ant-design/icons';
import { useAppContext } from '@/context/AppContext';
import './index.css';

const { Header: AntHeader } = Layout;

// 主要指数数据（模拟）
const marketIndices = [
  { name: '上证指数', value: '3245.67', change: '+1.23%', trend: 'up' },
  { name: '深证成指', value: '10876.54', change: '-0.45%', trend: 'down' },
  { name: '创业板指', value: '2234.89', change: '+0.87%', trend: 'up' },
];

const Header: React.FC = () => {
  const { toggleSidebar } = useAppContext();

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
        {marketIndices.map((index, idx) => (
          <div key={idx} className="market-index">
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
          <BellOutlined />
          <span className="notification-dot"></span>
        </button>
        <button className="header-btn">
          <SettingOutlined />
        </button>
        <div className="user-info">
          <div className="user-avatar"></div>
          <span className="user-name">用户</span>
        </div>
      </div>
    </AntHeader>
  );
};

export default Header;
