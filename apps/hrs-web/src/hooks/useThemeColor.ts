/**
 * useThemeColor —— 主题主色（--primary）的持久化与实时应用 Hook
 * =====================================================================
 * 【功能介绍】
 * 管理 HermesX Web 的「主题主色」：用户在「主题设置」弹窗里通过
 * ColorPicker 选择颜色后，本 Hook 负责把颜色写入 CSS 变量 --primary，
 * 让全站（按钮、高亮、边框、阴影等）即时联动换色，并持久化到
 * localStorage，刷新或切换浅色/深色后仍保持用户所选主色。
 *
 * 【设计要点】
 * - 主色在 index.css 中以 HSL 三元组（如 "193 100% 43%"）定义在 :root 与
 *   .dark 两处；由于 <html> 上的内联 style 优先级高于样式表规则，这里通过
 *   documentElement.style.setProperty('--primary', ...) 直接覆盖，实现全局联动换色。
 * - 内部以 HSL 三元组存储（与 index.css 的 --primary 语义一致）；
 *   对外暴露 HEX 读写（ColorPicker 使用 HEX），两者通过工具函数互相转换。
 * - 选中的颜色持久化于 localStorage（key: hermes-theme-color），
 *   应用启动时与主题切换后都会重新应用，避免丢失。
 * - 同时把当前主色（HEX）写到 <html data-theme-primary>，
 *   方便在 DevTools 即时确认当前生效的主色。
 * =====================================================================
 */
import { useCallback, useEffect, useState } from 'react';
import { useTheme } from 'next-themes';

// 持久化主色用的 localStorage key
const STORAGE_KEY = 'hermes-theme-color';
// 缺省主色（与 index.css :root 的 --primary 一致），采用 HSL 三元组字符串
const DEFAULT_PRIMARY_HSL = '193 100% 43%';

/** 将 HEX 字符串（支持 #RGB / #RRGGBB）转为 HSL 三元组字符串 "H S% L%" */
function hexToHslTriple(hex: string): string {
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

/** 将 HSL 三元组字符串 "H S% L%" 解析为 HEX（用于 ColorPicker 受控显示） */
function hslTripleToHex(hsl: string): string {
  // 容错：解析失败兜底返回项目默认青蓝
  const match = hsl.match(/(\d+)\s+(\d+)%?\s+(\d+)%?/);
  if (!match) return '#19B5C4';
  const h = parseInt(match[1], 10) / 360;
  const s = parseInt(match[2], 10) / 100;
  const l = parseInt(match[3], 10) / 100;

  // HSL 转 RGB 的核心辅助：根据 p/q 与色相偏移 t 计算单通道值
  const hue2rgb = (p: number, q: number, t: number) => {
    let tt = t;
    if (tt < 0) tt += 1;
    if (tt > 1) tt -= 1;
    if (tt < 1 / 6) return p + (q - p) * 6 * tt;
    if (tt < 1 / 2) return q;
    if (tt < 2 / 3) return p + (q - p) * (2 / 3 - tt) * 6;
    return p;
  };

  let r: number;
  let g: number;
  let b: number;
  // 灰度（无饱和）：R=G=B=L
  if (s === 0) {
    r = g = b = l;
  } else {
    // 标准 HSL -> RGB 转换公式
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    r = hue2rgb(p, q, h + 1 / 3);
    g = hue2rgb(p, q, h);
    b = hue2rgb(p, q, h - 1 / 3);
  }

  // 单通道值 -> 两位十六进制（大写）
  const toHex = (x: number) =>
    Math.round(x * 255)
      .toString(16)
      .padStart(2, '0');
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`.toUpperCase();
}

/** useThemeColor 的返回值类型定义 */
export type UseThemeColorResult = {
  /** 当前主色（HEX 字符串），用于 ColorPicker 受控显示 */
  color: string;
  /** 设置主色：接收 HEX 字符串，转换后写入 --primary 并持久化 */
  setColor: (hex: string) => void;
  /** 重置为缺省主色 */
  reset: () => void;
};

/**
 * 主题主色 Hook
 *
 * @returns 当前 HEX 颜色、设置方法、重置方法
 */
export function useThemeColor(): UseThemeColorResult {
  // 读取当前主题（用于主题切换后重新应用主色）
  const { theme } = useTheme();
  // 主色内部状态：以 HSL 三元组字符串存储；初始化时优先取 localStorage 中的用户选择
  const [hsl, setHsl] = useState<string>(() => {
    // 服务端渲染（无 window）时直接用缺省值，避免报错
    if (typeof window === 'undefined') return DEFAULT_PRIMARY_HSL;
    return window.localStorage.getItem(STORAGE_KEY) ?? DEFAULT_PRIMARY_HSL;
  });

  // 将主色应用到 <html> 的 --primary（内联 style 覆盖样式表），
  // 并写入 data-theme-primary（HEX）方便 DevTools 查看
  const apply = useCallback((nextHsl: string) => {
    document.documentElement.style.setProperty('--primary', nextHsl);
    document.documentElement.dataset.themePrimary = hslTripleToHex(nextHsl);
  }, []);

  // 主色状态变化时，立即应用到 DOM（覆盖启动时的首次应用）
  useEffect(() => {
    apply(hsl);
  }, [apply, hsl]);

  // 主题切换（light / dark / system）后重新应用，保持用户所选主色不变
  // （system 在解析后仍是 light / dark，这里统一重新写入即可）
  useEffect(() => {
    apply(hsl);
    // 仅依赖 theme；apply 为稳定引用，故关闭 exhaustive-deps 校验
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [theme, apply]);

  // 设置主色：HEX -> HSL，更新状态、应用到 DOM、并持久化到 localStorage
  const setColor = useCallback(
    (hex: string) => {
      const nextHsl = hexToHslTriple(hex);
      setHsl(nextHsl);
      apply(nextHsl);
      window.localStorage.setItem(STORAGE_KEY, nextHsl);
    },
    [apply]
  );

  // 重置主色：回到缺省 HSL 三元组，并同步状态 / DOM / 持久化
  const reset = useCallback(() => {
    setHsl(DEFAULT_PRIMARY_HSL);
    apply(DEFAULT_PRIMARY_HSL);
    window.localStorage.setItem(STORAGE_KEY, DEFAULT_PRIMARY_HSL);
  }, [apply]);

  // 对外暴露：HEX 形式当前色 + 设置 / 重置方法
  return { color: hslTripleToHex(hsl), setColor, reset };
}
