/**
 * @file RouteBoundary.tsx
 * @description 路由边界：统一的错误捕获与异步加载兜底。
 *  - RouteErrorBoundaryInner：React ErrorBoundary，捕获子组件「渲染期」异常。
 *  - RouteBoundary：组合 ErrorBoundary + Suspense，供布局包裹子路由。
 *  - RouteOutletBoundary：嵌套路由（<Outlet />）专用，非全屏。
 *  - RouteErrorBoundary：数据路由 errorElement，读取 useRouteError 处理 loader / lazy 失败。
 *  - PageLoadingFallback：Suspense 加载占位 spinner。
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-09-20
 */
import type React from 'react';
import { Component, Suspense, useState } from 'react';
import type { ErrorInfo } from 'react';
import { Outlet, useLocation, useRouteError, isRouteErrorResponse } from 'react-router-dom';
import { Check, ChevronDown, ChevronUp, Copy } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { Modal, HrsButton, ThemeToggle, LanguageSwitch } from '../../components';

/** 异步加载占位：居中 spinner；fullPage 时占满视口，否则占 60vh。 */
type PageLoadingFallbackProps = { fullPage?: boolean };

export const PageLoadingFallback: React.FC<PageLoadingFallbackProps> = ({ fullPage = true }) => (
  <div className={fullPage ? 'flex min-h-screen items-center justify-center bg-base' : 'flex min-h-[60vh] items-center justify-center'}>
    <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary/20 border-t-cyan" />
  </div>
);

type ErrorModalProps = {
  isOpen: boolean;
  title: string;
  description: string;
  /** 返回按钮文案（首页 / 登录 等） */
  backLabel: string;
  onBack: () => void;
  /** 错误详情（如异常 message），有值时显示「查看详情」开关 */
  detail?: string;
};

/** 错误 Modal 骨架：标题 + 描述 + 详情开关 + 重新加载/返回 + 主题与语言切换。两处错误路径共用。 */
const ErrorModal: React.FC<ErrorModalProps> = ({ isOpen, title, description, backLabel, onBack, detail }) => {
  const { t } = useUiLanguage();
  const [showDetail, setShowDetail] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!detail) return;
    navigator.clipboard?.writeText(detail).then(() => {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    });
  };

  return (
    <Modal isOpen={isOpen} isDismissable={false} variant="blur" hideCloseButton size="md" footerClassName="justify-center">
      <Modal.Header>
        <Modal.Heading>{title}</Modal.Heading>
      </Modal.Header>
      <Modal.Body>
        <p className="text-sm leading-6 text-secondary-text">{description}</p>
        {detail && (
          <span
            role="button"
            tabIndex={0}
            onClick={() => setShowDetail((prev) => !prev)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setShowDetail((prev) => !prev);
              }
            }}
            className="text-xs mt-4 gap-1 inline-flex cursor-pointer items-center text-primary hover:text-primary/80"
          >
            {
              showDetail ?
                (<>{t('routeError.hideDetails')}<ChevronUp className="h-4 w-4"/></>) :
                (<>{t('routeError.details')}<ChevronDown className="h-4 w-4"/></>)
            }
          </span>
        )}
        <AnimatePresence initial={false}>
          {showDetail && detail && (
            <motion.div
              key="error-detail"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.25, ease: 'easeOut' }}
              className="overflow-hidden"
            >
              <div className="mt-2 overflow-hidden rounded-md border border-dim bg-muted">
                <div className="flex items-center justify-between border-b border-dim px-3 py-1.5">
                  <span className="text-[11px] font-medium uppercase tracking-wide text-foreground-soft">
                    {t('routeError.errorDetail')}
                  </span>
                  <HrsButton
                    variant="ghost"
                    size="xs"
                    onClick={handleCopy}
                    className="text-primary hover:text-primary/80"
                  >
                    {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                    {copied ? t('routeError.copied') : t('routeError.copy')}
                  </HrsButton>
                </div>
                <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-words px-3 py-2 text-xs leading-6 text-foreground-soft">
                  {detail}
                </pre>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </Modal.Body>
      <Modal.Footer>
        <HrsButton variant="primary" size="md" onClick={() => window.location.reload()}>
          {t('routeError.reload')}
        </HrsButton>
        <HrsButton variant="secondary" size="md" onClick={onBack}>
          {backLabel}
        </HrsButton>
      </Modal.Footer>
      <Modal.Freedom>
        <div className="absolute top-4 right-4 z-[99] flex items-center gap-2 rounded-md bg-card px-2 py-1.5 shadow-sm backdrop-blur">
          <ThemeToggle />
          <LanguageSwitch />
        </div>
      </Modal.Freedom>
    </Modal>
  );
};

type RouteErrorBoundaryProps = {
  children: React.ReactNode;
  /** 路由变化（path + search）时自动重置错误态 */
  resetKey: string;
  text: {
    title: string;
    description: string;
    backHome: string;
  };
};

type RouteErrorBoundaryState = { hasError: boolean; errorMessage?: string };

/** React 错误边界：捕获子组件渲染期异常，展示错误 Modal（重新加载 / 返回首页）。 */
class RouteErrorBoundaryInner extends Component<RouteErrorBoundaryProps, RouteErrorBoundaryState> {
  override state: RouteErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): RouteErrorBoundaryState {
    return { hasError: true };
  }

  override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Route page failed to render or load', error, errorInfo);
    this.setState({ errorMessage: error.message });
  }

  // 路由切换时自动重置错误态，使新路由重新尝试渲染
  override componentDidUpdate(prevProps: RouteErrorBoundaryProps) {
    if (this.state.hasError && prevProps.resetKey !== this.props.resetKey) {
      this.setState({ hasError: false, errorMessage: undefined });
    }
  }

  override render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <ErrorModal
        isOpen
        title={this.props.text.title}
        description={this.props.text.description}
        backLabel={this.props.text.backHome}
        detail={this.state.errorMessage}
        onBack={() => window.location.assign('/')}
      />
    );
  }
}

/** 边界核心：ErrorBoundary + Suspense 组合，用于包裹子路由 / 内容。 */
export const RouteBoundary: React.FC<{ children: React.ReactNode; fullPage?: boolean }> = ({
  children,
  fullPage = true,
}) => {
  const location = useLocation();
  const { t } = useUiLanguage();
  const resetKey = `${location.pathname}${location.search}`;

  return (
    <RouteErrorBoundaryInner
      resetKey={resetKey}
      text={{
        title: t('routeError.title'),
        description: t('routeError.description'),
        backHome: t('routeError.backHome'),
      }}
    >
      <Suspense fallback={<PageLoadingFallback fullPage={fullPage} />}>{children}</Suspense>
    </RouteErrorBoundaryInner>
  );
};

/**
 * 嵌套路由边界：包裹 <Outlet />，非全屏。
 * 使用处：布局组件 Shell（src/components/layout/Shell.tsx）在渲染匹配子路由时使用 —— {children ?? <RouteOutletBoundary />}；
 * 单测见 components/layout/__tests__/RouteBoundary.test.tsx。
 */
export const RouteOutletBoundary: React.FC = () => (
  <RouteBoundary fullPage={false}>
    <Outlet />
  </RouteBoundary>
);

/**
 * 数据路由 errorElement：读取 useRouteError，处理 loader 抛错 / lazy 加载失败。
 * 与 RouteOutletBoundary（渲染期错误）分工。
 * 使用处：src/router/appRouter.tsx 中作为多个路由的 errorElement（如首页重定向、/login、/home 等，见第 43/49/60 行）；
 */
export const RouteErrorBoundary: React.FC = () => {
  const error = useRouteError();
  const { t } = useUiLanguage();
  const isRouteError = isRouteErrorResponse(error);
  const detail = isRouteError
    ? `${error.status} ${error.statusText}`
    : error instanceof Error
      ? error.message
      : '';

  return (
    <ErrorModal
      isOpen
      title={t('routeError.title')}
      description={t('routeError.description')}
      backLabel={t('routeError.backToLogin')}
      detail={detail}
      onBack={() => window.location.assign('/login')}
    />
  );
};
