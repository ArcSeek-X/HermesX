/**
 * 应用内容组件（从 App.tsx 抽取）。
 *
 * 职责：
 * 1. 必须位于 <Router> 之内，消费 useLocation / useAuth 等路由与鉴权上下文。
 * 2. 鉴权态介入路由：未登录且开启鉴权时，受保护路由重定向到 /login；登录态访问 /login 回首页。
 * 3. 渲染壳布局（Shell + RouteOutletBoundary）+ 子路由出口；
 *    路由完全由数据驱动——主业务路由来自 RouterStore 的 asyncRouterData（真源 MENU_MANIFEST 加工），
 *    白名单路由（根路径重定向、404 兜底、登录页）来自 router/Whitelist。
 */

import type React from 'react';
import { lazy, useEffect, useMemo } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { InlineTipCard, Shell } from './components';
import {
  PageLoadingFallback,
  RouteOutletBoundary,
  StandaloneRouteBoundary,
} from './components/layout/RouteBoundary';
import { useAuth } from './contexts/AuthContext';
import { useUiLanguage } from './contexts/UiLanguageContext';
import { useAgentChatStore } from './stores/agentChatStore';
import { useRouterStore } from './stores/RouterStore';
import { EXCEPTION_ROUTE, WHITE_LIST_ROUTE } from './router/Whitelist';
import { resolvePageImporter } from './router/pageImporter';
import type { AsyncRouteNode } from './types/router';

/**
 * ===================== 数据源驱动的动态路由 =====================
 * 主业务路由来自 RouterStore.asyncRouterData（页面路径内联为 routerPagePath）；
 * 白名单路由来自 router/Whitelist（自带 menuPagePath）。两者均经 resolvePageImporter 解析为懒加载组件。
 */

/** 懒加载组件缓存：同一 key 复用同一个 lazy 组件，避免每次渲染重建导致页面重挂载 */
const lazyPageCache = new Map<string, React.LazyExoticComponent<React.ComponentType>>();

/** 按 key + 页面路径字符串解析并缓存懒加载组件；无页面路径或未命中返回 null */
const getLazyPage = (
  key: string,
  pagePath?: string,
): React.LazyExoticComponent<React.ComponentType> | null => {
  if (!pagePath) {
    return null;
  }
  const importer = resolvePageImporter(pagePath);
  if (!importer) {
    return null;
  }
  let page = lazyPageCache.get(key);
  if (!page) {
    page = lazy(importer);
    lazyPageCache.set(key, page);
  }
  return page;
};

/** 把动态路由树扁平化并剔除无 path 的分组节点，便于统一渲染 */
const flattenAsyncRoutes = (nodes: AsyncRouteNode[]): AsyncRouteNode[] =>
  nodes.flatMap((node) => [
    ...(node.routerPath ? [node] : []),
    ...(node.children ? flattenAsyncRoutes(node.children) : []),
  ]);

/** 通用 <Route> 构造：redirect 节点走 Navigate，page 节点走懒加载页面；无 path 或无页面则返回 null */
const buildRoute = (
  key: string,
  path?: string,
  pagePath?: string,
  handle: { menuName?: string; menuId?: string; description?: string; icon?: string } = {},
  redirect?: string,
): React.ReactNode => {
  if (!path) return null;
  if (redirect) {
    return <Route key={key} path={path} element={<Navigate to={redirect} replace />} handle={handle} />;
  }
  const Page = getLazyPage(key, pagePath);
  return Page ? <Route key={key} path={path} element={<Page />} handle={handle} /> : null;
};

/** 主业务动态路由节点（AsyncRouteNode）→ <Route> */
const renderDynamicRoute = (node: AsyncRouteNode): React.ReactNode =>
  buildRoute(
    node.routerKey,
    node.routerPath,
    node.routerPagePath,
    { menuName: node.routerName, menuId: node.routerKey, description: node.routerDescription, icon: node.routerDescription },
    node.routerType === 'redirect' ? node.redirect : undefined,
  );

/**
 * 登录页需脱离 Shell 独立渲染，且在模块级从 Whitelist 预构建懒加载组件，
 * 避免组件渲染期创建组件（触发 react-hooks/static-components 规则）。
 */
const LoginLazyPage = getLazyPage(
  'login',
  WHITE_LIST_ROUTE.find((n) => n.routerKey === 'login')?.routerPagePath,
);

/**
 * 路由内部组件，必须位于 <Router> 之内，才能使用 useLocation / useAuth 等钩子。
 */
const AppContent: React.FC = () => {
  const location = useLocation();
  const { authEnabled, loggedIn, isLoading, loadError, refreshStatus } = useAuth();
  const { t } = useUiLanguage();

  // 业务路由数据源：由登录成功分支（见 LoginCard）构建并持久化；为空则无业务路由可渲染
  const asyncRouterData = useRouterStore((s) => s.asyncRouterData);
  const dynamicRoutes = useMemo(() => flattenAsyncRoutes(asyncRouterData), [asyncRouterData]);

  // 每次路由变化时，把当前路径同步给对话 store，供 ChatPage 等组件感知当前所在页
  useEffect(() => {
    useAgentChatStore.getState().setCurrentRoute(location.pathname);
  }, [location.pathname]);

  // 鉴权状态仍在初始化中：展示全屏加载占位，避免闪烁/误重定向
  if (isLoading) {
    return <PageLoadingFallback />;
  }

  // 鉴权状态加载失败：展示错误提示并提供重试按钮
  if (loadError) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-base px-4">
        <div className="w-full max-w-lg">
          <InlineTipCard variant="danger" content={loadError} />
        </div>
        <button
          type="button"
          className="btn-primary"
          onClick={() => void refreshStatus()}
        >
          {t('common.retry')}
        </button>
      </div>
    );
  }




  // 开启鉴权但未登录：在 /login 独立渲染登录页，否则重定向到 /login?redirect=当前路径. authEnabled && !loggedI
  if (true) {

    alert(location.pathname)
    if (location.pathname === '/login') {
      return LoginLazyPage ? (
        <StandaloneRouteBoundary>
          <LoginLazyPage />
        </StandaloneRouteBoundary>
      ) : null;
    }
    const redirect = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?redirect=${redirect}`} replace />;
  }

  // 正常渲染壳布局 + 子路由出口；路由全部由数据驱动注册
  return (
    <Routes>
      <Route
        element={(
          // Shell 提供常驻侧边导航与顶栏；RouteOutletBoundary 包裹子路由，负责错误边界
          <Shell>
            <RouteOutletBoundary />
          </Shell>
        )}
      >
        {/* 白名单：根路径重定向（数据驱动，来自 Whitelist） */}
        {WHITE_LIST_ROUTE.filter((n) => n.routerKey !== 'login').map(renderDynamicRoute)}
        {/* 主业务动态路由：全部来自 MENU_MANIFEST，替换原所有硬编码路由 */}
        {dynamicRoutes.map(renderDynamicRoute)}
        {/* 白名单：404 兜底（数据驱动，来自 Whitelist，置于最后） */}
        {EXCEPTION_ROUTE.map(renderDynamicRoute)}
      </Route>
    </Routes>
  );
};

export default AppContent;
