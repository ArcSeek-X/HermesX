/**
 * @file SidebarNav.tsx
 * @description 轻量侧边导航组件 SidebarNav。
 *
 * 作用：纯 React + Tailwind 自研（零第三方 UI 依赖），渲染品牌区 + 主菜单（content）+ 底部菜单（footer），
 *   支持两级菜单、运行模式（产品/调试）切换、AlphaSift 开关过滤「选股」、三态折叠联动、
 *   模式切换后自动跳转首个可跳转菜单。
 * 使用场景：由 Shell 布局层在桌面端固定侧栏处渲染，文档页也用作组件示例。
 *
 * 职责划分：
 * - 本文件：菜单数据组织（从 MenuStore 取 currentMenuData / AlphaSift 过滤 / content-footer 分区）+ 展开态 + 页面骨架
 * - ./MenuNode.tsx：单个菜单节点的渲染、路由高亮、跳转与子级递归
 *
 * 样式全部用 Tailwind + 主题 CSS 变量（--nav-*，来源 src/style/palette.css），
 * 与侧边栏 v1（SidebarNav-old.tsx）共用同一套视觉令牌，保证明暗主题一致。
 *
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-09-14
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BarChart3 } from 'lucide-react';
import { motion } from 'motion/react';
import MenuNode, { type SidebarMenuMode } from './MenuNode';
import { ScrollShadow } from '../../index';
import { ALPHASIFT_CONFIG_CHANGED_EVENT, SYSTEM_CONFIG_CHANGED_EVENT, alphasiftApi } from '../../../api/alphasift';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import { cn } from '../../../utils/cn';

import { useMenuStore } from '../../../stores';
import type { NavMenuNode } from '../../../types/moduleMenu';
import type { MenuCollapsedState } from '../../../stores';
import type { SidebarTheme } from '../../../types/theme';


/** 一级菜单展示模式：定义于 MenuNode.tsx，此处 re-export 以保持对外 API 不变 */
export type { SidebarMenuMode };
/** 侧栏视觉主题类型已下沉 types/theme.ts（单真源），此处 re-export 保持对外 API 不变 */
export type { SidebarTheme };

/**
 * 主题配置（模块级常量，避免每次渲染重建）：按主题分组的
 * - width：三态宽度（px），motion 动画的目标值
 * - aside_container：外层容器按状态的类名（如 pill 的 p-3、fully 时隐藏边框）
 * - aside：侧栏面板自身的圆角 / 边框 / 阴影
 */
const THEME_CONFIG: Record<
  SidebarTheme,
  {
    width: Record<MenuCollapsedState, number>;
    aside_container: Record<MenuCollapsedState, string>;
    aside: string;
  }
> = {
  pill: {
    width: { offcanvas: 160, collapsed: 80, fully: 0 },
    aside_container: { offcanvas: 'p-3', collapsed: 'p-3', fully: 'invisible border-none' },
    aside: 'rounded-md border border-primary/30 shadow-[0_4px_12px_-4px_hsl(var(--primary)/0.3)]',
  },
  square: {
    width: { offcanvas: 160, collapsed: 64, fully: 0 },
    aside_container: { offcanvas: '', collapsed: '', fully: '' },
    aside: 'border-r border-r-[var(--nav-divider)]',
  },
};


/** easeOutQuint：起步快、收尾缓。宽度用无回弹缓动——回弹会让菜单内容被压得比目标更窄而抖动/截断 */
const SIDEBAR_EASE: [number, number, number, number] = [0.22, 1, 0.36, 1];

type SidebarNavProps = {
  /** 根节点（motion.div 容器）的额外类名，可选，不传则无附加样式 */
  className?: string;
  /** 导航完成后的回调（如移动端抽屉跳转后关闭），可选，不传则不处理 */
  onNavigate?: () => void;
  /** 一级菜单展示模式：collapse=可折叠项 / group=分区标题，可选，默认 collapse */
  menuMode?: SidebarMenuMode;
  /** 视觉主题，决定容器圆角与三态宽度：pill=大圆角 / square=方角，可选，默认 square */
  theme?: SidebarTheme;
  /**
   * 侧栏折叠状态（三态）：offcanvas=正常 / collapsed=半折叠(64px 图标栏) / fully=完全收起。
   * 由外部（Shell 的 useLayoutStore）传入，本组件不自行订阅 store，便于复用与测试。必填。
   */
  menuCollapsedState: MenuCollapsedState;
};

/**
 * 轻量侧边导航：渲染品牌区 + 主菜单（content）+ 底部菜单（footer）。
 * 宽度由本组件根节点的 motion.div 按折叠态动画；折叠态由外部传入（Shell 取自 useLayoutStore）。
 */
export const SidebarNav: React.FC<SidebarNavProps> = ({
  className,
  onNavigate,
  menuMode = 'collapse',
  theme = 'square',
  menuCollapsedState,
}) => {
  const { t } = useUiLanguage();
  // 菜单数据统一从 MenuStore 的 currentMenuData 获取（已按当前模块筛选、含 menuPosition）
  const currentMenuData = useMenuStore((s) => s.currentMenuData);
  const navigate = useNavigate();
  // collapsed 为 64px 图标栏：菜单只显示图标、品牌区只显示 logo
  const isCollapsedRail = menuCollapsedState === 'collapsed';

  // AlphaSift 是否启用，控制「选股」入口显隐
  const [showAlphaSiftNav, setShowAlphaSiftNav] = useState(false);

  // 查询 AlphaSift 启用状态并监听配置变更，用 active 标志避免卸载后更新状态
  useEffect(() => {
    let active = true;
    const refreshAlphaSiftStatus = async () => {
      try {
        const status = await alphasiftApi.getStatus();
        if (active) setShowAlphaSiftNav(status.enabled);
      } catch {
        // 查询失败时默认隐藏选股入口
        if (active) setShowAlphaSiftNav(false);
      }
    };

    // 事件回调需为同步函数（不关心 async 返回值），故包一层
    const handleConfigChanged = () => {
      void refreshAlphaSiftStatus();
    };

    void refreshAlphaSiftStatus();
    window.addEventListener(ALPHASIFT_CONFIG_CHANGED_EVENT, handleConfigChanged);
    window.addEventListener(SYSTEM_CONFIG_CHANGED_EVENT, handleConfigChanged);

    return () => {
      active = false;
      window.removeEventListener(ALPHASIFT_CONFIG_CHANGED_EVENT, handleConfigChanged);
      window.removeEventListener(SYSTEM_CONFIG_CHANGED_EVENT, handleConfigChanged);
    };
  }, []);

  /**
   * 菜单分区：从 MenuStore 取 currentMenuData，AlphaSift 过滤「选股」+ 按 menuPosition 分区。
   * 用 useMemo 缓存，避免每次渲染重复 filter。
   */
  const { contentItems, footerItems } = useMemo(() => {
    const filtered = showAlphaSiftNav
      ? currentMenuData
      : currentMenuData.filter((item) => item.menuId !== 'screening');
    return {
      contentItems: filtered.filter((item) => item.menuPosition === 'content'),
      footerItems: filtered.filter((item) => item.menuPosition === 'footer'),
    };
  }, [currentMenuData, showAlphaSiftNav]);

  /**
   * 展开态：用户手动切换覆盖数据里的 menuExpanded 默认值。
   * 「用户显式值 ?? 数据默认」的派生方式，避免用 effect 同步状态，也免去模式切换后重置。
   */
  const [userExpanded, setUserExpanded] = useState<Record<string, boolean>>({});
  const toggle = useCallback((menuId: string) => {
    setUserExpanded((prev) => ({ ...prev, [menuId]: !prev[menuId] }));
  }, []);
  // 展开判定：用户显式切换过则用其值，否则回退数据里的 menuExpanded
  const isExpanded = useCallback(
    (node: NavMenuNode) => userExpanded[node.menuId] ?? node.menuExpanded,
    [userExpanded],
  );

  // 当前模块的菜单数据（currentMenuData）切换后，自动跳转到菜单栏第一个可跳转菜单：
  // 第一个一级菜单含二级时，跳到其内部第一个二级菜单；否则跳该一级菜单本身。
  const prevMenuDataRef = useRef<NavMenuNode[] | undefined>(undefined);
  useEffect(() => {
    const prevMenuData = prevMenuDataRef.current;
    prevMenuDataRef.current = currentMenuData;
    // 仅在菜单数据真正发生变化时跳转（跳过首次挂载，避免覆盖用户当前路由/深链）
    if (prevMenuData === undefined || prevMenuData === currentMenuData) return;
    const firstItem = contentItems[0];
    if (!firstItem) return;
    const target = firstItem.children?.length ? firstItem.children[0] : firstItem;
    if (target?.routePath) navigate(target.routePath);
  }, [currentMenuData, contentItems, navigate]);

  // 列表渲染：ul > MenuNode，二级由 MenuNode 内部再嵌一层 ul
  const renderList = (nodes: NavMenuNode[]) => (
    <ul className="flex flex-col gap-1.5">
      {nodes.map((node) => (
        <MenuNode
          key={node.menuId}
          node={node}
          level={0}
          collapsedState={menuCollapsedState}
          menuMode={menuMode}
          isExpanded={isExpanded}
          onToggle={toggle}
          onNavigate={onNavigate}
        />
      ))}
    </ul>
  );

  // 从模块级配置取出当前主题下的三态宽度与容器 / aside 类名（THEME_CONFIG 在模块级定义，避免每次渲染重建）
  const themeConfig = THEME_CONFIG[theme];
  const sidebarWidth = themeConfig.width[menuCollapsedState];
  const containerClass = themeConfig.aside_container[menuCollapsedState];
  const asideClass = themeConfig.aside;

  return (
    // 根节点：三态宽度动画（首屏不触发）+ overflow-hidden 裁剪
    <motion.div
      initial={false}
      animate={{ width: sidebarWidth }}
      transition={{ duration: 0.2, ease: SIDEBAR_EASE }}
      className={cn('hrs-sidebar h-full shrink-0 overflow-hidden z-1', containerClass, className)}
    >
      <aside className={cn('flex h-full w-full flex-col ', asideClass)} aria-label={t('layout.desktopSidebar')} >
        {/* 品牌区：图标栏态仅显示 logo */}
        <div className={cn('flex items-center gap-3 px-6 pt-3 pb-3', isCollapsedRail && 'justify-center px-0')}>
          <div
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-white"
            style={{ background: 'linear-gradient(135deg, hsl(var(--primary) / 0.96), hsl(var(--primary) / 0.78))' }}
          >
            <BarChart3 className="h-5 w-5" />
          </div>
          {!isCollapsedRail ? <span className="truncate text-md font-semibold text-foreground">HRS</span> : null}
        </div>

        {/* 主菜单区：占满剩余空间并在自身内部滚动；上下边缘随滚动位置渐隐（封装于 ScrollShadow） */}
        <ScrollShadow
          as="nav"
          className="hrs-sidebar-content min-h-0 flex-1 overflow-y-auto px-2 pt-2 scrollbar-none"
          aria-label={t('layout.mainNav')}
        >
          {renderList(contentItems)}
        </ScrollShadow>

        {/* 底部菜单区：固定在底部，不随主菜单滚动 */}
        {footerItems.length > 0 ? (
          <div className="shrink-0 px-2 pb-2">
            <div className="mx-1.5 h-px bg-[var(--nav-divider)]" />
            <div className="pt-3">{renderList(footerItems)}</div>
          </div>
        ) : null}
      </aside>

    </motion.div>
  );
};

export default SidebarNav;
