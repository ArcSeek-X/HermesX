/**
 * ThemeSync —— 主题状态 <-> DOM 的桥接（根层 / 使用层）
 *
 * 订阅 themeStore，把 store 真值同步到实际渲染：
 *   - themeMode  -> next-themes.setTheme：切 <html> 的 .light/.dark class，联动子树 resolvedTheme
 *                   （落盘由 themeStore 统一写入 hrs-pref-theme，本组件不负责持久化）
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
  // 刻意不把 setTheme 放进依赖：next-themes 0.4.x 的 setTheme 引用随其内部 theme 状态更换，
  // 跨标签页 storage 事件更新内部状态后若重新执行本 effect，会把本标签页的 themeMode
  // 再写回共享 key，两个标签页互相改写，令 <html> class 在明暗之间无限交替。
  // 只在 themeMode 真正变化时用当次渲染持有的 setTheme 回写一次即可。
  useEffect(() => {
    setTheme(themeMode);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [themeMode]);

  // themeColor 变化 -> 应用到 --primary
  useEffect(() => {
    applyPrimaryColor(themeColor);
  }, [themeColor]);

  return null;
};
