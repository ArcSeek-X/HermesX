/**
 * ThemeSync —— 主题状态 <-> DOM 的桥接（根层 / 使用层）
 *
 * 订阅 themeStore，把 store 真值同步到实际渲染：
 *   - themeMode  -> next-themes.setTheme：写入 hrs-pref-theme.themeMode（原始串）
 *                   并切 <html> 的 .light/.dark class，联动子树 resolvedTheme
 *   - themeColor -> 写入 <html> 的 --primary，全站主色联动
 *
 * 放在 NextThemesProvider 内部（见 ThemeProvider），仅客户端生效；
 * 组件本身不渲染任何 UI（返回 null）。store 是唯一真值，所有改主题的地方
 * 都走 store action，避免状态分叉。
 */
import { useEffect } from 'react';
import { useTheme } from 'next-themes';
import { useThemeStore } from '../../stores/themeStore';
import { applyPrimaryColor } from '../../utils/themeColor';

export const ThemeSync = () => {
  const { setTheme } = useTheme();
  const themeMode = useThemeStore((s) => s.themeMode);
  const themeColor = useThemeStore((s) => s.themeColor);

  // themeMode 变化 -> 同步给 next-themes（切 <html> class + resolvedTheme）
  useEffect(() => {
    setTheme(themeMode);
  }, [themeMode, setTheme]);

  // themeColor 变化 -> 应用到 --primary
  useEffect(() => {
    applyPrimaryColor(themeColor);
  }, [themeColor]);

  return null;
};
