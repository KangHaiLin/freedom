/**
 * 策略回测监控页面
 * 回测任务列表，性能指标可视化
 */
import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Table, Progress, Tag, Typography, Spin, Alert } from 'antd';
import ReactECharts from 'echarts-for-react';
import { BacktestTask } from '@/api/types';
import { getBacktestTasks } from '@/api/system';
import { formatPercent, formatDecimal } from '@/utils/formatters';
import './index.css';

const { Title } = Typography;

const statusColors: Record<string, string> = {
  pending: 'default',
  running: 'processing',
  completed: 'success',
  failed: 'error',
};

const StrategyMonitoring: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [tasks, setTasks] = useState<BacktestTask[]>([]);

  const fetchTasks = async () => {
    setLoading(true);
    try {
      const data = await getBacktestTasks();
      setTasks(data);
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
    // 每10秒刷新一次
    const interval = setInterval(fetchTasks, 10000);
    return () => clearInterval(interval);
  }, []);

  // 计算权益曲线数据（模拟）
  const getEquityOption = () => {
    if (tasks.length === 0) {
      return {
        title: { text: '暂无回测任务', left: 'center' },
      };
    }

    // 找到最近完成的有结果的任务
    const completedTask = tasks.find(
      (t) => t.status === 'completed' && t.result
    );

    if (!completedTask?.result) {
      return {
        title: { text: '暂无完成的回测', left: 'center' },
      };
    }

    // 生成模拟的权益曲线
    const points = 100;
    const data = [];
    let base = 100;
    for (let i = 0; i < points; i++) {
      const change = (Math.random() - 0.45) * 2;
      base = base * (1 + change / 100);
      data.push([i + 1, Number(base.toFixed(2))]);
    }

    return {
      tooltip: {
        trigger: 'axis',
      },
      xAxis: {
        type: 'category',
        name: '交易日',
      },
      yAxis: {
        type: 'value',
        name: '权益',
      },
      series: [
        {
          name: '权益曲线',
          data: data,
          type: 'line',
          smooth: true,
          areaStyle: {
            opacity: 0.2,
          },
        },
      ],
    };
  };

  const columns = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '策略',
      dataIndex: 'strategy',
      key: 'strategy',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string, task: BacktestTask) => (
        <div>
          <Tag color={statusColors[status]}>{status}</Tag>
          {status === 'running' && (
            <Progress percent={task.progress} size="small" style={{ width: 100, marginTop: 4 }} />
          )}
        </div>
      ),
    },
    {
      title: '开始时间',
      dataIndex: 'start_time',
      key: 'start_time',
    },
    {
      title: '收益率',
      key: 'return',
      render: (_, task) =>
        task.result ? formatPercent(task.result.total_return * 100) : '-',
    },
    {
      title: '夏普比率',
      key: 'sharpe',
      render: (_, task) =>
        task.result ? formatDecimal(task.result.sharpe_ratio, 2) : '-',
    },
    {
      title: '最大回撤',
      key: 'drawdown',
      render: (_, task) =>
        task.result ? formatPercent(task.result.max_drawdown * 100) : '-',
    },
  ];

  // 汇总统计
  const stats = {
    total: tasks.length,
    running: tasks.filter((t) => t.status === 'running').length,
    completed: tasks.filter((t) => t.status === 'completed').length,
    failed: tasks.filter((t) => t.status === 'failed').length,
  };

  return (
    <div className="strategy-page">
      <Title level={2}>策略回测监控</Title>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={6}>
          <Card title="总任务数">
            <div className="stat-big">{stats.total}</div>
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card title="运行中">
            <div className="stat-big" style={{ color: '#1890ff' }}>
              {stats.running}
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card title="已完成">
            <div className="stat-big" style={{ color: '#52c41a' }}>
              {stats.completed}
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card title="失败">
            <div className="stat-big" style={{ color: '#ff4d4f' }}>
              {stats.failed}
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24}>
          <Card title="权益曲线示例（最近完成）">
            <ReactECharts option={getEquityOption()} style={{ height: 350 }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24}>
          <Card title="回测任务列表">
            <Spin spinning={loading}>
              {tasks.length === 0 && !loading ? (
                <Alert message="暂无回测任务" type="info" />
              ) : (
                <Table
                  columns={columns}
                  dataSource={tasks}
                  rowKey="id"
                  pagination={{ pageSize: 10 }}
                />
              )}
            </Spin>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default StrategyMonitoring;
