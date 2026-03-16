/**
 * Axios 客户端配置
 * 自动添加 API Key 拦截器，统一错误处理
 */
import axios, { AxiosError, AxiosInstance, AxiosRequestConfig } from 'axios';
import { message } from 'antd';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

// 创建 Axios 实例
const client: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器：自动添加 API Key
client.interceptors.request.use(
  (config) => {
    // 从本地存储获取 API Key
    const apiKey = localStorage.getItem('quant_api_key');
    if (apiKey) {
      config.headers['X-API-Key'] = apiKey;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器：统一错误处理
client.interceptors.response.use(
  (response) => {
    const data = response.data;
    // 如果后端返回了 success 标记且不成功，显示错误
    if (data.success === false) {
      message.error(data.message || '请求失败');
      return Promise.reject(new Error(data.message || '请求失败'));
    }
    return response;
  },
  (error: AxiosError) => {
    if (error.response) {
      const status = error.response.status;
      if (status === 401) {
        message.error('未授权，请检查 API Key');
        // 清除无效的 API Key
        localStorage.removeItem('quant_api_key');
        window.location.reload();
      } else if (status === 403) {
        message.error('访问被拒绝');
      } else if (status === 404) {
        message.error('请求的资源不存在');
      } else if (status >= 500) {
        message.error('服务器错误');
      } else {
        message.error(`请求失败: ${status}`);
      }
    } else if (error.request) {
      message.error('网络错误，无法连接服务器');
    } else {
      message.error(`请求错误: ${error.message}`);
    }
    return Promise.reject(error);
  }
);

export default client;

// 通用请求方法包装
export const apiGet = async <T>(
  url: string,
  config?: AxiosRequestConfig
): Promise<T> => {
  const response = await client.get(url, config);
  return response.data.data;
};

export const apiPost = async <T>(
  url: string,
  data?: any,
  config?: AxiosRequestConfig
): Promise<T> => {
  const response = await client.post(url, data, config);
  return response.data.data;
};

export const apiPut = async <T>(
  url: string,
  data?: any,
  config?: AxiosRequestConfig
): Promise<T> => {
  const response = await client.put(url, data, config);
  return response.data.data;
};

export const apiDelete = async <T>(
  url: string,
  config?: AxiosRequestConfig
): Promise<T> => {
  const response = await client.delete(url, config);
  return response.data.data;
};
