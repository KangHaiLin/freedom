/**
 * 状态指标卡片
 * 用于仪表板显示概览指标
 */
import React from 'react';
import { Card, Statistic } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import './index.css';

interface StatusCardProps {
  title: string;
  value: number | string;
  suffix?: string;
  prefix?: string;
  change?: number;
  isIncreaseGood?: boolean;
  color?: string;
}

const StatusCard: React.FC<StatusCardProps> = ({
  title,
  value,
  suffix,
  prefix,
  change,
  isIncreaseGood = true,
  color,
}) => {
  const renderChange = () => {
    if (change === undefined) {
      return null;
    }
    const isGood = change > 0 ? isIncreaseGood : !isIncreaseGood;
    const color = isGood ? '#3f8600' : '#cf1322';
    const icon = change > 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />;
    return (
      <span style={{ color }}>
        {icon} {Math.abs(change).toFixed(1)}%
      </span>
    );
  };

  return (
    <Card>
      <Statistic
        title={title}
        value={value}
        suffix={suffix}
        prefix={prefix}
        valueStyle={color ? { color } : undefined}
      />
      {renderChange && (
        <div className="status-card-change">{renderChange()}</div>
      )}
    </Card>
  );
};

export default StatusCard;
