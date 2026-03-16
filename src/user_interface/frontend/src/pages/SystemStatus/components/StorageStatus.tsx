/**
 * 磁盘存储状态
 */
import React from 'react';
import { Progress, List, Card } from 'antd';
import { SystemMetrics } from '@/api/types';
import { formatBytes, formatPercent } from '@/utils/formatters';

interface StorageStatusProps {
  metrics: SystemMetrics | null;
}

const StorageStatus: React.FC<StorageStatusProps> = ({ metrics }) => {
  if (!metrics) {
    return <Card>暂无数据</Card>;
  }

  const percent = metrics.disk.percent;
  let status: 'normal' | 'active' | 'warning' | 'exception' = 'normal';
  if (percent > 85) {
    status = 'warning';
  }
  if (percent > 95) {
    status = 'exception';
  }

  return (
    <Card title="磁盘使用">
      <Progress
        percent={Number(percent.toFixed(1))}
        status={status}
        strokeWidth={20}
      />
      <div style={{ marginTop: 16, display: 'flex', justifyContent: 'space-between' }}>
        <span>已使用: {formatBytes(metrics.disk.used)}</span>
        <span>总共: {formatBytes(metrics.disk.total)}</span>
      </div>
    </Card>
  );
};

export default StorageStatus;
