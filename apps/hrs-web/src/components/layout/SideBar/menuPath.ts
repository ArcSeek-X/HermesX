/**
 * @file menuPath.ts
 * @description 菜单路由高亮判定（单一真源）。
 *   供 MenuNode 计算单节点高亮，以及 SidebarNav 做「父级自动展开命中子项」复用，
 *   避免两端各写一份匹配逻辑；抽到组件文件之外以满足 react-refresh 仅导出组件的约定。
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-10-13
 */

/**
 * 判断菜单配置的路由是否命中当前路径。
 *
 * @param routePath 菜单配置的路由；为空表示该项不可跳转，直接判为未命中
 * @param exact     true 要求与当前路径完全相等；false 时当前路径为其子路径也算命中
 * @param pathname  当前浏览器路径
 * @returns 命中返回 true，否则 false
 */
export const matchPath = (
  routePath: string | undefined,
  exact: boolean | undefined,
  pathname: string,
): boolean => {
  if (!routePath) return false;
  return exact ? pathname === routePath : pathname === routePath || pathname.startsWith(`${routePath}/`);
};
