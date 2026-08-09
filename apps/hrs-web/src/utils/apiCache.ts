/**
 * API 响应缓存（L1 - 内存缓存）
 *
 * 使用 Map 存储 API 响应，带 TTL 过期机制
 * 超过最大条目数时使用 LRU 策略淘汰
 *
 * 缓存层级：L1（最快，但仅在当前会话有效）
 * - 命中时直接返回内存数据，无需网络请求
 * - 适合频繁访问但变化不频繁的数据
 *
 * 使用场景：
 * - GET 请求自动缓存（通过 axios 拦截器）
 * - 手动调用 apiCache.get/set 控制缓存
 * - 调用 apiCache.invalidate() 清除特定缓存
 *
 * 示例：
 * ```typescript
 * // 自动缓存（通过拦截器）
 * const data = await apiClient.get('/kline/603019');
 *
 * // 手动控制
 * apiCache.set('custom-key', data, 60); // 缓存 60 秒
 * const cached = apiCache.get('custom-key');
 * apiCache.invalidate('kline:*'); // 清除所有 K 线缓存
 * ```
 */

import { MAX_CACHE_ENTRIES } from '../constants/cacheConfig';

/** 缓存条目结构 */
interface CacheEntry {
  /** 缓存的数据 */
  data: unknown;
  /** 过期时间戳（毫秒） */
  expireAt: number;
  /** 创建时间戳（毫秒） */
  createdAt: number;
  /** 最后访问时间戳（毫秒，用于 LRU 淘汰） */
  lastAccessAt: number;
}

/**
 * API 缓存类
 *
 * 特性：
 * - 自动过期：超过 TTL 的条目自动失效
 * - LRU 淘汰：超过最大条目数时，淘汰最久未访问的条目
 * - 通配符清除：支持按模式批量清除缓存
 */
class ApiCache {
  /** 缓存存储 */
  private cache = new Map<string, CacheEntry>();

  /**
   * 获取缓存数据
   *
   * @param key - 缓存键名
   * @returns 缓存的数据，未命中或已过期返回 null
   *
   * 注意：访问时会更新 lastAccessAt，影响 LRU 淘汰顺序
   */
  get<T = unknown>(key: string): T | null {
    const entry = this.cache.get(key);

    if (!entry) {
      return null;
    }

    // 检查是否过期
    if (Date.now() > entry.expireAt) {
      this.cache.delete(key);
      return null;
    }

    // 更新最后访问时间（LRU）
    entry.lastAccessAt = Date.now();
    return entry.data as T;
  }

  /**
   * 设置缓存数据
   *
   * @param key - 缓存键名
   * @param data - 缓存的数据
   * @param ttlSeconds - 有效期（秒），0 表示不缓存
   *
   * 注意：如果超过最大条目数，会自动淘汰最久未访问的条目
   */
  set(key: string, data: unknown, ttlSeconds: number): void {
    // 如果超过最大条目数，淘汰最久未访问的条目
    if (this.cache.size >= MAX_CACHE_ENTRIES) {
      this.evictLRU();
    }

    const now = Date.now();
    this.cache.set(key, {
      data,
      expireAt: now + ttlSeconds * 1000,
      createdAt: now,
      lastAccessAt: now,
    });
  }

  /**
   * 清除指定模式的缓存
   *
   * @param pattern - 键名模式（支持通配符 *）
   *
   * @example
   * invalidate('kline:*')  // 清除所有 kline 相关缓存
   * invalidate('kline:info:603019')  // 清除特定股票信息缓存
   * invalidate('*')  // 清除所有缓存
   */
  invalidate(pattern: string): void {
    const regex = new RegExp('^' + pattern.replace(/\*/g, '.*') + '$');

    for (const key of this.cache.keys()) {
      if (regex.test(key)) {
        this.cache.delete(key);
      }
    }
  }

  /**
   * 清除所有缓存
   *
   * 通常在用户登出或需要强制刷新时调用
   */
  clear(): void {
    this.cache.clear();
  }

  /**
   * 获取缓存统计信息
   *
   * @returns 当前缓存大小和最大条目数
   *
   * 用于调试和监控缓存使用情况
   */
  getStats(): { size: number; maxEntries: number } {
    return {
      size: this.cache.size,
      maxEntries: MAX_CACHE_ENTRIES,
    };
  }

  /**
   * LRU 淘汰：删除最久未访问的条目
   *
   * 当缓存达到容量上限时自动调用
   * 时间复杂度：O(n)，需要遍历所有条目
   */
  private evictLRU(): void {
    let oldestKey: string | null = null;
    let oldestTime = Infinity;

    for (const [key, entry] of this.cache.entries()) {
      if (entry.lastAccessAt < oldestTime) {
        oldestTime = entry.lastAccessAt;
        oldestKey = key;
      }
    }

    if (oldestKey) {
      this.cache.delete(oldestKey);
    }
  }
}

// 导出单例（全局共享同一个缓存实例）
export const apiCache = new ApiCache();
export default apiCache;
