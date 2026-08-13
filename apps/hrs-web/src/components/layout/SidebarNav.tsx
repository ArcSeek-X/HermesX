/**
 * 侧边导航组件（SidebarNav）
 *
 * 应用主导航菜单，支持两种展示形态：
 * - variant="default"：标准列表模式，用于移动端抽屉
 * - variant="rail"：精简轨道模式（图标居中），用于桌面端固定侧边栏
 *
 * 主要职责：
 * 1. 渲染导航项列表（首页、板块分析、K线、对话、选股、持仓等），顺序见 NAV_ITEMS
 * 2. 依据 AlphaSift 功能开关动态显隐「选股」入口
 * 3. 对话页支持未读完成标记（StatusDot 红点）
 */
import React, { useEffect, useState } from 'react';
import { Activity, BarChart3, Bell, BriefcaseBusiness, CandlestickChart, Gauge, Home, LayoutDashboard, LayoutGrid, MessageSquareQuote, Search, Settings2 } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { ALPHASIFT_CONFIG_CHANGED_EVENT, SYSTEM_CONFIG_CHANGED_EVENT, alphasiftApi } from '../../api/alphasift';
import { useAuth } from '../../contexts/AuthContext';
import { useAgentChatStore } from '../../stores/agentChatStore';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import type { UiTextKey } from '../../i18n/uiText';
import { cn } from '../../utils/cn';
import { StatusDot } from '../common/StatusDot';

type SidebarNavProps = {
  /** 是否折叠：仅显示图标，隐藏文字标签 */
  collapsed?: boolean;
  /** 导航点击回调，常用于移动端点击后关闭抽屉 */
  onNavigate?: () => void;
  /** 展示形态：default=标准列表，rail=精简轨道 */
  variant?: 'default' | 'rail';
};

/** 单个导航项的配置 */
type NavItem = {
  /** 唯一标识，同时用于 AlphaSift 过滤判断 */
  key: string;
  /** i18n 文案 key */
  labelKey: UiTextKey;
  /** 路由路径 */
  to: string;
  /** 图标组件 */
  icon: React.ComponentType<{ className?: string }>;
  /** 是否精确匹配（用于首页 "/" ） */
  exact?: boolean;
  /** 徽标类型，目前仅支持 'completion'（对话完成未读标记） */
  badge?: 'completion';
};

/**
 * 导航项配置列表，数组顺序即为菜单展示顺序。
 * 'screening'（选股）受 AlphaSift 开关控制，关闭时从列表中过滤。
 */
const NAV_ITEMS: NavItem[] = [
  { key: 'home', labelKey: 'layout.nav.home', to: '/home', icon: Home, exact: true },
  { key: 'stock-dashboard', labelKey: 'layout.nav.dashboard', to: '/stock-dashboard', icon: LayoutDashboard },
  { key: 'sector-analysis', labelKey: 'layout.nav.sectorAnalysis', to: '/sector-analysis', icon: LayoutGrid },
  { key: 'kline', labelKey: 'layout.nav.kline', to: '/kline', icon: CandlestickChart },
  { key: 'chat', labelKey: 'layout.nav.chat', to: '/chat', icon: MessageSquareQuote, badge: 'completion' },
  { key: 'screening', labelKey: 'layout.nav.screening', to: '/screening', icon: Search },
  { key: 'portfolio', labelKey: 'layout.nav.portfolio', to: '/portfolio', icon: BriefcaseBusiness },
  { key: 'decision-signals', labelKey: 'layout.nav.decisionSignals', to: '/decision-signals', icon: Activity },
  { key: 'backtest', labelKey: 'layout.nav.backtest', to: '/backtest', icon: BarChart3 },
  { key: 'alerts', labelKey: 'layout.nav.alerts', to: '/alerts', icon: Bell },
  { key: 'usage', labelKey: 'layout.nav.usage', to: '/usage', icon: Gauge },
  { key: 'settings', labelKey: 'layout.nav.settings', to: '/settings', icon: Settings2 },
];

export const SidebarNav: React.FC<SidebarNavProps> = ({ collapsed = false, onNavigate, variant = 'default' }) => {
  const { t } = useUiLanguage();
  // 对话完成标记：有新的 AI 回复完成时显示红点
  const completionBadge = useAgentChatStore((state) => state.completionBadge);
  // AlphaSift 是否启用，控制「选股」入口显隐
  const [showAlphaSiftNav, setShowAlphaSiftNav] = useState(false);

  /**
   * 查询 AlphaSift 启用状态并监听配置变更：
   * - 挂载时主动查询一次
   * - 监听 ALPHASIFT_CONFIG_CHANGED_EVENT / SYSTEM_CONFIG_CHANGED_EVENT，实时响应配置变更
   * - 用 active 标志避免异步回调在组件卸载后更新状态
   */
  useEffect(() => {
    let active = true;

    const refreshAlphaSiftStatus = async () => {
      try {
        const status = await alphasiftApi.getStatus();
        if (active) {
          setShowAlphaSiftNav(status.enabled);
        }
      } catch {
        // 查询失败时默认隐藏选股入口
        if (active) {
          setShowAlphaSiftNav(false);
        }
      }
    };

    void refreshAlphaSiftStatus();
    window.addEventListener(ALPHASIFT_CONFIG_CHANGED_EVENT, refreshAlphaSiftStatus);
    window.addEventListener(SYSTEM_CONFIG_CHANGED_EVENT, refreshAlphaSiftStatus);

    return () => {
      active = false;
      window.removeEventListener(ALPHASIFT_CONFIG_CHANGED_EVENT, refreshAlphaSiftStatus);
      window.removeEventListener(SYSTEM_CONFIG_CHANGED_EVENT, refreshAlphaSiftStatus);
    };
  }, []);

  // AlphaSift 未启用时过滤掉「选股」导航项
  const navItems = showAlphaSiftNav ? NAV_ITEMS : NAV_ITEMS.filter((item) => item.key !== 'screening');
  const isRail = variant === 'rail';

  // ===== 样式常量（按 variant / collapsed 预组合）=====

  // 导航项基础样式：布局、圆角、间距、默认文字色
  const itemBaseClass = cn(
    'group relative mx-auto flex h-[var(--nav-item-height)] items-center overflow-hidden rounded-2xl border border-transparent text-sm leading-none text-secondary-text transition-all',
    isRail
      ? collapsed
        ? 'w-full justify-center px-0'
        : 'w-fit justify-center gap-2.5 px-3'
      : collapsed
        ? 'w-full justify-center px-0'
        : 'w-fit gap-3 px-[var(--nav-item-padding-x)]'
  );
  // 交互态：hover 背景 + 文字变亮
  const itemInteractiveClass = cn(
    'hover:bg-[var(--nav-hover-bg)] hover:text-foreground'
  );
  // 激活态：高亮边框 + 背景 + 主色文字
  const itemActiveClass = 'border-[var(--nav-active-border)] bg-[var(--nav-active-bg)] font-medium text-[hsl(var(--primary))]';
  // 图标尺寸：rail 模式略小
  const itemIconClass = cn(isRail ? 'h-[18px] w-[18px]' : 'h-5 w-5', 'shrink-0');
  // 文字样式
  const itemLabelClass = cn('truncate', isRail ? 'text-center' : '');

  return (
    <div className="hrs-side-container flex h-full flex-col">
      {/* 品牌 Logo 区域 */}
      <div
        className={cn(
          'flex items-center',
          isRail ? 'mb-5 justify-center gap-2 pt-1' : 'mb-4 gap-2 px-1',
          collapsed || isRail ? 'justify-center' : ''
        )}
      >
        <div
          className={cn(
            'flex items-center justify-center text-white shadow-[0_12px_28px_var(--nav-brand-shadow)]',
            isRail ? 'h-9 w-9 rounded-[1rem]' : 'h-10 w-10 rounded-2xl'
          )}
          style={{
            // 背景基于当前主色 --primary 生成渐变，随主题色切换联动
            background:
              'linear-gradient(135deg, hsl(var(--primary) / 0.96), hsl(var(--primary) / 0.78))',
          }}
        >
          <BarChart3 className={cn(isRail ? 'h-[19px] w-[19px]' : 'h-5 w-5')} />
        </div>
        {/* 折叠时隐藏品牌文字 */}
        {!collapsed ? (
          <p className={cn('min-w-0 truncate font-semibold text-foreground', isRail ? 'text-[0.95rem] leading-none' : 'text-sm')}>HRS</p>
        ) : null}
      </div>

      {/* 导航项列表 */}
      <nav className={cn('flex flex-col items-center gap-1.5', isRail ? '' : 'flex-1')} aria-label={t('layout.mainNav')}>
        {navItems.map(({ key, labelKey, to, icon: Icon, exact, badge }) => {
          const label = t(labelKey);
          return (
          <NavLink
            key={key}
            to={to}
            end={exact}
            onClick={onNavigate}
            aria-label={label}
            className={({ isActive }) =>
              cn(
                itemBaseClass,
                itemInteractiveClass,
                isActive ? itemActiveClass : ''
              )
            }
          >
            {({ isActive }) => (
              <>
                <Icon className={cn(itemIconClass, isActive ? 'text-[var(--nav-icon-active)]' : 'text-current')} />
                {/* 折叠时隐藏文字标签 */}
                {!collapsed ? <span className={itemLabelClass}>{label}</span> : null}
                {/* 对话完成未读标记：右上角红点 */}
                {badge === 'completion' && completionBadge ? (
                  <StatusDot
                    tone="info"
                    data-testid="chat-completion-badge"
                    className={cn(
                      'absolute right-3 border-2 border-background shadow-[0_0_10px_var(--nav-indicator-shadow)]',
                      collapsed ? 'right-2 top-2' : ''
                    )}
                    aria-label={t('layout.newChatMessage')}
                  />
                ) : null}
              </>
            )}
          </NavLink>
        );
        })}
      </nav>
    </div>
  );
};
