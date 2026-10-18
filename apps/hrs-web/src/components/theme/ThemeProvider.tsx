/**
 * ThemeProvider —— 基于 next-themes 的全局主题提供者
 *
 * 关键约定：主题真值统一存放在 hrs-pref-theme（对象）并由 themeStore 独占读写，
 * 详见 stores/themeStore.ts。此处对该库的约定：
 * - next-themes 仅负责在 <html> 上切 .light/.dark class 与系统色跟随，不再承担落盘真值；
 * - 该库要求独立的 storageKey 且以「原始字符串」写盘，若指向 hrs-pref-theme 会覆盖掉
 *   我们的 JSON 对象，故使用 hrs-lib-next-themes 作为库内部键（刻意置于主题业务命名空间之外，
 *   应用永不读取）；
 * - defaultTheme 取 store 真值，避免首帧按 system 渲染造成闪色。
 * - attribute="class"：在 <html> 上切 .light/.dark class
 * - enableSystem：无记录时跟随系统（prefers-color-scheme）
 * - disableTransitionOnChange：切换时禁用过渡，避免颜色闪烁
 * 内部渲染 <ThemeSync/> 完成 store <-> DOM 的桥接。
 */
import type React from 'react';
import { ThemeProvider as NextThemesProvider } from 'next-themes';
import { ThemeSync } from './ThemeSync';
import { useThemeStore } from '../../stores/themeStore';

/** next-themes 库内部键：独立于主题业务命名空间（业务键仅 hrs-pref-theme），
 *  应用不读取，仅满足该库自身的读写要求 */
const NEXT_THEMES_STORAGE_KEY = 'hrs-lib-next-themes';

type ThemeProviderProps = {
  children: React.ReactNode;
};

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  // 以 store 真值作为 next-themes 初值，避免首帧按 system 渲染造成闪色
  const initialMode = useThemeStore.getState().themeMode;
  return (
    <NextThemesProvider
      attribute="class"
      storageKey={NEXT_THEMES_STORAGE_KEY}
      defaultTheme={initialMode}
      enableSystem
      disableTransitionOnChange
    >
      <ThemeSync />
      {children}
    </NextThemesProvider>
  );
};
