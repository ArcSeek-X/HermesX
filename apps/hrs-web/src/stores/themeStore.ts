/**
 * themeStore —— 主题（模式 + 主色 + 侧栏视觉主题）的全局状态
 * =====================================================================
 * Zustand 集中管理「主题模式（light/dark/system）」「主色（HEX）」与
 * 「侧栏视觉主题（pill/square）」。
 *
 * 持久化（三值收口为单一键）：
 * - 三个维度统一存放在 localStorage 的 hrs-pref-theme（对象形态），由 store 独占读写，
 *   消除原先「mode 由 next-themes 落盘、color/sidebar 由 store 落盘」的分键双写竞态。
 * - next-themes 仅负责 <html> class 与系统色跟随，其自身 storageKey 见 ThemeProvider；
 *   应用不再从 next-themes 的键读取真值。
 * - 首次读取时若新键缺失而存在旧的三键，自动做一次性迁移并落盘。
 *
 * 读取均按维度校验合法性，非法 / 缺失仅回退该维度，不牵连其他维度。
 * =====================================================================
 */
import { getStorageItem, setStorageItem } from '@utils/storage';
import { DEFAULT_PRIMARY_COLOR } from '@utils/themeColor';
import { create } from 'zustand';
import { LOCAL_STORAGE_PREFIX } from '../constants/cacheConfig';
import type { ThemeMode, SidebarTheme } from '../types/theme';

/** 主题持久化单一键（utils/storage 自动加 hrs-pref- 前缀 → hrs-pref-theme） */
const THEME_STORAGE_KEY = 'theme';

/** 迁移用：旧的分键键名（utils/storage 自动加前缀；mode 旧键由 next-themes 以原始串写入） */
const LEGACY_MODE_KEY = 'theme.themeMode';
const LEGACY_COLOR_KEY = 'theme.themeColor';
const LEGACY_SIDEBAR_KEY = 'theme.sidebarTheme';

/** 合法模式集合 */
const VALID_MODES: readonly ThemeMode[] = ['light', 'dark', 'system'];
/** 合法侧栏主题集合 */
const VALID_SIDEBAR_THEMES: readonly SidebarTheme[] = ['pill', 'square'];
/** 主色 HEX 格式校验 */
const HEX_COLOR = /^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/;

/** 持久化对象形态：三个主题维度同键存放 */
interface StoredTheme {
  themeMode: ThemeMode;
  themeColor: string;
  sidebarTheme: SidebarTheme;
}

/** 默认主题（各维度的回退值） */
const DEFAULT_THEME: StoredTheme = {
  themeMode: 'system',
  themeColor: DEFAULT_PRIMARY_COLOR,
  sidebarTheme: 'square',
};

/** 按维度校验并规整主题对象；非法仅回退该维度，不影响其他维度 */
function normalizeTheme(raw: Partial<StoredTheme> | null): StoredTheme {
  const themeMode =
    raw?.themeMode && VALID_MODES.includes(raw.themeMode) ? raw.themeMode : DEFAULT_THEME.themeMode;
  const themeColor =
    raw?.themeColor && HEX_COLOR.test(raw.themeColor) ? raw.themeColor : DEFAULT_THEME.themeColor;
  const sidebarTheme =
    raw?.sidebarTheme && VALID_SIDEBAR_THEMES.includes(raw.sidebarTheme)
      ? raw.sidebarTheme
      : DEFAULT_THEME.sidebarTheme;
  return { themeMode, themeColor, sidebarTheme };
}

/** 读取旧的分键（一次性迁移用）；无任何旧值返回 null */
function readLegacyTheme(): Partial<StoredTheme> | null {
  const legacy: Partial<StoredTheme> = {};
  try {
    const rawMode = window.localStorage.getItem(LOCAL_STORAGE_PREFIX + LEGACY_MODE_KEY);
    if (rawMode && (VALID_MODES as readonly string[]).includes(rawMode)) {
      legacy.themeMode = rawMode as ThemeMode;
    }
  } catch { /* 忽略 */ }
  const legacyColor = getStorageItem<string>(LEGACY_COLOR_KEY, 'local');
  if (legacyColor && HEX_COLOR.test(legacyColor)) legacy.themeColor = legacyColor;
  const legacySidebar = getStorageItem<string>(LEGACY_SIDEBAR_KEY, 'local');
  if (legacySidebar && (VALID_SIDEBAR_THEMES as readonly string[]).includes(legacySidebar)) {
    legacy.sidebarTheme = legacySidebar as SidebarTheme;
  }
  return Object.keys(legacy).length ? legacy : null;
}

/** 写入持久化主题对象：整对象覆盖写，保证三值同键不漂移 */
function writeStoredTheme(theme: StoredTheme): void {
  setStorageItem(THEME_STORAGE_KEY, theme, 'local');
}

/** 初始化：优先读新键；新键缺失时迁移旧的三键并立即落盘 */
function initTheme(): StoredTheme {
  const stored = getStorageItem<Partial<StoredTheme>>(THEME_STORAGE_KEY, 'local');
  if (stored) return normalizeTheme(stored);
  const legacy = readLegacyTheme();
  const migrated = normalizeTheme(legacy);
  if (legacy) writeStoredTheme(migrated); // 一次性迁移：旧分键归位到新单键
  return migrated;
}

/** 主题 Store 状态与 Action 定义 */
interface ThemeState extends StoredTheme {
  /** 设定主题模式并落盘（<html> class 切换由 ThemeSync 桥接 next-themes） */
  setThemeMode: (mode: ThemeMode) => void;
  /** 设定主色并落盘 */
  setThemeColor: (hex: string) => void;
  /** 设定侧栏视觉主题并落盘（外观由 SidebarNav 消费） */
  setSidebarTheme: (theme: SidebarTheme) => void;
  /** 恢复出厂默认（themeMode=system, themeColor=默认青蓝, sidebarTheme=square）并落盘 */
  themeReset: () => void;
}

export const useThemeStore = create<ThemeState>((set, get) => {
  const initial = initTheme();

  /** 整对象落盘：始终以最新内存态为准，避免三值分键时互相漂移 */
  const persistTheme = (): void => {
    const { themeMode, themeColor, sidebarTheme } = get();
    writeStoredTheme({ themeMode, themeColor, sidebarTheme });
  };

  return {
    ...initial,

    setThemeMode: (mode) => {
      set({ themeMode: mode });
      persistTheme();
    },

    setThemeColor: (hex) => {
      set({ themeColor: hex });
      persistTheme();
    },

    setSidebarTheme: (theme) => {
      set({ sidebarTheme: theme });
      persistTheme();
    },

    themeReset: () => {
      set({ ...DEFAULT_THEME });
      persistTheme();
    },
  };
});
