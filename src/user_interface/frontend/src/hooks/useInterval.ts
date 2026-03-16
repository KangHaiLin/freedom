/**
 * 定时器轮询 Hook
 */
import { useEffect, useRef } from 'react';

export function useInterval(callback: () => void, delay: number | null) {
  const savedCallback = useRef<() => void>();

  // 保存最新的回调
  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  // 设置定时器
  useEffect(() => {
    if (delay !== null) {
      const id = setInterval(() => {
        savedCallback.current?.();
      }, delay);
      return () => clearInterval(id);
    }
  }, [delay]);
}

export default useInterval;
