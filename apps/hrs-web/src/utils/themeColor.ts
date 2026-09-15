/**
 * themeColor —— 主题主色的 HEX <-> HSL 转换与 DOM 应用工具
 * =====================================================================
 * 从原 hooks/useThemeColor 抽离的纯函数（无 React 依赖），供
 * themeStore / ThemeSync / ThemeSetting 等共享：
 *   - 主色在 index.css 中以 HSL 三元组（如 "193 100% 43%"）定义在 :root 与 .dark；
 *   - <html> 上的内联 style 优先级高于样式表，故用
 *     documentElement.style.setProperty('--primary', ...) 覆盖，实现全局联动换色；
 *   - 对外以 HEX 暴露（ColorPicker 使用 HEX），内部按 HSL 三元组落盘/计算。
 *
 * @author Lensgcx (GaoCangxiong)
 * =====================================================================
 */

import type { ThemeMode } from '../types/theme';

/** 缺省主色 HEX（暗色默认青蓝，与 index.css :root 的 --primary 一致） */
export const DEFAULT_PRIMARY_COLOR = '#19B5C4';

/**
 * 将 HEX 字符串（支持 #RGB / #RRGGBB）转为 HSL 三元组字符串 "H S% L%"。
 * @param hex HEX 颜色，可带或不带前导 '#'
 * @returns 形如 "193 100% 43%" 的 HSL 三元组，供 CSS 变量与落盘使用
 */
export function hexToHslTriple(hex: string): string {
  // 去掉前导 '#'，并规整为 6 位十六进制
  let normalized = hex.trim();
  if (normalized.startsWith('#')) normalized = normalized.slice(1);
  // 缩写形式（如 #19b）展开为 #1199bb
  if (normalized.length === 3) {
    normalized = normalized
      .split('')
      .map((c) => c + c)
      .join('');
  }
  // 分别解析 R / G / B 通道（0~1）
  const r = parseInt(normalized.slice(0, 2), 16) / 255;
  const g = parseInt(normalized.slice(2, 4), 16) / 255;
  const b = parseInt(normalized.slice(4, 6), 16) / 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  // 亮度 L = (max + min) / 2
  const l = (max + min) / 2;
  let h = 0;
  let s = 0;
  // 仅当 max !== min 时存在饱和度与色相
  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    // 根据最大通道决定色相基准
    switch (max) {
      case r:
        h = (g - b) / d + (g < b ? 6 : 0);
        break;
      case g:
        h = (b - r) / d + 2;
        break;
      default:
        h = (r - g) / d + 4;
    }
    h /= 6;
  }
  // 转为整数度的 H、百分制的 S / L
  const hDeg = Math.round(h * 360);
  const sPct = Math.round(s * 100);
  const lPct = Math.round(l * 100);
  return `${hDeg} ${sPct}% ${lPct}%`;
}

/**
 * 将主色（HEX）应用到 <html> 的 --primary（内联 style 覆盖样式表），
 * 并写入 data-theme-primary（HEX）方便 DevTools 查看。
 * @param hex 目标主色（HEX 字符串）；仅客户端有效，SSR 下安全空操作
 */
export function applyPrimaryColor(hex: string): void {
  if (typeof document === 'undefined') return;
  const hsl = hexToHslTriple(hex);
  document.documentElement.style.setProperty('--primary', hsl);
  document.documentElement.dataset.themePrimary = hex.toUpperCase();
}

/**
 * 预览阶段直接切换 <html> 的 light/dark class（不落库、不经过 next-themes，
 * 避免重渲染 ThemeProvider 打断 TabNav 指示条滑动动画）。
 * @param mode 目标模式：light/dark 直接加对应 class；
 *             system 按 prefers-color-scheme 解析后落 light/dark class
 */
export function applyModePreview(mode: ThemeMode): void {
  if (typeof document === 'undefined') return;
  const root = document.documentElement;
  if (mode === 'system') {
    const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    root.classList.toggle('dark', isDark);
    root.classList.toggle('light', !isDark);
  } else {
    root.classList.remove('light', 'dark');
    root.classList.add(mode);
  }
}



