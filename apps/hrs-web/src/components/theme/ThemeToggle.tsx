/**
 * @file ThemeToggle.tsx
 * @description 主题循环切换按钮（图标点击式）。
 *
 * 交互：单一图标按钮，每次点击按「浅色 → 深色 → 跟随系统 → 浅色」循环切换。
 * - 图标表达当前选中的主题偏好：浅色=太阳、深色=月亮、跟随系统=显示器。
 * - 写入 useThemeStore.themeMode（唯一真值），由 ThemeSync 桥接 next-themes
 *   切换 <html> class 并联动 resolvedTheme，全站主题即时生效。
 *
 * 参考 LanguageSwitch 的「单一图标按钮 + 循环切换」形态，但将三语循环改为三主题循环。
 *
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-09-16
 */
import { Monitor, Moon, Sun, type LucideIcon } from 'lucide-react';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { useThemeStore } from '../../stores/themeStore';
import type { ThemeMode } from '../../types/theme';
import type { UiTextKey } from '../../i18n/uiText';

/** 主题循环选项：数组顺序即切换顺序（浅色 → 深色 → 跟随系统 → 浅色） */
const THEME_OPTIONS: Array<{ value: ThemeMode; labelKey: UiTextKey; icon: LucideIcon }> = [
  { value: 'light', labelKey: 'theme.themeMode.light', icon: Sun },
  { value: 'dark', labelKey: 'theme.themeMode.dark', icon: Moon },
  { value: 'system', labelKey: 'theme.themeMode.system', icon: Monitor },
];

export const ThemeToggle = () => {
  const { t } = useUiLanguage();
  // themeMode 是唯一真值（来自 store）；未设置时回退为 system
  const { themeMode, setThemeMode } = useThemeStore();
  const current: ThemeMode = themeMode ?? 'system';

  // 找到当前项，取循环顺序中的下一项（末尾回到开头）；未命中（异常值）回退首项
  const activeIndex = THEME_OPTIONS.findIndex((option) => option.value === current);
  const active = THEME_OPTIONS[activeIndex === -1 ? 0 : activeIndex];
  const next = THEME_OPTIONS[(activeIndex + 1) % THEME_OPTIONS.length];

  return (
    <button
      type="button"
      onClick={() => setThemeMode(next.value)}
      aria-label={t(active.labelKey)}
      title={t(active.labelKey)}
      className="inline-flex h-9 w-9 select-none items-center justify-center rounded-[10px] border border-border/70 bg-card/80 text-secondary-text shadow-soft-card transition-colors hover:bg-hover hover:text-foreground"
    >
      <active.icon className="h-[18px] w-[18px]" aria-hidden />
    </button>
  );
};
