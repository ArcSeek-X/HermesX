/**
 * 主题相关共享类型定义
 */

/** 主题模式（用户意图，非最终渲染值）：
 * - light：强制浅色；dark：强制深色；system：跟随系统 prefers-color-scheme 解析为实际 light/dark */
export type ThemeMode = 'light' | 'dark' | 'system';

/** 侧栏视觉主题（驱动 SidebarNavNew 外观，与明暗模式 themeMode 正交）：
 * - pill：大圆角/胶囊感（容器 p-3、面板 rounded-md + 边框 + 阴影）
 * - square：方角（仅右侧分隔线 border-r，无面板圆角/阴影），默认 */
export type SidebarTheme = 'pill' | 'square';
