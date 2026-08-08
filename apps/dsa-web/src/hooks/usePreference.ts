/**
 * 用户偏好 Hook（L4 - localStorage 永久缓存）
 *
 * 用于存储用户偏好设置，如默认周期、默认排序、主题等
 * 数据永久保存在 localStorage 中，除非用户手动清除
 *
 * 与 useCachedState 的区别：
 * - usePreference: 仅使用 localStorage，适合简单偏好设置，无内存缓存层
 * - useCachedState: 使用 PageStateStore + sessionStorage/localStorage，适合复杂页面状态
 */

import { useCallback, useState } from 'react';
import { getStorageItem, setStorageItem } from '../utils/storage';

/**
 * 使用用户偏好
 *
 * @param key - 偏好键名（会自动添加 dsa-pref- 前缀）
 * @param defaultValue - 默认值
 * @returns [当前值, 更新函数]
 *
 * @example
 * ```typescript
 * // K 线默认周期
 * const [defaultPeriod, setDefaultPeriod] = usePreference<KLinePeriod>('kline-default-period', 'daily');
 *
 * // 侧边栏折叠状态
 * const [sidebarCollapsed, setSidebarCollapsed] = usePreference('sidebar-collapsed', false);
 *
 * // 回测参数
 * const [evalDays, setEvalDays] = usePreference<string>('backtest-eval-days', '');
 * ```
 */
export function usePreference<T>(
  key: string,
  defaultValue: T
): [T, (value: T | ((prev: T) => T)) => void] {
  // 使用 useState 跟踪当前值，确保 setValue 后能触发重新渲染
  const [currentValue, setCurrentValue] = useState<T>(() => {
    try {
      const stored = getStorageItem<T>(key, 'local');
      if (stored !== null) {
        return stored;
      }
    } catch {
      // 读取失败时使用默认值
    }
    return defaultValue;
  });

  // 更新函数：同时更新 localStorage 和组件状态
  const setValue = useCallback(
    (value: T | ((prev: T) => T)) => {
      setCurrentValue((prev) => {
        const newValue = typeof value === 'function'
          ? (value as (prev: T) => T)(prev)
          : value;

        try {
          setStorageItem(key, newValue, 'local');
        } catch {
          // 存储失败时静默处理（如配额超限）
        }

        return newValue;
      });
    },
    [key]
  );

  return [currentValue, setValue];
}
