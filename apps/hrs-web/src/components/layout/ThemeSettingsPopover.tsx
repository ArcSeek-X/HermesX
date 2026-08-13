/**
 * ThemeSettingsPopover
 *
 * 主题设置弹窗：包含「主题模式（浅色/暗色/跟随系统）」与「主色配置」两部分。
 * 主色通过 useThemeColor 写入 --primary 并持久化到 localStorage，全局联动生效。
 *
 * 层级处理：弹层通过 createPortal 渲染到 document.body，并用 fixed 定位，
 * 避免被父级（如 <header class="z-30">）的 stacking context / overflow 影响层级，
 * 确保弹层始终在页面所有内容之上。
 */
import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Palette } from 'lucide-react';
import { motion } from 'motion/react';
import { useTheme } from 'next-themes';
import { cn } from '../../utils/cn';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { useThemeColor } from '../../hooks/useThemeColor';
import { ColorPicker } from '../basic/ColorPicker';
import { Button } from '../basic/Button';

/** 主题模式选项 */
const THEME_MODES = [
  { value: 'light', labelKey: 'theme.light' as const },
  { value: 'dark', labelKey: 'theme.dark' as const },
  { value: 'system', labelKey: 'theme.system' as const },
];

/** 主色预设色板（覆盖中性色、语义色与项目主色系） */
const PRIMARY_PRESETS = [
  '#19B5C4', // 项目青蓝（暗色默认）
  '#2C78CD', // 主蓝
  '#6366F1', // 靛蓝
  '#8B5CF6', // 紫
  '#EC4899', // 粉
  '#EF4444', // 红
  '#F59E0B', // 橙
  '#10B981', // 绿
  '#14B8A6', // 蓝绿
  '#64748B', // 灰蓝
];

export const ThemeSettingsPopover = () => {
  const { t } = useUiLanguage();
  const { theme, setTheme } = useTheme();
  const { color, setColor, reset } = useThemeColor();
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  // 弹层定位：top 紧贴触发按钮底部、right 与按钮右边缘对齐
  const [popoverStyle, setPopoverStyle] = useState<{ top: number; right: number } | null>(null);

  useEffect(() => setMounted(true), []);

  /** 依据触发按钮的位置计算弹层 fixed 定位 */
  const updatePopoverPosition = () => {
    const btn = triggerRef.current;
    if (!btn) {
      setPopoverStyle(null);
      return;
    }
    const rect = btn.getBoundingClientRect();
    setPopoverStyle({
      top: rect.bottom + 8,  // 紧贴按钮下沿 + 8px 间隔
      right: window.innerWidth - rect.right, // 弹层右边缘与按钮右边缘对齐
    });
  };

  // 点击外部 / Esc 关闭
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: MouseEvent) => {
      const target = e.target as Node;
      // 点击触发按钮或弹层内部均不算"外部"（弹层在 portal 中，需显式判断自身 DOM）
      if (triggerRef.current && triggerRef.current.contains(target)) return;
      if (popoverRef.current && popoverRef.current.contains(target)) return;
      setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  // 打开时计算位置，并监听滚动/缩放实时更新
  useEffect(() => {
    if (!open) {
      setPopoverStyle(null);
      return;
    }
    const frameId = window.requestAnimationFrame(updatePopoverPosition);
    window.addEventListener('resize', updatePopoverPosition);
    window.addEventListener('scroll', updatePopoverPosition, true);
    return () => {
      window.cancelAnimationFrame(frameId);
      window.removeEventListener('resize', updatePopoverPosition);
      window.removeEventListener('scroll', updatePopoverPosition, true);
    };
  }, [open]);

  const activeMode = mounted ? theme ?? 'system' : 'system';

  return (
    <div className="hrs-theme-setting relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={t('header.themeSettings')}
        title={t('header.themeSettings')}
        aria-haspopup="dialog"
        aria-expanded={open}
        className="inline-flex h-9 w-9 items-center justify-center rounded-[10px] border border-border/70 bg-card/80 text-secondary-text shadow-soft-card transition-colors hover:bg-hover hover:text-foreground"
      >
        <Palette className="h-4 w-4" />
      </button>

      {/* 弹层：portal 到 body + fixed 定位 + z-[130]，脱离父 stacking context 与 overflow 限制 */}
      {open && popoverStyle && typeof document !== 'undefined' && createPortal(
        <div
          role="dialog"
          aria-label={t('header.themeSettings')}
          className="hrs-theme-popover fixed z-[130] w-[360px] rounded-xl border border-border/80 bg-card p-4 shadow-lg"
          ref={popoverRef}
          style={{ top: popoverStyle.top, right: popoverStyle.right }}
        >
          <div className="mb-3 text-xs font-medium text-muted-text">{t('theme.menu')}</div>
          <div className="theme-mode-switch relative mb-4 flex items-center gap-1 rounded-lg border border-subtle bg-bg-elevated p-1">
            {THEME_MODES.map((mode) => {
              const active = activeMode === mode.value;
              return (
                <button
                  key={mode.value}
                  type="button"
                  onClick={() => setTheme(mode.value)}
                  className={cn(
                    'theme-mode-item relative z-10 flex-1 rounded-md px-2 py-1.5 text-xs !text-xs font-medium transition-colors',
                    active ? 'text-cyan' : 'text-muted-text hover:text-foreground'
                  )}
                >
                  {active && (
                    <motion.span
                      layoutId="theme-mode-highlight"
                      aria-hidden
                      className="pointer-events-none absolute inset-0 rounded-md bg-cyan/15"
                      transition={{ type: 'spring', stiffness: 400, damping: 32 }}
                    />
                  )}
                  <span className="relative z-10">{t(mode.labelKey)}</span>
                </button>
              );
            })}
          </div>

          <div className="mb-2 text-xs font-medium text-muted-text">{t('theme.primary')}</div>
          <ColorPicker
            value={color}
            onChange={setColor}
            presets={PRIMARY_PRESETS}
            showPreviewDot
            className="w-full [&_.react-colorful]:!w-full [&_.react-colorful-wrapper]:w-full"
          />
          <div className="mt-3 flex justify-end gap-3">
            <Button
              type="button" variant="settings-primary" onClick={() => {}}>
              {t('theme.save')}
            </Button>
            <Button type="button" variant="settings-secondary" onClick={reset}>
              {t('theme.reset')}
            </Button>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
};