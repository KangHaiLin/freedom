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
import { getPortfolioDashboard } from '@/api/portfolio';
import { HealthStatus, PortfolioDashboard, AssetAllocation, EquityCurvePoint } from '@/api/types';
import { ArrowUpRight, ArrowDownRight, DollarSign, TrendingUp, Activity, Target } from 'lucide-react';
import './index.css';

// 默认图标映射
const iconMap: Record<string, React.ElementType> = {
  '账户总值': DollarSign,
  '今日收益': TrendingUp,
  '持仓市值': Activity,
  '可用资金': Target,
};

// 默认颜色映射（资产配置）
const defaultColors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6'];

const Dashboard: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [dashboardData, setDashboardData] = useState<PortfolioDashboard | null>(null);
  const [watchlist] = useState<string[]>(['000001', '600000', '000002', '601318']);

  const { connected, quotes, subscribe } = useWebSocketContext();

  // 订阅自选股实时行情
  useEffect(() => {
    if (connected) {
      subscribe(watchlist);
    }
  }, [connected, subscribe, watchlist]);

  // 获取仪表盘数据
  const fetchDashboardData = async () => {
    try {
      const data = await getPortfolioDashboard();
      setDashboardData(data);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    }
  };

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
    fetchDashboardData();
    fetchHealth();
  }, []);

  useInterval(() => {
    fetchHealth();
    fetchDashboardData();
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

  // 格式化账户概览数据
  const getAccountData = () => {
    if (!dashboardData?.account_summary) {
      // 返回默认占位数据
      return [
        { name: '账户总值', value: '¥0', change: '0%', trend: 'neutral', icon: DollarSign },
        { name: '今日收益', value: '¥0', change: '0%', trend: 'neutral', icon: TrendingUp },
        { name: '持仓市值', value: '¥0', change: '0%', trend: 'neutral', icon: Activity },
        { name: '可用资金', value: '¥0', change: '0%', trend: 'neutral', icon: Target },
      ];
    }

    const summary = dashboardData.account_summary;
    return [
      {
        name: '账户总值',
        value: `¥${summary.total_asset.toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
        change: `${summary.total_pnl_pct >= 0 ? '+' : ''}${(summary.total_pnl_pct * 100).toFixed(1)}%`,
        trend: summary.total_pnl_pct >= 0 ? 'up' : 'down',
        icon: iconMap['账户总值'] || DollarSign,
      },
      {
        name: '今日收益',
        value: `¥${summary.daily_pnl.toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
        change: `${summary.daily_pnl_pct >= 0 ? '+' : ''}${(summary.daily_pnl_pct * 100).toFixed(1)}%`,
        trend: summary.daily_pnl_pct >= 0 ? 'up' : 'down',
        icon: iconMap['今日收益'] || TrendingUp,
      },
      {
        name: '持仓市值',
        value: `¥${summary.total_market_value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
        change: '',
        trend: 'neutral',
        icon: iconMap['持仓市值'] || Activity,
      },
      {
        name: '可用资金',
        value: `¥${summary.current_cash.toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
        change: '0%',
        trend: 'neutral',
        icon: iconMap['可用资金'] || Target,
      },
    ];
  };

  // 获取资产配置数据
  const getPieData = (): AssetAllocation[] => {
    if (!dashboardData?.asset_allocation || dashboardData.asset_allocation.length === 0) {
      // 默认数据
      return [
        { name: '股票', value: 0, color: '#3b82f6' },
        { name: '现金', value: 100, color: '#10b981' },
      ];
    }
    // 确保有颜色
    return dashboardData.asset_allocation.map((item, index) => ({
      ...item,
      color: item.color || defaultColors[index % defaultColors.length],
    }));
  };

  // 获取重仓持股数据
  const getTopHoldingsData = () => {
    if (!dashboardData?.top_holdings || dashboardData.top_holdings.length === 0) {
      return [];
    }

    // 补充股票名称（实际应该从基本面数据获取）
    const nameMap: Record<string, string> = {
      '600519': '贵州茅台',
      '300750': '宁德时代',
      '002594': '比亚迪',
      '601012': '隆基绿能',
      '601318': '中国平安',
    };

    return dashboardData.top_holdings.slice(0, 5).map(pos => ({
      name: nameMap[pos.ts_code] || pos.ts_code,
      code: pos.ts_code,
      value: Math.round(pos.market_value),
      profit: `${pos.unrealized_pnl_pct >= 0 ? '+' : ''}${(pos.unrealized_pnl_pct * 100).toFixed(1)}%`,
    }));
  };

  // 权益曲线图表选项
  const getEquityCurveOption = () => {
    let equityCurve: EquityCurvePoint[] = [];
    if (dashboardData?.equity_curve && dashboardData.equity_curve.length > 0) {
      equityCurve = dashboardData.equity_curve;
    } else {
      // 默认数据
      equityCurve = [
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
    }

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

  const accountData = getAccountData();
  const pieData = getPieData();
  const topHoldings = getTopHoldingsData();

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
