/**
 * 通用缓存状态 Hook（L2 + L3 缓存）
 *
 * 结合 L2（PageStateStore 内存缓存）和 L3（sessionStorage/localStorage 持久化）
 * - L2: 组件卸载时状态保留在 PageStateStore 中，切换路由不丢失
 * - L3: 同时持久化到浏览器存储，刷新页面后恢复
 *
 * 支持嵌套键名，如 'kline.stockCode'、'sector.activeTab'
 *
 * 与 usePreference 的区别：
 * - useCachedState: 使用 PageStateStore（L2）+ sessionStorage/localStorage（L3），适合复杂页面状态
 * - usePreference: 仅使用 localStorage（L4），适合简单偏好设置
 */

import { useCallback } from 'react';
import { usePageState, type PageStateStore } from '../stores/PageStateStore';
import { getStorageItem, setStorageItem } from '../utils/storage';

/** 存储类型：session（会话级）或 local（永久） */
type StorageType = 'session' | 'local';

/** useCachedState 配置选项 */
interface UseCachedStateOptions<T> {
  /** 存储类型：session（会话级，关闭标签页清除）或 local（永久保存） */
  storage?: StorageType;
  /** 自定义序列化函数（默认 JSON.stringify） */
  serialize?: (value: T) => string;
  /** 自定义反序列化函数（默认 JSON.parse） */
  deserialize?: (raw: string) => T;
}

/**
 * 从嵌套对象中按路径获取值
 *
 * @param obj - 源对象
 * @param path - 路径数组，如 ['stockCode'] 或 ['filters', 'market']
 * @returns 路径对应的值，不存在返回 undefined
 *
 * @example
 * getNestedValue({ kline: { stockCode: '603019' } }, ['kline', 'stockCode'])
 * // => '603019'
 */
function getNestedValue(obj: Record<string, unknown>, path: string[]): unknown {
  let current: unknown = obj;
  for (const key of path) {
    if (current && typeof current === 'object' && key in (current as Record<string, unknown>)) {
      current = (current as Record<string, unknown>)[key];
    } else {
      return undefined;
    }
  }
  return current;
}

/**
 * 在嵌套对象中按路径设置值（不可变更新）
 *
 * @param obj - 源对象
 * @param path - 路径数组
 * @param value - 要设置的值
 * @returns 新对象（原对象不被修改）
 *
 * @example
 * setNestedValue({ kline: { stockCode: '603019' } }, ['kline', 'period'], 'daily')
 * // => { kline: { stockCode: '603019', period: 'daily' } }
 */
function setNestedValue(obj: Record<string, unknown>, path: string[], value: unknown): Record<string, unknown> {
  if (path.length === 0) return obj;

  const result = { ...obj };
  let current: Record<string, unknown> = result;

  // 逐层创建新对象，确保不可变性
  for (let i = 0; i < path.length - 1; i++) {
    const key = path[i];
    const next = current[key];
    current[key] = next && typeof next === 'object' ? { ...(next as Record<string, unknown>) } : {};
    current = current[key] as Record<string, unknown>;
  }

  // 设置最终值
  current[path[path.length - 1]] = value;
  return result;
}

/**
 * 使用缓存状态
 *
 * 数据流向：
 * 1. 初始化时：PageStateStore → sessionStorage/localStorage → defaultValue
 * 2. 更新时：同时更新 PageStateStore 和 sessionStorage/localStorage
 *
 * @param key - 缓存键名（支持嵌套路径，如 'kline.stockCode'）
 * @param defaultValue - 默认值
 * @param options - 配置选项
 * @returns [当前值, 更新函数]
 *
 * @example
 * ```typescript
 * // K 线页面：股票代码（sessionStorage 持久化）
 * const [stockCode, setStockCode] = useCachedState('kline.stockCode', null, { storage: 'session' });
 *
 * // 板块分析：活跃 Tab（localStorage 永久保存）
 * const [activeTab, setActiveTab] = useCachedState('sector.activeTab', 'concept', { storage: 'local' });
 *
 * // 仅内存缓存（不持久化）
 * const [tempData, setTempData] = useCachedState('kline.tempData', null);
 * ```
 */
export function useCachedState<T>(
  key: string,
  defaultValue: T,
  options: UseCachedStateOptions<T> = {}
): [T, (value: T | ((prev: T) => T)) => void] {
  const { storage, serialize = JSON.stringify, deserialize = JSON.parse } = options;
  const { state, setState: setGlobalState } = usePageState();

  // 解析嵌套键名：'kline.stockCode' => ['kline', 'stockCode']
  const path = key.split('.');
  const moduleKey = path[0] as keyof PageStateStore;

  // 从 PageStateStore 读取当前值（L2 内存缓存）
  let currentValue: T = defaultValue;
  try {
    const moduleState = state[moduleKey] as unknown as Record<string, unknown>;
    const nested = path.length > 1 ? getNestedValue(moduleState, path.slice(1)) : moduleState;
    // null/undefined 视为无值，使用默认值
    if (nested !== undefined && nested !== null) {
      currentValue = nested as T;
    }
  } catch {
    // 读取失败时使用默认值
  }

  // 如果 PageStateStore 中没有有效值，尝试从浏览器存储恢复（L3 持久化缓存）
  if (currentValue === defaultValue && storage) {
    try {
      const stored = getStorageItem<string>(key, storage);
      if (stored !== null) {
        currentValue = deserialize(stored);
      }
    } catch {
      // 恢复失败时使用默认值
    }
  }

  // 更新函数：同时更新 PageStateStore 和浏览器存储
  const setValue = useCallback(
    (value: T | ((prev: T) => T)) => {
      // 计算新值
      const newValue = typeof value === 'function'
        ? (value as (prev: T) => T)(currentValue)
        : value;

      // 更新 PageStateStore（L2 内存缓存，不可变更新）
      if (path.length === 1) {
        // 简单键名：直接更新模块
        setGlobalState(moduleKey, newValue as any);
      } else {
        // 嵌套键名：深度更新模块内的字段
        const moduleState = state[moduleKey] as unknown as Record<string, unknown>;
        const updated = setNestedValue(moduleState, path.slice(1), newValue);
        setGlobalState(moduleKey, updated as any);
      }

      // 持久化到浏览器存储（L3）
      if (storage) {
        try {
          setStorageItem(key, serialize(newValue), storage);
        } catch {
          // 存储失败时静默处理（如配额超限）
        }
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [key, path, moduleKey, currentValue, state, setGlobalState, storage, serialize]
  );

  return [currentValue, setValue];
}
