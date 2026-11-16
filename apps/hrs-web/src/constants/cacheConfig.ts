/**
 * @file cacheConfig.ts
 * @description 前端请求缓存策略配置：集中定义各 API 的缓存 TTL、缓存键规则与存储键前缀。
 * 由 utils/apiCache.ts（请求缓存层）与 utils/storage.ts（本地存储层）读取。约定 TTL 单位为秒，0 表示不缓存。
 * 策略取舍：实时行情与板块概览允许短时缓存减轻上游压力；用户私有数据、鉴权状态、流式响应
 * 及依赖轮询的快讯/日历接口必须实时，避免命中旧数据；回测、信号等计算结果变化不频繁，可长缓存。
 * @author Lensgcx (GaoCangxiong)
 */

/**
 * 各 API 路径的缓存 TTL（秒），0 表示不缓存。
 * 键名须与 axios 实际请求的相对路径一致（含 /api/v1 前缀），否则前缀匹配失配会回落到默认 TTL，导致缓存策略错乱。
 */
export const CACHE_TTL_MAP: Record<string, number> = {
  // 实时行情与搜索
  '/api/v1/kline/': 30,
  '/api/v1/kline/search': 300,       // 搜索词变化不频繁

  // 板块数据：概览类短缓存，规模类 5 分钟
  '/api/v1/sector/market-overview': 30,
  '/api/v1/sector/concept-scale': 300,
  '/api/v1/sector/etf-scale': 300,
  '/api/v1/sector/indices': 30,
  '/api/v1/sector/market-cards': 0,  // 页面 30 秒轮询，缓存会把轮询短路成旧数据

  // 用户私有数据：不缓存，保证一致性
  '/api/v1/portfolio': 0,
  '/api/v1/alerts': 0,
  '/api/v1/recent-search/': 0,       // 清空后需立即反映，不能命中旧列表

  // 依赖轮询或流式响应：不缓存，否则列表长时间不更新
  '/api/v1/intelligence/live-news': 0,
  '/api/v1/intelligence/live-calendar': 0,
  '/api/v1/auth': 0,                 // 登录/登出/改密状态即时生效
  '/api/v1/agent/chat': 0,           // 流式响应

  // 计算结果：变化不频繁，可长缓存
  '/api/v1/backtest': 600,
  '/api/v1/decision-signals': 300,
  '/api/v1/screening': 60,
  '/api/v1/usage': 60,
};

/** 未匹配到规则时使用的默认 TTL（秒） */
export const DEFAULT_CACHE_TTL = 60;

/** L1 内存缓存最大条目数，超过后按 LRU 淘汰 */
export const MAX_CACHE_ENTRIES = 200;

/** localStorage 键名前缀，用于用户偏好（长期保存） */
export const LOCAL_STORAGE_PREFIX = 'hrs-pref-';

/** sessionStorage 键名前缀，用于页面状态（会话级） */
export const SESSION_STORAGE_PREFIX = 'hrs-state-';

/**
 * 按 URL 取接口的缓存 TTL。
 * 匹配顺序：先精确匹配，再按路径前缀匹配，均未命中则返回默认 TTL。
 * @param url 请求 URL，空值时返回 0（不缓存）
 * @returns 缓存 TTL（秒），0 表示不缓存
 */
export function getCacheTTL(url: string | undefined): number {
  if (!url) return 0;

  // 精确匹配优先
  if (CACHE_TTL_MAP[url] !== undefined) {
    return CACHE_TTL_MAP[url];
  }

  // 前缀匹配
  for (const [prefix, ttl] of Object.entries(CACHE_TTL_MAP)) {
    if (url.startsWith(prefix)) {
      return ttl;
    }
  }

  return DEFAULT_CACHE_TTL;
}

/**
 * 由请求要素构建缓存键，确保相同请求生成相同键。
 * 格式为 METHOD:URL:PARAMS，其中 PARAMS 缺省时省略该段。
 * @param method HTTP 方法（大小写不敏感，统一转大写）
 * @param url 请求 URL
 * @param params 请求参数，序列化为 JSON；不传时忽略
 * @returns 缓存键，如 GET:/kline/603019:{"period":"daily"}
 */
export function buildCacheKey(method: string, url: string, params?: Record<string, unknown>): string {
  const paramStr = params ? JSON.stringify(params) : '';
  return `${method.toUpperCase()}:${url}${paramStr ? ':' + paramStr : ''}`;
}
