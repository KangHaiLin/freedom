/**
 * 侧边栏导航
 */
import React from 'react';
import { Layout, Menu } from 'antd';
import {
  DashboardOutlined,
  StockOutlined,
  BarChartOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAppContext } from '@/context/AppContext';
import { MENU_ITEMS } from '@/utils/constants';
import './index.css';

const { Sider } = Layout;

const iconMap: Record<string, React.ReactNode> = {
  dashboard: <DashboardOutlined />,
  stock: <StockOutlined />,
  strategy: <BarChartOutlined />,
  setting: <SettingOutlined />,
};

const Sidebar: React.FC = () => {
  const { sidebarCollapsed } = useAppContext();
  const location = useLocation();
  const navigate = useNavigate();

  const selectedKey = location.pathname;

  return (
    <Sider width={200} collapsed={sidebarCollapsed} className="app-sidebar">
      <div className="sidebar-logo">
        {!sidebarCollapsed && <span>Quant Trading</span>}
      </div>
      <Menu
        mode="inline"
        selectedKeys={[selectedKey]}
        items={MENU_ITEMS.map((item) => ({
          key: item.key,
          icon: iconMap[item.icon],
          label: item.label,
          onClick: () => navigate(item.key),
        }))}
      />
    </Sider>
  );
};

export default Sidebar;
