/**
 * API 客户端（axios 实例）
 *
 * 集成 L1 内存缓存：
 * - 请求拦截器：GET 请求自动检查缓存，命中则直接返回
 * - 响应拦截器：GET 请求自动写入缓存
 *
 * 缓存配置：
 * - TTL 由 cacheConfig.ts 中的 CACHE_TTL_MAP 定义
 * - 缓存键名格式：METHOD:URL:PARAMS
 * - 最大条目数：MAX_CACHE_ENTRIES（LRU 淘汰）
 *
 * 使用示例：
 * ```typescript
 * // 自动缓存（GET 请求）
 * const data = await apiClient.get('/kline/603019');
 *
 * // 手动清除缓存
 * clearApiCache('/kline/*');
 * clearAllApiCache();
 * ```
 */

import axios from 'axios';
import { API_BASE_URL } from '../utils/constants';
import { attachParsedApiError } from './error';
import apiCache from '../utils/apiCache';
import { buildCacheKey, getCacheTTL } from '../constants/cacheConfig';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * 请求拦截器：检查缓存
 *
 * 对于 GET 请求，如果缓存命中则直接返回缓存数据，跳过网络请求
 * 通过设置 config.adapter 短路请求
 */
apiClient.interceptors.request.use((config) => {
  if (config.method === 'get') {
    const cacheKey = buildCacheKey(config.method, config.url || '', config.params);
    const cached = apiCache.get(cacheKey);

    if (cached) {
      // 缓存命中，通过 adapter 短路请求
      config.adapter = () =>
        Promise.resolve({
          data: cached,
          status: 200,
          statusText: 'OK',
          headers: {},
          config,
        });
    }
  }
  return config;
});

/**
 * 响应拦截器：
 * 1. 写入 GET 请求缓存
 * 2. 处理 401 未授权（跳转登录页）
 */
apiClient.interceptors.response.use(
  (response) => {
    // 写入缓存（仅 GET 请求）
    if (response.config.method === 'get') {
      const url = response.config.url || '';
      const ttl = getCacheTTL(url);

      if (ttl > 0) {
        const cacheKey = buildCacheKey(
          response.config.method,
          url,
          response.config.params
        );
        apiCache.set(cacheKey, response.data, ttl);
      }
    }
    return response;
  },
  (error) => {
    // 处理 401 未授权
    if (error.response?.status === 401) {
      const path = window.location.pathname + window.location.search;
      if (!path.startsWith('/login')) {
        const redirect = encodeURIComponent(path);
        window.location.assign(`/login?redirect=${redirect}`);
      }
    }
    attachParsedApiError(error);
    return Promise.reject(error);
  }
);

/**
 * 手动清除指定 API 的缓存
 *
 * @param urlPattern - URL 模式（支持通配符 *）
 *
 * @example
 * clearApiCache('/kline/*')  // 清除所有 K 线相关缓存
 * clearApiCache('/sector/indices')  // 清除特定接口缓存
 */
export function clearApiCache(urlPattern: string): void {
  apiCache.invalidate(urlPattern);
}

/**
 * 清除所有 API 缓存
 *
 * 通常在用户登出或需要强制刷新所有数据时调用
 */
export function clearAllApiCache(): void {
  apiCache.clear();
}

export default apiClient;
