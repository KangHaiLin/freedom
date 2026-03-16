/**
 * WebSocket 客户端
 * 单例连接管理，自动重连，订阅/取消订阅管理
 */
import { RealtimeQuote, WsMessage, WsSubscribe, WsQuoteUpdate } from './types';

type MessageCallback = (message: WsMessage) => void;
type QuoteCallback = (quote: RealtimeQuote) => void;

class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private connected: boolean = false;
  private reconnecting: boolean = false;
  private reconnectDelay: number = 1000;
  private maxReconnectDelay: number = 30000;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = Infinity;
  private subscriptions: Set<string> = new Set();
  private messageCallbacks: Set<MessageCallback> = new Set();
  private quoteCallbacks: Set<QuoteCallback> = new Set();

  constructor(url: string) {
    this.url = url;
  }

  connect(): void {
    if (this.ws !== null && this.ws.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.connected = true;
        this.reconnecting = false;
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
        // 重新订阅之前订阅的代码
        this.resubscribeAll();
      };

      this.ws.onclose = (event) => {
        this.connected = false;
        console.log(`WebSocket disconnected: code=${event.code}, reason=${event.reason}`);
        this.attemptReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      this.ws.onmessage = (event) => {
        this.handleMessage(event);
      };
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      this.attemptReconnect();
    }
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
      this.connected = false;
      this.reconnecting = false;
    }
  }

  isConnected(): boolean {
    return this.connected;
  }

  subscribe(codes: string[]): void {
    codes.forEach(code => this.subscriptions.add(code));
    if (this.connected) {
      this.sendSubscribe('subscribe', codes);
    }
  }

  unsubscribe(codes: string[]): void {
    codes.forEach(code => this.subscriptions.delete(code));
    if (this.connected) {
      this.sendSubscribe('unsubscribe', codes);
    }
  }

  unsubscribeAll(): void {
    const codes = Array.from(this.subscriptions);
    this.subscriptions.clear();
    if (this.connected && codes.length > 0) {
      this.sendSubscribe('unsubscribe', codes);
    }
  }

  private resubscribeAll(): void {
    const codes = Array.from(this.subscriptions);
    if (codes.length > 0) {
      this.sendSubscribe('subscribe', codes);
    }
  }

  private sendSubscribe(action: 'subscribe' | 'unsubscribe', codes: string[]): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const msg: WsSubscribe = { action, codes };
      this.ws.send(JSON.stringify(msg));
    }
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const message: WsMessage = JSON.parse(event.data);

      // 通知所有消息回调
      this.messageCallbacks.forEach(cb => {
        try {
          cb(message);
        } catch (e) {
          console.error('Error in message callback:', e);
        }
      });

      // 如果是行情更新，通知行情回调
      if (message.type === 'quote') {
        const quoteMsg = message as WsQuoteUpdate;
        this.quoteCallbacks.forEach(cb => {
          try {
            cb(quoteMsg.data);
          } catch (e) {
            console.error('Error in quote callback:', e);
          }
        });
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }

  private attemptReconnect(): void {
    if (this.reconnecting || this.reconnectAttempts >= this.maxReconnectAttempts) {
      return;
    }

    this.reconnecting = true;
    this.reconnectAttempts++;

    console.log(`Attempting reconnect in ${this.reconnectDelay}ms... (attempt ${this.reconnectAttempts})`);

    setTimeout(() => {
      if (!this.connected) {
        this.connect();
        // 指数退避
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
      }
    }, this.reconnectDelay);
  }

  addMessageCallback(callback: MessageCallback): () => void {
    this.messageCallbacks.add(callback);
    return () => this.messageCallbacks.delete(callback);
  }

  addQuoteCallback(callback: QuoteCallback): () => void {
    this.quoteCallbacks.add(callback);
    return () => this.quoteCallbacks.delete(callback);
  }

  send(data: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket not connected, message dropped');
    }
  }
}

// 全局单例
const WS_URL = (import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000/ws/realtime') as string;
const wsClient = new WebSocketClient(WS_URL);

export default wsClient;

// 便捷方法
export const connectWs = () => wsClient.connect();
export const disconnectWs = () => wsClient.disconnect();
export const subscribeQuotes = (codes: string[]) => wsClient.subscribe(codes);
export const unsubscribeQuotes = (codes: string[]) => wsClient.unsubscribe(codes);
export const addQuoteCallback = (cb: QuoteCallback) => wsClient.addQuoteCallback(cb);
export const isWsConnected = () => wsClient.isConnected();
