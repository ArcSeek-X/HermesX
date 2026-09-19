/**
 * 顶部页头 ShellHeader（h-14，固定在右侧列顶部，不随内容滚动）
 *
 * 含：移动端菜单按钮（< lg）、桌面端侧栏折叠按钮（>= lg）、当前路由标题/描述
 * （查 ROUTE_META，与侧栏同源无需维护映射）、右侧操作区
 * （股票搜索 / 主题设置 / 语言切换 / 个人设置）。
 *
 * @author Lensgcx (GaoCangxiong)
 */
import type React from 'react';
import { useState } from 'react';
import { ChevronsLeft, Menu, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import type { UiTextKey } from '../../i18n/uiText';
import { useLayoutStore } from '../../stores';
import { ROUTE_META } from '../../router/routeMeta';
import { ThemeSetting } from './HeaderComponents/ThemeSetting';
import { UserSetting } from './HeaderComponents/UserSetting';
import { LanguageSwitch } from './HeaderComponents/LanguageSwitch';
import { ThemeToggle } from '../theme/ThemeToggle';
import { ModeSwitch } from './HeaderComponents/ModeSwitch';
import { StockSearch } from '../StockSearch/StockSearch';
import { setStorageItem } from '../../utils/storage';
import { cn } from '../../utils/cn';

type ShellHeaderProps = {
  /** 切换侧边栏折叠状态（按 offcanvas → collapsed → fully 循环） */
  onToggleSidebar: () => void;
  /** 打开移动端导航抽屉 */
  onOpenMobileNav: () => void;
  /** 自定义类名，追加到根 header 元素，用于个性化样式覆盖 */
  className?: string;
};

export const ShellHeader: React.FC<ShellHeaderProps> = ({
  onToggleSidebar,
  onOpenMobileNav,
  className,
}) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useUiLanguage();
  // 折叠态直接订阅 store（决定折叠按钮的图标与无障碍提示），无需外部传入
  const menuCollapsedState = useLayoutStore((state) => state.menuCollapsedState);
  // 当前页标题/描述：直接查菜单数据派生的索引（改菜单即改页头，无需在此维护映射）
  const current = ROUTE_META[location.pathname];

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
          aria-label={
            menuCollapsedState === 'fully' ? t('layout.expandSidebar') : t('layout.collapseSidebar')
          }
        >
          {/* 三态图标：fully 显示展开；collapsed 显示「继续完全收起」；offcanvas 显示收起 */}
          {menuCollapsedState === 'fully' ? (
            <PanelLeftOpen className="h-5 w-5" />
          ) : menuCollapsedState === 'collapsed' ? (
            <ChevronsLeft className="h-5 w-5" />
          ) : (
            <PanelLeftClose className="h-5 w-5" />
          )}
        </button>



        {/* 当前路由标题 + 描述 */}
        <div className="min-w-0 flex-1">
          {/* 命中菜单时取菜单文案（t 未命中 i18n key 会返回 undefined，故回退到原始文案，兼容直写中文） */}
          <p className="truncate text-sm font-semibold text-foreground">
            {current ? t(current.title as UiTextKey) || current.title : t('layout.appFallbackTitle')}
          </p>
          <p className="truncate text-xs text-secondary-text">
            {current?.description
              ? t(current.description as UiTextKey) || current.description
              : t('layout.appFallbackDescription')}
          </p>
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
          <ModeSwitch />

          <ThemeSetting />
          <ThemeToggle />
          <LanguageSwitch />
          <UserSetting/>
        </div>
      </div>
    </header>
  );
};
