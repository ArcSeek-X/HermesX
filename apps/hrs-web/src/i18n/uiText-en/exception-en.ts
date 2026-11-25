/**
 * 英文（en）文案：exception 命名空间。
 * 由 uiText-en.ts 按 uiText-zh/ 分片结构拆分，经 uiText-en/index.ts 聚合；key 与中文分片逐一对齐。
 */

export const exceptionEn = {
  'exception.404.title': '404', // 404 route title (route handle)
  'exception.404.description': '404 page not found', // 404 route description (route handle)
  'exception.redirect.title': 'Redirect', // redirect route title (route handle)
  'exception.redirect.description': 'Automatically redirected to the target page', // redirect route description (route handle)
  'exception.routeBoundary.backHome': 'Back home', // route error: back to home
  'exception.routeBoundary.backToLogin': 'Back to login', // route error: back to login
  'exception.routeBoundary.description': 'This page or component could not load. The network may be unavailable, or the system version may have changed. Reload the page or return to login and try again.', // route error description
  'exception.routeBoundary.details': 'View details', // route error: expand details
  'exception.routeBoundary.hideDetails': 'Hide details', // route error: collapse details
  'exception.routeBoundary.errorDetail': 'Error detail', // route error detail block title
  'exception.routeBoundary.copy': 'Copy', // copy error detail
  'exception.routeBoundary.copied': 'Copied', // error detail copied to clipboard
  'exception.routeBoundary.reload': 'Reload', // route error: reload
  'exception.routeBoundary.title': 'Page failed to load', // route error title
} as const;
