/**
 * 根组件
 * 配置路由
 * 完全模仿example设计
 */
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import 'dayjs/locale/zh-cn';
import AppLayout from './components/Layout';
import Dashboard from './pages/Dashboard';
import MarketData from './pages/MarketData';
import StrategyMonitoring from './pages/StrategyMonitoring';
import SystemStatus from './pages/SystemStatus';
import { AppProvider } from './context/AppContext';
import { WebSocketProvider } from './context/WebSocketContext';
import './index.css';

const App: React.FC = () => {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorBgContainer: '#0f0f14',
          colorBgElevated: '#1a1a20',
          colorBorder: '#2a2a33',
          colorText: '#e5e7eb',
          colorTextSecondary: '#9ca3af',
          borderRadius: 10,
          fontSize: 16,
          fontFamily: 'inherit',
        },
        components: {
          Card: {
            colorBgContainer: '#0f0f14',
          },
        },
      }}
    >
      <AppProvider>
        <WebSocketProvider autoConnect={true}>
          <BrowserRouter>
            <AppLayout>
              <Routes>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/market" element={<MarketData />} />
                <Route path="/strategy" element={<StrategyMonitoring />} />
                <Route path="/system" element={<SystemStatus />} />
              </Routes>
            </AppLayout>
          </BrowserRouter>
        </WebSocketProvider>
      </AppProvider>
    </ConfigProvider>
  );
};

export default App;
