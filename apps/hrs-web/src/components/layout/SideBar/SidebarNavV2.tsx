/**
 * 侧边导航 V2（SidebarNavV2）：基于 HeroUI Pro 的 Sidebar 组件实现的应用主导航。
 * 支持两级菜单：一级为分组（routePath 有值才可跳转，空值仅展开），二级为具体页面；
 * 菜单名与图标按数据字段渲染，缺省时不显示但保留占位，保证上下对齐。
 * 随运行模式切换产品/调试菜单，「选股」受 AlphaSift 开关控制；
 * 通过 Provider 的 navigate 接入 react-router，点击菜单走 SPA 跳转而非整页刷新。
 * 只封装侧栏本体（Provider + Sidebar），Sidebar.Mobile / Sidebar.Main 由布局层组合。
 *
 * @author Lensgcx (GaoCangxiong)
 */
import React, { useEffect, useState } from 'react';
import { Sidebar } from '@heroui-pro/react';
import { useLocation, useNavigate } from 'react-router-dom';
import { BarChart3, Settings2 } from 'lucide-react';
import { ALPHASIFT_CONFIG_CHANGED_EVENT, SYSTEM_CONFIG_CHANGED_EVENT, alphasiftApi } from '../../../api/alphasift';
import { useAppMode } from '../../../contexts/AppModeContext';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import type { UiTextKey } from '../../../i18n/uiText';
import { PRODUCT_NAV_ITEMS, DEBUG_NAV_ITEMS, type NavMenuNode } from './menudata';

type SidebarNavV2Props = {
  /** 初始展开状态，默认展开 */
  defaultOpen?: boolean;
};

export const SidebarNavV2: React.FC<SidebarNavV2Props> = ({ defaultOpen = true }) => {
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
  const modeItems = isDevelopmentMode ? DEBUG_NAV_ITEMS : PRODUCT_NAV_ITEMS;
  const navItems = showAlphaSiftNav ? modeItems : modeItems.filter((item) => item.menuKey !== 'screening');
  // 命中当前路由：exact 项要求全等，其余按前缀匹配
  const isCurrent = (routePath: string, exact?: boolean) =>
    exact ? pathname === routePath : pathname === routePath || pathname.startsWith(`${routePath}/`);
  // 菜单名解析：优先按 i18n key 翻译，非 key（如「分组一」这类直写文案）原样显示
  const resolveMenuName = (menuName?: string) => (menuName ? t(menuName as UiTextKey) || menuName : '');
  // 含二级菜单的一级项默认展开，避免分组折叠后侧栏看起来是空的
  const defaultExpandedKeys = navItems.filter((item) => item.children?.length).map((item) => item.menuKey);

  /**
   * 递归渲染菜单节点：一级为分组（routePath 有值才跳转，空值仅展开），二级为子项。
   * 图标/名称按字段渲染，缺省时渲染空插槽（组件 CSS 已固定插槽尺寸）以保留占位对齐。
   */
  const renderMenuNodes = (items: NavMenuNode[]): React.ReactNode =>
    items.map(({ menuKey, menuName, routePath, menuIcon: MenuIcon, children, exact }) => {
      const label = resolveMenuName(menuName);
      const selfCurrent = !!routePath && isCurrent(routePath, exact);
      // 子项命中路由时，一级分组同步高亮
      const childCurrent =
        !selfCurrent && !!children?.some((child) => !!child.routePath && isCurrent(child.routePath, child.exact));

      return (
        <Sidebar.MenuItem
          key={menuKey}
          id={menuKey}
          href={routePath || undefined}
          textValue={label || menuKey}
          isCurrent={selfCurrent || childCurrent}
        >
          <Sidebar.MenuIcon>{MenuIcon ? <MenuIcon className="h-4 w-4" /> : null}</Sidebar.MenuIcon>
          <Sidebar.MenuLabel>{label}</Sidebar.MenuLabel>
          {children?.length ? (
            <>
              <Sidebar.MenuTrigger>
                <Sidebar.MenuIndicator />
              </Sidebar.MenuTrigger>
              <Sidebar.Submenu>{renderMenuNodes(children)}</Sidebar.Submenu>
            </>
          ) : null}
        </Sidebar.MenuItem>
      );
    });

  return (
    <Sidebar.Provider collapsible="icon" defaultOpen={defaultOpen} navigate={navigate}>
      <Sidebar>
        <Sidebar.Header>
          <div className="flex items-center gap-3 px-1 py-2">
            <div
              className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md"
              style={{ background: 'linear-gradient(135deg, hsl(var(--primary) / 0.96), hsl(var(--primary) / 0.78))' }}
            >
              <BarChart3 className="h-4 w-4 text-white" />
            </div>
            <span className="text-foreground text-sm font-semibold">HRS</span>
            <Sidebar.Trigger className="ml-auto" />
          </div>
        </Sidebar.Header>
        <Sidebar.Content>
          <Sidebar.Group>
            <Sidebar.GroupLabel>{t('layout.mainNav')}</Sidebar.GroupLabel>
            <Sidebar.Menu aria-label={t('layout.mainNav')} defaultExpandedKeys={defaultExpandedKeys}>
              {renderMenuNodes(navItems)}
            </Sidebar.Menu>
          </Sidebar.Group>
          <Sidebar.Separator />
          {/* 底部设置入口：与 SidebarNav 一致，独立于主菜单分组 */}
          <Sidebar.Group>
            <Sidebar.Menu aria-label={t('layout.nav.settings.title')}>
              <Sidebar.MenuItem
                id="settings"
                href="/settings"
                textValue={t('layout.nav.settings.title')}
                isCurrent={isCurrent('/settings')}
              >
                <Sidebar.MenuIcon>
                  <Settings2 className="h-4 w-4" />
                </Sidebar.MenuIcon>
                <Sidebar.MenuLabel>{t('layout.nav.settings.title')}</Sidebar.MenuLabel>
              </Sidebar.MenuItem>
            </Sidebar.Menu>
          </Sidebar.Group>
        </Sidebar.Content>
      </Sidebar>
    </Sidebar.Provider>
  );
};

export default SidebarNavV2;
