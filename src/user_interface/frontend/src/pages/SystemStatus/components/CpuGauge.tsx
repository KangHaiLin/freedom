/**
 * CPU 使用率仪表盘
 */
import React from 'react';
import ReactECharts from 'echarts-for-react';
import { SystemMetrics } from '@/api/types';

interface CpuGaugeProps {
  metrics: SystemMetrics | null;
}

const CpuGauge: React.FC<CpuGaugeProps> = ({ metrics }) => {
  const percent = metrics?.cpu.percent || 0;

  const getOption = () => {
    let color = '#52c41a';
    if (percent > 70) {
      color = '#faad14';
    }
    if (percent > 90) {
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
                [0.7, '#52c41a'],
                [0.9, '#faad14'],
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
            fontSize: 30,
            fontWeight: 'bold',
            formatter: '{value}%',
            offsetCenter: [0, '-10%'],
            valueAnimation: true,
          },
          data: [
            {
              value: percent.toFixed(1),
              name: 'CPU使用率',
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

export default CpuGauge;
