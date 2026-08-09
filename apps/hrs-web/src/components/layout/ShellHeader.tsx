/**
 * 顶部页头组件（ShellHeader）
 *
 * 固定在页面顶部的 sticky 导航栏，包含：
 * 1. 移动端菜单按钮（< lg 断点）：打开移动端侧边导航
 * 2. 桌面端侧边栏折叠/展开按钮（>= lg 断点）
 * 3. 当前路由的标题 + 描述（根据路径从 TITLES 映射表查询）
 * 4. 语言切换 + 主题切换按钮
 *
 * 注意：此组件当前未在 Shell.tsx 中使用，但作为备选布局保留。
 */
import type React from 'react';
import { Menu, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { useLocation } from 'react-router-dom';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import type { UiTextKey } from '../../i18n/uiText';
import { UiLanguageToggle } from '../i18n/UiLanguageToggle';
import { ThemeToggle } from '../theme/ThemeToggle';

type ShellHeaderProps = {
  /** 侧边栏是否处于折叠状态 */
  collapsed: boolean;
  /** 切换侧边栏折叠/展开 */
  onToggleSidebar: () => void;
  /** 打开移动端导航抽屉 */
  onOpenMobileNav: () => void;
};

/**
 * 路由路径 -> 页面标题/描述的映射表
 * key 为路由路径，value 包含 title 和 description 两个 i18n key
 * 当路径不在映射表中时，回退到 appFallbackTitle / appFallbackDescription
 */
const TITLES: Record<string, { title: UiTextKey; description: UiTextKey }> = {
  '/': { title: 'layout.route.home.title', description: 'layout.route.home.description' },
  '/sector-analysis': { title: 'layout.route.sectorAnalysis.title', description: 'layout.route.sectorAnalysis.description' },
  '/chat': { title: 'layout.route.chat.title', description: 'layout.route.chat.description' },
  '/portfolio': { title: 'layout.route.portfolio.title', description: 'layout.route.portfolio.description' },
  '/screening': { title: 'layout.route.screening.title', description: 'layout.route.screening.description' },
  '/backtest': { title: 'layout.route.backtest.title', description: 'layout.route.backtest.description' },
  '/alerts': { title: 'layout.route.alerts.title', description: 'layout.route.alerts.description' },
  '/usage': { title: 'layout.route.usage.title', description: 'layout.route.usage.description' },
  '/settings': { title: 'layout.route.settings.title', description: 'layout.route.settings.description' },
};

export const ShellHeader: React.FC<ShellHeaderProps> = ({
  collapsed,
  onToggleSidebar,
  onOpenMobileNav,
}) => {
  const location = useLocation();
  const { t } = useUiLanguage();
  // 根据当前路径查找标题配置，未匹配时为 undefined
  const current = TITLES[location.pathname];

  return (
    <header className="sticky top-0 z-30 border-b border-border/60 bg-background/84 backdrop-blur-xl">
      <div className="mx-auto flex h-16 w-full max-w-[1680px] items-center gap-3 px-4 sm:px-6 lg:px-8">
        {/* 移动端菜单按钮（< lg 断点显示） */}
        <button
          type="button"
          onClick={onOpenMobileNav}
          className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-border/70 bg-card/70 text-secondary-text transition-colors hover:bg-hover hover:text-foreground lg:hidden"
          aria-label={t('layout.openNav')}
        >
          <Menu className="h-5 w-5" />
        </button>

        {/* 桌面端侧边栏折叠/展开按钮（>= lg 断点显示） */}
        <button
          type="button"
          onClick={onToggleSidebar}
          className="hidden h-10 w-10 items-center justify-center rounded-xl border border-border/70 bg-card/70 text-secondary-text transition-colors hover:bg-hover hover:text-foreground lg:inline-flex"
          aria-label={collapsed ? t('layout.expandSidebar') : t('layout.collapseSidebar')}
        >
          {/* 折叠时显示展开图标，展开时显示折叠图标 */}
          {collapsed ? <PanelLeftOpen className="h-5 w-5" /> : <PanelLeftClose className="h-5 w-5" />}
        </button>

        {/* 当前路由标题 + 描述 */}
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-foreground">{current ? t(current.title) : t('layout.appFallbackTitle')}</p>
          <p className="truncate text-xs text-secondary-text">{current ? t(current.description) : t('layout.appFallbackDescription')}</p>
        </div>

        {/* 语言切换 + 主题切换 */}
        <UiLanguageToggle />
        <ThemeToggle />
      </div>
    </header>
  );
};
