/**
 * K线数据表格组件
 */
import React from 'react';
import { Table } from 'antd';
import { DailyKline, MinuteKline } from '@/api/types';
import { formatPrice, formatVolume, formatAmount } from '@/utils/formatters';
import { getChangeColor } from '@/utils/formatters';

interface DataTableProps {
  data: (DailyKline | MinuteKline)[];
  loading: boolean;
}

const DataTable: React.FC<DataTableProps> = ({ data, loading }) => {
  const columns = [
    {
      title: '时间',
      key: 'time',
      width: 140,
      render: (item: DailyKline | MinuteKline) => {
        return 'trade_date' in item ? item.trade_date : item.trade_time;
      },
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
      key: 'pct_change',
      width: 90,
      render: (item: DailyKline | MinuteKline) => {
        if ('pct_change' in item) {
          const color = getChangeColor(item.pct_change);
          return <span style={{ color }}>{formatPrice(item.pct_change)}%</span>;
        }
        return '-';
      },
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
      rowKey={(item) => ('trade_date' in item ? item.trade_date : item.trade_time)}
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
