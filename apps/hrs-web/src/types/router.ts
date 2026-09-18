import type {
  ModuleId,
  RouteAuthPolicy,
  RouteLoader,
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
  loader?: RouteLoader;
  children?: AsyncRouteNode[];
};
