/**
 * 总览仪表板页面
 * 系统概览、最近告警、实时自选股
 */
import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Table, List, Tag, Typography, Alert, Spin } from 'antd';
import ReactECharts from 'echarts-for-react';
import StatusCard from '@/components/StatusCard';
import PriceTicker from '@/components/PriceTicker';
import { useWebSocketContext } from '@/context/WebSocketContext';
import { useInterval } from '@/hooks/useInterval';
import { getHealthStatus, getDataSourceStatus } from '@/api/monitor';
import { RealtimeQuote, HealthStatus, DataSourceStatus } from '@/api/types';
import { HEALTH_COLOR } from '@/utils/constants';
import { formatPercent } from '@/utils/formatters';
import './index.css';

const { Title } = Typography;

const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [dataSources, setDataSources] = useState<DataSourceStatus[]>([]);
  const [watchlist, setWatchlist] = useState<string[]>(['000001', '600000', '000002', '601318']);

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

  const fetchDataSources = async () => {
    try {
      const data = await getDataSourceStatus();
      setDataSources(data);
    } catch (error) {
      console.error('Failed to fetch data sources:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    fetchDataSources();
  }, []);

  useInterval(() => {
    fetchHealth();
    fetchDataSources();
  }, 30000);

  // 计算概览数据
  const totalSources = dataSources.length;
  const availableSources = dataSources.filter((d) => d.available).length;

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

  // 数据质量趋势图（模拟数据）
  const getQualityOption = () => {
    const days = Array.from({ length: 30 }, (_, i) => `${i + 1}`);
    const quality = Array.from({ length: 30 }, () => 90 + Math.random() * 8);

    return {
      tooltip: {
        trigger: 'axis',
      },
      xAxis: {
        type: 'category',
        data: days,
      },
      yAxis: {
        type: 'value',
        min: 80,
        max: 100,
        name: '质量分',
      },
      series: [
        {
          name: '数据质量',
          data: quality,
          type: 'line',
          smooth: true,
          areaStyle: {
            opacity: 0.2,
          },
        },
      ],
    };
  };

  const statusColor = health?.overall_healthy
    ? alerts.length === 0
      ? 'success'
      : 'warning'
    : 'error';

  return (
    <div className="dashboard-page">
      <Title level={2}>仪表板</Title>

      {!connected && (
        <Alert
          message="实时行情连接未建立"
          description="请检查后端服务是否正常运行"
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <StatusCard
            title="数据源总数"
            value={totalSources}
          />
        </Col>
        <Col xs={24} sm={12} md={6}>
          <StatusCard
            title="可用数据源"
            value={availableSources}
            change={totalSources > 0 ? (availableSources / totalSources) * 100 : 0}
            isIncreaseGood={true}
          />
        </Col>
        <Col xs={24} sm={12} md={6}>
          <StatusCard
            title="活跃告警"
            value={alerts.length}
            change={alerts.length * 10}
            isIncreaseGood={false}
            color={alerts.length > 0 ? '#cf1322' : undefined}
          />
        </Col>
        <Col xs={24} sm={12} md={6}>
          <StatusCard
            title="系统状态"
            value={health?.overall_healthy ? '健康' : '异常'}
            color={health?.overall_healthy ? '#52c41a' : '#ff4d4f'}
          />
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="数据质量趋势（30天）">
            <ReactECharts option={getQualityOption()} style={{ height: 300 }} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="系统健康状态">
            <Spin spinning={loading}>
              {health && (
                <>
                  <div
                    className="health-overview"
                    style={{
                      backgroundColor: HEALTH_COLOR[health.status],
                    }}
                  >
                    <span className="health-status-text">
                      整体状态: {health.status.toUpperCase()}
                    </span>
                  </div>
                  <Table
                    size="small"
                    pagination={false}
                    dataSource={Object.entries(health.checks).map(([key, check]) => ({
                      key,
                      name: check.name,
                      status: check.status,
                      message: check.message,
                    }))}
                    columns={[
                      {
                        title: '检查项',
                        dataIndex: 'name',
                        key: 'name',
                      },
                      {
                        title: '状态',
                        dataIndex: 'status',
                        key: 'status',
                        render: (status) => (
                          <Tag color={HEALTH_COLOR[status as keyof typeof HEALTH_COLOR]}>
                            {status}
                          </Tag>
                        ),
                      },
                      {
                        title: '信息',
                        dataIndex: 'message',
                        key: 'message',
                      },
                    ]}
                  />
                </>
              )}
            </Spin>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} md={12}>
          <Card title="实时自选股行情">
            <div className="watchlist-container">
              {watchlist.map((code) => {
                const quote = quotes.get(code);
                if (quote) {
                  return (
                    <PriceTicker key={code} quote={quote} />
                  );
                }
                return (
                  <Card size="small" key={code} className="price-ticker-loading">
                    {code} - 加载中...
                  </Card>
                );
              })}
            </div>
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="最近告警">
            {alerts.length === 0 ? (
              <div className="no-alerts">当前没有活跃告警</div>
            ) : (
              <List
                dataSource={alerts}
                renderItem={(item) => (
                  <List.Item>
                    <div>
                      <Tag color={HEALTH_COLOR[item.status as keyof typeof HEALTH_COLOR]}>
                        {item.status}
                      </Tag>
                      <strong style={{ marginLeft: 8 }}>{item.name}</strong>
                      <div style={{ color: '#999', fontSize: 12, marginTop: 4 }}>
                        {item.message}
                      </div>
                    </div>
                  </List.Item>
                )}
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
