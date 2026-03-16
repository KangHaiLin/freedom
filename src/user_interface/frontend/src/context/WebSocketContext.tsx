/**
 * WebSocket 上下文
 * 全局共享一个 WebSocket 连接
 */
import React, { createContext, useContext, useEffect } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { RealtimeQuote } from '../api/types';

interface WebSocketContextType {
  connected: boolean;
  quotes: Map<string, RealtimeQuote>;
  connect: () => void;
  disconnect: () => void;
  subscribe: (codes: string[]) => void;
  unsubscribe: (codes: string[]) => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

interface WebSocketProviderProps {
  children: React.ReactNode;
  autoConnect?: boolean;
}

export function WebSocketProvider({
  children,
  autoConnect = true,
}: WebSocketProviderProps) {
  const ws = useWebSocket();

  useEffect(() => {
    if (autoConnect) {
      ws.connect();
      return () => {
        ws.disconnect();
      };
    }
  }, [autoConnect, ws]);

  return (
    <WebSocketContext.Provider value={ws}>{children}</WebSocketContext.Provider>
  );
}

export function useWebSocketContext(): WebSocketContextType {
  const context = useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error(
      'useWebSocketContext must be used within a WebSocketProvider'
    );
  }
  return context;
}

export default WebSocketContext;
