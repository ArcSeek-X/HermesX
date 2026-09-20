import type { AsyncRouteNode } from '../types/router';

/** 白名单路由：无需进入主业务菜单树即可单独消费，典型如登录页与根路径重定向。字段与 AsyncRouteNode 一一对应。 */
export const WHITE_LIST_ROUTE: AsyncRouteNode[] = [
  {
    routerKey: 'root-redirect',
    routerName: 'exception.redirect.title',
    routerPath: '/',
    routerDescription: 'exception.redirect.description',
    routerType: 'redirect',
    auth: 'protected',
    routerPagePath: '',
    redirect: '/home',
  },
  {
    routerKey: 'login',
    routerName: 'auth.login.title',
    routerPath: '/login',
    routerDescription: 'auth.login.description',
    routerType: 'page',
    auth: 'public',
    routerPagePath: 'pages/LoginPage/LoginPage',
  },
];

/** 异常路由：兜底或错误态页面，独立于主业务树维护。字段与 AsyncRouteNode 一一对应，文案走 i18n。 */
export const EXCEPTION_ROUTE: AsyncRouteNode[] = [
  {
    routerKey: 'not-found',
    routerName: 'exception.404.title',
    routerPath: '*',
    routerDescription: 'exception.404.description',
    routerType: 'fallback',
    auth: 'protected',
    routerPagePath: 'pages/NotFoundPage',
  },
];

/** 汇总后的完整白名单路由真源。 */
export const WHITE_LIST_ROUTE_MANIFEST: AsyncRouteNode[] = [
  ...WHITE_LIST_ROUTE,
  ...EXCEPTION_ROUTE,
];
