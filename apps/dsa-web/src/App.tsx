/**
 * 应用根组件：负责全局 Provider 装配与路由渲染。
 *
 * 设计要点：
 * 1. 全局 Provider 分层：UI 语言 → 路由 → 鉴权 → 页面状态，逐层向内包裹，
 *    保证子组件都能消费到对应的上下文。
 * 2. 路由采用「壳布局 + 子路由出口」结构（Shell + RouteOutletBoundary），
 *    左侧导航栏常驻，右侧内容区随路由切换。
 * 3. 鉴权态介入路由：未登录且开启鉴权时，受保护路由会被重定向到 /login。
 */

import type React from 'react';
import { lazy, useEffect } from 'react';
import { BrowserRouter as Router, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { ApiErrorAlert, Shell } from './components/common';
import {
  PageLoadingFallback,
  RouteOutletBoundary,
  StandaloneRouteBoundary,
} from './components/layout/RouteBoundary';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { UiLanguageProvider, useUiLanguage } from './contexts/UiLanguageContext';
import { PageStateProvider } from './stores/PageStateStore';
import { useAgentChatStore } from './stores/agentChatStore';
import './App.css';

/**
 * 页面级组件按需懒加载（code splitting）。
 * 每个页面都是独立 chunk，只有访问对应路由时才会下载，降低首屏体积。
 */
const HomePage = lazy(() => import('./pages/HomePage'));
const BacktestPage = lazy(() => import('./pages/BacktestPage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));
const LoginPage = lazy(() => import('./pages/LoginPage'));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'));
const ChatPage = lazy(() => import('./pages/ChatPage'));
const PortfolioPage = lazy(() => import('./pages/PortfolioPage'));
const DecisionSignalsPage = lazy(() => import('./pages/DecisionSignalsPage'));
const AlertsPage = lazy(() => import('./pages/AlertsPage'));
const TokenUsagePage = lazy(() => import('./pages/TokenUsagePage'));
const StockScreeningPage = lazy(() => import('./pages/StockScreeningPage'));
const SectorAnalysisPage = lazy(() => import('./pages/SectorAnalysisPage'));
const StockKLinePage = lazy(() => import('./pages/StockKLinePage'));

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
          <ApiErrorAlert error={loadError} />
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
      return (
        <StandaloneRouteBoundary>
          <LoginPage />
        </StandaloneRouteBoundary>
      );
    }
    const redirect = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?redirect=${redirect}`} replace />;
  }

  // 已登录状态下访问 /login：直接回到首页，避免登录页悬挂
  if (location.pathname === '/login') {
    return <Navigate to="/" replace />;
  }

  // 正常渲染壳布局 + 子路由出口
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
        {/* 首页：分析任务入口与历史记录 */}
        <Route path="/" element={<HomePage />} />
        {/* 板块分析 */}
        <Route path="/sector-analysis" element={<SectorAnalysisPage />} />
        {/* K 线行情 */}
        <Route path="/kline" element={<StockKLinePage />} />
        {/* AI 对话分析 */}
        <Route path="/chat" element={<ChatPage />} />
        {/* 持仓分析 */}
        <Route path="/portfolio" element={<PortfolioPage />} />
        {/* 决策信号 */}
        <Route path="/decision-signals" element={<DecisionSignalsPage />} />
        {/* 股票筛选 */}
        <Route path="/screening" element={<StockScreeningPage />} />
        {/* 回测 */}
        <Route path="/backtest" element={<BacktestPage />} />
        {/* 价格预警 */}
        <Route path="/alerts" element={<AlertsPage />} />
        {/* Token 用量 */}
        <Route path="/usage" element={<TokenUsagePage />} />
        {/* 系统设置 */}
        <Route path="/settings" element={<SettingsPage />} />
        {/* 兜底：未匹配任何路由时展示 404 */}
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
};

/**
 * 应用最外层组件：装配全局 Provider 并形成渲染树。
 * Provider 顺序（由外到内）：
 *   UiLanguageProvider → Router → AuthProvider → PageStateProvider → AppContent
 */
const App: React.FC = () => {
  return (
    <UiLanguageProvider>
      <Router>
        <AuthProvider>
          <PageStateProvider>
            <AppContent />
          </PageStateProvider>
        </AuthProvider>
      </Router>
    </UiLanguageProvider>
  );
};

export default App;
