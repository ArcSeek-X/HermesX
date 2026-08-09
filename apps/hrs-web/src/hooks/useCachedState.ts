/**
 * useCachedState —— 带本地持久化的 useState 增强版。
 *
 * 与普通 useState 的区别：状态变化会自动写入 localStorage（默认 key），
 * 组件再次挂载时优先从 localStorage 恢复，实现「刷新不丢状态」。
 *
 * 适用：用户偏好、表单草稿、折叠面板展开态等希望跨会话保留的轻量数据。
 */

import { useCallback, useEffect, useState } from 'react';

/** JSON 安全值均可作为状态类型。 */
export type CachedValue = unknown;

export interface UseCachedStateOptions {
  /** localStorage 键名 */
  key: string;
  /** 初始默认值（仅在无持久化值时使用） */
  defaultValue: CachedValue;
  /** 序列化函数，默认 JSON.stringify */
  serialize?: (value: CachedValue) => string;
  /** 反序列化函数，默认 JSON.parse */
  deserialize?: (raw: string) => CachedValue;
}

export function useCachedState({
  key,
  defaultValue,
  serialize = JSON.stringify,
  deserialize = JSON.parse,
}: UseCachedStateOptions) {
  // 惰性初始化：首次渲染时尝试从 localStorage 读取，失败则回退默认值
  const [value, setValue] = useState<CachedValue>(() => {
    try {
      const raw = localStorage.getItem(key);
      return raw === null ? defaultValue : deserialize(raw);
    } catch {
      return defaultValue;
    }
  });

  // 状态变化即写回 localStorage，保证持久化与内存状态一致
  useEffect(() => {
    try {
      localStorage.setItem(key, serialize(value));
    } catch {
      // 写入失败（如配额超限、隐私模式）时静默忽略，不影响内存态使用
    }
  }, [key, value, serialize]);

  // 暴露一个重置入口，清空内存态与持久化值
  const reset = useCallback(() => {
    try {
      localStorage.removeItem(key);
    } catch {
      // 忽略移除失败
    }
    setValue(defaultValue);
  }, [key, defaultValue]);

  return [value, setValue, reset] as const;
}
