/**
 * @file AuthStore.test.ts
 * @description AuthStore 单元测试：覆盖 bootstrap / login / logout / changePassword 的成功与失败路径。
 *   鉴权 API 与 stockPoolStore 均 mock，仅验证状态机的收敛与副作用（resetDashboardState）。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAuthStore } from '../AuthStore';

const mocks = vi.hoisted(() => ({
  getStatus: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
  changePassword: vi.fn(),
  resetDashboardState: vi.fn(),
}));

vi.mock('../../api/auth', () => ({
  authApi: {
    getStatus: mocks.getStatus,
    login: mocks.login,
    logout: mocks.logout,
    changePassword: mocks.changePassword,
  },
}));

// 复用真实错误解析（含 429 文案），仅屏蔽其调试 console.log
vi.mock('../../api/error', async (importOriginal) => ({ ...(await importOriginal()) }));

vi.mock('../stockPoolStore', () => ({
  useStockPoolStore: { getState: () => ({ resetDashboardState: mocks.resetDashboardState }) },
}));

const resetStore = (): void => {
  useAuthStore.setState({
    authEnabled: false,
    loggedIn: false,
    passwordSet: false,
    passwordChangeable: false,
    setupState: 'no_password',
    isLoading: true,
    loadError: null,
  });
};

beforeEach(() => {
  vi.spyOn(console, 'log').mockImplementation(() => undefined);
  mocks.getStatus.mockReset();
  mocks.login.mockReset();
  mocks.logout.mockReset();
  mocks.changePassword.mockReset();
  mocks.resetDashboardState.mockReset();
  resetStore();
});

describe('AuthStore bootstrap', () => {
  it('成功拉取状态：写入鉴权态并解除 loading', async () => {
    mocks.getStatus.mockResolvedValue({
      authEnabled: true,
      loggedIn: false,
      passwordSet: true,
      passwordChangeable: true,
      setupState: 'enabled',
    });
    await useAuthStore.getState().bootstrap();
    const s = useAuthStore.getState();
    expect(s.authEnabled).toBe(true);
    expect(s.loggedIn).toBe(false);
    expect(s.isLoading).toBe(false);
    expect(s.loadError).toBeNull();
    // 开启鉴权且未登录：应清空仪表盘敏感数据（登录态就绪前的防御）
    expect(mocks.resetDashboardState).toHaveBeenCalled();
  });

  it('拉取失败：复位默认态且置 loadError，并清空仪表盘敏感数据', async () => {
    mocks.getStatus.mockRejectedValue(new Error('network down'));
    await useAuthStore.getState().bootstrap();
    const s = useAuthStore.getState();
    expect(s.authEnabled).toBe(false);
    expect(s.loggedIn).toBe(false);
    expect(s.isLoading).toBe(false);
    expect(s.loadError).not.toBeNull();
    expect(mocks.resetDashboardState).toHaveBeenCalled();
  });
});

describe('AuthStore login', () => {
  it('登录成功：调用接口、刷新状态（loggedIn=true），返回 success', async () => {
    mocks.login.mockResolvedValue(undefined);
    mocks.getStatus.mockResolvedValue({
      authEnabled: true,
      loggedIn: true,
      passwordSet: true,
      passwordChangeable: true,
      setupState: 'enabled',
    });
    const res = await useAuthStore.getState().login('secret');
    expect(res.success).toBe(true);
    expect(mocks.login).toHaveBeenCalledWith('secret');
    expect(useAuthStore.getState().loggedIn).toBe(true);
  });

  it('登录失败（429）：返回 success=false 且文案为「登录过于频繁」', async () => {
    mocks.login.mockRejectedValue({ response: { status: 429 } });
    const res = await useAuthStore.getState().login('secret');
    expect(res.success).toBe(false);
    expect(res.error?.title).toBe('登录尝试过于频繁');
  });

  it('登录失败（其他错误）：返回 success=false 且携带解析后的错误', async () => {
    mocks.login.mockRejectedValue({ response: { status: 500, data: { detail: 'boom' } } });
    const res = await useAuthStore.getState().login('secret');
    expect(res.success).toBe(false);
    expect(res.error).not.toBeNull();
  });
});

describe('AuthStore logout', () => {
  it('登出成功：调用接口并刷新状态（loggedIn=false）', async () => {
    mocks.logout.mockResolvedValue(undefined);
    mocks.getStatus.mockResolvedValue({
      authEnabled: true,
      loggedIn: false,
      passwordSet: true,
      passwordChangeable: true,
      setupState: 'enabled',
    });
    await useAuthStore.getState().logout();
    expect(mocks.logout).toHaveBeenCalled();
    expect(useAuthStore.getState().loggedIn).toBe(false);
  });
});

describe('AuthStore changePassword', () => {
  it('改密成功：返回 success=true', async () => {
    mocks.changePassword.mockResolvedValue(undefined);
    const res = await useAuthStore.getState().changePassword('old', 'new', 'new');
    expect(res.success).toBe(true);
  });

  it('改密失败：返回 success=false', async () => {
    mocks.changePassword.mockRejectedValue({ response: { status: 400, data: { detail: 'no' } } });
    const res = await useAuthStore.getState().changePassword('old', 'new', 'new');
    expect(res.success).toBe(false);
  });
});
