/**
 * 缓存配置文件
 *
 * 定义各 API 接口的缓存 TTL（秒）和缓存键名规则
 * TTL = 0 表示不缓存
 *
 * 缓存策略：
 * - 实时行情：30 秒（平衡数据新鲜度和性能）
 * - 板块数据：30-300 秒（根据数据变化频率）
 * - 用户私有数据：不缓存（保证数据一致性）
 * - AI 聊天：不缓存（流式响应）
 * - 回测/决策信号：300-600 秒（计算结果变化不频繁）
 *
 * 键名前缀：
 * - localStorage: 'hrs-pref-'（用户偏好，永久保存）
 * - sessionStorage: 'hrs-state-'（页面状态，会话级）
 */

/** 各 API 路径的缓存 TTL（秒） */
export const CACHE_TTL_MAP: Record<string, number> = {
  // 实时行情 — 30 秒
  '/kline/': 30,
  '/kline/search': 300,       // 股票搜索变化不频繁，5 分钟

  // 板块数据 — 30 秒（市场概览）/ 5 分钟（云图数据）
  '/sector/market-overview': 30,
  '/sector/concept-scale': 300,
  '/sector/etf-scale': 300,
  '/sector/indices': 30,

  // 用户私有数据 — 不缓存（保证数据一致性）
  '/portfolio': 0,
  '/alerts': 0,

  // AI 聊天 — 不缓存（流式响应）
  '/chat': 0,

  // 回测结果 — 10 分钟（计算结果变化不频繁）
  '/backtest': 600,

  // 决策信号 — 5 分钟
  '/decision-signals': 300,

  // 股票筛选 — 1 分钟
  '/screening': 60,

  // Token 用量 — 1 分钟
  '/usage': 60,
};

/** 默认 TTL（未匹配到规则时使用） */
export const DEFAULT_CACHE_TTL = 60;

/** L1 内存缓存最大条目数（LRU 淘汰） */
export const MAX_CACHE_ENTRIES = 200;

/** localStorage 键名前缀（用户偏好） */
export const LOCAL_STORAGE_PREFIX = 'hrs-pref-';

/** sessionStorage 键名前缀（页面状态） */
export const SESSION_STORAGE_PREFIX = 'hrs-state-';

/**
 * 根据 URL 路径获取缓存 TTL
 *
 * 匹配规则：
 * 1. 精确匹配优先（如 '/kline/search'）
 * 2. 前缀匹配（如 '/kline/' 匹配所有 K 线接口）
 * 3. 未匹配到则使用默认 TTL
 *
 * @param url - API 路径
 * @returns 缓存 TTL（秒），0 表示不缓存
 *
 * @example
 * getCacheTTL('/kline/603019')  // => 30
 * getCacheTTL('/kline/search')  // => 300
 * getCacheTTL('/portfolio/123') // => 0
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
 * 构建缓存键名
 *
 * 格式：METHOD:URL:PARAMS
 * 确保相同请求参数生成相同键名
 *
 * @param method - HTTP 方法（GET/POST 等）
 * @param url - API 路径
 * @param params - 请求参数
 * @returns 缓存键名
 *
 * @example
 * buildCacheKey('GET', '/kline/603019', { period: 'daily' })
 * // => 'GET:/kline/603019:{"period":"daily"}'
 */
export function buildCacheKey(method: string, url: string, params?: Record<string, unknown>): string {
  const paramStr = params ? JSON.stringify(params) : '';
  return `${method.toUpperCase()}:${url}${paramStr ? ':' + paramStr : ''}`;
}
