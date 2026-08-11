/**
 * App 组件路由行为测试。
 *
 * 测试目标：在不依赖真实页面实现的前提下，验证 App 的鉴权拦截与路由渲染逻辑。
 * 手段：用 vi.mock 把各页面、AuthContext、agentChatStore 替换为轻量占位组件/函数，
 *       通过切换 useAuth 的返回值来驱动不同分支。
 */
import { fireEvent, render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import * as AuthContext from './contexts/AuthContext';
import { UI_LANGUAGE_STORAGE_KEY } from './utils/uiLanguage';

// 从 useAuth 推断鉴权状态类型，便于后续构造 mock 状态
type AuthState = ReturnType<typeof AuthContext.useAuth>;

/**
 * vi.hoisted：在模块加载（vi.mock）发生前就创建可被 mock 工厂引用的共享变量/桩函数。
 * 这里集中声明：
 * - setCurrentRoute：记录 App 调用 store.setCurrentRoute 的路径
 * - chatPageShouldThrow：受控开关，让 ChatPage 在测试中按需抛出，模拟页面加载失败
 * - useAgentChatStoreMock：store 的替身，默认返回固定 state，getState 暴露 setCurrentRoute
 */
const { chatPageShouldThrow, setCurrentRoute, useAgentChatStoreMock } = vi.hoisted(() => {
  const setCurrentRoute = vi.fn();
  const chatPageShouldThrow = { value: false };
  const state = { completionBadge: false };
  const useAgentChatStoreMock = Object.assign(
    vi.fn((selector?: (value: typeof state) => unknown) => (selector ? selector(state) : state)),
    { getState: () => ({ setCurrentRoute }) },
  );
  return { chatPageShouldThrow, setCurrentRoute, useAgentChatStoreMock };
});

// 用透传 children 的桩替换 AuthProvider；useAuth 由用例在 beforeEach 中动态 mock
vi.mock('./contexts/AuthContext', () => ({
  AuthProvider: ({ children }: { children: ReactNode }) => children,
  useAuth: vi.fn(),
}));

// 用上面 hoisted 的替身替换 agentChatStore
vi.mock('./stores/agentChatStore', () => ({
  useAgentChatStore: useAgentChatStoreMock,
}));

// 以下各页面均替换为带 data-testid 的占位组件，仅用于断言「某路由是否渲染了对应页面」

vi.mock('./pages/HomePage', () => ({
  default: () => <div data-testid="home-page">Home</div>,
}));

vi.mock('./pages/ChatPage', () => ({
  default: () => {
    // 受控抛错，用于验证错误边界（RouteOutletBoundary）的兜底 UI
    if (chatPageShouldThrow.value) {
      throw new Error('chunk load failed');
    }
    return <div data-testid="chat-page">Chat</div>;
  },
}));

vi.mock('./pages/PortfolioPage', () => ({
  default: () => <div data-testid="portfolio-page">Portfolio</div>,
}));

vi.mock('./pages/DecisionSignalsPage', () => ({
  default: () => <div data-testid="decision-signals-page">Decision signals</div>,
}));

vi.mock('./pages/BacktestPage', () => ({
  default: () => <div data-testid="backtest-page">Backtest</div>,
}));

vi.mock('./pages/AlertsPage', () => ({
  default: () => <div data-testid="alerts-page">Alerts</div>,
}));

vi.mock('./pages/TokenUsagePage', () => ({
  default: () => <div data-testid="token-usage-page">Usage</div>,
}));

vi.mock('./pages/SettingsPage', () => ({
  default: () => <div data-testid="settings-page">Settings</div>,
}));

vi.mock('./pages/NotFoundPage', () => ({
  default: () => <div data-testid="not-found-page">Not Found</div>,
}));

// 注意：mock 路径必须与 App.tsx 中 lazy import 的模块路径一致（./pages/LoginPage/LoginPage），
// 否则 mock 不生效，会渲染真实登录页导致测试找不到占位 testid
vi.mock('./pages/LoginPage/LoginPage', () => ({
  default: () => <div data-testid="login-page">Login</div>,
}));

/**
 * 构造一份默认鉴权状态，所有方法均为可追踪的 vi.fn 桩。
 * overrides 允许单个用例按需覆盖其中某些字段（如 isLoading / loggedIn）。
 */
function makeAuthState(overrides: Partial<AuthState> = {}): AuthState {
  return {
    authEnabled: false,
    loggedIn: false,
    passwordSet: false,
    passwordChangeable: false,
    setupState: 'no_password',
    isLoading: false,
    loadError: null,
    login: vi.fn().mockResolvedValue({ success: true }),
    changePassword: vi.fn().mockResolvedValue({ success: true }),
    logout: vi.fn().mockResolvedValue(undefined),
    refreshStatus: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

// 每个用例前：清空 mock 调用记录、复位受控开关、重置 URL 与语言，并恢复默认鉴权状态
beforeEach(() => {
  vi.clearAllMocks();
  chatPageShouldThrow.value = false;
  window.history.pushState({}, '', '/');
  localStorage.setItem(UI_LANGUAGE_STORAGE_KEY, 'zh');
  vi.mocked(AuthContext.useAuth).mockReturnValue(makeAuthState());
});

describe('App routing behavior', () => {
  // 鉴权初始化中：应展示加载占位（带 .border-t-cyan 样式）
  it('shows loading fallback while auth status is initializing', () => {
    vi.mocked(AuthContext.useAuth).mockReturnValue(makeAuthState({ isLoading: true }));

    const { container } = render(<App />);

    expect(container.querySelector('.border-t-cyan')).toBeInTheDocument();
  });

  // 开启鉴权但未登录 + 访问受保护路由：应重定向到 /login?redirect=<编码后的目标路径>
  it('redirects protected routes to login when auth is enabled but user is not logged in', async () => {
    vi.mocked(AuthContext.useAuth).mockReturnValue(makeAuthState({
      authEnabled: true,
      loggedIn: false,
      setupState: 'enabled',
    }));
    window.history.pushState({}, '', '/portfolio');

    render(<App />);

    expect(await screen.findByTestId('login-page')).toBeInTheDocument();
    expect(window.location.pathname).toBe('/login');
    expect(window.location.search).toBe('?redirect=%2Fportfolio');
  });

  // 鉴权就绪后访问 /chat：应渲染 ChatPage，且把当前路由同步给 store，同时不应渲染其它页面
  it('renders the current route page after auth is ready', async () => {
    window.history.pushState({}, '', '/chat');

    render(<App />);

    expect(await screen.findByTestId('chat-page')).toBeInTheDocument();
    expect(setCurrentRoute).toHaveBeenCalledWith('/chat');
    expect(screen.queryByTestId('login-page')).not.toBeInTheDocument();
    expect(screen.queryByTestId('home-page')).not.toBeInTheDocument();
  });

  // 鉴权就绪后访问 /usage：应渲染 TokenUsagePage
  it('routes /usage to the token usage page after auth is ready', async () => {
    window.history.pushState({}, '', '/usage');

    render(<App />);

    expect(await screen.findByTestId('token-usage-page')).toBeInTheDocument();
    expect(setCurrentRoute).toHaveBeenCalledWith('/usage');
    expect(screen.queryByTestId('home-page')).not.toBeInTheDocument();
  });

  // 鉴权就绪后访问 /decision-signals：应渲染决策信号页
  it('routes /decision-signals to the AI signals page after auth is ready', async () => {
    window.history.pushState({}, '', '/decision-signals');

    render(<App />);

    expect(await screen.findByTestId('decision-signals-page')).toBeInTheDocument();
    expect(setCurrentRoute).toHaveBeenCalledWith('/decision-signals');
    expect(screen.queryByTestId('home-page')).not.toBeInTheDocument();
  });

  // 已登录访问 /login：应被重定向回首页（不应停留登录页）
  it('redirects authenticated login visits back to the home page', async () => {
    vi.mocked(AuthContext.useAuth).mockReturnValue(makeAuthState({
      authEnabled: true,
      loggedIn: true,
      setupState: 'enabled',
    }));
    window.history.pushState({}, '', '/login');

    render(<App />);

    expect(await screen.findByTestId('home-page')).toBeInTheDocument();
    expect(screen.queryByTestId('login-page')).not.toBeInTheDocument();
  });

  // 页面渲染抛错：错误边界应展示「页面加载失败」提示与导航壳，
  // 点击重新加载/返回首页后可恢复并渲染正确页面（壳布局始终挂载）
  it('keeps the shell mounted and resets the route boundary after page render errors', async () => {
    // 抑制 React 错误边界打印到控制台的报错噪声
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    chatPageShouldThrow.value = true;
    window.history.pushState({}, '', '/chat');

    try {
      render(<App />);

      // 错误边界 UI：标题 + 导航栏 + 重新加载/返回首页按钮都应存在
      expect(await screen.findByRole('heading', { name: '页面加载失败' })).toBeInTheDocument();
      expect(screen.getByRole('navigation', { name: '主导航' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '重新加载页面' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '返回首页' })).toBeInTheDocument();

      // 关闭抛错开关后，点击「持仓」链接应能正常渲染持仓页，且错误提示消失
      chatPageShouldThrow.value = false;
      fireEvent.click(screen.getByRole('link', { name: '持仓' }));

      expect(await screen.findByTestId('portfolio-page')).toBeInTheDocument();
      expect(screen.queryByRole('heading', { name: '页面加载失败' })).not.toBeInTheDocument();
    } finally {
      consoleError.mockRestore();
    }
  });
});
