/**
 * @file MenuNode.tsx
 * @description 侧边栏单个菜单节点（<li>）：负责一个节点的路由高亮判定、点击跳转与子级递归渲染，
 *   由 SidebarNav 逐个渲染，并按 SidebarNav 下发的玻璃落点 id 标记落点行（data-active / data-menu-id）。
 *   折叠态由父级传入；路由与 i18n 由本组件自行从 hook 获取，免去逐层透传。
 *   四种形态（图标栏 / 分组标题 / 可折叠 / 叶子）各仅出现一次，故内联为 return 分支、不拆子组件，降低阅读跳转成本。
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-09-14
 */
import React from 'react';
import { AnimatePresence, motion, type Transition } from 'motion/react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import { menuIconRegistry } from './MenuIcon';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import type { UiTextKey } from '../../../i18n/uiText';
import { cn } from '../../../utils/cn';
import type { NavMenuNode } from '../../../types/moduleMenu';
import type { MenuCollapsedState } from '../../../stores';
import { matchPath } from './useNavThumb';
import styles from './SidebarNav.module.scss';

/** 一级菜单展示模式：group=一级作为分区标题（不可折叠）；collapse=一级为可折叠项 */
export type SidebarMenuMode = 'group' | 'collapse';

// 样式常量：模块级定义，避免每次渲染重复构造字符串
/** 行基础样式：固定行高 + 圆角 + 占位透明边框（激活换主色边框不抖动）；relative z-[1] 使菜单项压在玻璃（z-0）之上；opacity 过渡供 :has() 兄弟让位 */
const MENU_ITEM_BASE =
  'relative z-[1] flex w-full h-[var(--nav-item-height)] items-center gap-3 rounded-[calc(var(--radius)-4px)] border border-transparent px-4 leading-none transition-[color,background-color,border-color,opacity] duration-200 cursor-pointer';
/** 激活态背景：主色背景 + 主色边框（仅折叠图标栏 / 完全收起态使用，offcanvas 态改由滑行玻璃承担） */
const MENU_ITEM_ACTIVE = 'border-[var(--nav-active-border)] bg-[var(--nav-active-bg)]';
const MENU_ITEM_HOVER = 'hover:bg-[var(--nav-hover-bg)]';
const MENU_ITEM_TEXT = 'font-medium !text-foreground';
const MENU_ITEM_TEXT_ACTIVE = '!font-bold !text-primary';
/** 按压反馈：点下去轻微下陷，松手弹簧回弹 */
const MENU_ITEM_PRESS = { scale: 0.965 } as const;
const MENU_ITEM_PRESS_SPRING: Transition = { type: 'spring', stiffness: 520, damping: 28 };
/** 菜单层级 → 字号：一级 text-sm，二级 text-xs */
const MENU_ITEM_FONT_SIZE: Record<number, string> = { 0: '!text-sm', 1: 'text-xs' };
/** 子菜单展开/收起动画：height 0 ↔ auto + 淡入淡出（子项数量不定，高度交由 motion 实测） */
const SUBMENU_MOTION = {
  initial: { height: 0, opacity: 0 },
  animate: { height: 'auto', opacity: 1 },
  exit: { height: 0, opacity: 0 },
  transition: { duration: 0.22, ease: 'easeOut' },
} as const;

export type MenuNodeProps = {
  /** 菜单节点，必填 */
  node: NavMenuNode;
  /** 层级：0 为一级，递归渲染子级时 +1；默认 0 */
  level?: number;
  /**
   * 侧栏折叠状态（三态）：offcanvas=正常 / collapsed=半折叠(64px) / fully=完全收起。必填。
   */
  collapsedState: MenuCollapsedState;
  /** 一级菜单展示模式，必填 */
  menuMode: SidebarMenuMode;
  /** 展开判定：用户显式切换过则用其值，否则回退数据里的 menuExpanded。必填 */
  isExpanded: (node: NavMenuNode) => boolean;
  /**
   * 展开/收起切换回调：接收菜单 id 与当前有效展开态（本组件已算出），调用方据有效态取反即可。必填。
   */
  onToggle: (menuId: string, expanded: boolean) => void;
  /** 导航完成后的回调（移动端抽屉跳转后关闭），可选 */
  onNavigate?: () => void;
  /**
   * 滑行玻璃落点菜单 id（当前高亮行）：由 SidebarNav 解析（命中项被折叠隐藏时上移到可见祖先）。
   * 命中该 id 的行由玻璃承担选中背景，故打上 data-active 供玻璃定位与兄弟让位复用。可选。
   */
  highlightMenuId?: string | null;
};

/**
 * 单个菜单节点（<li>）：按折叠态与是否有子级，渲染成图标入口 / 分区标题 / 可折叠行 / 叶子四种形态之一。
 * 由 SidebarNav 逐个渲染，含子级时递归渲染一层子级 <ul>。抽成组件而非渲染函数，对 React Compiler 友好。
 */
const MenuNode: React.FC<MenuNodeProps> = ({
  node,
  level = 0,
  collapsedState,
  menuMode,
  isExpanded,
  onToggle,
  onNavigate,
  highlightMenuId,
}) => {
  const { pathname } = useLocation();
  const { t } = useUiLanguage();
  const navigate = useNavigate();

  const { menuId, menuName, routePath, menuIcon: iconName, children, exact } = node;
  // 图标名经白名单解析回组件；未命中则为 undefined，渲染时空占位
  const MenuIcon = iconName ? menuIconRegistry[iconName] : undefined;
  const label = menuName ? t(menuName as UiTextKey) || menuName : '';
  const hasChildren = !!children?.length;
  const expandedNow = isExpanded(node);
  // 分组节点（menuType==='group'）仅作分区标题、不可点击；以自身 menuType 为准，与全局 menuMode 无关
  const isGroup = node.menuType === 'group';

  // 自身命中路由，或子项命中时父级同步高亮（对齐 V2 的 selfCurrent / childCurrent）
  const isActiveRoute =
    matchPath(routePath, exact, pathname) ||
    (hasChildren && children.some((child) => matchPath(child.routePath, child.exact, pathname)));

  // 是否为滑行玻璃落点行：offcanvas 态下选中背景由玻璃承担，落点行即「视觉激活行」。
  // 命中路由的菜单可见时就是它自身；含激活子项的一级菜单被折叠（子项不在 DOM 中）时，玻璃上移到该一级菜单行。
  const isHighlight = !!highlightMenuId && highlightMenuId === menuId;

  /** 跳转：有 routePath 时走 react-router 的 SPA 跳转并回调；无 routePath 时静默忽略 */
  const goToRoute = () => {
    if (!routePath) return;
    navigate(routePath);
    onNavigate?.();
  };

  /** 统一点击处理（所有 <a> 共用）：阻止默认行为，避免整页刷新 */
  const handleClick: React.MouseEventHandler<HTMLElement> = (event) => {
    event.preventDefault();
    goToRoute();
  };

  /** 含子级节点主区点击：仅切换展开/收起，不跳转路由（父级为容器，路由由其子项承载）；带上有效展开态供上层取反 */
  const handleParentClick: React.MouseEventHandler<HTMLElement> = (event) => {
    event.preventDefault();
    onToggle(menuId, expandedNow);
  };

  // 图标外层始终占位 16×16，无图标时仅留空位，保证菜单项（含二级）文字对齐
  const menuIcon = (
    <span className={cn('h-4 w-4 shrink-0', isActiveRoute && 'text-primary')}>
      {MenuIcon ? <MenuIcon className="h-4 w-4" /> : null}
    </span>
  );

  // —— 图标栏（半折叠 64px）：只保留图标入口，可访问性用 title / aria-label 兜底 ——
  if (collapsedState === 'collapsed') {
    // 分组节点不可跳转，仅作图标占位（避免点击 group 路由 404）
    const navigable = !!routePath && !isGroup;
    return (
      <li className={`menu-node-collapsed-${level}`}>
        <motion.a
          href={navigable ? routePath : undefined}
          onClick={navigable ? handleClick : undefined}
          title={label}
          aria-label={label}
          whileTap={MENU_ITEM_PRESS}
          transition={MENU_ITEM_PRESS_SPRING}
          className={cn(
            MENU_ITEM_BASE,
            'justify-center px-0',
            styles.menuItem,
            MENU_ITEM_HOVER,
            isActiveRoute && MENU_ITEM_ACTIVE,
            !navigable && 'cursor-default',
          )}
          data-active={isActiveRoute ? 'true' : undefined}
          data-menu-id={menuId}
        >
          {menuIcon}
          {/* 文字常驻挂载（折叠态用 hidden 移出布局，避免 gap 把图标挤偏），与展开态结构一致，避免切换瞬间 DOM 增删 */}
          <span className="hidden">{label}</span>
        </motion.a>
      </li>
    );
  }

  // —— 含子级节点：两种模式共用同一份 childList，仅外层形态不同 ——
  if (hasChildren) {
    const childList = children.map((child) => (
      <MenuNode
        key={child.menuId}
        node={child}
        level={level + 1}
        collapsedState={collapsedState}
        menuMode={menuMode}
        isExpanded={isExpanded}
        onToggle={onToggle}
        onNavigate={onNavigate}
        highlightMenuId={highlightMenuId}
      />
    ));

    // 全局 group 模式：含子级的一级菜单均渲染为静态分区标题（纯文字、始终展开、无箭头、不可跳转）。
    // 注意：collapse 模式下即使 menuType==='group'，也走下方 accordion 分支（带 ChevronRight、点击展开/收起、不跳转路由）。
    if (menuMode === 'group') {
      return (
        <li className={`menu-node-group-${level}`}>
          <div className="relative z-[1] px-4 pb-1 pt-2 text-xs font-medium text-secondary-text/70">{label}</div>
          <ul className={cn(styles.navList, 'flex flex-col gap-1')}>{childList}</ul>
        </li>
      );
    }

    // collapse 模式：可折叠行（主区点击跳转并切换展开）+ 子菜单高度动画
    return (
      <li className={`menu-node-collapse-${level}`}>
        <motion.div
          className={cn(
            MENU_ITEM_BASE,
            styles.menuItem,
            MENU_ITEM_TEXT,
            MENU_ITEM_HOVER,
            isActiveRoute && MENU_ITEM_TEXT_ACTIVE,
            MENU_ITEM_FONT_SIZE[level],
            'pr-1.5',
          )}
          onClick={handleParentClick}
          whileTap={MENU_ITEM_PRESS}
          transition={MENU_ITEM_PRESS_SPRING}
          data-active={isHighlight ? 'true' : undefined}
          data-menu-id={menuId}
        >
          <span className="flex min-w-0 flex-1 items-center gap-3">
            {menuIcon}
            <span className="truncate">{label}</span>
          </span>

          <ChevronRight
            className={cn('flex h-4 w-4 transition-transform text-foreground-soft text-xs', expandedNow && 'rotate-90')}
          />
        </motion.div>
        <AnimatePresence initial={false}>
          {expandedNow ? (
            <motion.div key="submenu" {...SUBMENU_MOTION} className="overflow-hidden">
              <ul id={`menu-submenu-${menuId}`} className={cn(styles.navList, 'mt-1 flex flex-col gap-1')}>
                {childList}
              </ul>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </li>
    );
  }

  // —— 叶子节点：统一用 <a> 渲染；有 routePath 才跳转，无 routePath 时仅展示 ——
  // 注意：offcanvas 态下激活高亮由 SidebarNav 的滑行玻璃（.navThumb）承担，此处不再绘制自带背景
  // （避免双重高亮），仅保留文字激活色；折叠图标栏态仍用自带背景。
  return (
    <li className={`menu-node-collapse-${level}`}>
      <motion.a
        href={routePath}
        onClick={handleClick}
        aria-current={isActiveRoute ? 'page' : undefined}
        whileTap={MENU_ITEM_PRESS}
        transition={MENU_ITEM_PRESS_SPRING}
        className={cn(
          MENU_ITEM_BASE,
          styles.menuItem,
          MENU_ITEM_TEXT,
          MENU_ITEM_HOVER,
          isActiveRoute && MENU_ITEM_TEXT_ACTIVE,
          !routePath && 'cursor-default',
          MENU_ITEM_FONT_SIZE[level],
        )}
        data-active={isHighlight ? 'true' : undefined}
        data-menu-id={menuId}
      >
        {menuIcon}
        <span className="truncate">{label}</span>
      </motion.a>
    </li>
  );
};

export default MenuNode;
