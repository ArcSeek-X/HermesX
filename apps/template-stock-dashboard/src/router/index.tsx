/**
 * 路由配置
 */

import { Suspense, lazy, type ReactNode } from 'react';
import { createBrowserRouter, RouterProvider, useParams } from 'react-router-dom';
import { withFaroRouterInstrumentation } from '@grafana/faro-react';
import { Layout } from '@/components/layout';
import { Dashboard } from '@/pages/Dashboard';
import { Loading } from '@/components/common';
import { NotFound, RouteErrorFallback } from '@/pages/NotFound';

const Heatmap = lazy(() => import('@/pages/Heatmap').then((mod) => ({ default: mod.Heatmap })));
const Rankings = lazy(() => import('@/pages/Rankings').then((mod) => ({ default: mod.Rankings })));
const Boards = lazy(() => import('@/pages/Boards').then((mod) => ({ default: mod.Boards })));
const BoardDetail = lazy(() =>
  import('@/pages/Boards').then((mod) => ({ default: mod.BoardDetail }))
);
const Watchlist = lazy(() => import('@/pages/Watchlist').then((mod) => ({ default: mod.Watchlist })));
const Scanner = lazy(() => import('@/pages/Scanner').then((mod) => ({ default: mod.Scanner })));
const Settings = lazy(() => import('@/pages/Settings').then((mod) => ({ default: mod.Settings })));
const StockDetail = lazy(() =>
  import('@/pages/StockDetail').then((mod) => ({ default: mod.StockDetail }))
);
const EndOfDayPicker = lazy(() =>
  import('@/pages/EndOfDayPicker').then((mod) => ({ default: mod.EndOfDayPicker }))
);

function withSuspense(element: ReactNode) {
  return (
    <Suspense fallback={<Loading fullScreen text="加载页面..." />}>
      {element}
    </Suspense>
  );
}

// key 按参数重挂载：切换股票/板块即重置组件，旧实例在途请求的 setState 作废，杜绝串数据
function StockDetailRoute() {
  const { code } = useParams<{ code: string }>();
  return <StockDetail key={code} />;
}

function BoardDetailRoute() {
  const { type, code } = useParams<{ type: string; code: string }>();
  return <BoardDetail key={`${type}/${code}`} />;
}

const browserRouter = createBrowserRouter(
  [
    {
      path: '/',
      element: <Layout />,
      errorElement: <RouteErrorFallback />,
      children: [
        {
          index: true,
          element: <Dashboard />,
        },
        {
          path: 'heatmap',
          element: withSuspense(<Heatmap />),
        },
        {
          path: 'rankings',
          element: withSuspense(<Rankings />),
        },
        {
          path: 'boards',
          element: withSuspense(<Boards />),
        },
        {
          path: 'boards/:type/:code',
          element: withSuspense(<BoardDetailRoute />),
        },
        {
          path: 'watchlist',
          element: withSuspense(<Watchlist />),
        },
        {
          path: 'scanner',
          element: withSuspense(<Scanner />),
        },
        {
          path: 'eod-picker',
          element: withSuspense(<EndOfDayPicker />),
        },
        {
          path: 'settings',
          element: withSuspense(<Settings />),
        },
        {
          path: 's/:code',
          element: withSuspense(<StockDetailRoute />),
        },
        {
          path: '*',
          element: <NotFound />,
        },
      ],
    },
  ],
  { basename: import.meta.env.BASE_URL }
);

// Faro 的 data-router 路由遥测必须包裹 router 实例才生效（要求 initializeFaro 已先执行，见 main.tsx 的加载顺序）
const router = import.meta.env.PROD
  ? withFaroRouterInstrumentation(browserRouter)
  : browserRouter;

export function AppRouter() {
  return <RouterProvider router={router} />;
}
