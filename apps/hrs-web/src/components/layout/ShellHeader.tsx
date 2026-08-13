/**
 * 顶部页头组件（ShellHeader）
 *
 * 固定在右侧列顶部（h-12），滚动发生在兄弟元素 hrs-page-container 上，
 * 因此 header 天然不随内容区滚动。
 * 内部内容撑满父容器宽度。
 *
 * 包含：
 * 1. 移动端菜单按钮（< lg 断点）：打开移动端侧边导航
 * 2. 桌面端侧边栏折叠/展开按钮（>= lg 断点）
 * 3. 当前路由的标题 + 描述（根据路径从 TITLES 映射表查询）
 * 4. 右侧操作区：主题设置、中英文切换、个人设置（齿轮）
 *
 * 注意：此组件在 Shell.tsx 的右侧列中使用，作为右侧内容区的顶部页头。
 */
import type React from 'react';
import { useState } from 'react';
import { Menu, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import type { UiTextKey } from '../../i18n/uiText';
import { ThemeSettingsPopover } from './ThemeSettingsPopover';
import { UserMenu } from './UserMenu';
import { LanguageMenu } from './LanguageMenu';
import { StockAutocomplete } from '../StockAutocomplete/StockAutocomplete';
import { setStorageItem } from '../../utils/storage';
import { cn } from '../../utils/cn';

type ShellHeaderProps = {
  /** 侧边栏是否处于折叠状态 */
  collapsed: boolean;
  /** 切换侧边栏折叠/展开 */
  onToggleSidebar: () => void;
  /** 打开移动端导航抽屉 */
  onOpenMobileNav: () => void;
  /** 自定义类名，追加到根 header 元素，用于个性化样式覆盖 */
  className?: string;
};

/**
 * 路由路径 -> 页面标题/描述的映射表
 * key 为路由路径，value 包含 title 和 description 两个 i18n key
 * 当路径不在映射表中时，回退到 appFallbackTitle / appFallbackDescription
 */
const TITLES: Record<string, { title: UiTextKey; description: UiTextKey }> = {
  '/home': { title: 'layout.route.home.title', description: 'layout.route.home.description' },
  '/stock-dashboard': { title: 'layout.route.dashboard.title', description: 'layout.route.dashboard.description' },
  '/sector-analysis': { title: 'layout.route.sectorAnalysis.title', description: 'layout.route.sectorAnalysis.description' },
  '/kline': { title: 'layout.route.kline.title', description: 'layout.route.kline.description' },
  '/chat': { title: 'layout.route.chat.title', description: 'layout.route.chat.description' },
  '/portfolio': { title: 'layout.route.portfolio.title', description: 'layout.route.portfolio.description' },
  '/decision-signals': { title: 'layout.route.decisionSignals.title', description: 'layout.route.decisionSignals.description' },
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
  className,
}) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useUiLanguage();
  // 根据当前路径查找标题配置，未匹配时为 undefined
  const current = TITLES[location.pathname];

  // 头部股票搜索框：提交后将规范代码写入 sessionStorage（与 K 线页共享键）并跳转 /kline
  const [stockQuery, setStockQuery] = useState('');

  return (
    <header className={cn('hrs-header z-30 h-14 border-b border-border/60 bg-background backdrop-blur-xl', className)}>
      <div className="flex h-full w-full items-center gap-3">
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

        {/* 右侧操作区：股票搜索 / 主题设置 / 中英文切换 / 个人设置 */}
        <div className="flex items-center gap-2">
          <StockAutocomplete
            value={stockQuery}
            onChange={setStockQuery}
            onSubmit={(code) => {
              if (!code) return;
              // 写入 sessionStorage（与 StockKLinePage 共享的 useCachedState 键），跳转后由 K 线页加载数据
              setStorageItem('kline.stockCode', code, 'session');
              setStockQuery('');
              navigate('/kline');
            }}
            onClear={() => setStockQuery('')}
            placeholder={t('kline.searchPlaceholder')}
            ariaLabel={t('kline.searchPlaceholder')}
            className="!h-9 !text-xs w-60 lg:w-56 !rounded-[10px] !border-border/70 !bg-card/80 !shadow-soft-card focus:!border-border/70"
          />
          <ThemeSettingsPopover />
          <LanguageMenu />
          <UserMenu />
        </div>
      </div>
    </header>
  );
};
