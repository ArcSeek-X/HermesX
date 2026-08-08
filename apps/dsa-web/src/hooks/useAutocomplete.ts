/**
 * useAutocomplete —— 输入框自动补全（typeahead）通用钩子。
 *
 * 能力：
 * - 维护输入框文本（query）、候选列表（suggestions）、加载态与高亮索引。
 * - 通过外部传入的 fetcher 异步拉取候选，并在文本变化后做防抖（debounce）。
 * - 支持键盘上下选择（activeIndex），回车确认、失焦收起等常见交互。
 *
 * 设计：与具体数据源解耦，任何「输入 → 拉取建议」的场景（股票代码、板块名等）都可复用。
 */

import { useCallback, useEffect, useRef, useState } from 'react';

/** fetcher 入参：当前输入文本；返回候选字符串数组（或空数组）。 */
export type AutocompleteFetcher = (query: string) => Promise<string[]>;

/** 钩子返回的一组状态与方法。 */
export interface UseAutocompleteOptions {
  /** 异步拉取候选的函数 */
  fetcher: AutocompleteFetcher;
  /** 防抖延迟（毫秒），默认 250ms */
  debounceMs?: number;
  /** 最小触发字符数，低于此长度不发起请求，默认 1 */
  minChars?: number;
}

export function useAutocomplete({ fetcher, debounceMs = 250, minChars = 1 }: UseAutocompleteOptions) {
  // 当前输入框文本
  const [query, setQuery] = useState('');
  // 候选列表
  const [suggestions, setSuggestions] = useState<string[]>([]);
  // 是否正在加载候选
  const [loading, setLoading] = useState(false);
  // 键盘高亮项索引（-1 表示未选中）
  const [activeIndex, setActiveIndex] = useState(-1);
  // 下拉是否展开
  const [open, setOpen] = useState(false);

  // 保存最新的 fetcher，避免因 fetcher 引用变化导致 effect 频繁重建
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;
  // 标记是否仍处于「最近一次请求」的有效窗口，组件卸载后避免 setState
  const aliveRef = useRef(true);

  useEffect(() => {
    aliveRef.current = true;
    return () => {
      aliveRef.current = false;
    };
  }, []);

  /**
   * 拉取候选：仅当 query 达到最小字符数时生效。
   * 使用定时器实现防抖，连续输入只保留最后一次请求。
   */
  useEffect(() => {
    if (query.trim().length < minChars) {
      setSuggestions([]);
      setOpen(false);
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const result = await fetcherRef.current(query.trim());
        if (!aliveRef.current) return;
        setSuggestions(result);
        setOpen(true);
      } catch {
        if (aliveRef.current) setSuggestions([]);
      } finally {
        if (aliveRef.current) setLoading(false);
      }
    }, debounceMs);

    return () => clearTimeout(timer);
  }, [query, debounceMs, minChars]);

  /** 选中某个候选：回填文本、收起下拉、清空高亮。 */
  const select = useCallback((value: string) => {
    setQuery(value);
    setOpen(false);
    setActiveIndex(-1);
  }, []);

  /** 键盘下移：在候选范围内循环高亮。 */
  const moveDown = useCallback(() => {
    setActiveIndex((i) => (suggestions.length ? (i + 1) % suggestions.length : -1));
  }, [suggestions.length]);

  /** 键盘上移：在候选范围内循环高亮。 */
  const moveUp = useCallback(() => {
    setActiveIndex((i) => (suggestions.length ? (i - 1 + suggestions.length) % suggestions.length : -1));
  }, [suggestions.length]);

  /** 关闭下拉（如失焦）。 */
  const close = useCallback(() => setOpen(false), []);

  return {
    query,
    setQuery,
    suggestions,
    loading,
    open,
    activeIndex,
    setActiveIndex,
    select,
    moveDown,
    moveUp,
    close,
  };
}
