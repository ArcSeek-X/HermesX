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
import { ThemeSetting } from './HeaderComponents/ThemeSetting';
import { UserSetting } from './HeaderComponents/UserSetting';
import { LanguageSwitch } from './HeaderComponents/LanguageSwitch';
import { StockSearch } from '../StockSearch/StockSearch';
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
/**
 * 路径 -> 顶栏标题/描述的映射。
 *
 * **顺序与 SidebarNav 的 NAV_ITEMS 保持一致**（便于对照维护）；
 * 未命中的路径会回退到兜底标题，因此新增菜单项时务必同步登记，
 * /settings 不在主菜单中（由用户菜单进入），置于末尾。
 */
const TITLES: Record<string, { title: UiTextKey; description: UiTextKey }> = {
  '/home': { title: 'layout.nav.home.title', description: 'layout.nav.home.description' },
  '/stock-dashboard': { title: 'layout.nav.dashboard.title', description: 'layout.nav.dashboard.description' },
  '/sector-analysis': { title: 'layout.nav.sectorAnalysis.title', description: 'layout.nav.sectorAnalysis.description' },
  '/watchlist': { title: 'layout.nav.watchlist.title', description: 'layout.nav.watchlist.description' },
  '/live-news': { title: 'layout.nav.liveNews.title', description: 'layout.nav.liveNews.description' },
  '/kline': { title: 'layout.nav.kline.title', description: 'layout.nav.kline.description' },
  '/chat': { title: 'layout.nav.chat.title', description: 'layout.nav.chat.description' },
  '/review': { title: 'layout.nav.review.title', description: 'layout.nav.review.description' },
  '/portfolio': { title: 'layout.nav.portfolio.title', description: 'layout.nav.portfolio.description' },
  '/decision-signals': { title: 'layout.nav.decisionSignals.title', description: 'layout.nav.decisionSignals.description' },
  '/backtest': { title: 'layout.nav.backtest.title', description: 'layout.nav.backtest.description' },
  '/alerts': { title: 'layout.nav.alerts.title', description: 'layout.nav.alerts.description' },
  '/usage': { title: 'layout.nav.usage.title', description: 'layout.nav.usage.description' },
  '/screening': { title: 'layout.nav.screening.title', description: 'layout.nav.screening.description' },
  '/codeTest': { title: 'layout.nav.codeTest.title', description: 'layout.nav.codeTest.description' },
  '/settings': { title: 'layout.nav.settings.title', description: 'layout.nav.settings.description' },
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
          <StockSearch
            value={stockQuery}
            size="sm"
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
            className="h-9 text-xs w-60"
          />
           
          {/* <StockSearch
            value={stockQuery}
            size="sm"
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
            className="h-9 text-xs w-60"
          />
           
          <StockSearch
            value={stockQuery}
            size="xl"
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
            className="h-9 text-xs w-60"
          /> */}
          <ThemeSetting />
          <LanguageSwitch />
          <UserSetting/>
        </div>
      </div>
    </header>
  );
};
