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

  // 用例 1：登录成功时，应跳转到 redirect 指向的页面（/settings）
  it('navigates to redirect after a successful login', async () => {
    // 模拟登录态：login 返回成功
    useAuthMock.mockReturnValue({
      login: vi.fn().mockResolvedValue({ success: true }),
    });

    render(<LoginPage />);

    // 填入账号与登录密码，并点击「授权进入工作台」
    fireEvent.change(screen.getByLabelText('账号'), { target: { value: 'admin' } });
    fireEvent.change(screen.getByLabelText('登录密码'), { target: { value: 'passwd6' } });
    fireEvent.click(screen.getByRole('button', { name: '授权进入工作台' }));

    // 断言：navigate 以 replace 方式跳转到 /settings
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/settings', { replace: true }));
    // 断言：登录密码框未处于错误态
    expect(screen.getByLabelText('登录密码')).not.toHaveAttribute('aria-invalid');
  });

  // 用例 2：账号为空时提交，应展示必填校验错误且不发起登录
  it('shows a validation error and does not login when account is empty', async () => {
    // 模拟登录态：login 为 spy，用于断言未被调用
    const loginSpy = vi.fn().mockResolvedValue({ success: true });
    useAuthMock.mockReturnValue({ login: loginSpy });

    render(<LoginPage />);

    // 只填密码、留空账号，点击「授权进入工作台」
    fireEvent.change(screen.getByLabelText('登录密码'), { target: { value: 'passwd6' } });
    fireEvent.click(screen.getByRole('button', { name: '授权进入工作台' }));

    // 断言：展示账号必填提示，且 login 未被调用
    expect(await screen.findByText('请输入账号')).toBeInTheDocument();
    expect(loginSpy).not.toHaveBeenCalled();
    expect(navigate).not.toHaveBeenCalled();
  });

  // 用例 3：密码为空时提交，应展示必填校验错误且不发起登录
  it('shows a validation error and does not login when password is empty', async () => {
    // 模拟登录态：login 为 spy，用于断言未被调用
    const loginSpy = vi.fn().mockResolvedValue({ success: true });
    useAuthMock.mockReturnValue({ login: loginSpy });

    render(<LoginPage />);

    // 只填账号、留空密码，点击「授权进入工作台」
    fireEvent.change(screen.getByLabelText('账号'), { target: { value: 'admin' } });
    fireEvent.click(screen.getByRole('button', { name: '授权进入工作台' }));

    // 断言：展示密码必填提示，且 login 未被调用
    expect(await screen.findByText('请输入密码')).toBeInTheDocument();
    expect(loginSpy).not.toHaveBeenCalled();
    expect(navigate).not.toHaveBeenCalled();
  });

  // 用例 4：登录页不应在根节点内联覆盖主题 CSS 变量，否则会破坏浅色模式
  it('does not override login theme tokens inline so light mode can take effect', () => {
    useAuthMock.mockReturnValue({
      login: vi.fn(),
    });

    const { container } = render(<LoginPage />);
    // 取页面根节点
    const pageRoot = container.firstElementChild as HTMLElement | null;

    // 断言：根节点存在，且内联 style 中不包含登录背景色变量（确保浅色模式可生效）
    expect(pageRoot).not.toBeNull();
    expect(pageRoot?.getAttribute('style') ?? '').not.toContain('--login-bg-main');
  });
});
