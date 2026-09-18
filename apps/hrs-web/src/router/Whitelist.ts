import type { AppRouteNode } from './manifest';

/** 白名单路由：无需进入主业务菜单树即可单独消费，典型如登录页与根路径重定向。 */
export const WHITE_LIST_ROUTE: AppRouteNode[] = [
  {
    menuId: 'root-redirect',
    menuName: 'layout.appFallbackTitle',
    routePath: '/',
    menuPosition: 'content',
    level: 0,
    menuExpanded: false,
    menuDescription: '根路径兼容旧链接：重定向到首页',
    menuType: 'redirect',
    auth: 'protected',
    moduleId: ['productModel', 'developmentMode'],
    menuVisible: false,
    redirect: '/home',
  },
  {
    menuId: 'login',
    menuName: '登录',
    routePath: '/login',
    menuPosition: 'content',
    level: 0,
    menuExpanded: false,
    menuDescription: '登录页（独立布局）',
    menuType: 'page',
    auth: 'public',
    moduleId: ['productModel', 'developmentMode'],
    menuVisible: false,
    loader: () => import('../pages/LoginPage/LoginPage'),
  },
];


/** 异常路由：兜底或错误态页面，独立于主业务树维护。 */
export const EXCEPTION_ROUTE: AppRouteNode[] = [
{
    menuId: 'not-found',
    menuName: '404',
    routePath: '*',
    menuPosition: 'content',
    level: 0,
    menuExpanded: false,
    menuDescription: '兜底未命中路由',
    menuType: 'fallback',
    auth: 'protected',
    moduleId: ['productModel', 'developmentMode'],
    menuVisible: false,
    loader: () => import('../pages/NotFoundPage'),
  }
];



/** 汇总后的完整路由真源。 */
export const WHITE_LIST_ROUTE_MANIFEST: AppRouteNode[] = [
  ...WHITE_LIST_ROUTE,
  ...EXCEPTION_ROUTE,
];
