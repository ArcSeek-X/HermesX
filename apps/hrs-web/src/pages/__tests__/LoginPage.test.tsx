// 测试库：render 渲染组件、screen 查询 DOM、fireEvent 模拟交互、waitFor 等待异步更新
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
// 测试框架：beforeEach 每个用例前重置、describe 用例分组、it 单个用例、vi 做 mock、expect 断言
import { beforeEach, describe, expect, it, vi } from 'vitest';
// 被测页面组件
import LoginPage from '../LoginPage/LoginPage';

// 用 vi.hoisted 在模块 mock 之前创建可被外部引用的共享 mock 函数。
// 把 navigate / useSearchParams 的返回值、useAuth 的返回值都做成可注入的 mock，
// 这样在用例里可以精确控制路由跳转、查询参数和登录逻辑的行为。
const { navigate, useSearchParamsMock, useAuthMock } = vi.hoisted(() => ({
  navigate: vi.fn(),          // 替代 useNavigate 的返回函数，用于断言跳转目标
  useSearchParamsMock: vi.fn(), // 替代 useSearchParams，用于注入 redirect 参数
  useAuthMock: vi.fn(),       // 替代 useAuth，用于注入登录态与 setupState
}));

// mock 自定义 hooks：把 useAuth 替换为调用 useAuthMock，便于在用例里返回不同登录态
vi.mock('../../hooks', () => ({
  useAuth: () => useAuthMock(),
}));

// mock react-router-dom：保留真实实现，只把 useNavigate / useSearchParams 换成可控 mock，
// 既保证 Link、Routes 等路由能力可用，又能断言 navigate 的调用参数、注入 search params
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => navigate,
    useSearchParams: () => useSearchParamsMock(),
  };
});

describe('LoginPage', () => {
  // 每个用例执行前：清空所有 mock 调用记录、固定浅色主题、预设 redirect=/settings 查询参数
  beforeEach(() => {
    vi.clearAllMocks();
    document.documentElement.className = 'light';
    useSearchParamsMock.mockReturnValue([new URLSearchParams('redirect=%2Fsettings')]);
  });

  // 用例 1：首次设置场景下，两次密码不一致时应拦截提交并提示错误，且不应调用登录
  it('blocks first-time setup when confirmation does not match', async () => {
    const login = vi.fn();
    // 模拟「尚未设置密码」的首次设置态，login 用于断言是否被调用
    useAuthMock.mockReturnValue({
      login,
      passwordSet: false,
      setupState: 'no_password',
    });

    render(<LoginPage />);

    // 在两个密码框填入不一致的值，并点击「完成设置并登录」
    fireEvent.change(screen.getByLabelText('管理员密码'), { target: { value: 'passwd6' } });
    fireEvent.change(screen.getByLabelText('确认密码'), { target: { value: 'passwd7' } });
    fireEvent.click(screen.getByRole('button', { name: '完成设置并登录' }));

    // 断言：出现「两次输入的密码不一致」提示；login 未被调用（提交被拦截）
    expect(await screen.findByText('两次输入的密码不一致')).toBeInTheDocument();
    expect(login).not.toHaveBeenCalled();
    // 断言：两个密码框的错误态样式（data-appearance=login）被应用
    expect(screen.getByLabelText('管理员密码')).toHaveAttribute('data-appearance', 'login');
    expect(screen.getByLabelText('确认密码')).toHaveAttribute('data-appearance', 'login');
  });

  // 用例 2：已设置密码且登录成功时，应跳转到 redirect 指向的页面（/settings）
  it('navigates to redirect after a successful login', async () => {
    // 模拟「已启用、已设置密码」的登录态，login 返回成功
    useAuthMock.mockReturnValue({
      login: vi.fn().mockResolvedValue({ success: true }),
      passwordSet: true,
      setupState: 'enabled',
    });

    render(<LoginPage />);

    // 填入登录密码并点击「授权进入工作台」
    fireEvent.change(screen.getByLabelText('登录密码'), { target: { value: 'passwd6' } });
    fireEvent.click(screen.getByRole('button', { name: '授权进入工作台' }));

    // 断言：navigate 以 replace 方式跳转到 /settings
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/settings', { replace: true }));
    // 断言：登录密码框处于正常（login）外观态，未报错
    expect(screen.getByLabelText('登录密码')).toHaveAttribute('data-appearance', 'login');
  });

  // 用例 3：登录页不应在根节点内联覆盖主题 CSS 变量，否则会破坏浅色模式
  it('does not override login theme tokens inline so light mode can take effect', () => {
    useAuthMock.mockReturnValue({
      login: vi.fn(),
      passwordSet: true,
      setupState: 'enabled',
    });

    const { container } = render(<LoginPage />);
    // 取页面根节点
    const pageRoot = container.firstElementChild as HTMLElement | null;

    // 断言：根节点存在，且内联 style 中不包含登录背景色变量（确保浅色模式可生效）
    expect(pageRoot).not.toBeNull();
    expect(pageRoot?.getAttribute('style') ?? '').not.toContain('--login-bg-main');
  });
});
