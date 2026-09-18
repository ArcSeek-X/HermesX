import { create } from 'zustand';
import {
  MENU_MANIFEST,
  isPageLikeRouteNode,
  type AppRouteNode,
} from '../router/manifest';
import type { AsyncRouteNode } from '../types/router';
import { getStorageItem, setStorageItem } from '../utils/storage';
import { EXCEPTION_ROUTE } from '../router/Whitelist';

const ASYNC_ROUTER_STORAGE_KEY = 'router.asyncRouterList';

interface RouterState {
  /** 动态路由树，需持久化 */
  asyncRouterList: AsyncRouteNode[];
  /** 直接覆盖动态路由树并落盘 */
  setAsyncRouterList: (routes: AsyncRouteNode[]) => void;
  /** 从真源构建动态路由树并落盘 */
  buildAsyncRouterList: () => void;
  /** 刷新动态路由树并落盘 */
  refreshAsyncRouterList: () => void;
  /** 恢复基于当前真源的默认动态路由树 */
  resetAsyncRouterList: () => void;
}

const toAsyncRouteNode = (
  node: AppRouteNode & { menuType: 'page' | 'redirect' | 'fallback' },
  children?: AsyncRouteNode[],
): AsyncRouteNode => ({
  menuId: node.menuId,
  menuName: node.menuName,
  menuDescription: node.menuDescription,
  path: node.routePath ?? '',
  auth: node.auth,
  moduleId: node.moduleId,
  menuType: node.menuType,
  redirect: node.redirect,
  loader: node.loader,
  children: children?.length ? children : undefined,
});

const buildAsyncRouteTree = (nodes: AppRouteNode[]): AsyncRouteNode[] =>
  nodes.flatMap((node) => {
    const children = node.children?.length ? buildAsyncRouteTree(node.children) : undefined;

    if (!isPageLikeRouteNode(node) || !node.routePath) {
      return children ?? [];
    }

    return [toAsyncRouteNode(node, children)];
  });

const buildAsyncRouterListFromSource = (): AsyncRouteNode[] =>
  buildAsyncRouteTree([...MENU_MANIFEST, ...EXCEPTION_ROUTE]);

const mergeAsyncRoutesWithRuntime = (
  persisted: AsyncRouteNode[],
  runtime: AsyncRouteNode[],
): AsyncRouteNode[] =>
  persisted.map((item) => {
    const runtimeNode = runtime.find((candidate) => candidate.menuId === item.menuId && candidate.path === item.path);
    const mergedChildren = item.children?.length
      ? mergeAsyncRoutesWithRuntime(item.children, runtimeNode?.children ?? [])
      : undefined;

    return {
      ...runtimeNode,
      ...item,
      children: mergedChildren ?? item.children,
    };
  });

const isAsyncRouteNode = (value: unknown): value is AsyncRouteNode =>
  typeof value === 'object' && value !== null && 'menuId' in value && 'path' in value && 'menuType' in value;

const normalizeStoredAsyncRouterList = (value: unknown): AsyncRouteNode[] | null => {
  if (!Array.isArray(value)) {
    return null;
  }

  const normalizeNode = (item: unknown): AsyncRouteNode | null => {
    if (!isAsyncRouteNode(item)) {
      return null;
    }

    const node = item as AsyncRouteNode;
    const children = Array.isArray(node.children)
      ? node.children.map(normalizeNode).filter((child): child is AsyncRouteNode => child !== null)
      : undefined;

    return {
      menuId: node.menuId,
      menuName: node.menuName,
      menuDescription: node.menuDescription,
      path: node.path,
      auth: node.auth,
      moduleId: node.moduleId,
      menuType: node.menuType,
      redirect: node.redirect,
      loader: node.loader,
      children: children?.length ? children : undefined,
    };
  };

  return value.map(normalizeNode).filter((node): node is AsyncRouteNode => node !== null);
};

const readStoredAsyncRouterList = (): AsyncRouteNode[] =>
{
  const runtimeAsyncRouterList = buildAsyncRouterListFromSource();
  const storedAsyncRouterList = normalizeStoredAsyncRouterList(
    getStorageItem(ASYNC_ROUTER_STORAGE_KEY, 'local'),
  );

  return storedAsyncRouterList
    ? mergeAsyncRoutesWithRuntime(storedAsyncRouterList, runtimeAsyncRouterList)
    : runtimeAsyncRouterList;
};

const persistAsyncRouterList = (routes: AsyncRouteNode[]): void => {
  setStorageItem(ASYNC_ROUTER_STORAGE_KEY, routes, 'local');
};

const initialAsyncRouterList = readStoredAsyncRouterList();

export const useRouterStore = create<RouterState>((set, get) => ({
  asyncRouterList: initialAsyncRouterList,

  setAsyncRouterList: (routes) => {
    persistAsyncRouterList(routes);
    set({ asyncRouterList: routes });
  },

  buildAsyncRouterList: () => {
    get().setAsyncRouterList(buildAsyncRouterListFromSource());
  },

  refreshAsyncRouterList: () => {
    get().buildAsyncRouterList();
  },

  resetAsyncRouterList: () => {
    get().setAsyncRouterList(buildAsyncRouterListFromSource());
  },
}));
