/**
 * 主题上下文提供者（ThemeProvider）
 *
 * 基于 next-themes 库封装的全局主题提供者，在应用根节点包裹此组件后，
 * 子树中可通过 useTheme() 获取当前主题并切换。
 *
 * 配置说明：
 * - attribute="class"：通过在 <html> 上添加/移除 class（"light" / "dark"）来切换主题
 * - defaultTheme="system"：首次访问（无 localStorage 记录）时跟随系统偏好
 * - enableSystem：允许跟随系统偏好（prefers-color-scheme），用户选择 "system" 时生效
 * - disableTransitionOnChange：切换主题时禁用 CSS 过渡动画，避免颜色渐变闪烁
 */
import type React from 'react';
import { ThemeProvider as NextThemesProvider } from 'next-themes';

type ThemeProviderProps = {
  children: React.ReactNode;
};

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      {children}
    </NextThemesProvider>
  );
};
