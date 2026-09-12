/**
 * 侧边导航 V2（SidebarNavV2）：基于 HeroUI Pro 的 Sidebar 组件实现的应用主导航。
 * 支持两级菜单：一级为分组（routePath 有值才可跳转，空值仅展开），二级为具体页面；
 * 菜单名与图标按数据字段渲染，缺省时不显示但保留占位，保证上下对齐。
 * 随运行模式切换产品/调试菜单，「选股」受 AlphaSift 开关控制；
 * 通过 Provider 的 navigate 接入 react-router，点击菜单走 SPA 跳转而非整页刷新。
 * 菜单项内部样式对标 SidebarNav.tsx（44px 行高 / 20px 图标 / 主色高亮体系），
 * 由 SidebarNavV2.module.scss 以 data-slot 变体选择器覆盖 HeroUI Pro 内容层默认值。
 * 一级菜单支持两种展示模式（menuMode）：
 * - group：一级菜单作为分区标题（Group + GroupLabel + Menu），二级子项平铺。
 * - collapse（默认）：一级菜单为可折叠菜单项，由 renderMenuNodes 递归渲染一二级。
 * 只封装侧栏本体（Provider + Sidebar），Sidebar.Mobile / Sidebar.Main 由布局层组合。
 *
 * @author Lensgcx (GaoCangxiong)
 */
import React, { useEffect, useRef, useState } from 'react';
import { Sidebar } from '@heroui-pro/react';
import { useLocation, useNavigate } from 'react-router-dom';
import { BarChart3, Settings2 } from 'lucide-react';
import { ALPHASIFT_CONFIG_CHANGED_EVENT, SYSTEM_CONFIG_CHANGED_EVENT, alphasiftApi } from '../../../api/alphasift';
import { useAppMode } from '../../../contexts/AppModeContext';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import type { UiTextKey } from '../../../i18n/uiText';
import { cn } from '../../../utils/cn';
import { PRODUCT_MENU_ITEMS, DEBUG_MENU_ITEMS, type NavMenuNode } from './menudata';
// 菜单项内部样式覆盖层（CSS Module）：见文件头注释
import styles from './SidebarNavV2.module.scss';

/** 一级菜单展示模式：group=一级以分区标题（GroupLabel）呈现；collapse=一级为可折叠菜单项 */
export type SidebarMenuMode = 'group' | 'collapse';

type SidebarNavV2Props = {
  /** 初始展开状态，默认展开 */
  defaultOpen?: boolean;
  /** 导航完成后的回调（用于移动端抽屉在跳转后自动关闭） */
  onNavigate?: () => void;
  /** 透传到根节点 Sidebar.Provider 的额外类名 */
  className?: string;
  /** 一级菜单展示模式，默认 collapse（一级为可折叠菜单项） */
  menuMode?: SidebarMenuMode;
};

export const SidebarNavV2: React.FC<SidebarNavV2Props> = ({
  defaultOpen = true,
  onNavigate,
  className,
  menuMode = 'collapse',//group
}) => {
  const { t } = useUiLanguage();
  // 运行模式：决定侧边栏呈现产品菜单还是调试菜单
  const { isDevelopmentMode } = useAppMode();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  // AlphaSift 是否启用，控制「选股」入口显隐
  const [showAlphaSiftNav, setShowAlphaSiftNav] = useState(false);

  // 查询 AlphaSift 启用状态并监听配置变更，用 active 标志避免卸载后更新状态
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

  // 按运行模式选择菜单，AlphaSift 未启用时过滤掉「选股」
  const modeMenuItems = isDevelopmentMode ? DEBUG_MENU_ITEMS : PRODUCT_MENU_ITEMS;
  const materialMenuItems = showAlphaSiftNav ? modeMenuItems : modeMenuItems.filter((item) => item.menuId !== 'screening');

  const contentMenuItems = materialMenuItems.filter((item) => item.menuPosition === 'content');
  const footerMenuItems = materialMenuItems.filter((item) => item.menuPosition === 'footer');


  // 命中当前路由：exact 项要求全等，其余按前缀匹配
  const isCurrentRoute = (routePath: string, exact?: boolean) =>
    exact ? pathname === routePath : pathname === routePath || pathname.startsWith(`${routePath}/`);
  // 菜单名解析：优先按 i18n key 翻译，非 key（如「分组一」这类直写文案）原样显示
  const resolveMenuName = (menuName?: string) => (menuName ? t(menuName as UiTextKey) || menuName : '');



  // 默认展开项由各菜单节点的 menuExpanded 字段控制（true 即默认展开）
  const defaultExpandedKeys = contentMenuItems.filter((item) => item.menuExpanded).map((item) => item.menuId);
  // 底部菜单项默认展开由各节点的 menuExpanded 字段控制（true 即默认展开）
  const footerExpandedKeys = footerMenuItems.filter((item) => item.menuExpanded).map((item) => item.menuId);


console.log('defaultExpandedKeys',defaultExpandedKeys)

console.log('footerExpandedKeys',footerExpandedKeys)

  // 运行模式（产品/调试）切换后，自动跳转到菜单栏第一个可跳转菜单：
  // 第一个一级菜单含二级时，跳到其内部第一个二级菜单；否则跳该一级菜单本身。
  const prevModeRef = useRef<boolean | undefined>(undefined);
  useEffect(() => {
    const prevMode = prevModeRef.current;
    prevModeRef.current = isDevelopmentMode;
    // 仅在运行模式真正发生变化时跳转（跳过首次挂载，避免覆盖用户当前路由/深链）
    if (prevMode === undefined || prevMode === isDevelopmentMode) return;
    const firstMenuItem = contentMenuItems[0];
    if (!firstMenuItem) return;
    const targetMenuItem = firstMenuItem.children?.length ? firstMenuItem.children[0] : firstMenuItem;
    const targetPath = targetMenuItem?.routePath;
    if (targetPath) {
      navigate(targetPath);
    }
  }, [isDevelopmentMode]);


  /**
   * 递归渲染菜单节点：一级为分组（routePath 有值才跳转，空值仅展开），二级为子项。
   * 图标/名称按字段渲染，缺省时渲染空插槽（组件 CSS 已固定插槽尺寸）以保留占位对齐。
   * 样式：一级应用 styles.menuItem + styles.menuItemLevel1（含 16px 左右内边距），
   * 二级应用 styles.menuItem，保留 HeroUI 默认缩进以区分层级。
   */
  const renderMenuNodes = (items: NavMenuNode[], depth = 0): React.ReactNode =>
    items.map(({ menuId, menuName, routePath, menuIcon: MenuIcon, children, exact }) => {
      const label = resolveMenuName(menuName);
      const selfCurrent = !!routePath && isCurrentRoute(routePath, exact);
      // 子项命中路由时，一级分组同步高亮
      const childCurrent =
        !selfCurrent && !!children?.some((child) => !!child.routePath && isCurrentRoute(child.routePath, child.exact));

      return (
        <Sidebar.MenuItem
          key={menuId}
          id={menuId}
          href={routePath || undefined}
          textValue={label || menuId}
          isCurrent={selfCurrent || childCurrent}
          className={depth === 0 ? cn(styles.menuItem, styles.menuItemLevel1) : styles.menuItem}
        >
          <Sidebar.MenuIcon>{MenuIcon ? <MenuIcon className="h-5 w-5" /> : null}</Sidebar.MenuIcon>
          <Sidebar.MenuLabel>{label}</Sidebar.MenuLabel>
          {children?.length ? (
            <>
              <Sidebar.MenuTrigger>
                <Sidebar.MenuIndicator />
              </Sidebar.MenuTrigger>
              <Sidebar.Submenu>{renderMenuNodes(children, depth + 1)}</Sidebar.Submenu>
            </>
          ) : null}
        </Sidebar.MenuItem>
      );
    });

  /**
   * collapse 模式渲染：Group + Menu 包裹 renderMenuNodes 的结果，一级菜单为可折叠项，不渲染 GroupLabel。
   * 也被 group 模式的一级叶子节点复用（作为无分区标题的平铺容器），避免两处重复同一包裹结构。
   */
  const renderCollapseMode = (items: NavMenuNode[], expandedKeys?: string[]) => (
    <Sidebar.Group>
      <Sidebar.Menu aria-label={t('layout.mainNav')} defaultExpandedKeys={expandedKeys} className={styles.menu}>
        {renderMenuNodes(items)}
      </Sidebar.Menu>
    </Sidebar.Group>
  );

  /**
   * group 模式渲染：一级节点作为分区呈现（Group + GroupLabel + Menu），二级子项平铺在该 Menu 内；
   * 无子项的一级叶子节点合并进一个 Menu 平铺，避免出现空的分组标题。
   * 分区标题优先取 description，缺省回退 menuName（沿用 description 字段语义）。
   */
  const renderGroupMode = (items: NavMenuNode[]): React.ReactNode => {
    const groupItems = items.filter((item) => item.children?.length);
    const leafItems = items.filter((item) => !item.children?.length);

    return (
      <>
        {groupItems.map((item) => {
          const groupLabel = resolveMenuName(item.menuName);
          return (
            <Sidebar.Group key={item.menuId}>
              <Sidebar.GroupLabel>{groupLabel}</Sidebar.GroupLabel>
              <Sidebar.Menu aria-label={groupLabel} className={styles.menu}>
                {renderMenuNodes(item.children ?? [], 1)}
              </Sidebar.Menu>
            </Sidebar.Group>
          );
        })}
        {leafItems.length ? renderCollapseMode(leafItems) : null}
      </>
    );
  };

  return (
    <Sidebar.Provider
      collapsible="icon"
      defaultOpen={defaultOpen}
      navigate={(href) => {
        navigate(href);
        onNavigate?.();
      }}
      className={cn('hrs-sidebar-V2', className)}
    >
      <Sidebar className='w-full flex h-full flex-col'>
        {/* 头部：整块横向排列 + 垂直居中。
            HeroUI 的 .sidebar__header 默认 column、上下 padding 不对称（pt-4/pb-2），
            且 .sidebar__header > * 会把直接子元素的 justify-content/gap/width 强制清零；
            Pro 样式未分层，同特异性下会盖掉 Tailwind 工具类，故冲突属性用 `!` 提权。 */}
        <Sidebar.Header className="flex-row! items-center py-3!">
          <div className="flex items-center justify-start! gap-3!">
            <div
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
              style={{ background: 'linear-gradient(135deg, hsl(var(--primary) / 0.96), hsl(var(--primary) / 0.78))' }}
            >
              <BarChart3 className="h-5 w-5 text-white" />
            </div>
            <span className="text-foreground text-md font-semibold">HRS</span>
            {/* <Sidebar.Trigger className="ml-auto" /> */}
          </div>
        </Sidebar.Header>
        {/* 主菜单区：flex-1 + min-h-0 占满剩余空间并在自身内部滚动；
            底部设置入口已移出至 Sidebar.Footer，避免随菜单一起滚动。 */}
        <Sidebar.Content className='hrs-sidebar-content flex-1 min-h-0'>
          {menuMode === 'group' ? (
            // group 模式：一级菜单以 GroupLabel 分区标题呈现，按菜单数据动态渲染
            renderGroupMode(contentMenuItems)
          ) : (
            // collapse 模式：不渲染 GroupLabel，一级菜单作为可折叠项由 renderMenuNodes 递归渲染一二级
            renderCollapseMode(contentMenuItems, defaultExpandedKeys)
          )}
        </Sidebar.Content>
        {/* 底部区域：上方按 menuPosition='footer' 动态渲染菜单，底部固定设置入口 */}
        <Sidebar.Footer className='shrink-0'>
          <Sidebar.Separator />
          {footerMenuItems.length > 0 &&
            (menuMode === 'group'
              ? renderGroupMode(footerMenuItems)
              : renderCollapseMode(footerMenuItems, footerExpandedKeys))}
        </Sidebar.Footer>
      </Sidebar>
    </Sidebar.Provider>
  );
};

export default SidebarNavV2;
