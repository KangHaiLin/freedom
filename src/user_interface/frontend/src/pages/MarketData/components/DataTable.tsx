/**
 * K线数据表格组件
 */
import React from 'react';
import { Table } from 'antd';
import { DailyKline } from '@/api/types';
import { formatPrice, formatVolume, formatAmount } from '@/utils/formatters';
import { getChangeColor } from '@/utils/formatters';

interface DataTableProps {
  data: DailyKline[];
  loading: boolean;
}

const DataTable: React.FC<DataTableProps> = ({ data, loading }) => {
  const columns = [
    {
      title: '日期',
      dataIndex: 'trade_date',
      key: 'trade_date',
      width: 120,
    },
    {
      title: '开盘',
      dataIndex: 'open',
      key: 'open',
      render: formatPrice,
      width: 80,
    },
    {
      title: '收盘',
      dataIndex: 'close',
      key: 'close',
      render: formatPrice,
      width: 80,
    },
    {
      title: '最高',
      dataIndex: 'high',
      key: 'high',
      render: formatPrice,
      width: 80,
    },
    {
      title: '最低',
      dataIndex: 'low',
      key: 'low',
      render: formatPrice,
      width: 80,
    },
    {
      title: '涨跌幅',
      dataIndex: 'pct_change',
      key: 'pct_change',
      render: (pct: number) => {
        const color = getChangeColor(pct);
        return <span style={{ color }}>{formatPrice(pct)}%</span>;
      },
      width: 90,
    },
    {
      title: '成交量(手)',
      dataIndex: 'volume',
      key: 'volume',
      render: formatVolume,
    },
    {
      title: '成交额',
      dataIndex: 'amount',
      key: 'amount',
      render: formatAmount,
    },
  ];

  return (
    <Table
      columns={columns}
      dataSource={data}
      loading={loading}
      rowKey="trade_date"
      pagination={{
        pageSize: 20,
        showSizeChanger: true,
        showTotal: (total) => `共 ${total} 条`,
      }}
      scroll={{ x: 800 }}
      size="small"
    />
  );
};

export default DataTable;
