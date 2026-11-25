/**
 * 繁體中文（zh-Hant）文案：exception 命名空间。
 * 由 uiText-zh-Hant.ts 按 uiText-zh/ 分片结构拆分，经 uiText-zh-Hant/index.ts 聚合；key 与中文分片逐一对齐。
 */

export const exceptionZhHant = {
  'exception.404.title': '404', // 404 路由標題（route handle）
  'exception.404.description': '404 頁面未找到', // 404 路由描述（route handle）
  'exception.redirect.title': '重定向', // 重定向路由標題（route handle）
  'exception.redirect.description': '自動重定向到目標頁面', // 重定向路由描述（route handle）
  'exception.routeBoundary.backHome': '返回首頁', // 路由錯誤返回首頁
  'exception.routeBoundary.backToLogin': '返回登錄', // 路由錯誤返回登錄
  'exception.routeBoundary.description': '目前頁面資源或組件未能正常載入，可能是網絡中断或系統版本已更新。請重新載入頁面，或返回登錄後再試。', // 路由錯誤描述
  'exception.routeBoundary.details': '查看詳情', // 路由錯誤展開詳情
  'exception.routeBoundary.hideDetails': '收起詳情', // 路由錯誤收起詳情
  'exception.routeBoundary.errorDetail': '錯誤詳情', // 路由錯誤詳情代碼塊標題
  'exception.routeBoundary.copy': '複製', // 複製錯誤詳情
  'exception.routeBoundary.copied': '已複製', // 錯誤詳情已複製到剪貼板
  'exception.routeBoundary.reload': '重新載入', // 路由錯誤重新載入
  'exception.routeBoundary.title': '頁面載入失敗', // 路由錯誤標題
} as const;
