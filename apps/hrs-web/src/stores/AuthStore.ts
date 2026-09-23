/**
 * @file AuthStore.ts
 * @description 鉴权状态 Store（Zustand）。作为全局鉴权唯一真源，替代原 AuthContext，
 *   使鉴权状态可在 React Router 的 loader（运行于 React 之外）经 getState() 读取，
 *   支撑数据路由的 loader 守卫（protectedLoader）。
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-09-20
 */
import { create } from 'zustand';
import { authApi } from '../api/auth';
import { useStockPoolStore } from './stockPoolStore';
import {
  createParsedApiError,
  getParsedApiError,
  type ParsedApiError,
} from '../api/error';

/** 初始设置状态：enabled=已启用 | password_retained=密码已保留 | no_password=未设置密码 */
type SetupState = 'enabled' | 'password_retained' | 'no_password';

/** 鉴权状态切片 */
interface AuthState {
  /** 是否启用了管理员认证 */
  authEnabled: boolean;
  /** 当前是否已登录 */
  loggedIn: boolean;
  /** 是否已设置管理员密码 */
  passwordSet: boolean;
  /** 是否可以修改密码 */
  passwordChangeable: boolean;
  /** 初始设置状态 */
  setupState: SetupState;
  /** 状态是否正在加载（仅阻塞式 bootstrap 前为 true） */
  isLoading: boolean;
  /** 加载错误信息 */
  loadError: ParsedApiError | null;
  /** 拉取后端认证状态（首次启动与每次登录/登出后调用） */
  bootstrap: () => Promise<void>;
  /** 登录方法 */
  login: (password: string) => Promise<{ success: boolean; error?: ParsedApiError }>;
  /** 修改密码方法 */
  changePassword: (
    currentPassword: string,
    newPassword: string,
    newPasswordConfirm: string,
  ) => Promise<{ success: boolean; error?: ParsedApiError }>;
  /** 登出方法 */
  logout: () => Promise<void>;
  /** 刷新认证状态（同 bootstrap，供组件主动刷新） */
  refreshStatus: () => Promise<void>;
}

/** 从登录错误中提取用户友好的错误信息，对 429 做特殊处理 */
const extractLoginError = (err: unknown): ParsedApiError => {
  const parsed = getParsedApiError(err);
  if (parsed.status === 429) {
    return createParsedApiError({
      title: '登录尝试过于频繁',
      message: '尝试次数过多，请稍后再试。',
      rawMessage: parsed.rawMessage,
      status: parsed.status,
      category: parsed.category,
    });
  }
  return parsed;
};

/** 拉取失败：复位全部状态为默认，并清空仪表盘敏感数据 */
const resetToDefault = (set: (partial: Partial<AuthState>) => void): void => {
  set({
    authEnabled: false,
    loggedIn: false,
    passwordSet: false,
    passwordChangeable: false,
    setupState: 'no_password',
    isLoading: false,
    loadError: null,
  });
  useStockPoolStore.getState().resetDashboardState();
};

export const useAuthStore = create<AuthState>((set, get) => ({
  authEnabled: false,
  loggedIn: false,
  passwordSet: false,
  passwordChangeable: false,
  setupState: 'no_password',
  isLoading: true,
  loadError: null,

  bootstrap: async () => {

    try {
      const status = await authApi.getStatus();
      set({
        authEnabled: status.authEnabled,
        loggedIn: status.loggedIn,
        passwordSet: status.passwordSet ?? false,
        passwordChangeable: status.passwordChangeable ?? false,
        setupState: status.setupState,
        isLoading: false,
        loadError: null,
      });
      // 认证已启用但未登录：重置仪表盘数据，避免泄露上次登录的敏感信息
      if (status.authEnabled && !status.loggedIn) {
        useStockPoolStore.getState().resetDashboardState();
      }
    } catch (err) {
      resetToDefault(set);
      set({ loadError: getParsedApiError(err) });
    }
  },

  login: async (password) => {
    try {
      await authApi.login(password);
      await get().bootstrap();
      return { success: true };
    } catch (err) {
      return { success: false, error: extractLoginError(err) };
    }
  },

  changePassword: async (currentPassword, newPassword, newPasswordConfirm) => {
    try {
      await authApi.changePassword(currentPassword, newPassword, newPasswordConfirm);
      return { success: true };
    } catch (err) {
      return { success: false, error: getParsedApiError(err) };
    }
  },

  logout: async () => {
    let logoutError: unknown = null;
    try {
      await authApi.logout();
    } catch (err) {
      logoutError = err;
    } finally {
      await get().bootstrap();
    }
    // 非 401 错误向上抛出（401 表示已登出，无需处理）
    if (logoutError && getParsedApiError(logoutError).status !== 401) {
      throw logoutError;
    }
  },

  refreshStatus: () => get().bootstrap(),
}));
