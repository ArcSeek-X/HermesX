/**
 * @file asyncRouteFactory.ts
 * @description 动态路由工厂：将动态路由树（AsyncRouteNode[]）映射为 React Router 的 RouteObject[]。
 *   合并原 pageImporter（页面懒加载解析）与本工厂纯函数，集中处理「树 → 路由对象」与「页面路径 → 懒加载导入」。
 *   业务路由恒以 pathless protected 父路由为基准，故路径统一去掉前导 '/'，由 patchRoutes 注入其 children。
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-09-20
 */
import type { ComponentType } from 'react';
import { redirect, type RouteObject } from 'react-router-dom';
import type { AsyncRouteNode, RouteHandle } from '../types/router';

// ===== 页面模块懒加载解析（原 pageImporter）=====

/**
 * 页面模块懒加载导入函数类型：返回解析为 { default: ComponentType } 的 Promise。
 * 由 manifest 的 menuPagePath 字符串经 resolvePageImporter 解析为可执行导入函数。
 */
export type RouteLoader = () => Promise<{ default: ComponentType }>;

/**
 * 真源页面模块的懒加载导入映射（Vite 构建期静态收集）。
 * 键为相对本文件的 '../pages/<相对路径>.tsx'，与 manifest 中的 menuPagePath 字符串
 * （如 'pages/StockDashboardPage'）经前缀 '../' 与后缀 '.tsx' 补全后一一对应。
 */
const pageModules = import.meta.glob('../pages/**/*.tsx');

/**
 * 将真源中的 menuPagePath 字符串（如 'pages/StockDashboardPage'）解析为可执行的懒加载导入函数。
 * @param pagePath menuPagePath 字符串（不含 '../' 前缀与 '.tsx' 后缀）
 * @returns 懒加载导入函数；未命中返回 undefined
 */
export const resolvePageImporter = (pagePath?: string): RouteLoader | undefined => {
  if (!pagePath) {
    return undefined;
  }
  const key = `../${pagePath}.tsx`;
  return (pageModules[key] as RouteLoader | undefined);
};

// ===== 路由树 → React Router 路由对象 =====

/** 扁平化路由树：去掉无 path 的分组节点，便于统一映射 */
const flattenRoutes = (nodes: AsyncRouteNode[]): AsyncRouteNode[] =>
  nodes.flatMap((node) => [
    ...(node.routerPath ? [node] : []),
    ...(node.children ? flattenRoutes(node.children) : []),
  ]);

/**
 * 将动态路由节点映射为 React Router 路由对象。
 * - page 节点：路由级 lazy 懒加载 + handle 元数据（routerName / routerDescription 供页头 useMatches 读取）
 * - redirect 节点：loader 重定向
 * @param nodes 动态路由树（来自 RouterStore.asyncRouteData）
 * @returns RouteObject 数组；空输入返回空数组
 */
export const buildAsyncRoutes = (nodes: AsyncRouteNode[]): RouteObject[] =>
  flattenRoutes(nodes).map((node) => ({
    // 以 pathless protected 为父，路径须相对（去掉前导 '/'），由 patchRoutes 解析到根 '/'
    path: node.routerPath.replace(/^\//, ''),
    handle: { routerName: node.routerName, routerDescription: node.routerDescription } satisfies RouteHandle,
    ...(node.routerType === 'redirect'
      ? { loader: () => redirect(node.redirect!) }
      : {
          lazy: () =>
            resolvePageImporter(node.routerPagePath)!().then((module) => ({
              Component: (module as { default: ComponentType }).default,
            })),
        }),
  }));
