/**
 * useStockIndex —— 主要指数概览数据钩子。
 *
 * 职责：
 * - 从后端拉取大盘主要指数（如上证、深证、创业板等）的实时/延时行情。
 * - 对外暴露指数列表、加载态、错误态与手动刷新方法。
 *
 * 设计：数据获取与渲染组件解耦，页面只需消费返回的状态，无需关心请求细节。
 */

import { useCallback, useEffect, useState } from 'react';

/** 单条指数行情的展示模型。 */
export interface StockIndex {
  /** 指数代码，如 000001（上证综指） */
  code: string;
  /** 指数名称 */
  name: string;
  /** 最新点位 */
  value: number;
  /** 涨跌幅（百分比，如 1.25 表示 +1.25%） */
  changePercent: number;
}

/** 从 data_service 获取指数行情的抽象（实际实现注入于调用处）。 */
export type StockIndexFetcher = () => Promise<StockIndex[]>;

export interface UseStockIndexOptions {
  /** 拉取指数行情的函数 */
  fetcher: StockIndexFetcher;
  /** 是否自动在挂载时拉取，默认 true */
  autoFetch?: boolean;
}

export function useStockIndex({ fetcher, autoFetch = true }: UseStockIndexOptions) {
  const [indices, setIndices] = useState<StockIndex[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // 封装一次拉取：管理加载/错误态并写入结果
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetcher();
      setIndices(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  }, [fetcher]);

  // 默认挂载即拉取
  useEffect(() => {
    if (autoFetch) {
      void load();
    }
  }, [autoFetch, load]);

  return { indices, loading, error, refresh: load };
}
