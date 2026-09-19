/**
 * @file routeMeta.ts
 * @description 由路由清单（router/manifest）派生页头文案索引 ROUTE_META。
 *
 * 架构约定：manifest.ts 是数据真源，只存放原始数据（MENU_MANIFEST），不承载处理逻辑；
 * 本文件负责"处理"——递归收集 MENU_MANIFEST 中各页面的标题/描述，按 routePath 建索引，
 * 供 ShellHeader 按 pathname 查当前页的标题/描述。
 */

import { MENU_MANIFEST } from './manifest';
import type { AppRouteNode } from './manifest';

/** 页面文案：标题 + 可选描述（i18n key 或直写文案） */
export type RouteMeta = {
  title: string;
  description?: string;
};

/**
 * 递归收集路由清单中的页面文案（按 routePath 建索引），供页头（ShellHeader）按 pathname 查标题/描述。
 * 跳过无 routePath 的分组节点；先展开的节点优先（产品菜单优先于调试菜单）。
 */
const collectRouteMeta = (nodes: AppRouteNode[], acc: Record<string, RouteMeta> = {}): Record<string, RouteMeta> => {
  for (const node of nodes) {
    if (node.routePath && !acc[node.routePath]) {
      acc[node.routePath] = { title: node.menuName ?? node.menuId, description: node.menuDescription };
    }
    if (node.children?.length) collectRouteMeta(node.children, acc);
  }
  return acc;
};

/** 全站路由文案索引（由 MENU_MANIFEST 派生）；未命中的路由由调用方回退兜底文案 */
export const ROUTE_META: Record<string, RouteMeta> = collectRouteMeta(
  MENU_MANIFEST.flatMap((moduleNode) => moduleNode.children ?? []),
);
