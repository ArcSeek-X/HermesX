/**
 * 主题切换组件（ThemeToggle）
 *
 * 提供浅色 / 暗色 / 跟随系统三种主题切换能力，以弹出菜单形式呈现。
 *
 * 支持三种展示形态（variant）：
 * - default：独立按钮模式，右上角浮动（用于移动端顶栏）
 * - nav：导航项模式，与侧边栏导航项样式一致（用于移动端抽屉）
 * - rail：精简轨道模式，图标居中（用于桌面端固定侧边栏）
 *
 * 交互逻辑：
 * 1. 点击触发按钮展开下拉菜单
 * 2. 菜单展示三个选项（浅色/暗色/系统），当前选中项带勾选标记
 * 3. 点击选项后立即切换主题并关闭菜单
 * 4. 点击组件外部区域自动关闭菜单
 *
 * 主题状态来源：next-themes 的 useTheme()
 * - theme：用户选择的主题偏好（light / dark / system）
 * - resolvedTheme：实际生效的主题（system 模式下解析为 light 或 dark）
 */
import type React from 'react';
import { useEffect, useRef, useState } from 'react';
import { Check, Monitor, Moon, Sun } from 'lucide-react';
import { useTheme } from 'next-themes';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import type { UiTextKey } from '../../i18n/uiText';
import { cn } from '../../utils/cn';

/** 可选主题值 */
type ThemeOption = 'light' | 'dark' | 'system';
/** 组件展示形态 */
type ThemeToggleVariant = 'default' | 'nav' | 'rail';

/**
 * 主题选项配置列表
 * 用于渲染下拉菜单中的三个选项
 */
const THEME_OPTIONS: Array<{
  value: ThemeOption;
  labelKey: UiTextKey;
  icon: typeof Sun;
}> = [
  { value: 'light', labelKey: 'theme.light', icon: Sun },
  { value: 'dark', labelKey: 'theme.dark', icon: Moon },
  { value: 'system', labelKey: 'theme.system', icon: Monitor },
];

/**
 * 将主题值解析为国际化文案
 * 未匹配的值（含 undefined）回退为"跟随系统"
 */
function resolveThemeLabel(theme: string | undefined, t: (key: UiTextKey) => string) {
  switch (theme) {
    case 'light':
      return t('theme.light');
    case 'dark':
      return t('theme.dark');
    default:
      return t('theme.system');
  }
}

interface ThemeToggleProps {
  /** 展示形态：default=独立按钮，nav=导航项，rail=精简轨道 */
  variant?: ThemeToggleVariant;
  /** 是否折叠（仅显示图标，隐藏文字），用于 nav 和 rail 模式 */
  collapsed?: boolean;
  /** 外层容器自定义样式类名 */
  wrapperClassName?: string;
  /** 触发按钮自定义样式类名（传入时覆盖默认样式） */
  triggerClassName?: string;
  /** 触发按钮激活（菜单展开）时的自定义样式类名 */
  triggerActiveClassName?: string;
  /** 图标自定义样式类名 */
  iconClassName?: string;
  /** 文字标签自定义样式类名 */
  labelClassName?: string;
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({
  variant = 'default',
  collapsed = false,
  wrapperClassName,
  triggerClassName,
  triggerActiveClassName,
  iconClassName,
  labelClassName,
}) => {
  // theme=用户选择的主题偏好，resolvedTheme=实际生效主题，setTheme=切换主题
  const { theme, resolvedTheme, setTheme } = useTheme();
  const { t } = useUiLanguage();
  // 下拉菜单是否展开
  const [open, setOpen] = useState(false);
  // 外层容器引用，用于判断点击是否在组件外部
  const containerRef = useRef<HTMLDivElement | null>(null);

  /**
   * 监听全局点击事件：
   * 菜单展开时，点击组件外部区域自动关闭菜单
   */
  useEffect(() => {
    if (!open) {
      return undefined;
    }

    const handlePointerDown = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    document.addEventListener('mousedown', handlePointerDown);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
    };
  }, [open]);

  // 用户选择的主题偏好（未设置时回退为 system）
  const activeTheme = (theme as ThemeOption | undefined) ?? 'system';
  // 实际生效的视觉主题（system 模式下会解析为 light 或 dark）
  const visualTheme = resolvedTheme ?? 'dark';
  // 触发按钮图标：浅色显示太阳，暗色显示月亮
  const TriggerIcon = visualTheme === 'light' ? Sun : Moon;
  const isNavVariant = variant === 'nav';
  const isRailVariant = variant === 'rail';

  return (
    <div className={cn('relative', isRailVariant ? 'w-full' : '', wrapperClassName)} ref={containerRef}>
      {/* ===== 触发按钮 ===== */}
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        data-state={open ? 'open' : 'closed'}
        className={cn(
          // 优先使用外部传入的自定义样式，否则按 variant 使用默认样式
          triggerClassName
            ? triggerClassName
            : isRailVariant
              ? 'flex h-[var(--nav-item-height)] w-full items-center justify-center gap-2.5 rounded-2xl border border-transparent px-2 text-sm leading-none text-secondary-text transition-all hover:bg-[var(--nav-hover-bg)] hover:text-foreground data-[state=open]:border-[var(--nav-active-border)] data-[state=open]:bg-[var(--nav-active-bg)] data-[state=open]:text-[hsl(var(--primary))]'
              : isNavVariant
                ? 'group relative flex h-12 w-full select-none items-center gap-3 rounded-[1.35rem] border border-transparent px-4 text-sm text-secondary-text transition-all duration-300 hover:bg-hover hover:text-foreground data-[state=open]:border-subtle data-[state=open]:bg-subtle data-[state=open]:text-foreground'
                : 'inline-flex h-10 items-center gap-2 rounded-xl border border-border/70 bg-card/80 px-3 text-sm text-secondary-text shadow-soft-card transition-colors hover:bg-hover hover:text-foreground',
          // 菜单展开时追加激活样式
          triggerClassName && open ? triggerActiveClassName : '',
          // nav 模式折叠时居中
          isNavVariant && collapsed ? 'justify-center px-2' : ''
        )}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={t('theme.toggle')}
      >
        <TriggerIcon className={iconClassName ?? cn('shrink-0', isRailVariant ? 'h-[18px] w-[18px]' : isNavVariant ? 'h-5 w-5' : 'h-4 w-4')} />
        {/* 文字标签：根据 variant 和 collapsed 状态决定显示内容 */}
        {isRailVariant ? (
          <span className={cn('text-sm', labelClassName ?? 'truncate')}>{t('theme.theme')}</span>
        ) : isNavVariant ? (
          collapsed ? null : <span className={cn('text-sm', labelClassName ?? 'truncate')}>{t('theme.theme')}</span>
        ) : (
          <span className="hidden sm:inline">{resolveThemeLabel(activeTheme, t)}</span>
        )}
      </button>

      {/* ===== 下拉菜单 ===== */}
      {open ? (
        <div
          role="menu"
          aria-label={t('theme.menu')}
          className={cn(
            'z-[100] min-w-[8rem] overflow-hidden rounded-2xl border border-border/70 bg-elevated p-1.5 shadow-[0_24px_48px_rgba(3,8,20,0.32)] backdrop-blur-xl',
            // nav/rail 模式菜单向上弹出（底部空间不足），default 模式向下弹出
            isNavVariant || isRailVariant
              ? 'absolute bottom-full left-0 mb-2 w-max min-w-[9rem]'
              : 'absolute right-0 mt-2'
          )}
        >
          {THEME_OPTIONS.map(({ value, labelKey, icon: Icon }) => {
            const isActive = activeTheme === value;
            return (
              <button
                key={value}
                type="button"
                role="menuitemradio"
                aria-checked={isActive}
                onClick={() => {
                  setTheme(value);
                  setOpen(false);
                }}
                className={cn(
                  'flex w-full items-center justify-between rounded-xl px-3 py-2 text-sm transition-colors',
                  // 选中项高亮，非选中项 hover 变亮
                  isActive
                    ? 'bg-cyan/10 text-foreground'
                    : 'text-secondary-text hover:bg-hover hover:text-foreground'
                )}
              >
                <span className="flex items-center gap-2">
                  <Icon className="h-4 w-4" />
                  {t(labelKey)}
                </span>
                {/* 选中项显示勾选标记 */}
                {isActive ? <Check className="h-4 w-4 text-cyan" /> : null}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
};
