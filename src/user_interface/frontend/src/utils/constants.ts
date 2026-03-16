/**
 * 应用常量
 */

// 侧边栏菜单项
export const MENU_ITEMS = [
  {
    key: '/dashboard',
    label: '仪表板',
    icon: 'dashboard',
  },
  {
    key: '/market',
    label: '行情数据',
    icon: 'stock',
  },
  {
    key: '/strategy',
    label: '策略监控',
    icon: 'strategy',
  },
  {
    key: '/system',
    label: '系统状态',
    icon: 'setting',
  },
];

// K线周期选项
export const KLINE_FREQS = [
  { label: '日线', value: '1d' },
  { label: '1分钟', value: '1m' },
  { label: '5分钟', value: '5m' },
  { label: '15分钟', value: '15m' },
];

// 涨跌颜色
export const UP_COLOR = '#ef5350';
export const DOWN_COLOR = '#26a69a';
export const FLAT_COLOR = '#9e9e9e';

// 健康状态颜色
export const HEALTH_COLOR = {
  ok: '#52c41a',
  warning: '#faad14',
  critical: '#ff4d4f',
};

// 格式常量
export const DATE_FORMAT = 'YYYY-MM-DD';
export const DATETIME_FORMAT = 'YYYY-MM-DD HH:mm:ss';
