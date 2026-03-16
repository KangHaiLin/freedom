/**
 * API 调用 Hook
 * 自动处理 loading、error、data 状态
 */
import { useState, useCallback, useRef } from 'react';

export interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

export function useApi<T>() {
  const [state, setState] = useState<ApiState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const isMountedRef = useRef(true);

  const request = useCallback(
    async (apiCall: () => Promise<T>): Promise<T | null> => {
      setState({ data: null, loading: true, error: null });

      try {
        const data = await apiCall();
        if (isMountedRef.current) {
          setState({ data, loading: false, error: null });
        }
        return data;
      } catch (error) {
        if (isMountedRef.current) {
          setState({
            data: null,
            loading: false,
            error: error instanceof Error ? error : new Error(String(error)),
          });
        }
        return null;
      }
    },
    []
  );

  const setData = useCallback((data: T) => {
    setState({ data, loading: false, error: null });
  }, []);

  const clear = useCallback(() => {
    setState({ data: null, loading: false, error: null });
  }, []);

  return {
    ...state,
    request,
    setData,
    clear,
  };
}

export default useApi;
