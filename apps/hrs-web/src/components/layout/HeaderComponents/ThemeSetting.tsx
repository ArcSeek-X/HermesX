/**
 * ThemeSetting
 *
 * 主题设置弹窗：包含「主题模式（浅色/暗色/跟随系统）」与「主色配置」两部分。
 * 主题模式 / 主色由 themeStore（Zustand）统一管理并持久化；本组件作为使用层从 store 读取，
 * 向基础组件（TabNav / ColorPicker）传 props：操作即预览、点「保存」才提交到 store 落库。
 *
 * 层级处理：弹层通过 createPortal 渲染到 document.body，并用 fixed 定位，
 * 避免被父级（如 <header class="z-30">）的 stacking context / overflow 影响层级，
 * 确保弹层始终在页面所有内容之上。
 *
 * @author Lensgcx (GaoCangxiong)
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Palette } from 'lucide-react';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import { useThemeStore } from '../../../stores/themeStore';
import type { ThemeMode, SidebarTheme } from '../../../types/theme';
import { applyPrimaryColor, applyModePreview } from '../../../utils/themeColor';
import { Button,ColorPicker,TabNav } from '../../index';


/** 主题模式选项 */
const THEME_MODES = [
  { value: 'light', labelKey: 'theme.themeMode.light' as const },
  { value: 'dark', labelKey: 'theme.themeMode.dark' as const },
  { value: 'system', labelKey: 'theme.themeMode.system' as const },
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

/** 侧栏视觉主题选项（驱动 SidebarNav 外观，与明暗模式正交） */
const SIDEBAR_THEMES = [
  { value: 'pill',   labelKey: 'theme.sidebarTheme.pill' as const },
  { value: 'square', labelKey: 'theme.sidebarTheme.square' as const },
];

/**
 * 切换主题时的"过渡抑制"机关（suppress / restore 一对函数）。
 * ---------------------------------------------------------------------------
 * 背景（为什么需要）：
 *   正式链路 setThemeMode -> ThemeSync -> next-themes 由 disableTransitionOnChange
 *   负责在切换瞬间禁用过渡；但弹层内的预览路径走的是 applyModePreview / applyPrimaryColor
 *   直接改 <html> 的 light/dark class 与 --primary，完全绕过 next-themes，于是
 *   disableTransitionOnChange 不生效 —— 切换瞬间部分元素瞬变、部分元素仍走 CSS
 *   过渡渐变，产生视觉时间差。这里手工复刻 next-themes 的"切换瞬间禁用过渡"行为，
 *   让预览与正式切换的视觉表现一致。
 * 机制：切换前把一条全局 transition:none 的 <style> 注入 <head>，切换后下一帧移除。
 */
let noTransitionStyle: HTMLStyleElement | null = null;
/** 切换前调用：临时禁用全站过渡/动画（保留 TabNav 指示条滑动），消除预览切换的时间差 */
function suppressThemeTransition(): void {
  if (typeof document === 'undefined') return; // SSR 安全：服务端无 DOM，直接跳过，避免报错
  if (!noTransitionStyle) {
    // 懒创建单例 style 节点（模块级复用，避免每次预览都 createElement + 重复插入）
    noTransitionStyle = document.createElement('style');
    noTransitionStyle.textContent =
      // 全局杀掉过渡与动画：颜色/背景/边框等一律瞬变，不渐变，消除时间差
      '*,*::before,*::after{transition:none!important;animation:none!important}' +
      // 例外：TabNav 指示条只做 transform 位移，不在主题换色范围，单独放开其滑动动画
      '[data-slot="tabs-indicator"]{transition:transform 200ms ease!important}';
  }
  document.head.appendChild(noTransitionStyle);
  // 强制同步重排（读 offsetHeight 触发 reflow）：让"过渡已禁用"这个样式在
  // 下方 applyModePreview / applyPrimaryColor 改 <html> class 之前先生效，
  // 否则插入 style 与改 class 落在同一帧、浏览器可能合并渲染，仍会闪一下
  void document.documentElement.offsetHeight;
}

/** 切换后（requestAnimationFrame 中）调用：移除注入的 style，恢复全站过渡/动画 */
function restoreThemeTransition(): void {
  if (noTransitionStyle && noTransitionStyle.parentNode) {
    noTransitionStyle.parentNode.removeChild(noTransitionStyle);
  }
}

export const ThemeSetting = () => {
  const { t } = useUiLanguage();
  // 已保存真值（last-saved）：来自 Zustand，刷新/切换后保持
  const { themeMode, themeColor, sidebarTheme, setThemeMode, setThemeColor, setSidebarTheme } = useThemeStore();
  // 弹层内预览草稿：操作即所见，仅点「保存」才提交到 store
  const [draftMode, setDraftMode] = useState<ThemeMode>(themeMode);
  const [draftColor, setDraftColor] = useState<string>(themeColor);
  // 侧栏视觉主题草稿：与主题模式/主色同走 draft + 保存，避免未提交即作用到真实侧栏（侧栏在弹层背后，无法实时 DOM 预览）
  const [draftSidebarTheme, setDraftSidebarTheme] = useState<SidebarTheme>(sidebarTheme);
  // 预览应用：把 draft 即时写到 DOM（切 <html> class + 改 --primary），不落库
  const applyPreview = useCallback(
    (m: ThemeMode, c: string) => {
      // 预览前临时禁用全局过渡（与 next-themes disableTransitionOnChange 对齐），
      // 避免切换瞬间各元素过渡不一致产生时间差；指示条 transform 滑动单独保留。
      suppressThemeTransition();
      applyModePreview(m);
      applyPrimaryColor(c);
      requestAnimationFrame(restoreThemeTransition);
    },
    []
  );
  const [open, setOpen] = useState(false); // 弹层开关：true 时渲染主题设置弹层
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  // 打开：草稿初始化为「上次保存的状态」；关闭：丢弃预览、DOM 还原为已保存值
  useEffect(() => {
    if (!open) {
      setDraftMode(themeMode);
      setDraftColor(themeColor);
      setDraftSidebarTheme(sidebarTheme);
      applyPreview(themeMode, themeColor);
    }
    // 仅依赖 open：关闭时用闭包里的 store 当前值（即 last-saved）还原
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);
  // 弹层定位：top 紧贴触发按钮底部、right 与按钮右边缘对齐
  const [popoverStyle, setPopoverStyle] = useState<{ top: number; right: number } | null>(null); // 弹层 fixed 定位坐标（top/right），null 表示尚未计算

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



  return (
    <div className="hrs-theme-setting relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={t('layout.header.themeSettings')}
        title={t('layout.header.themeSettings')}
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
          aria-label={t('layout.header.themeSettings')}
          className="hrs-theme-popover fixed z-[130] w-[360px] rounded-xl border border-border/80 bg-card p-4 shadow-lg"
          ref={popoverRef}
          style={{ top: popoverStyle.top, right: popoverStyle.right }}
        >
          <div className="mb-3 text-xs font-medium text-muted-text">{t('theme.themeMode.settingTitle')}</div>

          <TabNav
            items={THEME_MODES.map((mode) => ({ value: mode.value, label: t(mode.labelKey) }))}
            value={draftMode}
            onChange={(m) => {
              setDraftMode(m as ThemeMode);
              applyPreview(m as ThemeMode, draftColor);
            }}
            variant="primary"
            ariaLabel={t('theme.themeMode.settingTitle')}
            className='mb-3'
            tabsClassName="theme-mode-switch w-full"
          />


          <div className="mb-2 text-xs font-medium text-muted-text">{t('theme.themeColor.settingTitle')}</div>

          <ColorPicker
            value={draftColor}
            onChange={(c) => {
              setDraftColor(c);
              applyPreview(draftMode, c);
            }}
            presets={PRIMARY_PRESETS}
            showPreviewDot
            className="w-full [&_.react-colorful]:!w-full [&_.react-colorful-wrapper]:w-full"
          />

          {/* 侧栏风格：与主题模式/主色同走 draft，保存后才作用到真实侧栏；
              预览用下方缩略示意（pill/square 长相随 draft 即时切换），弹层背后的真实侧栏不实时变 */}
          <div className="mb-2 mt-1 text-xs font-medium text-muted-text">{t('theme.sidebarTheme.settingTitle')}</div>

          <TabNav
            items={SIDEBAR_THEMES.map((opt) => ({ value: opt.value, label: t(opt.labelKey) }))}
            value={draftSidebarTheme}
            onChange={(v) => setDraftSidebarTheme(v as SidebarTheme)}
            variant="primary"
            ariaLabel={t('theme.sidebarTheme.settingTitle')}
            className="mb-3"
            tabsClassName="theme-sidebar-switch w-full"
          />

          {/* 缩略预览：随 draft 即时切换，示意 pill（大圆角胶囊）/ square（方角） */}
          <div className="mb-3 flex items-center justify-center rounded-lg border border-border/60 bg-card/50 p-3">
            <div
              className={
                draftSidebarTheme === 'pill'
                  ? 'h-24 w-12 overflow-hidden rounded-2xl border border-primary/30 bg-background shadow-[0_4px_12px_-4px_hsl(var(--primary)/0.3)]'
                  : 'h-24 w-12 overflow-hidden rounded-none border-r border-border bg-background'
              }
            >
              <div className="m-1.5 space-y-1.5">
                <div className="h-3 rounded bg-foreground/10" />
                <div className="h-3 rounded bg-foreground/10" />
                <div className="h-3 rounded bg-foreground/10" />
              </div>
            </div>
          </div>

          <div className="mt-3 flex justify-end gap-3">
            <Button
              type="button" variant="settings-primary"
              onClick={() => {
                setThemeMode(draftMode);
                setThemeColor(draftColor);
                setSidebarTheme(draftSidebarTheme);
                setOpen(false);
              }}>
              {t('theme.save')}
            </Button>
            <Button
              type="button" variant="settings-secondary"
              onClick={() => {
                setDraftMode(themeMode);
                setDraftColor(themeColor);
                setDraftSidebarTheme(sidebarTheme);
                applyPreview(themeMode, themeColor);
              }}>
              {t('theme.reset')}
            </Button>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
};
