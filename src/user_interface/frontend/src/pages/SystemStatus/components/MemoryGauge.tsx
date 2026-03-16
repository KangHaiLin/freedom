/**
 * 内存使用率仪表盘
 */
import React from 'react';
import ReactECharts from 'echarts-for-react';
import { SystemMetrics } from '@/api/types';
import { formatBytes } from '@/utils/formatters';

interface MemoryGaugeProps {
  metrics: SystemMetrics | null;
}

const MemoryGauge: React.FC<MemoryGaugeProps> = ({ metrics }) => {
  const percent = metrics?.memory.percent || 0;
  const used = metrics?.memory.used || 0;
  const total = metrics?.memory.total || 1;

  const getOption = () => {
    let color = '#52c41a';
    if (percent > 80) {
      color = '#faad14';
    }
    if (percent > 95) {
      color = '#ff4d4f';
    }

    return {
      series: [
        {
          type: 'gauge',
          startAngle: 180,
          endAngle: 0,
          min: 0,
          max: 100,
          splitNumber: 5,
          radius: '100%',
          center: ['50%', '75%'],
          axisLine: {
            lineStyle: {
              width: 30,
              color: [
                [0.8, '#52c41a'],
                [0.95, '#faad14'],
                [1, '#ff4d4f'],
              ],
            },
          },
          pointer: {
            length: '60%',
            width: 8,
          },
          title: {
            show: true,
            offsetCenter: [0, '20%'],
            fontSize: 16,
          },
          detail: {
            fontSize: 20,
            fontWeight: 'bold',
            formatter: '{value}%\n' + `${formatBytes(used)} / ${formatBytes(total)}`,
            offsetCenter: [0, '-15%'],
            valueAnimation: true,
            lineHeight: 25,
          },
          data: [
            {
              value: percent.toFixed(1),
              name: '内存使用率',
            },
          ],
        },
      ],
    };
  };

  return (
    <ReactECharts option={getOption()} style={{ height: 200, width: '100%' }} />
  );
};

export default MemoryGauge;
