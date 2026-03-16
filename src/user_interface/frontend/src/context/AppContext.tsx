/**
 * 应用全局上下文
 * 存储 API Key、应用配置等全局状态
 */
import React, { createContext, useContext, useState, useEffect } from 'react';

interface AppContextType {
  apiKey: string;
  setApiKey: (key: string) => void;
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

interface AppProviderProps {
  children: React.ReactNode;
}

export function AppProvider({ children }: AppProviderProps) {
  // 从本地存储加载 API Key
  const [apiKey, setApiKeyState] = useState<string>(() => {
    return localStorage.getItem('quant_api_key') || '';
  });

  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);

  // 保存 API Key 到本地存储
  const setApiKey = (key: string) => {
    setApiKeyState(key);
    if (key) {
      localStorage.setItem('quant_api_key', key);
    } else {
      localStorage.removeItem('quant_api_key');
    }
  };

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  useEffect(() => {
    // 可以在这里做一些初始化工作
  }, []);

  const value: AppContextType = {
    apiKey,
    setApiKey,
    sidebarCollapsed,
    toggleSidebar,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

// 自定义 hook 方便使用
export function useAppContext(): AppContextType {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
}

export default AppContext;
