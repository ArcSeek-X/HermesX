/**
 * usePreference —— 用户偏好 Hook（L4：localStorage 永久缓存层）
 *
 * 用于存储用户偏好设置，如默认周期、默认排序、主题等。
 * 数据永久保存在 localStorage 中，除非用户手动清除。
 *
 * 与 useCachedState 的区别：
 * - usePreference：仅使用 localStorage，适合简单偏好设置，无额外内存缓存层（直接基于 useState 驱动渲染）。
 * - useCachedState：使用 PageStateStore + sessionStorage/localStorage，适合复杂页面状态共享。
 */

import { useCallback, useState } from 'react';
import { getStorageItem, setStorageItem } from '../utils/storage';

/**
 * 读取并使用某个用户偏好。
 *
 * @param key - 偏好键名（内部会自动添加 `dsa-pref-` 前缀，调用方无需关心）
 * @param defaultValue - 默认值（localStorage 中无该值时使用）
 * @returns [当前值, 更新函数]；更新函数支持直接传值或函数式更新（同 useState 语义）
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
  // 用 useState 跟踪当前值，setValue 后触发重渲染；初始值惰性从 localStorage 读取
  const [currentValue, setCurrentValue] = useState<T>(() => {
    try {
      const stored = getStorageItem<T>(key, 'local');
      if (stored !== null) {
        return stored;
      }
    } catch {
      // 读取失败时回退到默认值
    }
    return defaultValue;
  });

  // 更新函数：同时写入 localStorage 与组件内存态；支持函数式更新
  const setValue = useCallback(
    (value: T | ((prev: T) => T)) => {
      setCurrentValue((prev) => {
        const newValue = typeof value === 'function'
          ? (value as (prev: T) => T)(prev)
          : value;

        try {
          setStorageItem(key, newValue, 'local');
        } catch {
          // 存储失败时静默处理（如配额超限、隐私模式），不影响内存态
        }

        return newValue;
      });
    },
    [key]
  );

  return [currentValue, setValue];
}
