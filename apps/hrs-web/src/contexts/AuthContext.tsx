/**
 * @file AuthContext.tsx
 * @description 认证上下文，提供全局认证状态管理（登录/登出/修改密码/状态刷新）
 * @module contexts
 */

import type React from 'react';
import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { createParsedApiError, getParsedApiError, type ParsedApiError } from '../api/error';
import { authApi } from '../api/auth';
import { useStockPoolStore } from '../stores';

/**
 * 认证上下文值类型定义
 */
type AuthContextValue = {
  /** 是否启用了管理员认证 */
  authEnabled: boolean;
  /** 当前是否已登录 */
  loggedIn: boolean;
  /** 是否已设置管理员密码 */
  passwordSet: boolean;
  /** 是否可以修改密码 */
  passwordChangeable: boolean;
  /** 初始设置状态：enabled=已启用 | password_retained=密码已保留 | no_password=未设置密码 */
  setupState: 'enabled' | 'password_retained' | 'no_password';
  /** 状态是否正在加载 */
  isLoading: boolean;
  /** 加载错误信息 */
  loadError: ParsedApiError | null;
  /** 登录方法 */
  login: (password: string) => Promise<{ success: boolean; error?: ParsedApiError }>;
  /** 修改密码方法，需提供当前密码和新密码（含确认） */
  changePassword: (
    currentPassword: string,
    newPassword: string,
    newPasswordConfirm: string
  ) => Promise<{ success: boolean; error?: ParsedApiError }>;
  /** 登出方法 */
  logout: () => Promise<void>;
  /** 刷新认证状态 */
  refreshStatus: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

/**
 * 从登录错误中提取用户友好的错误信息
 * 对 429（请求过多）做特殊处理，提示用户稍后重试
 * @param err - 捕获到的错误对象
 * @returns 解析后的错误信息
 */
function extractLoginError(err: unknown): ParsedApiError {
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
}

/**
 * 认证上下文 Provider 组件
 *
 * 在应用根层包裹此 Provider，后代组件即可通过 useAuth() 获取认证状态和操作方法。
 * 挂载时自动请求后端认证状态，未登录时重置仪表盘数据。
 *
 * @param children - 子组件
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [authEnabled, setAuthEnabled] = useState(false);
  const [loggedIn, setLoggedIn] = useState(false);
  const [passwordSet, setPasswordSet] = useState(false);
  const [passwordChangeable, setPasswordChangeable] = useState(false);
  const [setupState, setSetupState] = useState<'enabled' | 'password_retained' | 'no_password'>('no_password');
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<ParsedApiError | null>(null);

  /**
   * 从后端拉取认证状态
   * 如果认证已启用但未登录，重置仪表盘状态（清除敏感数据）
   * 拉取失败时重置所有状态为默认值并重置仪表盘
   */
  const fetchStatus = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const status = await authApi.getStatus();
      setAuthEnabled(status.authEnabled);
      setLoggedIn(status.loggedIn);
      setPasswordSet(status.passwordSet ?? false);
      setPasswordChangeable(status.passwordChangeable ?? false);
      setSetupState(status.setupState);
      // 认证已启用但未登录：重置仪表盘数据，避免泄露上次登录的敏感信息
      if (status.authEnabled && !status.loggedIn) {
        useStockPoolStore.getState().resetDashboardState();
      }
    } catch (err) {
      setLoadError(getParsedApiError(err));
      // 拉取失败：重置所有状态为默认值
      setAuthEnabled(false);
      setLoggedIn(false);
      setPasswordSet(false);
      setPasswordChangeable(false);
      setSetupState('no_password');
      useStockPoolStore.getState().resetDashboardState();
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 组件挂载时自动拉取认证状态
  useEffect(() => {
    void fetchStatus();
  }, [fetchStatus]);

  /**
   * 登录方法
   * 调用后端登录接口，成功后刷新认证状态
   * @param password - 管理员密码
   * @returns 登录结果，包含 success 标志和可能的错误信息
   */
  const login = useCallback(
    async (password: string): Promise<{ success: boolean; error?: ParsedApiError }> => {
      try {
        await authApi.login(password);
        await fetchStatus();
        return { success: true };
      } catch (err: unknown) {
        return { success: false, error: extractLoginError(err) };
      }
    },
    [fetchStatus]
  );

  /**
   * 修改密码方法
   * @param currentPassword - 当前密码
   * @param newPassword - 新密码
   * @param newPasswordConfirm - 新密码确认
   * @returns 修改结果，包含 success 标志和可能的错误信息
   */
  const changePassword = useCallback(
    async (
      currentPassword: string,
      newPassword: string,
      newPasswordConfirm: string
    ): Promise<{ success: boolean; error?: ParsedApiError }> => {
      try {
        await authApi.changePassword(currentPassword, newPassword, newPasswordConfirm);
        return { success: true };
      } catch (err: unknown) {
        return { success: false, error: getParsedApiError(err) };
      }
    },
    []
  );

  /**
   * 登出方法
   * 即使登出请求失败（非 401），也会刷新认证状态
   * 401 错误表示已登出，静默处理
   */
  const logout = useCallback(async () => {
    let logoutError: unknown = null;
    try {
      await authApi.logout();
    } catch (err) {
      logoutError = err;
    } finally {
      // 无论登出成功与否，都刷新认证状态
      await fetchStatus();
    }

    // 非 401 错误向上抛出（401 表示已登出，无需处理）
    if (logoutError && getParsedApiError(logoutError).status !== 401) {
      throw logoutError;
    }
  }, [fetchStatus]);

  return (
    <AuthContext.Provider
      value={{
        authEnabled,
        loggedIn,
        passwordSet,
        passwordChangeable,
        setupState,
        isLoading,
        loadError,
        login,
        changePassword,
        logout,
        refreshStatus: fetchStatus,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components -- useAuth is a hook, co-located for context access
/**
 * 认证上下文 Hook
 * 必须在 AuthProvider 内部使用，否则抛出错误
 * @returns 认证上下文值
 */
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return ctx;
}
