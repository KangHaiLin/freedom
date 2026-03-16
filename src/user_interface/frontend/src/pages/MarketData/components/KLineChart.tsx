/**
 * K线图组件
 */
import React from 'react';
import ReactECharts from 'echarts-for-react';
import { DailyKline, MinuteKline } from '@/api/types';

interface KLineChartProps {
  data: (DailyKline | MinuteKline)[];
}

const KLineChart: React.FC<KLineChartProps> = ({ data }) => {
  const option = getOption(data);

  return (
    <ReactECharts
      option={option}
      style={{ height: 500, width: '100%' }}
      notMerge={true}
    />
  );
};

function getOption(data: (DailyKline | MinuteKline)[]) {
  if (!data || data.length === 0) {
    return {
      title: {
        text: '暂无数据',
        left: 'center',
        top: 'center',
      },
    };
  }

  // 格式化数据
  const dates: string[] = [];
  const values: number[][] = [];
  const volumes: number[] = [];

  data.forEach((item) => {
    const date = 'trade_date' in item ? item.trade_date : item.trade_time;
    dates.push(date);
    values.push([item.open, item.close, item.low, item.high]);
    volumes.push(item.volume);
  });

  // 计算均线
  const ma5 = calculateMA(values, 5);
  const ma10 = calculateMA(values, 10);
  const ma20 = calculateMA(values, 20);

  return {
    animation: true,
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
      },
    },
    legend: {
      data: ['K线', 'MA5', 'MA10', 'MA20'],
      top: 10,
    },
    grid: [
      {
        left: '10%',
        right: '8%',
        top: 60,
        height: '50%',
      },
      {
        left: '10%',
        right: '8%',
        top: '65%',
        height: '25%',
      },
    ],
    xAxis: [
      {
        type: 'category',
        data: dates,
        boundaryGap: true,
        axisLine: { onZero: false },
        splitLine: { show: false },
        min: 'dataMin',
        max: 'dataMax',
      },
      {
        type: 'category',
        gridIndex: 1,
        data: dates,
        boundaryGap: true,
        axisLine: { onZero: false },
        axisTick: { show: false },
        splitLine: { show: false },
        min: 'dataMin',
        max: 'dataMax',
      },
    ],
    yAxis: [
      {
        type: 'value',
        scale: true,
        splitNumber: 5,
      },
      {
        type: 'value',
        scale: true,
        gridIndex: 1,
        splitNumber: 2,
        axisLabel: { show: false },
        axisLine: { show: false },
        axisTick: { show: false },
      },
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: values,
        itemStyle: {
          color: '#ef5350',
          color0: '#26a69a',
          borderColor: '#ef5350',
          borderColor0: '#26a69a',
        },
      },
      {
        name: 'MA5',
        type: 'line',
        data: ma5,
        smooth: true,
        symbol: 'none',
        lineStyle: {
          width: 1,
        },
      },
      {
        name: 'MA10',
        type: 'line',
        data: ma10,
        smooth: true,
        symbol: 'none',
        lineStyle: {
          width: 1,
        },
      },
      {
        name: 'MA20',
        type: 'line',
        data: ma20,
        smooth: true,
        symbol: 'none',
        lineStyle: {
          width: 1,
        },
      },
      {
        name: '成交量',
        type: 'bar',
        data: volumes,
        xAxisIndex: 1,
        yAxisIndex: 1,
        itemStyle: {
          color: '#1890ff',
        },
      },
    ],
  };
}

function calculateMA(candles: number[][], period: number): (number | null)[] {
  const result: (number | null)[] = [];
  for (let i = 0; i < candles.length; i++) {
    if (i < period - 1) {
      result.push(null);
      continue;
    }
    let sum = 0;
    for (let j = 0; j < period; j++) {
      sum += candles[i - j][1]; // close price
    }
    result.push(sum / period);
  }
  return result;
}

export default KLineChart;
