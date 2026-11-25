/**
 * 简体中文（zh）文案：异常页面 exception 类别。
 * 由 uiText-zh.ts 按类别拆分，经 uiText-zh/index.ts 聚合；key 与三语主字典保持一致。
 */

export const exceptionZh = {
  // ---- 第 6 类 异常页面  ----
  // 404页面/重定向页面
  'exception.404.title': '404', // 404 路由标题（route handle）
  'exception.404.description': '404 页面未找到', // 404 路由描述（route handle）
  'exception.redirect.title': '重定向', // 重定向路由标题（route handle）
  'exception.redirect.description': '自动重定向到目标页面', // 重定向路由描述（route handle）
  // exception.routeBoundary.*
  'exception.routeBoundary.backHome': '返回首页', // 路由错误返回首页
  'exception.routeBoundary.backToLogin': '返回登录', // 路由错误返回登录
  'exception.routeBoundary.description': '当前页面资源或组件未能正常加载，可能是网络中断或系统版本已更新。请重新加载页面，或返回登录后再试。', // 路由错误描述
  'exception.routeBoundary.details': '查看详情', // 路由错误展开详情
  'exception.routeBoundary.hideDetails': '收起详情', // 路由错误收起详情
  'exception.routeBoundary.errorDetail': '错误详情', // 路由错误详情代码块标题
  'exception.routeBoundary.copy': '复制', // 复制错误详情
  'exception.routeBoundary.copied': '已复制', // 错误详情已复制到剪贴板
  'exception.routeBoundary.reload': '重新加载', // 路由错误重新加载
  'exception.routeBoundary.title': '页面加载失败', // 路由错误标题

} as const;
