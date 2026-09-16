/**
 * themeStore —— 主题（模式 + 主色 + 侧栏视觉主题）的全局状态与本地持久化
 * =====================================================================
 * 【职责】
 * 用 Zustand 集中管理「主题模式（light/dark/system）」「主色（HEX）」与
 * 「侧栏视觉主题（pill/square）」，并通过 utils/storage 落盘到 localStorage
 * （自动 hrs-pref- 前缀），实现刷新/切换后保持。
 *
 * 【与下层的关系】
 * - next-themes 仍负责 <html> 的 dark/light class 与应用内 resolvedTheme（视图派生）；
 * - ThemeSync 桥接组件订阅本 store，把 themeMode 同步给 next-themes、把 themeColor 应用到 DOM；
 * - sidebarTheme 为组件级视觉偏好（非全局 CSS 变量），由 Shell 订阅后作为 prop 透传给
 *   SidebarNavNew 消费，不经由 ThemeSync；
 * - 使用层组件（ThemeSetting / HomePage）从本 store 读数据并向下给基础组件传 props；
 * - 基础组件（ColorPicker 等）不感知 store，只收 props。
 *
 * 【持久化约定】
 * - themeMode    -> hrs-pref-theme.themeMode（并同步 next-themes 的 theme 键防 FOUC）
 * - themeColor   -> hrs-pref-theme.themeColor
 * - sidebarTheme -> hrs-pref-theme.sidebarTheme
 *
 * 设计参照 LayoutStore：落盘写在 action 内（而非 persist 中间件），读取时校验合法性。
 *
 * @author Lensgcx (GaoCangxiong)
 * =====================================================================
 */
import { create } from 'zustand';
import { getStorageItem, setStorageItem } from '../utils/storage';
import { DEFAULT_PRIMARY_COLOR } from '../utils/themeColor';
import type { ThemeMode, SidebarTheme } from '../types/theme';

/** 持久化键（utils/storage 自动加 hrs-pref- 前缀），与 store 字段名对齐 */
const THEME_MODE_STORAGE_KEY = 'theme.themeMode';
const THEME_COLOR_STORAGE_KEY = 'theme.themeColor';
/** 侧栏视觉主题持久化键（pill/square），与 store 字段名 sidebarTheme 对齐 */
const THEME_SIDEBAR_STORAGE_KEY = 'theme.sidebarTheme';

/** 合法模式集合 */
const VALID_MODES: readonly ThemeMode[] = ['light', 'dark', 'system'];
/** 合法侧栏主题集合 */
const VALID_SIDEBAR_THEMES: readonly SidebarTheme[] = ['pill', 'square'];

/**
 * 从 localStorage 读取上次保存的主题模式。
 * @returns 合法模式串；键缺失或值不在白名单时回退 'system'
 */
const readStoredMode = (): ThemeMode => {
  const stored = getStorageItem<string>(THEME_MODE_STORAGE_KEY, 'local');
  if (stored && (VALID_MODES as readonly string[]).includes(stored)) return stored as ThemeMode;
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
  /** 侧栏视觉主题：pill=大圆角（胶囊感）/ square=方角，驱动 SidebarNavNew 外观 */
  sidebarTheme: SidebarTheme;
  /** 设定主题模式并落盘（同步 next-themes theme 键防 FOUC） */
  setThemeMode: (mode: ThemeMode) => void;
  /** 设定主色并落盘 */
  setThemeColor: (hex: string) => void;
  /** 设定侧栏视觉主题并落盘（外观由 SidebarNavNew 消费） */
  setSidebarTheme: (theme: SidebarTheme) => void;
  /** 恢复出厂默认（themeMode=system, themeColor=默认青蓝, sidebarTheme=square）并落盘 */
  themeReset: () => void;
}

/**
 * 同步 next-themes 的 theme 键到 localStorage，避免首屏 hydration 前 FOUC。
 * @param mode 待同步的主题模式；仅客户端生效，SSR 下跳过
 */
const syncNextThemesTheme = (mode: ThemeMode) => {
  if (typeof window !== 'undefined') window.localStorage.setItem('theme', mode);
};

export const useThemeStore = create<ThemeState>((set) => ({
  // 初始状态：优先从 localStorage 恢复，非法值回退默认
  themeMode: readStoredMode(),
  themeColor: readStoredPrimaryColor(),
  sidebarTheme: readStoredSidebarTheme(),

  /**
   * 设定主题模式：持久化到 localStorage、同步 next-themes 的 theme 键，最后更新内存状态。
   * @param mode 目标主题模式（light/dark/system）；真正作用到 <html> 由 ThemeSync 桥接
   */
  setThemeMode: (mode) => {
    setStorageItem(THEME_MODE_STORAGE_KEY, mode, 'local');
    syncNextThemesTheme(mode);
    set({ themeMode: mode });
  },

  /**
   * 设定主色：持久化到 localStorage 并更新内存状态（DOM 应用由 ThemeSync 桥接）。
   * @param hex 目标主色（HEX 字符串）
   */
  setThemeColor: (hex) => {
    setStorageItem(THEME_COLOR_STORAGE_KEY, hex, 'local');
    set({ themeColor: hex });
  },

  /**
   * 设定侧栏视觉主题：持久化到 localStorage 并更新内存状态（外观由 SidebarNavNew 消费）。
   * @param theme 目标侧栏主题（pill/square）
   */
  setSidebarTheme: (theme) => {
    setStorageItem(THEME_SIDEBAR_STORAGE_KEY, theme, 'local');
    set({ sidebarTheme: theme });
  },

  /** 恢复出厂默认并落盘 */
  themeReset: () => {
    setStorageItem(THEME_MODE_STORAGE_KEY, 'system', 'local');
    setStorageItem(THEME_COLOR_STORAGE_KEY, DEFAULT_PRIMARY_COLOR, 'local');
    setStorageItem(THEME_SIDEBAR_STORAGE_KEY, 'square', 'local');
    syncNextThemesTheme('system');
    set({ themeMode: 'system', themeColor: DEFAULT_PRIMARY_COLOR, sidebarTheme: 'square' });
  },
}));
