/**
 * 系统状态页面
 * CPU、内存、磁盘监控，数据源状态，系统信息
 */
import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Table, Tag, Spin, Typography } from 'antd';
import { SystemMetrics, ApplicationMetrics, DataSourceStatus } from '@/api/types';
import { getSystemMetrics, getApplicationMetrics, getDataSourceStatus } from '@/api/monitor';
import { getSystemInfo } from '@/api/system';
import { HEALTH_COLOR } from '@/utils/constants';
import { formatDuration, formatPercent, formatDecimal } from '@/utils/formatters';
import { useInterval } from '@/hooks/useInterval';
import CpuGauge from './components/CpuGauge';
import MemoryGauge from './components/MemoryGauge';
import StorageStatus from './components/StorageStatus';
import './index.css';

const { Title } = Typography;

const SystemStatus: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics | null>(null);
  const [appMetrics, setAppMetrics] = useState<ApplicationMetrics | null>(null);
  const [dataSources, setDataSources] = useState<DataSourceStatus[]>([]);
  const [systemInfo, setSystemInfo] = useState<any>(null);

  const fetchAll = async () => {
    try {
      const [sysMetrics, appM, dsInfo, sysInfo] = await Promise.all([
        getSystemMetrics(),
        getApplicationMetrics(),
        getDataSourceStatus(),
        getSystemInfo(),
      ]);
      setSystemMetrics(sysMetrics);
      setAppMetrics(appM);
      setDataSources(dsInfo);
      setSystemInfo(sysInfo);
    } catch (error) {
      console.error('Failed to fetch system info:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  // 每15秒刷新一次
  useInterval(() => {
    fetchAll();
  }, 15000);

  const dataSourceColumns = [
    {
      title: '数据源名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '可用性',
      dataIndex: 'available',
      key: 'available',
      render: (available: boolean) => (
        <Tag color={available ? HEALTH_COLOR.ok : HEALTH_COLOR.critical}>
          {available ? '可用' : '不可用'}
        </Tag>
      ),
    },
    {
      title: '延迟(ms)',
      dataIndex: 'latency_ms',
      key: 'latency_ms',
      render: (latency: number) => latency.toFixed(2),
    },
    {
      title: '最后更新',
      dataIndex: 'last_update',
      key: 'last_update',
    },
    {
      title: '信息',
      dataIndex: 'message',
      key: 'message',
    },
  ];

  return (
    <div className="system-status-page">
      <Title level={2}>系统状态监控</Title>

      <Spin spinning={loading}>
        <Row gutter={[16, 16]}>
          <Col xs={24} md={8}>
            <Card>
              <CpuGauge metrics={systemMetrics} />
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card>
              <MemoryGauge metrics={systemMetrics} />
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <StorageStatus metrics={systemMetrics} />
          </Col>
        </Row>

        {appMetrics && (
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={24}>
              <Card title="应用性能指标">
                <Row gutter={[16, 16]}>
                  <Col xs={24} sm={6}>
                    <div className="metric-card">
                      <div className="metric-label">总请求数</div>
                      <div className="metric-value">{appMetrics.requests.total}</div>
                    </div>
                  </Col>
                  <Col xs={24} sm={6}>
                    <div className="metric-card">
                      <div className="metric-label">QPS</div>
                      <div className="metric-value">{formatDecimal(appMetrics.requests.qps, 2)}</div>
                    </div>
                  </Col>
                  <Col xs={24} sm={6}>
                    <div className="metric-card">
                      <div className="metric-label">错误率</div>
                      <div className="metric-value" style={{
                        color: appMetrics.requests.error_rate > 0.05 ? '#ff4d4f' : undefined,
                      }}>
                        {formatPercent(appMetrics.requests.error_rate * 100)}
                      </div>
                    </div>
                  </Col>
                  <Col xs={24} sm={6}>
                    <div className="metric-card">
                      <div className="metric-label">平均延迟(ms)</div>
                      <div className="metric-value">{formatDecimal(appMetrics.requests.latency_avg * 1000, 2)}</div>
                    </div>
                  </Col>
                </Row>
                <Row gutter={[16, 16]} style={{ marginTop: 8 }}>
                  <Col xs={24} sm={6}>
                    <div className="metric-card">
                      <div className="metric-label">P95延迟(ms)</div>
                      <div className="metric-value">{formatDecimal(appMetrics.requests.latency_p95 * 1000, 2)}</div>
                    </div>
                  </Col>
                  <Col xs={24} sm={6}>
                    <div className="metric-card">
                      <div className="metric-label">P99延迟(ms)</div>
                      <div className="metric-value">{formatDecimal(appMetrics.requests.latency_p99 * 1000, 2)}</div>
                    </div>
                  </Col>
                </Row>
              </Card>
            </Col>
          </Row>
        )}

        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} md={16}>
            <Card title="数据源状态">
              <Table
                columns={dataSourceColumns}
                dataSource={dataSources}
                pagination={false}
                rowKey="name"
                size="small"
              />
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card title="系统信息">
              {systemInfo && (
                <div className="system-info-list">
                  <div className="info-item">
                    <span className="info-label">版本:</span>
                    <span className="info-value">{systemInfo.version}</span>
                  </div>
                  <div className="info-item">
                    <span className="info-label">Python版本:</span>
                    <span className="info-value">{systemInfo.python_version}</span>
                  </div>
                  <div className="info-item">
                    <span className="info-label">操作系统:</span>
                    <span className="info-value">{systemInfo.os}</span>
                  </div>
                  <div className="info-item">
                    <span className="info-label">启动时间:</span>
                    <span className="info-value">{systemInfo.start_time}</span>
                  </div>
                  <div className="info-item">
                    <span className="info-label">运行时间:</span>
                    <span className="info-value">
                      {formatDuration(systemInfo.uptime_seconds)}
                    </span>
                  </div>
                </div>
              )}
            </Card>
          </Col>
        </Row>
      </Spin>
    </div>
  );
};

export default SystemStatus;
