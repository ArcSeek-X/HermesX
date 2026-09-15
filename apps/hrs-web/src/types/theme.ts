/**
 * 主题相关共享类型定义
 */

/** 主题模式（用户意图，非最终渲染值）：
 * - light：强制浅色；dark：强制深色；system：跟随系统 prefers-color-scheme 解析为实际 light/dark */
export type ThemeMode = 'light' | 'dark' | 'system';
