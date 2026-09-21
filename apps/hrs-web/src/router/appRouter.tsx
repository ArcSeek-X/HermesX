/**
 * @file appRouter.tsx
 * @description 数据路由实例与守卫：创建 createBrowserRouter，定义登录路由、受保护布局（Shell），
 *   并暴露 protectedLoader。业务路由经 RouterStore.registerAsyncRoutes 动态注入 protected.children。
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-09-21
 */
import {
  createBrowserRouter,
  redirect,
  type LoaderFunctionArgs,
} from 'react-router-dom';
import { useAuthStore } from '../stores/AuthStore';
import { useRouterStore } from '../stores/RouterStore';
import type { RouteHandle } from '../types/router';
import { buildAsyncRoutes } from './asyncRouteFactory';
import LoginPage from '../pages/LoginPage/LoginPage';
import { Shell } from '../components';
import { RouteErrorBoundary } from '../components/layout/RouteBoundary';
import NotFoundPage from '../pages/NotFoundPage';

/** 受保护布局守卫：未登录且开启鉴权时重定向到登录页（携来源路径，登录后可原路返回） */
export const protectedLoader = ({ request }: LoaderFunctionArgs): Response | null => {
  const { authEnabled, loggedIn } = useAuthStore.getState();
  // 仅开启鉴权且未登录才拦截；已登录或未开启鉴权直接放行
  if (authEnabled && !loggedIn) {
    const url = new URL(request.url);
    throw redirect(`/login?redirect=${encodeURIComponent(url.pathname + url.search)}`);
  }
  return null;
};

/** 业务路由种子：从持久化的 asyncRouteData 同步还原，作为 protected.children 初始值。
 *  必须写进 createBrowserRouter 初始配置（而非仅运行时 patchRoutes）：否则刷新时初始匹配早于注入，
 *  会把已登录业务地址（如 /home）误判为未匹配而落到 * 兜底跳 /404。登录后 registerAsyncRoutes 仍以 patchRoutes 整体替换。 */
const initialBusinessRoutes = buildAsyncRoutes(useRouterStore.getState().asyncRouteData);

export const router = createBrowserRouter([
  // 根路径：重定向至登录页
  {
    path: '/',
    children: [
      { index: true, loader: () => redirect('/login'), errorElement: <RouteErrorBoundary /> },
    ],
  },
  {
    path: '/login',
    element: <LoginPage />,
    errorElement: <RouteErrorBoundary />,
    // 登录页静态元数据（i18n 键），供 ShellHeader 经 useMatches 读取渲染页头
    handle: {
      routerName: 'auth.login.title',
      routerDescription: 'auth.login.description',
    } satisfies RouteHandle,
  },
  {
    id: 'protected',
    element: <Shell />,
    loader: protectedLoader,

    children: [
      // 异常兜底 404：置于顶层（不挂在 protected 之下），避免被 registerAsyncRoutes 的 patchRoutes 整体替换时覆盖
      {
        path: '404',
        loader: ({ request }) => {
          const { authEnabled, loggedIn } = useAuthStore.getState();
          if (authEnabled && !loggedIn) {
            const url = new URL(request.url);
            throw redirect(`/login?redirect=${encodeURIComponent(url.pathname + url.search)}`);
          }
          console.log("404")
          return null;
        },
        element: <NotFoundPage />,
      },
      // 业务路由种子：刷新时初始匹配即可命中；登录后由 registerAsyncRoutes 整体替换
      ...initialBusinessRoutes,
    ],
  },
  // 异常兜底：顶层 * 路由
  {
    path: '*',
    loader: ({ request }) => {
      const { authEnabled, loggedIn } = useAuthStore.getState();
      const url = new URL(request.url);
      // 未登录且开启鉴权：优先跳登录（单跳直达）；否则跳 /404
      if (authEnabled && !loggedIn) {
        return redirect(`/login?redirect=${encodeURIComponent(url.pathname + url.search)}`);
      }
      console.log("*******")
      return redirect('/404');
    },
  },
]);
