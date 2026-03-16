/**
 * 环境配置
 */

export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || '/api',
  wsBaseUrl: import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000/ws/realtime',
  env: import.meta.env.MODE || 'development',
  isDevelopment: import.meta.env.DEV,
  isProduction: import.meta.env.PROD,
};

export default config;
