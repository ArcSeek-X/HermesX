/**
 * 简体中文（zh）文案：登录/注册 auth 类别。
 * 由 uiText-zh.ts 按类别拆分，经 uiText-zh/index.ts 聚合；key 与三语主字典保持一致。
 */

export const authZh = {
  // ---- 第 7 类 登录/注册 auth ----
  'auth.login.title': '登录页', // 管理员登录页标题（route handle）
  'auth.login.description': '管理员登录认证，进入量化决策工作台', // 管理员登录页路由描述（route handle）
  'auth.login.adminLogin': '管理员登录', // 管理员登录标题
  'auth.login.hidePassword': '隐藏密码', // 隐藏密码按钮提示
  'auth.login.loginDescription': '访问 HRS 量化决策引擎需要有效的身份凭证。', // 登录页描述
  'auth.login.loginFailed': '登录失败', // 登录失败提示
  'auth.login.loginPassword': '登录密码', // 登录密码标签
  'auth.login.loginPasswordPlaceholder': '请输入密码', // 登录密码占位符
  'auth.login.loginSubmit': '授权进入工作台', // 登录提交按钮
  'auth.login.loginSubmitting': '正在建立连接...', // 登录提交中状态
  'auth.login.pageTitle': '登录 - HRS', // 登录页标题
  'auth.login.passwordMismatch': '两次输入的密码不一致', // 密码不一致提示
  'auth.login.passwordRequired': '请输入密码', // 密码必填校验提示
  'auth.login.showPassword': '显示密码', // 显示密码按钮提示
  'auth.login.username': '账号', // 账号标签
  'auth.login.usernamePlaceholder': '请输入账号', // 账号占位符
  'auth.login.usernameRequired': '请输入账号', // 账号必填校验提示
  'auth.login.validationFailed': '验证未通过', // 验证失败提示

} as const;
