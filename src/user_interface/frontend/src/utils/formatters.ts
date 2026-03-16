/**
 * 格式化工具函数
 * 价格、日期、数字等格式化
 */

import { UP_COLOR, DOWN_COLOR, FLAT_COLOR } from './constants';

// 格式化价格
export const formatPrice = (price: number | null | undefined): string => {
  if (price === null || price === undefined) {
    return '-';
  }
  return price.toFixed(2);
};

// 格式化涨跌幅
export const formatChangePct = (pct: number | null | undefined): string => {
  if (pct === null || pct === undefined) {
    return '-';
  }
  const sign = pct > 0 ? '+' : '';
  return `${sign}${pct.toFixed(2)}%`;
};

// 获取涨跌颜色
export const getChangeColor = (change: number): string => {
  if (change > 0) {
    return UP_COLOR;
  } else if (change < 0) {
    return DOWN_COLOR;
  } else {
    return FLAT_COLOR;
  }
};

// 格式化成交量（手）
export const formatVolume = (volume: number | null | undefined): string => {
  if (volume === null || volume === undefined) {
    return '-';
  }
  if (volume >= 1000000) {
    return `${(volume / 1000000).toFixed(2)}M';
  }
  if (volume >= 1000) {
    return `${(volume / 1000).toFixed(2)}K';
  }
  return volume.toString();
};

// 格式化成交额
export const formatAmount = (amount: number | null | undefined): string => {
  if (amount === null || amount === undefined) {
    return '-';
  }
  // 单位：亿元
  if (amount >= 100000000) {
    return `${(amount / 100000000).toFixed(2)}亿';
  }
  // 单位：万元
  if (amount >= 10000) {
    return `${(amount / 10000).toFixed(2)}万';
  }
  return `${amount.toFixed(0)}`;
};

// 格式化字节数
export const formatBytes = (bytes: number): string => {
  if (bytes === 0) {
    return '0 B';
  }
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
};

// 格式化百分比
export const formatPercent = (value: number): string => {
  return `${value.toFixed(2)}%`;
};

// 格式化时间间隔
export const formatDuration = (seconds: number): string => {
  if (seconds < 60) {
    return `${seconds.toFixed(0)}秒`;
  }
  if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}分${secs.toFixed(0)}秒`;
  }
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}小时${minutes}分`;
};

// 格式化小数位数
export const formatDecimal = (value: number | undefined | null, decimals: number = 2): string => {
  if (value === null || value === undefined) {
    return '-';
  }
  return value.toFixed(decimals);
};
