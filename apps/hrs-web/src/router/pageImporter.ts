import type { RouteLoader } from './manifest';

/**
 * 真源页面模块的懒加载导入映射（Vite 构建期静态收集）。
 * 键为相对本文件的 '../pages/<相对路径>.tsx'，与 manifest/Whitelist 中的 menuPagePath 字符串
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
