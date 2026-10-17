/**
 * 顶部页头 ShellHeader（h-14，固定在右侧列顶部，不随内容滚动）
 *
 * 含：移动端菜单按钮（< lg）、桌面端侧栏折叠按钮（>= lg）、当前路由标题/描述
 * （查当前路由 handle，与侧栏/路由同源无需维护映射）、右侧操作区
 * （股票搜索 / 主题设置 / 语言切换 / 个人设置）。
 *
 * @author Lensgcx (GaoCangxiong)
 */
import type React from 'react';
import { useState } from 'react';
import { Menu } from 'lucide-react';
import { useLocation, useMatches, useNavigate } from 'react-router-dom';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import type { UiTextKey } from '../../i18n/uiText';
import type { RouteHandle } from '../../types/router';
import { ThemeSetting } from './HeaderComponents/ThemeSetting';
import { UserSetting } from './HeaderComponents/UserSetting';
import { LanguageSwitch } from './HeaderComponents/LanguageSwitch';
import { FullscreenToggle } from './HeaderComponents/FullscreenToggle';
import { ApplicationMenu } from './HeaderComponents/ApplicationMenu';
import { MenuSwitcher } from './HeaderComponents/MenuSwitcher';
import { BackToHome } from './HeaderComponents/BackToHome';
import { ThemeToggle } from '../theme/ThemeToggle';
import { ModeSwitch } from './HeaderComponents/ModeSwitch';
import { StockSearch } from '../StockSearch/StockSearch';
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
  const navigate = useNavigate();
  const { t } = useUiLanguage();
  const location = useLocation();
  const matches = useMatches();
  // 个股 K 线页已有独立页内搜索框，顶部搜索框在该路由下隐藏（避免重复输入入口）
  const isKLineRoute = location.pathname === '/stock/kline';
  // 当前页标题/描述：经 useMatches 读取路由 handle（数据路由原生能力），与侧栏/路由同源；按字段独立 i18n 兜底
  const handle = matches[matches.length - 1]?.handle as RouteHandle | undefined;
  const title = handle?.routerName
    ? t(handle.routerName as UiTextKey) || handle.routerName
    : t('layout.appFallbackTitle');
  const description = handle?.routerDescription
    ? t(handle.routerDescription as UiTextKey) || handle.routerDescription
    : t('layout.appFallbackDescription');

  // 头部股票搜索框：提交后带 ?stockCode= 跳转 K 线页
  const [stockQuery, setStockQuery] = useState('');

  return (
    <header className={cn('hrs-header z-30 h-14 border-b border-border/60 backdrop-blur-xl', className)}>
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
        <MenuSwitcher onToggleSidebar={onToggleSidebar} />

        {/* 回到主页按钮：点击跳转 /home */}
        <BackToHome />

        {/* 我的应用下拉面板：应用入口从 MENU_MANIFEST 真源渲染 */}
        <ApplicationMenu />

        {/* 当前路由标题 + 描述 */}
        <div className="min-w-0 flex-1">
          {/* <p className="truncate text-sm font-semibold text-foreground">{title}</p>
          <p className="truncate text-xs text-secondary-text">{description}</p> */}
        </div>

        {/* 右侧操作区：股票搜索 / 主题设置 / 中英文切换 / 个人设置 */}
        <div className="flex items-center gap-2">
          {!isKLineRoute && (
            <StockSearch
              value={stockQuery}
              size="sm"
              onChange={setStockQuery}
              onSubmit={(code) => {
                if (!code) return;
                setStockQuery('');
                // 统一跳转模式：带 ?stockCode= 直达 K 线页，与自选股列表一致
                navigate(`/stock/kline?stockCode=${encodeURIComponent(code)}`);
              }}
              onClear={() => setStockQuery('')}
              className="h-9 text-xs w-60"
            />
          )}
          <ModeSwitch />

          <ThemeSetting />
          <ThemeToggle />
          <LanguageSwitch />
          <FullscreenToggle />
          <UserSetting/>
        </div>
      </div>
    </header>
  );
};
