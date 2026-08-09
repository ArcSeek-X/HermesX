/**
 * 存储工具（浏览器存储层）
 *
 * 作用：封装 localStorage 与 sessionStorage，提供带前缀、带 JSON 序列化、
 * 且在私有模式/配额超限等异常下安全降级（不抛错）的读写接口。
 * 同时提供按 HRS 前缀批量清理的能力，供登出或重置场景使用。
 */

/**
 * 存储工具（L3 - 浏览器存储层）
 *
 * 封装 localStorage 和 sessionStorage，提供安全的读写接口
 * 处理私有模式下存储不可用的情况
 *
 * 存储层级：
 * - localStorage: 永久存储，除非用户手动清除（用于用户偏好）
 * - sessionStorage: 会话级存储，关闭标签页后清除（用于临时状态）
 *
 * 键名前缀：
 * - localStorage: 'hrs-pref-'（用户偏好）
 * - sessionStorage: 'hrs-state-'（页面状态）
 *
 * 使用场景：
 * - usePreference: 使用 localStorage 存储用户偏好
 * - useCachedState: 使用 sessionStorage/localStorage 持久化页面状态
 * - PageStateStore: 使用 sessionStorage 同步全局状态
 */

import { LOCAL_STORAGE_PREFIX, SESSION_STORAGE_PREFIX } from '../constants/cacheConfig';

/**
 * 检查存储是否可用
 *
 * 某些浏览器（如 Safari 私有模式）可能禁用存储
 * 通过测试读写来判断是否可用
 */
function isStorageAvailable(storage: Storage): boolean {
  try {
    const key = '__test__';
    storage.setItem(key, 'test');
    storage.removeItem(key);
    return true;
  } catch {
    return false;
  }
}

/** localStorage 是否可用 */
export const isLocalStorageAvailable = typeof window !== 'undefined'
  ? isStorageAvailable(window.localStorage)
  : false;

/** sessionStorage 是否可用 */
export const isSessionStorageAvailable = typeof window !== 'undefined'
  ? isStorageAvailable(window.sessionStorage)
  : false;

/**
 * 安全地获取存储项
 *
 * @param key - 键名（不含前缀，会自动添加）
 * @param storageType - 存储类型：'local'（localStorage）或 'session'（sessionStorage）
 * @returns 解析后的值，失败返回 null
 *
 * @example
 * ```typescript
 * const value = getStorageItem<string>('user-preference', 'local');
 * // 实际读取的键名：'hrs-pref-user-preference'
 * ```
 */
export function getStorageItem<T = unknown>(
  key: string,
  storageType: 'local' | 'session' = 'local'
): T | null {
  try {
    const storage = storageType === 'local' ? window.localStorage : window.sessionStorage;
    const prefix = storageType === 'local' ? LOCAL_STORAGE_PREFIX : SESSION_STORAGE_PREFIX;
    const fullKey = `${prefix}${key}`;
    const raw = storage.getItem(fullKey);
    if (raw === null) return null;
    return JSON.parse(raw) as T;
  } catch {
    // 解析失败或存储不可用时返回 null
    return null;
  }
}

/**
 * 安全地设置存储项
 *
 * @param key - 键名（不含前缀，会自动添加）
 * @param value - 要存储的值（会自动 JSON 序列化）
 * @param storageType - 存储类型：'local'（localStorage）或 'session'（sessionStorage）
 *
 * @example
 * ```typescript
 * setStorageItem('user-preference', { theme: 'dark' }, 'local');
 * // 实际存储的键名：'hrs-pref-user-preference'
 * ```
 */
export function setStorageItem<T = unknown>(
  key: string,
  value: T,
  storageType: 'local' | 'session' = 'local'
): void {
  try {
    const storage = storageType === 'local' ? window.localStorage : window.sessionStorage;
    const prefix = storageType === 'local' ? LOCAL_STORAGE_PREFIX : SESSION_STORAGE_PREFIX;
    const fullKey = `${prefix}${key}`;
    storage.setItem(fullKey, JSON.stringify(value));
  } catch {
    // 存储失败时静默处理（如配额超限、私有模式禁用）
    console.warn(`Failed to set storage item: ${key}`, value);
  }
}

/**
 * 安全地移除存储项
 *
 * @param key - 键名（不含前缀，会自动添加）
 * @param storageType - 存储类型：'local'（localStorage）或 'session'（sessionStorage）
 *
 * @example
 * ```typescript
 * removeStorageItem('user-preference', 'local');
 * ```
 */
export function removeStorageItem(
  key: string,
  storageType: 'local' | 'session' = 'local'
): void {
  try {
    const storage = storageType === 'local' ? window.localStorage : window.sessionStorage;
    const prefix = storageType === 'local' ? LOCAL_STORAGE_PREFIX : SESSION_STORAGE_PREFIX;
    const fullKey = `${prefix}${key}`;
    storage.removeItem(fullKey);
  } catch {
    // 静默处理
  }
}

/**
 * 清除所有 HRS 相关的存储项
 *
 * 遍历存储，删除所有以 HRS 前缀开头的键
 *
 * @param storageType - 存储类型：'local'（仅 localStorage）、'session'（仅 sessionStorage）或 'all'（全部）
 *
 * @example
 * ```typescript
 * // 清除所有 HRS 数据（登出时调用）
 * clearHRSStorage('all');
 *
 * // 仅清除用户偏好
 * clearHRSStorage('local');
 * ```
 */
export function clearHRSStorage(storageType: 'local' | 'session' | 'all' = 'all'): void {
  try {
    const clearStorage = (storage: Storage, prefix: string) => {
      const keysToRemove: string[] = [];
      // 遍历所有键，找出以 HRS 前缀开头的
      for (let i = 0; i < storage.length; i++) {
        const key = storage.key(i);
        if (key && key.startsWith(prefix)) {
          keysToRemove.push(key);
        }
      }
      // 批量删除
      keysToRemove.forEach(key => storage.removeItem(key));
    };

    if (storageType === 'local' || storageType === 'all') {
      clearStorage(window.localStorage, LOCAL_STORAGE_PREFIX);
    }
    if (storageType === 'session' || storageType === 'all') {
      clearStorage(window.sessionStorage, SESSION_STORAGE_PREFIX);
    }
  } catch {
    // 静默处理
  }
}
