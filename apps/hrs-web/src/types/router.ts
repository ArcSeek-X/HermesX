import type {
  ModuleId,
  RouteAuthPolicy,
  RouteMenuType,
} from '../router/manifest';

/** 动态路由树节点。 */
export type AsyncRouteNode = {
  menuId: string;
  menuName?: string;
  menuDescription: string;
  path: string;
  auth?: RouteAuthPolicy;
  moduleId?: ModuleId[];
  menuType: Exclude<RouteMenuType, 'group'>;
  redirect?: string;
  /** 页面模块路径（字符串，如 'pages/StockDashboardPage'）：运行时经 pageImporter 解析为懒加载导入函数 */
  menuPagePath?: string;
  children?: AsyncRouteNode[];
};
