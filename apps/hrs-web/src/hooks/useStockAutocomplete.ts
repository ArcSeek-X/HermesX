/**
 * useStockAutocomplete —— 股票搜索（自动搜索补全）
 *
 * 文件作用：
 * 管理搜索框"输入即提示"的完整交互逻辑：接收股票索引（来自 useStockIndex），
 * 在用户输入时基于本地索引做模糊搜索（支持代码/中文名/拼音全拼/拼音简拼/别名），
 * 通过防抖避免高频输入频繁计算，并对外暴露：
 *   - 候选列表（suggestions）与下拉开关（isOpen）、键盘高亮索引（highlightedIndex）
 *   - 键盘上下选择（highlightPrevious/highlightNext）、回车确认（handleSelect）
 *   - IME 输入法组合态（isComposing）、运行时降级标记（runtimeFallback）
 * 调用方：StockSearch 搜索框组件（K 线页、聊天页等复用）。
 *
 * 注意：本文件是"股票索引搜索"版本；曾因误被替换为"通用 fetcher 自动补全"版本
 * 导致搜索框组件渲染崩溃并永久降级，请勿再混淆。
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import type { StockIndexItem, StockSuggestion } from '../types/stockIndex';
import { searchStocks } from '../utils/searchStocks';
import { SEARCH_CONFIG } from '../utils/stockIndexSchema';

/** useStockAutocomplete 可配置项 */
export interface UseStockAutocompleteOptions {
  /** 触发搜索的最小输入长度（低于该长度不匹配，默认取 SEARCH_CONFIG.MIN_QUERY_LENGTH=2） */
  minLength?: number;
  /** 输入防抖延迟（毫秒，默认取 SEARCH_CONFIG.DEBOUNCE_MS=200） */
  debounceMs?: number;
  /** 候选结果条数上限（默认取 SEARCH_CONFIG.DEFAULT_LIMIT=10） */
  limit?: number;
}

/** useStockAutocomplete 返回的状态与方法集合 */
export interface UseStockAutocompleteResult {
  /** 当前输入文本 */
  query: string;
  /** 更新输入文本（内部带防抖，防抖结束后触发搜索） */
  setQuery: (value: string) => void;
  /** 搜索候选列表（StockSuggestion[]，含匹配类型/匹配字段/得分） */
  suggestions: StockSuggestion[];
  /** 是否展开下拉列表 */
  isOpen: boolean;
  /** 键盘高亮的候选索引（-1 表示未高亮任何项） */
  highlightedIndex: number;
  /** 手动设置高亮索引 */
  setHighlightedIndex: (index: number) => void;
  /** 高亮上移（循环到末尾） */
  highlightPrevious: () => void;
  /** 高亮下移（循环到开头） */
  highlightNext: () => void;
  /** 选中某个候选：回填代码、收起下拉、清空高亮 */
  handleSelect: (suggestion: StockSuggestion) => void;
  /** 关闭下拉并清空高亮 */
  close: () => void;
  /** 重置全部搜索状态（清空输入、候选、下拉、高亮） */
  reset: () => void;
  /** 是否处于输入法组合输入中（组合期间不响应回车等快捷键） */
  isComposing: boolean;
  /** 设置输入法组合状态 */
  setIsComposing: (composing: boolean) => void;
  /** 是否已进入运行时降级模式（搜索逻辑抛错后置 true，调用方退化为普通输入框） */
  runtimeFallback: boolean;
  /** 搜索流程捕获到的运行时错误 */
  error: Error | null;
}

/**
 * 自动补全 Hook
 *
 * @param index   股票索引数据（由 useStockIndex 提供）
 * @param options 配置项（最小长度 / 防抖 / 结果上限，均可省略走默认值）
 * @returns 自动补全状态与方法（见 UseStockAutocompleteResult）
 */
export function useStockAutocomplete(
  index: StockIndexItem[],
  options: UseStockAutocompleteOptions = {}
): UseStockAutocompleteResult {
  // 从配置项取值，缺省时使用股票索引字段表里统一定义的默认值
  const {
    minLength = SEARCH_CONFIG.MIN_QUERY_LENGTH,
    debounceMs = SEARCH_CONFIG.DEBOUNCE_MS,
    limit = SEARCH_CONFIG.DEFAULT_LIMIT,
  } = options;

  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<StockSuggestion[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState<number>(-1);
  const [isComposing, setIsComposing] = useState(false);
  // 运行时降级标记：本地搜索抛错后置 true，之后不再搜索，交回调用方降级处理
  const [runtimeFallback, setRuntimeFallback] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // 防抖定时器引用（组件卸载时统一清理）
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 实际搜索函数（由防抖定时器在延迟结束后调用）
  const search = useCallback((q: string) => {
    // 已降级则不再执行搜索，避免反复抛错
    if (runtimeFallback) {
      return;
    }

    // 输入过短（如只有一个字符）直接清空候选并收起下拉
    if (q.length < minLength) {
      setSuggestions([]);
      setIsOpen(false);
      setHighlightedIndex(-1);
      return;
    }

    try {
      // 本地索引模糊匹配：代码/名称/拼音全拼/简拼/别名，返回按得分排序的候选
      const results = searchStocks(q, index, { limit });
      setSuggestions(results);
      // 有匹配才展开下拉；匹配不到时收起，避免空列表闪烁
      setIsOpen(results.length > 0);
      // 每次新搜索默认不高亮任何项，由用户按方向键主动选择
      setHighlightedIndex(-1);
    } catch (caught) {
      // 搜索逻辑异常（理论上不该发生）：记录错误并进入降级模式，
      // 调用方（StockSearch）会退化为普通输入框，保证搜索功能不整体失效
      const runtimeError = caught instanceof Error ? caught : new Error('Autocomplete search failed');
      console.error('Autocomplete search failed. Falling back to plain input.', runtimeError);
      setError(runtimeError);
      setRuntimeFallback(true);
      setSuggestions([]);
      setIsOpen(false);
      setHighlightedIndex(-1);
    }
  }, [index, minLength, limit, runtimeFallback]);

  // 输入变化处理：先更新 query，再做防抖延迟搜索（连续输入只保留最后一次）
  const handleInputChange = useCallback((value: string) => {
    setQuery(value);

    // 清除上一次的防抖定时器，实现"停止输入 debounceMs 后才搜索"
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // 已降级则不再发起搜索
    if (runtimeFallback) {
      return;
    }

    // 启动新的防抖定时器
    debounceTimerRef.current = setTimeout(() => {
      search(value);
    }, debounceMs);
  }, [search, debounceMs, runtimeFallback]);

  // 选中候选：把候选的展示代码回填到输入框，并收起下拉、清空高亮
  const handleSelect = useCallback((suggestion: StockSuggestion) => {
    setQuery(suggestion.displayCode);
    setIsOpen(false);
    setSuggestions([]);
    setHighlightedIndex(-1);
  }, []);

  // 高亮上移：无候选时不动；已在首项则循环跳到最后一项
  const highlightPrevious = useCallback(() => {
    setHighlightedIndex(prev => {
      if (prev <= 0) return suggestions.length - 1;
      return prev - 1;
    });
  }, [suggestions.length]);

  // 高亮下移：无候选时不动；已在末项则循环跳到第一项
  const highlightNext = useCallback(() => {
    setHighlightedIndex(prev => {
      if (prev >= suggestions.length - 1) return 0;
      return prev + 1;
    });
  }, [suggestions.length]);

  // 关闭下拉并清空高亮（如失焦、按 Esc）
  const close = useCallback(() => {
    setIsOpen(false);
    setHighlightedIndex(-1);
  }, []);

  // 重置全部状态（清空输入内容与候选）
  const reset = useCallback(() => {
    setQuery('');
    setSuggestions([]);
    setIsOpen(false);
    setHighlightedIndex(-1);
  }, []);

  // 组件卸载时清理防抖定时器，防止卸载后定时器触发 setState
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  return {
    query,
    setQuery: handleInputChange,
    suggestions,
    isOpen,
    highlightedIndex,
    setHighlightedIndex,
    highlightPrevious,
    highlightNext,
    handleSelect,
    close,
    reset,
    isComposing,
    setIsComposing,
    runtimeFallback,
    error,
  };
}

/**
 * 默认导出 Hook（与具名导出等价，便于按需 import 风格使用）
 */
export default useStockAutocomplete;
