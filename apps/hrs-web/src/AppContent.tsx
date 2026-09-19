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
import { type AppRouteNode } from './router/manifest';

/**
 * ===================== 数据源驱动的动态路由 =====================
 * 路由不再写死，全部由数据生成：
 * - 主业务路由：来自 RouterStore.asyncRouterData（由真源 MENU_MANIFEST 加工成 AsyncRouteNode[]）。
 * - 白名单路由：来自 router/Whitelist（根路径重定向、404 兜底、登录页）。
 *
 * menuPagePath 是字符串（页面模块路径，如 'pages/StockDashboardPage'），运行时经 resolvePageImporter
 * （基于 import.meta.glob 收集的真源页面模块）解析为懒加载导入函数。真源 MENU_MANIFEST 为准，
 * 节点自带 menuPagePath 即视为有效，无需额外兜底。
 */

/** 懒加载组件缓存：同一 menuId 复用同一个 lazy 组件，避免每次渲染重建导致页面重挂载 */
const lazyPageCache = new Map<string, React.LazyExoticComponent<React.ComponentType>>();

/** 按 menuId + 页面路径字符串解析并缓存懒加载组件；无 menuPagePath 或未命中返回 null */
const getLazyPage = (
  menuId: string,
  pagePath?: string,
): React.LazyExoticComponent<React.ComponentType> | null => {
  if (!pagePath) {
    return null;
  }
  const importer = resolvePageImporter(pagePath);
  if (!importer) {
    return null;
  }
  let page = lazyPageCache.get(menuId);
  if (!page) {
    page = lazy(importer);
    lazyPageCache.set(menuId, page);
  }
  return page;
};

/** 把动态路由树扁平化并剔除无 path 的分组节点，便于统一渲染 */
const flattenAsyncRoutes = (nodes: AsyncRouteNode[]): AsyncRouteNode[] =>
  nodes.flatMap((node) => [
    ...(node.path ? [node] : []),
    ...(node.children ? flattenAsyncRoutes(node.children) : []),
  ]);

/** 把单个主业务动态路由节点（AsyncRouteNode，使用 path）转换为 <Route>：redirect 走 Navigate，page 走懒加载 */
const renderDynamicRoute = (node: AsyncRouteNode): React.ReactNode => {
  const handle = { menuName: node.menuName, icon: node.menuDescription };
  if (node.menuType === 'redirect' && node.redirect) {
    return <Route key={node.menuId} path={node.path} element={<Navigate to={node.redirect} replace />} handle={handle} />;
  }
  const Page = getLazyPage(node.menuId, node.menuPagePath);
  if (!Page) {
    return null;
  }
  return <Route key={node.menuId} path={node.path} element={<Page />} handle={handle} />;
};

/** 把单个白名单路由节点（AppRouteNode，使用 routePath）转换为 <Route> */
const renderWhitelistRoute = (node: AppRouteNode): React.ReactNode => {
  if (!node.routePath) {
    return null;
  }
  const handle = { menuName: node.menuName, icon: node.menuDescription };
  if (node.menuType === 'redirect' && node.redirect) {
    return <Route key={node.menuId} path={node.routePath} element={<Navigate to={node.redirect} replace />} handle={handle} />;
  }
  const Page = getLazyPage(node.menuId, node.menuPagePath);
  if (!Page) {
    return null;
  }
  return <Route key={node.menuId} path={node.routePath} element={<Page />} handle={handle} />;
};

/**
 * 登录页需脱离 Shell 独立渲染，且在模块级从 Whitelist 预构建懒加载组件，
 * 避免组件渲染期创建组件（触发 react-hooks/static-components 规则）。
 */
const LoginLazyPage = getLazyPage(
  'login',
  WHITE_LIST_ROUTE.find((n) => n.menuId === 'login')?.menuPagePath,
);

/**
 * 路由内部组件，必须位于 <Router> 之内，才能使用 useLocation / useAuth 等钩子。
 */
const AppContent: React.FC = () => {
  // 当前路由信息（含 pathname 与 search）
  const location = useLocation();
  // 鉴权状态：是否开启鉴权、是否已登录、是否正在初始化、初始化错误等
  const { authEnabled, loggedIn, isLoading, loadError, refreshStatus } = useAuth();
  // UI 多语言文案函数
  const { t } = useUiLanguage();

  // === 动态路由数据源 ===
  // asyncRouterData 由登录成功分支（见 LoginCard）构建并持久化；持久化被删除/为空则视为缺少路由信息，
  // 此时无业务路由可渲染，由鉴权/重定向逻辑导向登录页，无需在此刻意重建。
  const asyncRouterData = useRouterStore((s) => s.asyncRouterData);
  // 全量主业务动态路由（来自 MENU_MANIFEST，经 asyncRouterData 扁平化），替换原所有硬编码路由
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

  // 开启了鉴权但未登录：
  // - 当前正好在 /login，则独立渲染登录页（不带导航壳）
  // - 否则把目标路径编码进 query，重定向到 /login?redirect=...，登录后可跳回
  if (authEnabled && !loggedIn) {
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
        {WHITE_LIST_ROUTE.filter((n) => n.menuId !== 'login').map(renderWhitelistRoute)}
        {/* 主业务动态路由：全部来自 MENU_MANIFEST，替换原所有硬编码路由 */}
        {dynamicRoutes.map(renderDynamicRoute)}
        {/* 白名单：404 兜底（数据驱动，来自 Whitelist，置于最后） */}
        {EXCEPTION_ROUTE.map(renderWhitelistRoute)}
      </Route>
    </Routes>
  );
};

export default AppContent;
