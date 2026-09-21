/**
 * 路由边界组件
 *
 * 为路由页面提供两层保护：
 * 1. ErrorBoundary：捕获子组件渲染或加载时的异常，展示友好的错误页面，支持「重新加载」和「返回首页」
 * 2. Suspense：在异步组件（lazy import）加载期间展示 loading spinner
 *
 * 导出组件：
 * - PageLoadingFallback：页面加载中的 spinner 占位符
 * - RouteBoundary：核心边界组件，组合 ErrorBoundary + Suspense
 * - RouteOutletBoundary：用于嵌套路由（<Outlet />），非全屏模式
 * - StandaloneRouteBoundary：独立全屏边界，用于包裹非路由内容（如登录页）
 *
 * @author Lensgcx (GaoCangxiong)
 */
import type React from 'react';
import { Component, Suspense } from 'react';
import type { ErrorInfo } from 'react';
import { Outlet, useLocation, useRouteError, isRouteErrorResponse } from 'react-router-dom';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { Modal } from '../basic/Modal/Modal';
import { HrsButton } from '../basic/HrsButton/HrsButton';
import { ThemeToggle } from '../theme/ThemeToggle';
import { LanguageSwitch } from './HeaderComponents/LanguageSwitch';

/** 页面加载中占位符：居中展示旋转 spinner，支持全屏 / 区域两种模式 */
type PageLoadingFallbackProps = {
  /** 是否全屏模式（默认 true），false 时高度为 60vh */
  fullPage?: boolean;
};

export const PageLoadingFallback: React.FC<PageLoadingFallbackProps> = ({ fullPage = true }) => (
  <div
    className={
      fullPage
        ? 'flex min-h-screen items-center justify-center bg-base'
        : 'flex min-h-[60vh] items-center justify-center'
    }
  >
    <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan/20 border-t-cyan" />
  </div>
);

/** 路由错误边界的 Props：包含子节点、重置 key、全屏标志、国际化文案 */
type RouteErrorBoundaryProps = {
  children: React.ReactNode;
  /** 路由路径 + 查询参数，路径变化时自动重置错误状态 */
  resetKey: string;
  /** 是否全屏展示错误页 */
  fullPage: boolean;
  /** 错误页国际化文案（标题、描述、重新加载、返回首页） */
  text: {
    title: string;
    description: string;
    reload: string;
    backHome: string;
  };
};

/** 错误边界状态：hasError 标记是否处于错误状态 */
type RouteErrorBoundaryState = {
  hasError: boolean;
};

/**
 * 路由错误边界（Class Component）
 *
 * - 通过 getDerivedStateFromError 捕获子组件渲染异常
 * - 通过 componentDidCatch 将错误输出到控制台
 * - 路由切换（resetKey 变化）时自动重置错误状态，无需手动刷新
 */
class RouteErrorBoundaryInner extends Component<RouteErrorBoundaryProps, RouteErrorBoundaryState> {
  override state: RouteErrorBoundaryState = {
    hasError: false,
  };

  static getDerivedStateFromError(): RouteErrorBoundaryState {
    return { hasError: true };
  }

  override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Route page failed to render or load', error, errorInfo);
  }

  /** 路由变化时自动重置错误状态，让新路由重新尝试渲染 */
  override componentDidUpdate(prevProps: RouteErrorBoundaryProps) {
    if (this.state.hasError && prevProps.resetKey !== this.props.resetKey) {
      this.setState({ hasError: false });
    }
  }

  override render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    // 错误态以模态框呈现：遮罩 + 居中对话框；点遮罩/关闭按钮回首页（路由变化触发错误重置）
    return (
      <Modal isOpen={this.state.hasError} isDismissable={false} variant="blur" hideCloseButton size="md" footerClassName="justify-center">
        <Modal.Header>
          <Modal.Heading>{this.props.text.title}</Modal.Heading>
        </Modal.Header>
        <Modal.Body>
          <p className="text-sm leading-6 text-secondary-text">{this.props.text.description}</p>
        </Modal.Body>
        <Modal.Footer>
          <HrsButton variant="primary" size="md" onClick={() => window.location.reload()}>
            {this.props.text.reload}
          </HrsButton>
          <HrsButton variant="secondary" size="md" onClick={() => window.location.assign('/')}>
            {this.props.text.backHome}
          </HrsButton>
        </Modal.Footer>
        <Modal.Freedom>
          <div className="absolute top-4 right-4 z-99 flex items-center gap-2 rounded-md  bg-card px-2 py-1.5  shadow-sm backdrop-blur">
            <ThemeToggle />
            <LanguageSwitch />
          </div>
        </Modal.Freedom>
      </Modal>
    );
  }
}

/**
 * 路由边界核心组件
 *
 * 组合 ErrorBoundary + Suspense：
 * - 子组件渲染异常 → 展示错误页（重新加载 / 返回首页）
 * - 子组件异步加载中 → 展示 loading spinner
 * - 路由切换时自动重置错误状态
 */
export const RouteBoundary: React.FC<{ children: React.ReactNode; fullPage?: boolean }> = ({
  children,
  fullPage = true,
}) => {
  const location = useLocation();
  const { t } = useUiLanguage();
  // 用路径+查询参数作为 resetKey，路由变化时触发错误边界重置
  const resetKey = `${location.pathname}${location.search}`;

  return (
    <RouteErrorBoundaryInner
      resetKey={resetKey}
      fullPage={fullPage}
      text={{
        title: t('routeError.title'),
        description: t('routeError.description'),
        reload: t('routeError.reload'),
        backHome: t('routeError.backHome'),
      }}
    >
      <Suspense fallback={<PageLoadingFallback fullPage={fullPage} />}>{children}</Suspense>
    </RouteErrorBoundaryInner>
  );
};

/** 嵌套路由边界：非全屏模式，包裹 <Outlet />，用于布局内的子路由区域 */
export const RouteOutletBoundary: React.FC = () => (
  <RouteBoundary fullPage={false}>
    <Outlet />
  </RouteBoundary>
);

/** 独立全屏边界：全屏模式，用于包裹登录页等独立页面 */
export const StandaloneRouteBoundary: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <RouteBoundary fullPage>
    {children}
  </RouteBoundary>
);

/**
 * 轻量路由错误边界（数据路由 errorElement）：读取 useRouteError，展示错误提示并提供重新加载。
 * 用于受保护布局 / 登录路由的 loader 或 lazy 加载失败兜底，与 RouteOutletBoundary（页面渲染错误）分工。
 */
export const RouteErrorBoundary: React.FC = () => {
  const error = useRouteError();

  console.log(error)
  const { t } = useUiLanguage();
  const isRouteError = isRouteErrorResponse(error);
  const detail = isRouteError
    ? `${error.status} ${error.statusText}`
    : error instanceof Error
      ? error.message
      : '';
  return (
    <Modal
      isOpen
      isDismissable={false}
      variant="blur"
      hideCloseButton
      size="md"
      footerClassName="justify-center"
    >
      <Modal.Header>
        <Modal.Heading>{t('routeError.title')}</Modal.Heading>
      </Modal.Header>
      <Modal.Body>
        <p className="text-sm leading-6 text-secondary-text">{t('routeError.description')}</p>
        <p className="text-sm leading-6 text-secondary-text">（{detail}）</p>
      </Modal.Body>
      <Modal.Footer>
        <HrsButton variant="primary" size="md" onClick={() => window.location.reload()}>
          {t('routeError.reload')}
        </HrsButton>
        <HrsButton variant="secondary" size="md" onClick={() => window.location.assign('/login')}>
          {t('routeError.backToLogin')}
        </HrsButton>
      </Modal.Footer>
      <Modal.Freedom>
        <div className="absolute top-4 right-4 z-99 flex items-center gap-2 rounded-md bg-card px-2 py-1.5 shadow-sm backdrop-blur">
          <ThemeToggle />
          <LanguageSwitch />
        </div>
      </Modal.Freedom>
    </Modal>
  );
};


