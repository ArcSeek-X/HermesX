/**
 * @file RouterStore.ts
 * @description 动态路由状态 Store（Zustand）。以路由清单 `MENU_MANIFEST` 为唯一真值源，
 *   在登录后构建全量动态路由树（asyncRouterData）并持久化；刷新浏览器时直接从持久化还原，
 *   无需重建。白名单路由（登录页、404 兜底等）不进入本 Store，由路由注册层在最终注册时合并。
 *
 * 持久化边界：
 * - asyncRouterData：动态路由树（含 children 的树状结构），需持久化到 localStorage；
 *   存储即唯一权威数据源，有则直接可用，缺失视为未登录（空数组）。
 *
 * 两个业务场景与 Store 入口的对应关系（登录功能尚未实现，以下入口供后续直接调用）：
 * - 场景一 首次登录：登录成功后调用 `buildAsyncRouterData()` ——
 *   遍历真源数据、按转换关系构建全量动态路由树并持久化。
 * - 场景二 刷新浏览器（已登录）：store 初始化时（模块加载）自动从 localStorage
 *   还原 asyncRouterData（见文件底部 `initial*` 初始化），无需手动调用；
 *   路由注册层直接消费 `asyncRouterData` 将其挂入路由表（"建立动态路由"）。
 *
 * 使用场景：被路由注册层经由 `useRouterStore` 读取 `asyncRouterData`，
 *   并叠加 Whitelist 中的白名单路由后注册为最终的动态路由表。
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-09-19
 */
import { create } from 'zustand';
import {
  MENU_MANIFEST,
  isPageLikeRouteNode,
  type AppRouteNode,
} from '../router/manifest';
import type { AsyncRouteNode } from '../types/router';
import { getStorageItem, setStorageItem } from '../utils/storage';

/** localStorage 中持久化「动态路由树（asyncRouterData）」的键；存储即路由数据源，有则直接可用 */
const ASYNC_ROUTER_STORAGE_KEY = 'router.asyncRouterData';

interface RouterState {
  /** 动态路由树（树状结构，含 children）。需持久化（见 ASYNC_ROUTER_STORAGE_KEY）；
   *  存储缺失（未登录）时为空数组，登录后由 buildAsyncRouterData 构建并落盘 */
  asyncRouterData: AsyncRouteNode[];
  /** 场景一：登录后构建全量动态路由树并持久化 */
  buildAsyncRouterData: () => void;
}

/**
 * 将路由节点（AppRouteNode）映射为动态路由节点（AsyncRouteNode）。
 * 仅搬运路由注册所需的字段，未命中的字段回退为默认值；若存在子节点则一并挂上。
 * @param node 源路由节点，不允许为 null
 * @param children 已构建好的子路由节点；为空或 undefined 时不挂 children 字段
 * @returns 转换后的 AsyncRouteNode
 */
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
  menuPagePath: node.menuPagePath,
  children: children?.length ? children : undefined,
});

/**
 * 递归构建动态路由树：仅保留可生成路由的节点（page/redirect/fallback），
 * 其余节点（如 group）仅透传其 children，不保留壳。
 * @param nodes 路由节点森林（可能含多级 children）
 * @returns 动态路由树数组；无匹配路由时返回空数组
 */
const buildAsyncRouteTree = (nodes: AppRouteNode[]): AsyncRouteNode[] =>
  nodes.flatMap((node) => {
    const children = node.children?.length ? buildAsyncRouteTree(node.children) : undefined;
    if (!isPageLikeRouteNode(node) || !node.routePath) {
      return children ?? [];
    }
    return [toAsyncRouteNode(node, children)];
  });

/**
 * 读取持久化的动态路由树（asyncRouterData）。
 * 存储即唯一权威数据源：写入方（buildAsyncRouterData）产出的是结构干净的 AsyncRouteNode[]，
 * 经 JSON 往返后字段无损（menuPagePath 为字符串，可随树一同持久化），故此处不做逐节点清洗，
 * 只做顶层数组形态校验——与 MenuStore.readStoredMenuData 的「信任自有持久化」策略一致。
 * 存储缺失、解析失败、非数组一律视为「没有」，返回空数组（刻意的合法初值）。
 * 副作用：读取 localStorage（'local' 作用域）的 ASYNC_ROUTER_STORAGE_KEY。
 * @returns 持久化的动态路由树；缺失或格式非法时返回空数组
 */
const readStoredAsyncRouterData = (): AsyncRouteNode[] => {
  const stored = getStorageItem<AsyncRouteNode[]>(ASYNC_ROUTER_STORAGE_KEY, 'local');
  // 只接受数组形态：null（缺失/解析失败/存储不可用）与 JSON 基本类型一律视为「没有」。
  // 空数组是刻意的合法初值，不伪装成已初始化。
  return Array.isArray(stored) ? stored : [];
};

// ===== 场景二：从持久化加载 - store 初始化（模块加载时自动执行）=====
// 刷新浏览器（已登录）时直接从 localStorage 还原 asyncRouterData；未登录则为空数组，无需手动调用。
const initialAsyncRouterData = readStoredAsyncRouterData();

/** 内部统一出口：持久化 + 写入 state（消除 action 的重复骨架）。 */
const applyAsyncRouterData = (
  set: (partial: Partial<RouterState>) => void,
  asyncRouterData: AsyncRouteNode[],
): void => {
  setStorageItem(ASYNC_ROUTER_STORAGE_KEY, asyncRouterData, 'local');
  set({ asyncRouterData });
};

export const useRouterStore = create<RouterState>((set) => ({
  // 场景二：以下初始 state 在 store 初始化时由 localStorage 还原（见 initial*），直接内联无需 return
  asyncRouterData: initialAsyncRouterData,

  // 场景一：首次登录成功 → 构建全量动态路由树并持久化
  buildAsyncRouterData: () => {
    const asyncRouterData = buildAsyncRouteTree(
      MENU_MANIFEST.flatMap((moduleNode) => moduleNode.children ?? []),
    );
    applyAsyncRouterData(set, asyncRouterData);
  },
}));
