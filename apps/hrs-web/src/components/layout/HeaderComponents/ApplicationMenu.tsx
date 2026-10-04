/**
 * ApplicationMenu
 *
 * 头部「我的应用」下拉面板：点击触发按钮弹出应用入口列表（motion.div 动画）。
 * 应用数据来自 MenuStore 的 menuData（由 router/manifest.ts 真源构建），
 * 当前含 productModel（产品）与 developmentMode（开发调试）两个模块；
 * 模块级元数据（名称/图标/描述）随 menuData 一并下发，新增模块无需改此组件。
 *
 * 层级处理：弹层通过 createPortal 渲染到 document.body（fixed 定位），
 * 避免被父级（如 <header class="z-30">）的 stacking context / overflow 影响层级，
 * 确保弹层始终在页面所有内容之上（与 ThemeSetting 同一套路）。
 *
 * @author Lensgcx (GaoCangxiong)
 */
import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'motion/react';
import { LayoutGrid } from 'lucide-react';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import type { UiTextKey } from '../../../i18n/uiText';
import { useMenuStore } from '../../../stores/MenuStore';
import { menuIconRegistry } from '../SideBar/MenuIcon';

export const ApplicationMenu = () => {
  const { t } = useUiLanguage();
  // 与 ModeSwitch 同路：点击应用项时同步切换当前模块，首页跳转由 SidebarNav 监听
  // currentMenuData 变化的 effect 自动完成（无需在此显式 navigate，避免重复跳转）。
  const setCurrentModuleId = useMenuStore((s) => s.setCurrentModuleId);
  // 模块列表直接来自 MenuStore 的 menuData（与菜单数据同步，且已含模块名/图标/描述等元数据）。
  // menuData 在登录后由 buildMenuData 构建，未登录时为空，下拉自然为空。
  const menuData = useMenuStore((s) => s.menuData);
  const currentModuleId = useMenuStore((s) => s.currentModuleId);
  const modules = Object.values(menuData);



  // 弹层开关：true 时渲染我的应用下拉面板
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  // 弹层 fixed 定位坐标（top/left），null 表示尚未计算
  const [popoverStyle, setPopoverStyle] = useState<{ top: number; left: number } | null>(null);

  /** 依据触发按钮的位置计算弹层 fixed 定位（紧贴按钮下沿，左边缘对齐） */
  const updatePopoverPosition = () => {
    const btn = triggerRef.current;
    if (!btn) {
      setPopoverStyle(null);
      return;
    }
    const rect = btn.getBoundingClientRect();
    setPopoverStyle({
      top: rect.bottom + 8,
      left: rect.left,
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

  /** 模块文案：兼容 i18n key 与直写文案（与 ShellHeader 同一兜底策略） */
  const moduleText = (text: string | undefined) =>
    text ? t(text as UiTextKey) || text : '';

  return (
    <div className="relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={t('layout.header.myApps')}
        title={t('layout.header.myApps')}
        aria-haspopup="menu"
        aria-expanded={open}
        className="inline-flex h-9 select-none items-center justify-center gap-1.5 rounded-[10px] border border-border/70 bg-card/80 px-3 text-secondary-text shadow-soft-card transition-colors hover:bg-hover hover:text-foreground"
      >
        <LayoutGrid className="h-4 w-4" />
        <span
          aria-hidden
          className="hidden text-[12px] font-semibold leading-none tracking-tight sm:inline"
        >
          {t('layout.header.myApps')}
        </span>
      </button>

      {/* 弹层：portal 到 body + fixed 定位 + z-[130]，脱离父 stacking context 与 overflow 限制 */}
      {typeof document !== 'undefined' && createPortal(
        <AnimatePresence>
          {open && popoverStyle && (
            <motion.div
              ref={popoverRef}
              role="menu"
              aria-label={t('layout.header.myApps')}
              initial={{ opacity: 0, y: -6, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -6, scale: 0.98 }}
              transition={{ duration: 0.18, ease: 'easeOut' }}
              className="fixed z-[130] w-[340px] origin-top-left rounded-md border border-border/80 bg-card p-4 pt-2 mt-2 shadow-md"
              style={{ top: popoverStyle.top, left: popoverStyle.left }}
            >
              <div className="px-3 py-2 text-xs font-medium text-muted-text">{t('layout.header.myApps')}</div>
              <div className="grid grid-cols-2 gap-1">
                {modules.map((module) => {
                  const isActive = module.moduleId === currentModuleId;
                  const Icon = menuIconRegistry[module.moduleIcon ?? ''] ?? LayoutGrid;
                  return (
                    <button
                      key={module.moduleId}
                      type="button"
                      role="menuitem"
                      aria-current={isActive ? 'true' : undefined}
                      onClick={() => {
                        setOpen(false);
                        setCurrentModuleId(module.moduleId);
                      }}
                      className={`flex items-start gap-2.5 rounded-sm p-2.5 text-left transition-colors hover:bg-hover ${
                        isActive ? 'bg-primary/10 ring-1 ring-primary/30' : ''
                      }`}
                    >
                      <span className="mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <Icon className="h-4 w-4" />
                      </span>
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-medium text-foreground">
                          {moduleText(module.moduleName)}
                        </span>
                        {module.moduleDescription && (
                          <span className="mt-0.5 block truncate text-xs text-secondary-text">
                            {moduleText(module.moduleDescription)}
                          </span>
                        )}
                      </span>
                    </button>
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>,
        document.body
      )}
    </div>
  );
};
