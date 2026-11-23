/**
 * 动态路由状态：以 MENU_MANIFEST 为唯一真源，登录后构建并持久化全量路由树，
 * 刷新时直接从 localStorage 还原。清单指纹变更即丢弃旧缓存，避免用过期的页面路径注册路由。
 * 登录页与 404 兜底由 appRouter 静态声明，不进入本 Store。
 */
import { getStorageItem, setStorageItem } from '@utils/storage';
import { create } from 'zustand';
import type { AsyncRouteNode } from '../types/router';
import { MENU_MANIFEST, MENU_MANIFEST_FINGERPRINT } from '../router/manifest';
import type { NavMenuNode } from '../types/moduleMenu';

/** 本地持久化动态路由树的键；存储即路由数据源，缺失视为未登录 */
const ASYNC_ROUTER_STORAGE_KEY = 'router.asyncRouteData';

/** 持久化 blob：路由树 + 产出时的清单指纹，用于识别真源变更 */
interface StoredAsyncRouterBlob {
  fingerprint: string;
  routes: AsyncRouteNode[];
}

interface RouterState {
  /** 动态路由树；刷新时从 localStorage 还原，未登录或清单变更时为空数组 */
  asyncRouteData: AsyncRouteNode[];
  /** 从 MENU_MANIFEST 重建全量路由树并持久化，同时标记业务路由需重新注入 */
  buildAsyncRouterData: () => void;
  /** 业务路由是否需要注入受保护布局：true=尚未注入，false=已注入；避免每次导航重复 patchRoutes */
  addRouteFlag: boolean;
}

/**
 * 菜单节点 → 动态路由节点：只搬运路由注册需要的字段，缺失路径回退为空字符串。
 * 子节点递归转换后一并挂载；空子节点不挂 children。
 */
const toAsyncRouteNode = (
  node: NavMenuNode,
  children?: AsyncRouteNode[],
): AsyncRouteNode => ({
  routerKey: node.menuCode,
  routerName: node.menuName,
  routerPath: node.menuRoutePath ?? '',
  routerPagePath: node.menuPagePath ?? '',
  routerType: 'page',
  auth: node.auth,
  routerDescription: node.menuDescription,
  children: children?.length ? children : undefined,
});

/**
 * 递归构建动态路由树：按 menuSort 升序，仅保留启用的 page 节点；
 * 分组等非页面节点只透传子树，不保留壳。
 */
const buildAsyncRouteTree = (nodes: NavMenuNode[]): AsyncRouteNode[] =>
  [...nodes].sort((a, b) => a.menuSort - b.menuSort).flatMap((node) => {
    if (node.menuStatus === 0) return [];
    const children = node.children?.length ? buildAsyncRouteTree(node.children) : undefined;
    if (node.menuType !== 'page' || !node.menuRoutePath) {
      return children ?? [];
    }
    return [toAsyncRouteNode(node, children)];
  });

/**
 * 读取本地持久化的路由树：只接受指纹一致、形态合法的 blob，其余一律视为未登录或已过期。
 * 清单变更后旧页面路径可能查不到模块（resolvePageImporter 失败），因此整块丢弃并等待重新登录构建。
 */
const readStoredAsyncRouterData = (): AsyncRouteNode[] => {
  const stored = getStorageItem<StoredAsyncRouterBlob>(ASYNC_ROUTER_STORAGE_KEY, 'local');
  if (!stored || typeof stored !== 'object' || stored.fingerprint !== MENU_MANIFEST_FINGERPRINT
    || !Array.isArray(stored.routes)) {
    return [];
  }
  // routerPagePath 允许为空（redirect 节点无页面），只校验字段类型。
  return stored.routes.every((n) => n && typeof n.routerKey === 'string' && typeof n.routerPagePath === 'string')
    ? stored.routes
    : [];
};

// store 初始化即从 localStorage 还原，刷新后无需重建；未登录为空数组。
const initialAsyncRouterData = readStoredAsyncRouterData();

/** 统一出口：写入持久化 blob 并同步 state。 */
const applyAsyncRouterData = (
  set: (partial: Partial<RouterState>) => void,
  asyncRouteData: AsyncRouteNode[],
): void => {
  const storedBlob: StoredAsyncRouterBlob = {
    fingerprint: MENU_MANIFEST_FINGERPRINT,
    routes: asyncRouteData,
  };
  setStorageItem(ASYNC_ROUTER_STORAGE_KEY, storedBlob, 'local');
  set({ asyncRouteData });
};

export const useRouterStore = create<RouterState>((set) => ({
  asyncRouteData: initialAsyncRouterData,
  // 本会话尚未注入业务路由，首次 registerAsyncRoutes 时注入
  addRouteFlag: true,

  buildAsyncRouterData: () => {
    const asyncRouteData = buildAsyncRouteTree(
      MENU_MANIFEST,
    );
    applyAsyncRouterData(set, asyncRouteData);
    // 路由数据已重建，必须重新注入，不能沿用上次的「已注入」标记
    set({ addRouteFlag: true });
  },

  // 业务路由注册由 routeRegistration 消费本 Store，避免反向依赖 appRouter
}));
