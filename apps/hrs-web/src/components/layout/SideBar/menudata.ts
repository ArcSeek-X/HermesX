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
  Sidebar as SidebarIcon, Sparkles, Star, Table, Tags, TextCursorInput, WrapText,Settings2
} from 'lucide-react';
import type { ComponentType } from 'react';

/**
 * 菜单节点：一级（分组）与二级（子项）共用同一套字段，保证两层结构一致。
 * 字段书写顺序约定：menuId → menuName → routePath → menuIcon → menuBadge → menuPosition → level → menuExpanded → description → (exact) → (children)。
 *
 * 渲染约定（见 SidebarNavV2）：
 * - `routePath` 有值才可点击跳转；一级节点为空串/不传时仅作为分组，点击不跳转、只展开二级。
 * - `menuName` 传 i18n key 时走多语言翻译，传普通文案（如「分组一」）则原样显示；不传则不显示。
 * - `menuIcon` 不传则不显示；图标插槽宽度由组件 CSS 固定，缺省时占位保留，保证文案对齐。
 * - `menuBadge`：菜单徽章标志，默认为空（不显示）。
 * - `description` 与 `menuName` 保持一致（key 写 key、中文写中文）；一级节点（depth === 0）有值时由 GroupLabel 渲染。
 * - `level`：0 为一级分组/顶级项，1 为二级子项。
 * - `menuPosition`：菜单所在区域，`header`/`content`/`footer`，默认 `content`。
 * - `exact`：可选，是否精确匹配高亮，默认按前缀匹配（仅个别项使用）。
 */
export type NavMenuNode = {
  /** 唯一标识（即 HeroUI Tree 节点的 id），同时用于 AlphaSift 过滤判断（需全局唯一） */
  menuId: string;
  /** 菜单名称：i18n key 或直写文案，不传则不显示 */
  menuName?: string;
  /** 路由路径：不传或空串表示不可跳转（一级分组场景） */
  routePath?: string;
  /** 菜单图标，不传则不显示但保留占位 */
  menuIcon?: ComponentType<{ className?: string }>;
  /** 菜单徽章标志，默认为空（不显示） */
  menuBadge?: string;
  /** 菜单所在区域：header / content / footer，默认 content */
  menuPosition: 'header' | 'content' | 'footer';
  /** 菜单层级：0 为一级分组/顶级项，1 为二级子项；用于渲染样式与展开逻辑区分 */
  level: number;
  /** 菜单是否默认展开，默认 false */
  menuExpanded: boolean;
  /** 描述文案：与 menuName 保持一致（key 写 key、中文写中文）；一级节点有值时由 GroupLabel 渲染 */
  description: string;
  /** 是否精确匹配高亮，默认按前缀匹配 */
  exact?: boolean;
  /** 二级菜单 */
  children?: NavMenuNode[];
};

/** 产品菜单：产品使用模式（normal）下呈现，数组顺序即展示顺序。'screening' 受 AlphaSift 开关控制。 */
export const PRODUCT_MENU_ITEMS: NavMenuNode[] = [
  { menuId: 'home', menuName: 'layout.nav.home.title', routePath: '/home', menuIcon: Home, menuPosition: 'content', level: 0, menuExpanded: false, description: 'layout.nav.home.title', exact: true },
  { menuId: 'stock-dashboard', menuName: 'layout.nav.dashboard.title', routePath: '/stock-dashboard', menuIcon: LayoutDashboard, menuPosition: 'content', level: 0, menuExpanded: false, description: 'layout.nav.dashboard.title' },
  { menuId: 'sector-analysis', menuName: 'layout.nav.sectorAnalysis.title', routePath: '/sector-analysis', menuIcon: LayoutGrid, menuPosition: 'content', level: 0, menuExpanded: false, description: 'layout.nav.sectorAnalysis.title' },
  { menuId: 'watchlist', menuName: 'layout.nav.watchlist.title', routePath: '/watchlist', menuIcon: Star, menuPosition: 'content', level: 0, menuExpanded: false, description: 'layout.nav.watchlist.title' },
  { menuId: 'live-calendar', menuName: 'layout.nav.liveCalendar.title', routePath: '/live-calendar', menuIcon: CalendarDays, menuPosition: 'content', level: 0, menuExpanded: false, description: 'layout.nav.liveCalendar.title' },
  { menuId: 'live-news', menuName: 'layout.nav.liveNews.title', routePath: '/live-news', menuIcon: Newspaper, menuPosition: 'content', level: 0, menuExpanded: false, description: 'layout.nav.liveNews.title' },
  { menuId: 'kline', menuName: 'layout.nav.kline.title', routePath: '/kline', menuIcon: CandlestickChart, menuPosition: 'content', level: 0, menuExpanded: false, description: 'layout.nav.kline.title' },
  { menuId: 'chat', menuName: 'layout.nav.chat.title', routePath: '/chat', menuIcon: MessageSquareQuote, menuPosition: 'content', level: 0, menuExpanded: false, description: 'layout.nav.chat.title' },
  { menuId: 'review', menuName: 'layout.nav.review.title', routePath: '/review', menuIcon: History, menuPosition: 'content', level: 0, menuExpanded: false, description: 'layout.nav.review.title' },
  { menuId: 'portfolio', menuName: 'layout.nav.portfolio.title', routePath: '/portfolio', menuIcon: BriefcaseBusiness, menuPosition: 'content', level: 0, menuExpanded: false, description: 'layout.nav.portfolio.title' },
  { menuId: 'decision-signals', menuName: 'layout.nav.decisionSignals.title', routePath: '/decision-signals', menuIcon: Activity, menuPosition: 'content', level: 0, menuExpanded: false, description: 'layout.nav.decisionSignals.title' },
  { menuId: 'backtest', menuName: 'layout.nav.backtest.title', routePath: '/backtest', menuIcon: BarChart3, menuPosition: 'content', level: 0, menuExpanded: false, description: 'layout.nav.backtest.title' },
  { menuId: 'alerts', menuName: 'layout.nav.alerts.title', routePath: '/alerts', menuIcon: Bell, menuPosition: 'content', level: 0, menuExpanded: false, description: 'layout.nav.alerts.title' },
  { menuId: 'usage', menuName: 'layout.nav.usage.title', routePath: '/usage', menuIcon: Gauge, menuPosition: 'content', level: 0, menuExpanded: false, description: 'layout.nav.usage.title' },
  { menuId: 'screening', menuName: 'layout.nav.screening.title', routePath: '/screening', menuIcon: Search, menuPosition: 'content', level: 0, menuExpanded: false, description: 'layout.nav.screening.title' },
  { menuId: 'code-test', menuName: 'layout.nav.codeTest.title', routePath: '/codeTest', menuIcon: FlaskConical, menuPosition: 'content', level: 0, menuExpanded: false, description: 'layout.nav.codeTest.title' },
  { menuId: 'settings', menuName: 'layout.nav.settings.title', routePath: '/settings', menuIcon: Settings2, menuPosition: 'footer', level: 0, menuExpanded: false, description: 'layout.nav.settings.title' },

];



/**
 * 开发调试菜单：开发调试模式（debug）下呈现。
 * 一级为分组（routePath 为空串，仅展开不跳转），二级为各组件文档页。
 */
export const DEBUG_MENU_ITEMS: NavMenuNode[] = [
  {
    menuId: 'Basic',
    menuName: '基础',
    routePath: '',
    menuIcon: CheckSquare,
    menuBadge: '',
    menuPosition: 'content',
    level: 0,
    menuExpanded: true,
    description: '基础',
    children: [
      { menuId: 'docs-button', menuName: 'layout.nav.development.docsButton.title', routePath: '/docs/component/button', menuIcon: MousePointerClick, menuPosition: 'content', level: 1, menuExpanded: false, description: 'layout.nav.development.docsButton.title' },
    ],
  },
  {
    menuId: 'Form',
    menuName: '表单',
    menuIcon: CheckSquare,
    routePath: '',
    menuPosition: 'content',
    level: 0,
    menuExpanded: false,
    description: '表单',
    children: [
      { menuId: 'docs-input', menuName: 'layout.nav.development.docsInput.title', routePath: '/docs/component/input', menuIcon: TextCursorInput, menuPosition: 'content', level: 1, menuExpanded: false, description: 'layout.nav.development.docsInput.title' },
      { menuId: 'docs-text-area', menuName: 'layout.nav.development.docsTextArea.title', routePath: '/docs/component/textArea', menuIcon: WrapText, menuPosition: 'content', level: 1, menuExpanded: false, description: 'layout.nav.development.docsTextArea.title' },
      { menuId: 'docs-select', menuName: 'layout.nav.development.docsSelect.title', routePath: '/docs/component/select', menuIcon: ChevronsUpDown, menuPosition: 'content', level: 1, menuExpanded: false, description: 'layout.nav.development.docsSelect.title' },
      { menuId: 'docs-checkbox', menuName: 'layout.nav.development.docsCheckbox.title', routePath: '/docs/component/checkbox', menuIcon: CheckSquare, menuPosition: 'content', level: 1, menuExpanded: false, description: 'layout.nav.development.docsCheckbox.title' },
    ],
  },

  {
    menuId: 'DataDisplay',
    menuName: '数据展示',
    menuIcon: CheckSquare,
    routePath: '',
    menuPosition: 'content',
    level: 0,
    menuExpanded: false,
    description: '数据展示',
    children: [
      { menuId: 'docs-chip', menuName: 'layout.nav.development.docsChip.title', routePath: '/docs/component/chip', menuIcon: Tags, menuPosition: 'content', level: 1, menuExpanded: false, description: 'layout.nav.development.docsChip.title' },
      { menuId: 'docs-table', menuName: 'layout.nav.development.docsTable.title', routePath: '/docs/component/table', menuIcon: Table, menuPosition: 'content', level: 1, menuExpanded: false, description: 'layout.nav.development.docsTable.title' },
    ],
  },
  {
    menuId: 'Navigation',
    menuName: '导航',
    menuIcon: CheckSquare,
    routePath: '',
    menuPosition: 'content',
    level: 0,
    menuExpanded: false,
    description: '导航',
    children: [
      { menuId: 'docs-side-bar', menuName: 'layout.nav.development.docsSideBar.title', routePath: '/docs/component/sideBar', menuIcon: SidebarIcon, menuPosition: 'content', level: 1, menuExpanded: false, description: 'layout.nav.development.docsSideBar.title' },
      { menuId: 'docs-tab-nav', menuName: 'layout.nav.development.docsTabNav.title', routePath: '/docs/component/tabNav', menuIcon: LayoutList, menuPosition: 'content', level: 1, menuExpanded: false, description: 'layout.nav.development.docsTabNav.title' },
    ],
  },
  {
    menuId: 'Layout',
    menuName: '布局',
    menuIcon: CheckSquare,
    routePath: '',
    menuPosition: 'content',
    level: 0,
    menuExpanded: false,
    description: '布局',
    children: [
      { menuId: 'docs-separator', menuName: 'layout.nav.development.docsSeparator.title', routePath: '/docs/component/separator', menuIcon: Minus, menuPosition: 'content', level: 1, menuExpanded: false, description: 'layout.nav.development.docsSeparator.title' },
      { menuId: 'docs-anim-card', menuName: 'layout.nav.development.docsAnimCard.title', routePath: '/docs/component/animCard', menuIcon: Sparkles, menuPosition: 'content', level: 1, menuExpanded: false, description: 'layout.nav.development.docsAnimCard.title' },
      { menuId: 'docs-news-card', menuName: 'layout.nav.development.docsNewsCard.title', routePath: '/docs/component/newsCard', menuIcon: Newspaper, menuPosition: 'content', level: 1, menuExpanded: false, description: 'layout.nav.development.docsNewsCard.title' },
      { menuId: 'docs-list-card', menuName: 'layout.nav.development.docsListCard.title', routePath: '/docs/component/listCard', menuIcon: List, menuPosition: 'content', level: 1, menuExpanded: false, description: 'layout.nav.development.docsListCard.title' },
    ],
  },

  {
    menuId: 'Overlays',
    menuName: '浮层',
    menuIcon: CheckSquare,
    routePath: '',
    menuPosition: 'content',
    level: 0,
    menuExpanded: false,
    description: '浮层',
    children: [
      { menuId: 'docs-drawer', menuName: 'layout.nav.development.docsDrawer.title', routePath: '/docs/component/drawer', menuIcon: PanelRight, menuPosition: 'content', level: 1, menuExpanded: false, description: 'layout.nav.development.docsDrawer.title' },
      { menuId: 'docs-toast', menuName: 'layout.nav.development.docsToast.title', routePath: '/docs/component/toast', menuIcon: BellRing, menuPosition: 'content', level: 1, menuExpanded: false, description: 'layout.nav.development.docsToast.title' },
      { menuId: 'docs-modal', menuName: 'layout.nav.development.docsModal.title', routePath: '/docs/component/modal', menuIcon: AppWindow, menuPosition: 'content', level: 1, menuExpanded: false, description: 'layout.nav.development.docsModal.title' },
    ],
  },
];
