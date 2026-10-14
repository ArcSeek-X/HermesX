/**
 * @file KeepAliveOutlet.tsx
 * @description 路由缓存出口：基于 keepalive-for-react(-router)，使受保护布局下的页面在
 *   路由切换后保留实例，切回时状态 / 数据原样恢复。设计基准见 ADR-002。
 *
 * 关键点：
 * - 缓存键 = pathname + search + hash（query / hash 变化即重挂载）；
 * - exclude / include 规则引用须保持稳定（库按引用做 memo 比较），故以 useMemo 固化；
 * - 库要求不能包裹 <React.StrictMode />（开发模式缓存不可预期），见 main.tsx；
 * - 滚动偏移以 location 为键，在切页前后保存 / 恢复（layout effect，先于 paint）。
 */
import type React from 'react';
import { useEffect, useLayoutEffect, useMemo, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import KeepAliveRouteOutlet from 'keepalive-for-react-router';
import { RouteBoundary } from '../../pages/ErrorPage/RouteBoundary';
import { useScrollContainerRef } from '../../contexts/ScrollContainerContext';
import { KEEP_ALIVE_CONFIG } from '../../router/keepAliveConfig';

/** 转义 RegExp 元字符，保证 pathname 按字面匹配 */
const escapeRegExp = (value: string): string => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/**
 * 名单规则 → 库匹配规则：精确 pathname 原样透传；`*` 结尾的前缀规则转 RegExp
 * （'/docs/*' → /^\/docs(\/|$)/，命中自身与全部子路径，不误伤 /docsX）。
 * 私有不导出：组件文件混导出非组件会触发 react-refresh/only-export-components。
 */
const toMatchRules = (rules: string[]): Array<string | RegExp> =>
  rules.map((rule) => {
    if (!rule.endsWith('*')) {
      return rule;
    }
    const base = rule.slice(0, -1).replace(/\/$/, '');
    return new RegExp(`^${escapeRegExp(base)}(/|$)`);
  });

/** 缓存节点错误边界：复用统一路由边界，逐页隔离 */
const CacheErrorElement: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <RouteBoundary fullPage={false}>{children}</RouteBoundary>
);

/**
 * 滚动位置保存 / 恢复。应用唯一滚动容器是 Main 内的 main.hrs-page-container（经
 * ScrollContainerContext 下发）；库切页会重建缓存节点 DOM，但滚动容器不重建，故以 location
 * 为键记录偏移、切回时在 layout effect（paint 前）恢复，避免停留在上一页的滚动偏移上。
 */
const RouteScrollRestoration: React.FC = () => {
  const location = useLocation();
  // Context 引用被编译器视为不可变值，先同步进本地 ref 再读写其 DOM 属性，避免 immutability lint 误判
  const contextScrollContainerRef = useScrollContainerRef();
  const scrollContainerRef = useRef<HTMLElement | null>(null);
  useEffect(() => {
    scrollContainerRef.current = contextScrollContainerRef?.current ?? null;
  }, [contextScrollContainerRef]);

  const locationKey = `${location.pathname}${location.search}${location.hash}`;
  const currentLocationKeyRef = useRef(locationKey);
  const scrollOffsetByRouteRef = useRef(new Map<string, number>());

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) {
      return undefined;
    }
    const recordScroll = () => {
      scrollOffsetByRouteRef.current.set(currentLocationKeyRef.current, container.scrollTop);
    };
    container.addEventListener('scroll', recordScroll, { passive: true });
    return () => container.removeEventListener('scroll', recordScroll);
  }, []);

  useLayoutEffect(() => {
    const container = scrollContainerRef.current;
    const previousLocationKey = currentLocationKeyRef.current;
    currentLocationKeyRef.current = locationKey;
    if (!container) {
      return;
    }
    // 离开页兜底：滚动事件未及触发（如刷新后浏览器恢复滚动）时，以当前 scrollTop 保存；
    // 已记录过则信任监听值，避免被节点切换后的钳制值覆盖
    if (
      previousLocationKey !== locationKey
      && !scrollOffsetByRouteRef.current.has(previousLocationKey)
      && container.scrollTop > 0
    ) {
      scrollOffsetByRouteRef.current.set(previousLocationKey, container.scrollTop);
    }
    // 首屏（无任何记录）：不干预浏览器自身的滚动恢复
    if (scrollOffsetByRouteRef.current.size === 0) {
      return;
    }
    container.scrollTop = scrollOffsetByRouteRef.current.get(locationKey) ?? 0;
  }, [locationKey]);

  return null;
};

/**
 * 路由缓存出口，替换 Shell 内 `<RouteOutletBoundary />`。
 * 非缓存路由渲染路径与 `<Outlet />` 一致（exclude 命中页同样渲染，仅离开即销毁）。
 */
export const KeepAliveOutlet: React.FC = () => {
  const location = useLocation();

  // include 为空数组时不下发（传 undefined）：库判定为「include ? 命中 include : 未命中 exclude」，
  // 空数组在 JS 中为 truthy，原样传入会被当成「启用了白名单却谁都不匹配」导致全站不缓存。
  const matchProps = useMemo(() => {
    const exclude = toMatchRules(KEEP_ALIVE_CONFIG.exclude);
    const include =
      KEEP_ALIVE_CONFIG.include.length > 0 ? toMatchRules(KEEP_ALIVE_CONFIG.include) : undefined;
    return { exclude, include };
  }, []);

  return (
    <>
      <KeepAliveRouteOutlet
        activeCacheKey={`${location.pathname}${location.search}${location.hash}`}
        max={KEEP_ALIVE_CONFIG.maxCacheSize}
        maxAliveTime={KEEP_ALIVE_CONFIG.maxAliveTime}
        errorElement={CacheErrorElement}
        {...matchProps}
      />
      {/* 须在 KeepAliveRouteOutlet 之后渲染：其 layout effect 要晚于库重建缓存节点 DOM，
          否则恢复滚动偏移时新页内容尚未挂载、偏移会被钳制 */}
      <RouteScrollRestoration />
    </>
  );
};
