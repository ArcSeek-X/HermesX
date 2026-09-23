/**
 * themeStore —— 主题（模式 + 主色 + 侧栏视觉主题）的全局状态
 * =====================================================================
 * Zustand 集中管理「主题模式（light/dark/system）」「主色（HEX）」与
 * 「侧栏视觉主题（pill/square）」。
 *
 * 持久化分工（关键：避免双写竞态）：
 * - themeMode    -> hrs-pref-theme.themeMode：next-themes 以原始串写盘，
 *                   store 仅读取用于初始化；落盘发生在 ThemeSync 订阅变化后调
 *                   next-themes.setTheme 时（同时切 <html> class）。
 * - themeColor   -> hrs-pref-theme.themeColor：store 经 utils/storage 写盘。
 * - sidebarTheme -> hrs-pref-theme.sidebarTheme：store 经 utils/storage 写盘，
 *                   由 Shell 作 prop 透传 SidebarNav 消费（非全局 CSS）。
 *
 * 读取均校验合法性，非法/缺失回退默认。
 * =====================================================================
 */
import { getStorageItem, setStorageItem } from '@utils/storage';
import { DEFAULT_PRIMARY_COLOR } from '@utils/themeColor';
import { create } from 'zustand';
import { LOCAL_STORAGE_PREFIX } from '../constants/cacheConfig';
import type { ThemeMode, SidebarTheme } from '../types/theme';

/** 键名片段（utils/storage 自动加 hrs-pref- 前缀）。
 *  mode 片段仅用于 readStoredMode 拼接原始键读取；color/sidebar 由 setStorageItem 写盘。 */
const THEME_MODE_STORAGE_KEY = 'theme.themeMode';
const THEME_COLOR_STORAGE_KEY = 'theme.themeColor';
const THEME_SIDEBAR_STORAGE_KEY = 'theme.sidebarTheme';

/** 合法模式集合 */
const VALID_MODES: readonly ThemeMode[] = ['light', 'dark', 'system'];
/** 合法侧栏主题集合 */
const VALID_SIDEBAR_THEMES: readonly SidebarTheme[] = ['pill', 'square'];

/**
 * 从 localStorage 读取上次保存的主题模式（原始字符串，由 next-themes 写入）。
 * @returns 合法模式串；键缺失或值不在白名单时回退 'system'
 */
const readStoredMode = (): ThemeMode => {
  try {
    const stored = window.localStorage.getItem(LOCAL_STORAGE_PREFIX + THEME_MODE_STORAGE_KEY);
    if (stored && (VALID_MODES as readonly string[]).includes(stored)) return stored as ThemeMode;
  } catch { /* 忽略 */ }
  return 'system';
};

/**
 * 从 localStorage 读取上次保存的主色（HEX）。
 * @returns 合法 HEX；键缺失或格式非法时回退 DEFAULT_PRIMARY_COLOR
 */
const readStoredPrimaryColor = (): string => {
  const stored = getStorageItem<string>(THEME_COLOR_STORAGE_KEY, 'local');
  if (stored && /^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/.test(stored)) return stored;
  return DEFAULT_PRIMARY_COLOR;
};

/**
 * 从 localStorage 读取上次保存的侧栏视觉主题。
 * @returns 合法主题串；键缺失或值不在白名单时回退 'square'（与组件默认一致）
 */
const readStoredSidebarTheme = (): SidebarTheme => {
  const stored = getStorageItem<string>(THEME_SIDEBAR_STORAGE_KEY, 'local');
  if (stored && (VALID_SIDEBAR_THEMES as readonly string[]).includes(stored)) return stored as SidebarTheme;
  return 'square';
};

/** 主题 Store 状态与 Action 定义 */
interface ThemeState {
  /** 主题模式：light / dark / system（system=跟随系统） */
  themeMode: ThemeMode;
  /** 主色（HEX 字符串） */
  themeColor: string;
  /** 侧栏视觉主题：pill=大圆角（胶囊感）/ square=方角，驱动 SidebarNav 外观 */
  sidebarTheme: SidebarTheme;
  /** 设定主题模式（落盘由 ThemeSync 桥接） */
  setThemeMode: (mode: ThemeMode) => void;
  /** 设定主色并落盘 */
  setThemeColor: (hex: string) => void;
  /** 设定侧栏视觉主题并落盘（外观由 SidebarNav 消费） */
  setSidebarTheme: (theme: SidebarTheme) => void;
  /** 恢复出厂默认（themeMode=system, themeColor=默认青蓝, sidebarTheme=square）并落盘 */
  themeReset: () => void;
}

export const useThemeStore = create<ThemeState>((set) => ({
  // 初始状态：优先从 localStorage 恢复，非法值回退默认
  themeMode: readStoredMode(),
  themeColor: readStoredPrimaryColor(),
  sidebarTheme: readStoredSidebarTheme(),

  /**
   * 设定主题模式：仅更新内存状态；落盘与 <html> class 切换由 ThemeSync 订阅后调
   * next-themes.setTheme 完成（next-themes 以原始字符串写入 hrs-pref-theme.themeMode）。
   * @param mode 目标主题模式（light/dark/system）
   */
  setThemeMode: (mode) => {
    set({ themeMode: mode });
  },

  /**
   * 设定主色：写盘并更新内存（DOM 应用由 ThemeSync 桥接 --primary）。
   * @param hex 目标主色（HEX 字符串）
   */
  setThemeColor: (hex) => {
    setStorageItem(THEME_COLOR_STORAGE_KEY, hex, 'local');
    set({ themeColor: hex });
  },

  /**
   * 设定侧栏视觉主题：写盘并更新内存（外观由 SidebarNav 消费）。
   * @param theme 目标侧栏主题（pill/square）
   */
  setSidebarTheme: (theme) => {
    setStorageItem(THEME_SIDEBAR_STORAGE_KEY, theme, 'local');
    set({ sidebarTheme: theme });
  },

  /** 恢复出厂默认：mode 落盘交给 next-themes，主色/侧栏主题由 store 落盘 */
  themeReset: () => {
    setStorageItem(THEME_COLOR_STORAGE_KEY, DEFAULT_PRIMARY_COLOR, 'local');
    setStorageItem(THEME_SIDEBAR_STORAGE_KEY, 'square', 'local');
    set({ themeMode: 'system', themeColor: DEFAULT_PRIMARY_COLOR, sidebarTheme: 'square' });
  },
}));
