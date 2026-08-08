/**
 * 应用外壳布局组件（Shell）
 *
 * 负责整体页面骨架的搭建，包含三部分：
 * 1. 移动端顶部浮动栏（菜单按钮 + 主题/语言切换），仅在 < lg 断点显示
 * 2. 桌面端固定侧边栏（aside），仅在 >= lg 断点显示
 * 3. 主内容区域（main），渲染 children 或 <Outlet />
 *
 * 移动端通过 Drawer 抽屉弹出侧边栏导航，桌面端则常驻显示侧边栏。
 * 当窗口从移动端宽度放大到桌面端宽度（>= 1024px）时，自动关闭抽屉。
 */
import type React from 'react';
import { useEffect, useState } from 'react';
import { Menu } from 'lucide-react';
import { Outlet } from 'react-router-dom';
import { Drawer } from '../common/Drawer';
import { SidebarNav } from './SidebarNav';
import { cn } from '../../utils/cn';
import { ThemeToggle } from '../theme/ThemeToggle';
import { UiLanguageToggle } from '../i18n/UiLanguageToggle';
import { useUiLanguage } from '../../contexts/UiLanguageContext';

type ShellProps = {
  children?: React.ReactNode;
};

export const Shell: React.FC<ShellProps> = ({ children }) => {
  // 移动端抽屉是否展开
  const [mobileOpen, setMobileOpen] = useState(false);
  // 侧边栏折叠状态（当前固定为展开，预留折叠能力）
  const collapsed = false;
  const { t } = useUiLanguage();

  /**
   * 监听窗口尺寸变化：
   * 当抽屉打开且窗口宽度放大到桌面端（>= 1024px）时，自动关闭抽屉，
   * 避免桌面端同时出现固定侧边栏和抽屉。
   */
  useEffect(() => {
    if (!mobileOpen) {
      return undefined;
    }

    const handleResize = () => {
      if (window.innerWidth >= 1024) {
        setMobileOpen(false);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [mobileOpen]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* ===== 移动端顶部浮动栏（< lg 断点）===== */}
      <div className="pointer-events-none fixed inset-x-0 top-3 z-40 flex items-start justify-between px-3 lg:hidden">
        {/* 菜单按钮：点击后打开移动端抽屉 */}
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          className="pointer-events-auto inline-flex h-10 w-10 items-center justify-center rounded-xl border border-border/70 bg-card/85 text-secondary-text shadow-soft-card backdrop-blur-md transition-colors hover:bg-hover hover:text-foreground"
          aria-label={t('layout.openNav')}
        >
          <Menu className="h-5 w-5" />
        </button>
        {/* 主题切换 + 语言切换：右上角浮动 */}
        <div className="pointer-events-auto flex items-center gap-2">
          <UiLanguageToggle />
          <ThemeToggle />
        </div>
      </div>

      {/* ===== 主体区域：侧边栏 + 内容区 ===== */}
      <div className="mx-auto flex min-h-screen w-full max-w-[1680px] px-3 py-3 sm:px-4 sm:py-4 lg:px-5">
        {/* 桌面端固定侧边栏（>= lg 断点） */}
        <aside
          className={cn(
            'sticky top-3 z-40 hidden shrink-0 overflow-visible rounded-[1.5rem] border border-[var(--shell-sidebar-border)] bg-card/72 p-2.5 shadow-soft-card backdrop-blur-sm transition-[width] duration-200 lg:flex',
            'max-h-[calc(100vh-1.5rem)] self-start sm:top-4 sm:max-h-[calc(100vh-2rem)]',
            collapsed ? 'w-[64px]' : 'w-[136px]'
          )}
          aria-label={t('layout.desktopSidebar')}
        >
          <SidebarNav collapsed={collapsed} variant="rail" onNavigate={() => setMobileOpen(false)} />
        </aside>

        {/* 主内容区域：优先渲染 children，否则渲染路由 <Outlet /> */}
        <main className="min-h-0 min-w-0 flex-1 pt-14 lg:pl-3 lg:pt-0 touch-pan-y">
          {children ?? <Outlet />}
        </main>
      </div>

      {/* ===== 移动端抽屉导航（从左侧滑出）===== */}
      <Drawer
        isOpen={mobileOpen}
        onClose={() => setMobileOpen(false)}
        title={t('layout.navMenu')}
        width="max-w-xs"
        zIndex={90}
        side="left"
      >
        <SidebarNav onNavigate={() => setMobileOpen(false)} />
      </Drawer>
    </div>
  );
};
