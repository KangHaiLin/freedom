/**
 * WebSocket Hook
 * 封装连接状态和订阅管理
 */
import { useEffect, useState, useCallback } from 'react';
import wsClient from '../api/websocket';
import { RealtimeQuote } from '../api/types';

export interface UseWebSocketReturn {
  connected: boolean;
  quotes: Map<string, RealtimeQuote>;
  connect: () => void;
  disconnect: () => void;
  subscribe: (codes: string[]) => void;
  unsubscribe: (codes: string[]) => void;
}

export function useWebSocket(): UseWebSocketReturn {
  const [connected, setConnected] = useState(wsClient.isConnected());
  const [quotes, setQuotes] = useState<Map<string, RealtimeQuote>>(new Map());

  useEffect(() => {
    // 添加报价更新回调
    const removeCallback = wsClient.addQuoteCallback((quote) => {
      setQuotes((prev) => {
        const next = new Map(prev);
        next.set(quote.code, quote);
        return next;
      });
    });

    // 检查连接状态
    setConnected(wsClient.isConnected());

    return () => {
      removeCallback();
    };
  }, []);

  const connect = useCallback(() => {
    wsClient.connect();
    setConnected(true);
  }, []);

  const disconnect = useCallback(() => {
    wsClient.disconnect();
    setConnected(false);
  }, []);

  const subscribe = useCallback((codes: string[]) => {
    wsClient.subscribe(codes);
  }, []);

  const unsubscribe = useCallback((codes: string[]) => {
    wsClient.unsubscribe(codes);
    setQuotes((prev) => {
      const next = new Map(prev);
      codes.forEach((code) => next.delete(code));
      return next;
    });
  }, []);

  return {
    connected,
    quotes,
    connect,
    disconnect,
    subscribe,
    unsubscribe,
  };
}

export default useWebSocket;
