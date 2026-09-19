/**
 * ThemeProvider —— 基于 next-themes 的全局主题提供者
 *
 * 关键约定：storageKey="hrs-pref-theme.themeMode" 让应用主题键成为唯一真值
 * （不再有裸 `theme` 键），next-themes 以原始字符串读写它。
 * - attribute="class"：在 <html> 上切 .light/.dark class
 * - defaultTheme / enableSystem：无记录时跟随系统（prefers-color-scheme）
 * - disableTransitionOnChange：切换时禁用过渡，避免颜色闪烁
 * 内部渲染 <ThemeSync/> 完成 store <-> DOM 的桥接。
 */
import type React from 'react';
import { ThemeProvider as NextThemesProvider } from 'next-themes';
import { ThemeSync } from './ThemeSync';

type ThemeProviderProps = {
  children: React.ReactNode;
};

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  return (
    <NextThemesProvider
      attribute="class"
      storageKey="hrs-pref-theme.themeMode"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      <ThemeSync />
      {children}
    </NextThemesProvider>
  );
};
