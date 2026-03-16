/**
 * 主布局组件
 * 侧边栏 + 顶栏 + 内容区
 */
import React from 'react';
import { Layout as AntLayout } from 'antd';
import Header from '../Header';
import Sidebar from '../Sidebar';
import './index.css';

const { Content } = AntLayout;

interface AppLayoutProps {
  children: React.ReactNode;
}

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {

  return (
    <AntLayout className="app-layout">
      <Sidebar />
      <AntLayout>
        <Header />
        <Content className="app-content">{children}</Content>
      </AntLayout>
    </AntLayout>
  );
};

export default AppLayout;
