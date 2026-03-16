/**
 * 顶部导航栏
 */
import React from 'react';
import { Layout, Button, Space, Typography } from 'antd';
import { MenuOutlined, BulbOutlined } from '@ant-design/icons';
import { useAppContext } from '@/context/AppContext';
import './index.css';

const { Header: AntHeader } = Layout;
const { Title } = Typography;

const Header: React.FC = () => {
  const { toggleSidebar } = useAppContext();

  return (
    <AntHeader className="app-header">
      <div className="header-left">
        <Button
          icon={<MenuOutlined />}
          onClick={toggleSidebar}
          type="text"
        />
        <Title level={4} style={{ margin: '0 0 0 16px', color: '#fff', fontSize: 18 }}>
          A股量化交易系统
        </Title>
      </div>
      <div className="header-right">
        <Space>
          <span style={{ color: '#fff', opacity: 0.8 }}>
            <BulbOutlined /> 量化投资
          </span>
        </Space>
      </div>
    </AntHeader>
  );
};

export default Header;
