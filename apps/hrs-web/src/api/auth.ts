import apiClient from './index';

/**
 * 鉴权相关 API（Web 端密码保护）。
 * 负责查询鉴权状态、开启/关闭鉴权、登录、修改密码与登出。
 */

/** 鉴权状态响应：描述当前是否启用密码保护、是否已登录、密码设置情况 */
export type AuthStatusResponse = {
  /** 是否启用了鉴权（密码保护开启） */
  authEnabled: boolean;
  /** 当前会话是否已登录 */
  loggedIn: boolean;
  /** 是否已设置密码 */
  passwordSet?: boolean;
  /** 当前登录用户是否允许修改密码 */
  passwordChangeable?: boolean;
  /** 设置状态：enabled=已启用 / password_retained=保留旧密码 / no_password=尚未设置密码 */
  setupState: 'enabled' | 'password_retained' | 'no_password';
};

export const authApi = {
  /** 获取当前鉴权状态（页面初始化时调用，决定是否展示登录页） */
  async getStatus(): Promise<AuthStatusResponse> {
    const { data } = await apiClient.get<AuthStatusResponse>('/api/v1/auth/status');
    return data;
  },

  /**
   * 更新鉴权设置。
   * @param authEnabled 是否开启鉴权
   * @param password 新密码（开启或首次设置时提供）
   * @param passwordConfirm 新密码确认
   * @param currentPassword 当前密码（修改已设置密码时用于校验）
   */
  async updateSettings(
    authEnabled: boolean,
    password?: string,
    passwordConfirm?: string,
    currentPassword?: string
  ): Promise<AuthStatusResponse> {
    const body: {
      authEnabled: boolean;
      password?: string;
      passwordConfirm?: string;
      currentPassword?: string;
    } = { authEnabled };
    if (password !== undefined) {
      body.password = password;
    }
    if (passwordConfirm !== undefined) {
      body.passwordConfirm = passwordConfirm;
    }
    if (currentPassword !== undefined) {
      body.currentPassword = currentPassword;
    }
    const { data } = await apiClient.post<AuthStatusResponse>('/api/v1/auth/settings', body);
    return data;
  },

  /** 登录：校验密码并建立会话 */
  async login(password: string): Promise<void> {
    await apiClient.post('/api/v1/auth/login', { password });
  },

  /** 修改密码（需提供当前密码 + 两次新密码确认） */
  async changePassword(
    currentPassword: string,
    newPassword: string,
    newPasswordConfirm: string
  ): Promise<void> {
    await apiClient.post('/api/v1/auth/change-password', {
      currentPassword,
      newPassword,
      newPasswordConfirm,
    });
  },

  /** 登出当前会话 */
  async logout(): Promise<void> {
    await apiClient.post('/api/v1/auth/logout');
  },
};
