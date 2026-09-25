/**
 * @file appRouter.tsx
 * @description 数据路由实例与守卫：创建 createBrowserRouter，定义登录路由、受保护布局（Shell），
 *   并暴露 protectedLoader。业务路由经 routeRegistration.registerAsyncRoutes 动态注入 protected 下的 business 子路由（404 兜底固定在 Shell 内，不在此注入）。
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
import { Shell } from '@components/layout/Shell';
import { RouteErrorBoundary } from '../pages/ErrorPage/RouteBoundary';
import LoginPage from '../pages/LoginPage/LoginPage';
import NotFoundPage from '../pages/ErrorPage/NotFoundPage';

/**
 * 鉴权守卫：未登录且开启鉴权时返回「跳登录页」的 Response（携来源路径），否则返回 null 放行。
 * 供 protectedLoader、404 兜底、* 兜底三处 loader 共用，避免重复鉴权逻辑。
 */
const guardAuthRedirect = (request: Request): Response | null => {
  const { authEnabled, loggedIn } = useAuthStore.getState();
  if (authEnabled && !loggedIn) {
    const url = new URL(request.url);
    return redirect(`/login?redirect=${encodeURIComponent(url.pathname + url.search)}`);
  }
  return null;
};

/** 受保护布局守卫：未登录且开启鉴权时重定向到登录页（携来源路径，登录后可原路返回） */
export const protectedLoader = ({ request }: LoaderFunctionArgs): Response | null =>
  guardAuthRedirect(request);

/** 业务路由种子：从持久化的 asyncRouteData 同步还原，作为 protected 下 business 子路由的初始值。
 *  必须写进 createBrowserRouter 初始配置（而非仅运行时 patchRoutes）：否则刷新时初始匹配早于注入，
 *  会把已登录业务地址（如 /home）误判为未匹配而落到 * 兜底跳 /404。登录后 registerAsyncRoutes 以 patchRoutes('business') 整体替换。 */
const initialBusinessRoutes = buildAsyncRoutes(useRouterStore.getState().asyncRouteData);

/** 初始 hydration 占位：React Router v7 数据路由在首屏初始化（跑 loader）期间会渲染 HydrateFallback；
 *  若不提供，开发期会告警 "No `HydrateFallback` element provided to render during initial hydration"。
 *  这里给一个轻量加载占位，等价于原先空白渲染，但消除告警并避免首屏白屏闪烁。 */
function RouteHydrateFallback() {
  return (
    <div className="flex h-screen w-full items-center justify-center text-muted-text">
      Loading…
    </div>
  );
}

export const router = createBrowserRouter([
  {
    // 显式根路由：包裹登录 / 受保护布局 / 兜底路由；挂 HydrateFallback 消除上述 dev 告警。
    // 等价于原先的隐式根，不影响现有匹配与 patchRoutes('business') 注入。
    HydrateFallback: RouteHydrateFallback,
    children: [
      // 根路径：重定向至登录页（顶层 index 路由，无需再包一层 path: '/'）
      { index: true, loader: () => redirect('/login'), errorElement: <RouteErrorBoundary /> },
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
        errorElement: <RouteErrorBoundary />,
        children: [
          // 异常兜底 404：固定在 Shell 内（底座为 Shell），不参与动态注入，避免被 patchRoutes 整体替换时冲掉
          {
            path: '404',
            loader: () => null,
            element: <NotFoundPage />,
          },
          // 动态业务路由容器：刷新时初始匹配即可命中；登录后由 registerAsyncRoutes 以 patchRoutes('business') 整体替换
          {
            id: 'business',
            children: initialBusinessRoutes,
          },
        ],
      },
      // 异常兜底：顶层 * 路由，未匹配路径统一收口（未登录跳登录，已登录跳 /404）
      {
        path: '*',
        loader: ({ request }) => {
          const res = guardAuthRedirect(request);
          if (res) return res;
          return redirect('/404');
        },
      },
    ],
  },
]);
