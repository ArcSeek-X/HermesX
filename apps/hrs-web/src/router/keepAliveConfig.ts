/**
 * @file keepAliveConfig.ts
 * @description 路由缓存（Keep-Alive）配置，仓库侧唯一真源。字段与底层库 keepalive-for-react
 *   的 KeepAliveRouteOutlet 入参对齐，策略即其 props 的声明式映射。默认除 exclude 外全部
 *   缓存页面实例，切回路由时状态 / 数据原样恢复。设计基准见 ADR-002。
 */

/** 单条名单规则：精确 pathname，或以 `*` 结尾的前缀规则（如 '/docs/*'，含自身与全部子路径） */
type KeepAliveRule = string;

interface KeepAliveConfig {
  /** 黑名单：命中的 pathname 不缓存（离开即销毁），优先级高于 include */
  exclude: KeepAliveRule[];
  /** 白名单：非空时仅缓存命中项；空数组 = 不启用（除 exclude 外都缓存） */
  include: KeepAliveRule[];
  /** 缓存闲置过期时间（秒）：0 = 不过期，仅受 maxCacheSize 约束 */
  maxAliveTime: number;
  /** 缓存页数量硬上限（LRU）：超出淘汰最久未用页，内存护栏 */
  maxCacheSize: number;
}

/**
 * 默认配置：黑名单生效、白名单未启用——除清单外全部缓存。
 * exclude：登录页 /login（鉴权页，结构上本就不流经缓存出口，双保险）、流式对话
 * /choose/chat（实例缓存语义不安全）、组件调试 /docs/*、调试页 /codeTest、兜底页 /404。
 * include 留空即走黑名单语义；改为白名单时填入目标 pathname 规则即可。
 */
export const KEEP_ALIVE_CONFIG: KeepAliveConfig = {
  exclude: ['/login', '/choose/chat', '/docs/*', '/codeTest', '/404'],
  include: [],
  maxAliveTime: 0,
  maxCacheSize: 8,
};
