import type {
  RouteAuthPolicy,
  RouteMenuType,
} from '../router/manifest';

/** 动态路由树节点。 */
export type AsyncRouteNode = {
  routerKey: string;
  routerName?: string;
  routerPath: string;
  /** 路由实际指向的页面模块路径（如 'pages/HomePage'），由真源 MENU_MANIFEST.menuPagePath 映射而来 */
  routerPagePath: string;
  routerType: Exclude<RouteMenuType, 'group'>;
  auth?: RouteAuthPolicy;
  redirect?: string;
  routerDescription: string;
  children?: AsyncRouteNode[];
};
