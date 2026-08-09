/**
 * useStockIndex —— 股票索引加载 Hook
 *
 * 文件作用：
 * 负责加载前端本地股票索引（/stocks.index.json，约 3 万条，覆盖 A 股/港股/美股等，
 * 每条记录包含代码、中文名、拼音全拼/简拼、别名、市场、资产类型等字段），
 * 并把加载过程封装为 React 状态，对外暴露：
 *   - index：股票索引数据（供 searchStocks 本地模糊匹配使用）
 *   - loading / loaded：加载中 / 是否已完成加载
 *   - error / fallback：加载失败的错误信息与降级标记
 * 调用方：搜索框自动补全（StockAutocomplete）、聊天页股票识别（ChatPage）、
 * 决策信号页热门候选（DecisionSignalsPage）等。
 *
 * 注意：本文件是"股票索引"版本；曾因误被替换为"大盘指数概览"版本
 * 导致搜索框自动补全组件渲染崩溃并永久降级，请勿再混淆。
 */

import { useState, useEffect } from 'react';
import type { StockIndexItem } from '../types/stockIndex';
import { loadStockIndex } from '../utils/stockIndexLoader';
import type { IndexLoadResult } from '../utils/stockIndexLoader';

/** useStockIndex 返回的状态集合 */
export interface UseStockIndexResult {
  /** 股票索引数据（StockIndexItem[]，见 types/stockIndex.ts） */
  index: StockIndexItem[];
  /** 是否正在加载中 */
  loading: boolean;
  /** 加载失败时的错误对象（成功时为 null） */
  error: Error | null;
  /** 是否启用了降级模式（索引文件加载失败时置 true，调用方据此退化为普通输入框） */
  fallback: boolean;
  /** 索引是否已成功加载完成 */
  loaded: boolean;
}

/**
 * 股票索引加载 Hook
 *
 * @param enabled 是否启用加载；默认 true。传 false 时（如聊天页后端未就绪前）
 *                不发起请求，并返回全空的索引状态，避免无谓的网络开销。
 * @returns 索引数据与加载状态（见 UseStockIndexResult）
 */
export function useStockIndex(enabled = true): UseStockIndexResult {
  // 索引数据；loading 初始值跟随 enabled，避免启用时出现"未加载完成"的闪烁态
  const [index, setIndex] = useState<StockIndexItem[]>([]);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<Error | null>(null);
  // 降级标记：索引文件缺失/解析失败时为 true，调用方据此回退到"无自动补全"模式
  const [fallback, setFallback] = useState(false);

  useEffect(() => {
    // enabled 为 false 时不加载（聊天页等场景可延后到条件满足再启用）
    if (!enabled) {
      return;
    }

    // mounted 标记：组件卸载后丢弃异步结果，避免卸载后 setState 触发 React 警告
    let mounted = true;

    async function load() {
      setLoading(true);
      setError(null);

      // 从 /stocks.index.json 读取并解析索引（压缩 tuple 格式会被自动解包）
      const result: IndexLoadResult = await loadStockIndex();

      // 组件仍在挂载中才提交状态，防止竞态与内存泄漏
      if (mounted) {
        setIndex(result.data);
        setFallback(result.fallback);
        if (result.error) {
          setError(result.error);
        }
        setLoading(false);
      }
    }

    load();

    // 卸载时置 mounted 为 false，使进行中的请求结果被丢弃
    return () => {
      mounted = false;
    };
  }, [enabled]);

  return {
    // enabled 为 false 时统一返回空数据/空闲状态，保证调用方拿到的状态自洽
    index: enabled ? index : [],
    loading: enabled ? loading : false,
    error: enabled ? error : null,
    fallback: enabled ? fallback : false,
    loaded: enabled ? !loading : false,
  };
}

/**
 * 默认导出 Hook（与具名导出等价，便于按需 import 风格使用）
 */
export default useStockIndex;
