/**
 * @file menudata.ts
 * @description 侧边栏菜单数据源：定义菜单节点类型与产品/调试两套菜单树（图标、i18n key、路由），
 * 被 SidebarNavV2（HeroUI Pro Sidebar）复用；应用主导航 SidebarNav 各自维护自有常量。
 * @author Lensgcx (GaoCangxiong)
 */
import {
  Activity, AppWindow, BarChart3, Bell, BellRing, BriefcaseBusiness, CalendarDays, CandlestickChart,
  CheckSquare, ChevronsUpDown, FlaskConical, Gauge, History, Home, LayoutDashboard, LayoutGrid,
  LayoutList, List, MessageSquareQuote, Minus, MousePointerClick, Newspaper, PanelRight, Search,
  Sidebar as SidebarIcon, Sparkles, Star, Table, Tags, TextCursorInput, WrapText,
} from 'lucide-react';
import type { ComponentType } from 'react';

/**
 * 菜单节点：一级（分组）与二级（子项）共用同一套字段，保证两层结构一致。
 *
 * 渲染约定（见 SidebarNavV2）：
 * - `routePath` 有值才可点击跳转；一级节点为空串/不传时仅作为分组，点击不跳转、只展开二级。
 * - `menuName` 传 i18n key 时走多语言翻译，传普通文案（如「分组一」）则原样显示；不传则不显示。
 * - `menuIcon` 不传则不显示；图标插槽宽度由组件 CSS 固定，缺省时占位保留，保证文案对齐。
 */
export type NavMenuNode = {
  /** 唯一标识，同时用于 AlphaSift 过滤判断与 Tree 的 id（需全局唯一） */
  menuKey: string;
  /** 菜单名称：i18n key 或直写文案，不传则不显示 */
  menuName?: string;
  /** 路由路径：不传或空串表示不可跳转（一级分组场景） */
  routePath?: string;
  /** 菜单图标，不传则不显示但保留占位 */
  menuIcon?: ComponentType<{ className?: string }>;
  /** 二级菜单 */
  children?: NavMenuNode[];
  /** 是否精确匹配高亮，默认按前缀匹配 */
  exact?: boolean;
};

/** 产品菜单：产品使用模式（normal）下呈现，数组顺序即展示顺序。'screening' 受 AlphaSift 开关控制。 */
export const PRODUCT_NAV_ITEMS: NavMenuNode[] = [
  { menuKey: 'home', menuName: 'layout.nav.home.title', routePath: '/home', menuIcon: Home, exact: true },
  { menuKey: 'stock-dashboard', menuName: 'layout.nav.dashboard.title', routePath: '/stock-dashboard', menuIcon: LayoutDashboard },
  { menuKey: 'sector-analysis', menuName: 'layout.nav.sectorAnalysis.title', routePath: '/sector-analysis', menuIcon: LayoutGrid },
  { menuKey: 'watchlist', menuName: 'layout.nav.watchlist.title', routePath: '/watchlist', menuIcon: Star },
  { menuKey: 'live-calendar', menuName: 'layout.nav.liveCalendar.title', routePath: '/live-calendar', menuIcon: CalendarDays },
  { menuKey: 'live-news', menuName: 'layout.nav.liveNews.title', routePath: '/live-news', menuIcon: Newspaper },
  { menuKey: 'kline', menuName: 'layout.nav.kline.title', routePath: '/kline', menuIcon: CandlestickChart },
  { menuKey: 'chat', menuName: 'layout.nav.chat.title', routePath: '/chat', menuIcon: MessageSquareQuote },
  { menuKey: 'review', menuName: 'layout.nav.review.title', routePath: '/review', menuIcon: History },
  { menuKey: 'portfolio', menuName: 'layout.nav.portfolio.title', routePath: '/portfolio', menuIcon: BriefcaseBusiness },
  { menuKey: 'decision-signals', menuName: 'layout.nav.decisionSignals.title', routePath: '/decision-signals', menuIcon: Activity },
  { menuKey: 'backtest', menuName: 'layout.nav.backtest.title', routePath: '/backtest', menuIcon: BarChart3 },
  { menuKey: 'alerts', menuName: 'layout.nav.alerts.title', routePath: '/alerts', menuIcon: Bell },
  { menuKey: 'usage', menuName: 'layout.nav.usage.title', routePath: '/usage', menuIcon: Gauge },
  { menuKey: 'screening', menuName: 'layout.nav.screening.title', routePath: '/screening', menuIcon: Search },
  { menuKey: 'code-test', menuName: 'layout.nav.codeTest.title', routePath: '/codeTest', menuIcon: FlaskConical },
];

/**
 * 开发调试菜单：开发调试模式（debug）下呈现。
 * 一级为分组（routePath 为空串，仅展开不跳转），二级为各组件文档页。
 */
export const DEBUG_NAV_ITEMS: NavMenuNode[] = [
  {
    menuKey: 'docs-components',
    menuName: '分组一',
    routePath: '',
    menuIcon: CheckSquare,
    children: [
      { menuKey: 'docs-checkbox', menuName: 'layout.nav.development.docsCheckbox.title', routePath: '/docs/component/checkbox', menuIcon: CheckSquare },
      { menuKey: 'docs-drawer', menuName: 'layout.nav.development.docsDrawer.title', routePath: '/docs/component/drawer', menuIcon: PanelRight },
      { menuKey: 'docs-button', menuName: 'layout.nav.development.docsButton.title', routePath: '/docs/component/button', menuIcon: MousePointerClick },
      { menuKey: 'docs-select', menuName: 'layout.nav.development.docsSelect.title', routePath: '/docs/component/select', menuIcon: ChevronsUpDown },
      { menuKey: 'docs-separator', menuName: 'layout.nav.development.docsSeparator.title', routePath: '/docs/component/separator', menuIcon: Minus },
      { menuKey: 'docs-table', menuName: 'layout.nav.development.docsTable.title', routePath: '/docs/component/table', menuIcon: Table },
      { menuKey: 'docs-toast', menuName: 'layout.nav.development.docsToast.title', routePath: '/docs/component/toast', menuIcon: BellRing },
      { menuKey: 'docs-modal', menuName: 'layout.nav.development.docsModal.title', routePath: '/docs/component/modal', menuIcon: AppWindow },
      { menuKey: 'docs-anim-card', menuName: 'layout.nav.development.docsAnimCard.title', routePath: '/docs/component/animCard', menuIcon: Sparkles },
      { menuKey: 'docs-news-card', menuName: 'layout.nav.development.docsNewsCard.title', routePath: '/docs/component/newsCard', menuIcon: Newspaper },
      { menuKey: 'docs-list-card', menuName: 'layout.nav.development.docsListCard.title', routePath: '/docs/component/listCard', menuIcon: List },
      { menuKey: 'docs-tab-nav', menuName: 'layout.nav.development.docsTabNav.title', routePath: '/docs/component/tabNav', menuIcon: LayoutList },
      { menuKey: 'docs-input', menuName: 'layout.nav.development.docsInput.title', routePath: '/docs/component/input', menuIcon: TextCursorInput },
      { menuKey: 'docs-text-area', menuName: 'layout.nav.development.docsTextArea.title', routePath: '/docs/component/textArea', menuIcon: WrapText },
      { menuKey: 'docs-chip', menuName: 'layout.nav.development.docsChip.title', routePath: '/docs/component/chip', menuIcon: Tags },
      { menuKey: 'docs-side-bar', menuName: 'layout.nav.development.docsSideBar.title', routePath: '/docs/component/sideBar', menuIcon: SidebarIcon },
    ],
  },
];
