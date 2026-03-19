/**
 * 总览仪表板页面
 * 完全模仿example设计
 */
import React, { useEffect, useState } from 'react';
import { Card } from 'antd';
import ReactECharts from 'echarts-for-react';
import PriceTicker from '@/components/PriceTicker';
import { useWebSocketContext } from '@/context/WebSocketContext';
import { useInterval } from '@/hooks/useInterval';
import { getHealthStatus } from '@/api/monitor';
import { HealthStatus } from '@/api/types';
import { ArrowUpRight, ArrowDownRight, DollarSign, TrendingUp, Activity, Target } from 'lucide-react';
import './index.css';

// 模拟账户概览数据
const accountData = [
  { name: '账户总值', value: '¥2,456,789', change: '+12.5%', trend: 'up', icon: DollarSign },
  { name: '今日收益', value: '¥15,234', change: '+2.3%', trend: 'up', icon: TrendingUp },
  { name: '持仓市值', value: '¥1,987,654', change: '-0.8%', trend: 'down', icon: Activity },
  { name: '可用资金', value: '¥469,135', change: '0%', trend: 'neutral', icon: Target },
];

// 资产配置饼图数据
const pieData = [
  { name: '股票', value: 65, color: '#3b82f6' },
  { name: '现金', value: 20, color: '#10b981' },
  { name: '债券', value: 10, color: '#f59e0b' },
  { name: '其他', value: 5, color: '#8b5cf6' },
];

// 重仓持股数据
const topHoldings = [
  { name: '贵州茅台', code: '600519', value: 285000, profit: '+15.2%' },
  { name: '宁德时代', code: '300750', value: 245000, profit: '+8.7%' },
  { name: '比亚迪', code: '002594', value: 198000, profit: '-2.3%' },
  { name: '隆基绿能', code: '601012', value: 156000, profit: '+5.1%' },
  { name: '中国平安', code: '601318', value: 134000, profit: '+3.4%' },
];

const Dashboard: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [watchlist] = useState<string[]>(['000001', '600000', '000002', '601318']);

  const { connected, quotes, subscribe } = useWebSocketContext();

  // 订阅自选股实时行情
  useEffect(() => {
    if (connected) {
      subscribe(watchlist);
    }
  }, [connected, subscribe, watchlist]);

  // 定时刷新健康状态
  const fetchHealth = async () => {
    try {
      const data = await getHealthStatus();
      setHealth(data);
    } catch (error) {
      console.error('Failed to fetch health status:', error);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  useInterval(() => {
    fetchHealth();
  }, 30000);

  // 获取告警列表
  const getAlerts = () => {
    if (!health) {
      return [];
    }
    const alerts = [];
    for (const [name, check] of Object.entries(health.checks)) {
      if (check.status !== 'ok') {
        alerts.push({
          name,
          status: check.status,
          message: check.message,
        });
      }
    }
    return alerts;
  };

  const alerts = getAlerts();

  // 权益曲线图表选项
  const getEquityCurveOption = () => {
    const equityCurve = [
      { date: '01/01', value: 1000000 },
      { date: '01/08', value: 1050000 },
      { date: '01/15', value: 1120000 },
      { date: '01/22', value: 1080000 },
      { date: '01/29', value: 1150000 },
      { date: '02/05', value: 1200000 },
      { date: '02/12', value: 1280000 },
      { date: '02/19', value: 1350000 },
      { date: '02/26', value: 1420000 },
      { date: '03/05', value: 1480000 },
      { date: '03/12', value: 1520000 },
      { date: '03/17', value: 1587654 },
    ];

    return {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#1f2937',
        borderColor: '#4b5563',
        textStyle: {
          color: '#e5e7eb',
        },
      },
      grid: {
        left: 60,
        right: 20,
        bottom: 30,
        top: 10,
      },
      xAxis: {
        type: 'category',
        data: equityCurve.map(item => item.date),
        axisLine: {
          lineStyle: {
            color: '#4b5563',
          },
        },
        axisLabel: {
          color: '#9ca3af',
          fontSize: 12,
        },
      },
      yAxis: {
        type: 'value',
        axisLine: {
          lineStyle: {
            color: '#4b5563',
          },
        },
        axisLabel: {
          color: '#9ca3af',
          fontSize: 12,
        },
        splitLine: {
          lineStyle: {
            color: '#374151',
          },
        },
      },
      series: [
        {
          name: '账户权益',
          type: 'line',
          data: equityCurve.map(item => item.value),
          smooth: true,
          lineStyle: {
            color: '#3b82f6',
            width: 2,
          },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [{
                offset: 0.05, color: 'rgba(59, 130, 246, 0.3)'
              }, {
                offset: 0.95, color: 'rgba(59, 130, 246, 0)'
              }]
            },
          },
        },
      ],
    };
  };

  return (
    <div className="dashboard-page space-y-6">
      {/* 页头 */}
      <div className="page-header">
        <h2 className="page-title">仪表板</h2>
        <p className="page-description">账户总览和系统监控</p>
      </div>

      {/* 账户概览卡片 */}
      <div className="stats-grid">
        {accountData.map((item, index) => (
          <Card key={index} className="stat-card">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="stat-label">{item.name}</p>
                <p className="stat-value">{item.value}</p>
                <div className="flex items-center gap-1">
                  {item.trend === 'up' && (
                    <ArrowUpRight className="stat-arrow text-red-400" />
                  )}
                  {item.trend === 'down' && (
                    <ArrowDownRight className="stat-arrow text-green-400" />
                  )}
                  <span
                    className={`stat-change ${
                      item.trend === 'up'
                        ? 'text-red-400'
                        : item.trend === 'down'
                        ? 'text-green-400'
                        : 'text-gray-300'
                    }`}
                  >
                    {item.change}
                  </span>
                </div>
              </div>
              <div className="stat-icon-container">
                <item.icon className="stat-icon text-blue-400" />
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* 权益曲线和资产配置 */}
      <div className="two-column-grid">
        <Card className="main-card">
          <h3 className="card-title">账户权益曲线</h3>
          <ReactECharts option={getEquityCurveOption()} style={{ height: 300 }} />
        </Card>

        <Card className="side-card">
          <h3 className="card-title">资产配置</h3>
          <ReactECharts
            option={{
              backgroundColor: 'transparent',
              tooltip: {
                trigger: 'item',
                backgroundColor: '#1f2937',
                borderColor: '#4b5563',
                textStyle: {
                  color: '#e5e7eb',
                },
              },
              series: [
                {
                  name: '资产配置',
                  type: 'pie',
                  radius: ['60%', '80%'],
                  center: ['50%', '40%'],
                  data: pieData,
                  itemStyle: {
                    borderRadius: 4,
                    borderColor: '#0a0a0f',
                    borderWidth: 2,
                  },
                  label: {
                    show: false,
                  },
                },
              ],
            }}
            style={{ height: 200 }}
          />
          <div className="pie-legend">
            {pieData.map((item, index) => (
              <div key={index} className="pie-legend-item">
                <div className="flex items-center gap-2">
                  <div className="legend-color" style={{ backgroundColor: item.color }}></div>
                  <span className="legend-name">{item.name}</span>
                </div>
                <span className="legend-value">{item.value}%</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* 重仓持股和系统状态 */}
      <div className="two-column-grid">
        <Card className="card-half">
          <h3 className="card-title">重仓持股</h3>
          <div className="holdings-list">
            {topHoldings.map((stock, index) => (
              <div key={index} className="holding-item">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="holding-name">{stock.name}</span>
                    <span className="holding-code">{stock.code}</span>
                  </div>
                  <p className="holding-value">¥{stock.value.toLocaleString()}</p>
                </div>
                <div className="text-right">
                  <span
                    className={`holding-profit ${
                      stock.profit.startsWith('+') ? 'text-red-400' : 'text-green-400'
                    }`}
                  >
                    {stock.profit}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="card-half">
          <h3 className="card-title">系统状态</h3>
          <div className="system-alerts">
            {alerts.length === 0 ? (
              <div className="no-alerts">当前没有活跃告警</div>
            ) : (
              <div className="alerts-list">
                {alerts.map((alert, index) => (
                  <div key={index} className="alert-item">
                    <div className="flex items-center justify-between">
                      <span className="alert-name">{alert.name}</span>
                      <span className={`alert-badge ${alert.status}`}>
                        {alert.status}
                      </span>
                    </div>
                    <p className="alert-message">{alert.message}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* 实时自选股 */}
      <Card>
        <h3 className="card-title">实时自选股行情</h3>
        <div className="watchlist-container">
          {watchlist.map((code) => {
            const quote = quotes.get(code);
            if (quote) {
              return (
                <div key={code} className="watchlist-item">
                  <PriceTicker quote={quote} />
                </div>
              );
            }
            return (
              <div key={code} className="watchlist-loading">
                {code} - 加载中...
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
};

export default Dashboard;
