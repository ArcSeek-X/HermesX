/**
 * useCachedState —— 带浏览器持久化的 useState 增强版。
 *
 * 与普通 useState 的区别：状态变化会自动写入 localStorage / sessionStorage（带 HRS 前缀），
 * 组件再次挂载时优先从存储恢复，实现「刷新不丢状态」。
 *
 * 适用：用户偏好、表单草稿、折叠面板展开态等希望跨会话保留的轻量数据。
 * 底层复用 utils/storage 的存储工具，自带前缀与异常安全降级。
 */

import { useCallback, useEffect, useState } from 'react';
import { getStorageItem, removeStorageItem, setStorageItem } from '../utils/storage';

export interface UseCachedStateOptions {
  /** 存储类型：'local'（localStorage，永久，默认）或 'session'（sessionStorage，会话级） */
  storage?: 'local' | 'session';
}

/**
 * 带持久化的 useState。
 *
 * @param key - 存储键名（自动加 HRS 前缀，无需手动加）
 * @param defaultValue - 初始默认值（仅在无持久化值时使用）
 * @param options - 可选配置，storage 指定使用 localStorage 还是 sessionStorage
 * @returns [value, setValue, reset]，reset 用于清空持久化值并恢复默认
 *
 * @example
 * ```typescript
 * const [period, setPeriod] = useCachedState<KLinePeriod>('kline.period', '1m', { storage: 'local' });
 * ```
 */
export function useCachedState<T>(
  key: string,
  defaultValue: T,
  { storage = 'local' }: UseCachedStateOptions = {},
) {
  // 惰性初始化：首次渲染时尝试从存储读取，失败则回退默认值
  const [value, setValue] = useState<T>(() => {
    const stored = getStorageItem<T>(key, storage);
    return stored === null ? defaultValue : stored;
  });

  // 状态变化即写回存储，保证持久化与内存状态一致
  useEffect(() => {
    setStorageItem(key, value, storage);
  }, [key, value, storage]);

  // 暴露一个重置入口，清空内存态与持久化值
  const reset = useCallback(() => {
    removeStorageItem(key, storage);
    setValue(defaultValue);
  }, [key, storage, defaultValue]);

  return [value, setValue, reset] as const;
}
