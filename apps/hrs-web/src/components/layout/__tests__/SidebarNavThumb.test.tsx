/**
 * @file SidebarNavThumb.test.tsx
 * @description 侧栏「滑行玻璃」（.navThumb）落点回归测试。
 *   锁定曾经的错位反例：激活项是二级菜单时折叠其一级父菜单，玻璃必须落到该一级菜单行上
 *   （既不能停在旧坐标，也不能飘到相邻菜单行），重新展开后回落到激活的二级菜单。
 *   断言基于落点行的 data-active 标记（玻璃按 data-menu-id 定位同一行），不依赖 jsdom 的几何测量。
 */
import { act, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { SidebarNav } from '../SideBar/SidebarNav';
import { useMenuStore } from '../../../stores';
import type { NavMenuNode } from '../../../types/moduleMenu';

vi.mock('../../../api/alphasift', () => ({
  ALPHASIFT_CONFIG_CHANGED_EVENT: 'alphasift-config-changed',
  SYSTEM_CONFIG_CHANGED_EVENT: 'hrs-system-changed',
  alphasiftApi: {
    // 用永不 resolve 的 Promise：本用例只关心落点，避免异步 setState 落在 act 之外产生告警
    getStatus: vi.fn().mockReturnValue(new Promise(() => undefined)),
  },
}));

// 对齐文档页侧栏结构：可折叠一级菜单「导航」（自身无 routePath）含二级页「侧边栏」，同级另有「布局」
const docsMenu: NavMenuNode[] = [
  {
    menuId: 'docs-nav',
    menuName: '导航',
    routePath: '',
    menuExpanded: true,
    description: '',
    level: 0,
    menuPosition: 'content',
    children: [
      {
        menuId: 'docs-sidebar',
        menuName: '侧边栏',
        routePath: '/docs/component/sideBar',
        menuExpanded: false,
        description: '',
        level: 1,
        menuPosition: 'content',
      },
    ],
  },
  {
    menuId: 'docs-layout',
    menuName: '布局',
    routePath: '/docs/component/layout',
    menuExpanded: false,
    description: '',
    level: 0,
    menuPosition: 'content',
  },
];

/** 渲染侧栏并停在二级页路由（激活项是二级菜单） */
const renderNav = () =>
  render(
    <MemoryRouter initialEntries={['/docs/component/sideBar']}>
      <SidebarNav menuCollapsedState="offcanvas" />
    </MemoryRouter>,
  );

/** 取指定菜单行（MenuNode 在落点行打 data-active，玻璃按 data-menu-id 定位） */
const rowOf = (container: HTMLElement, menuId: string) =>
  container.querySelector<HTMLElement>(`[data-menu-id="${menuId}"]`);

describe('SidebarNav 滑行玻璃落点', () => {
  beforeEach(() => {
    useMenuStore.setState({ currentMenuData: docsMenu });
  });

  afterEach(() => {
    // 复位菜单数据：用例结束组件可能仍在挂载中（cleanup 顺序不定），故包在 act 内避免状态更新告警
    act(() => {
      useMenuStore.setState({ currentMenuData: [] });
    });
  });

  it('激活项可见时落点为该二级菜单', () => {
    const { container } = renderNav();

    expect(rowOf(container, 'docs-sidebar')).toHaveAttribute('data-active', 'true');
    expect(rowOf(container, 'docs-nav')).not.toHaveAttribute('data-active', 'true');
  });

  it('默认展开的一级菜单首次点击即折叠，落点上移到该一级菜单行（不落在相邻菜单上）', () => {
    const { container } = renderNav();

    // 单次点击即生效：有效展开态来自数据默认/路由自动展开时，不能被反推成「展开」而吞掉首次点击
    fireEvent.click(screen.getByText('导航'));

    expect(rowOf(container, 'docs-nav')).toHaveAttribute('data-active', 'true');
    // 曾经的错位表现：落点飘到相邻的一级菜单「布局」上
    expect(rowOf(container, 'docs-layout')).not.toHaveAttribute('data-active', 'true');
  });

  it('一级菜单重新展开后落点回落到激活的二级菜单', () => {
    const { container } = renderNav();

    fireEvent.click(screen.getByText('导航'));
    fireEvent.click(screen.getByText('导航'));

    expect(rowOf(container, 'docs-sidebar')).toHaveAttribute('data-active', 'true');
    expect(rowOf(container, 'docs-nav')).not.toHaveAttribute('data-active', 'true');
  });

  it('路由切换到同层一级页时落点跟随路由', () => {
    const { container } = render(
      <MemoryRouter initialEntries={['/docs/component/layout']}>
        <SidebarNav menuCollapsedState="offcanvas" />
      </MemoryRouter>,
    );

    expect(rowOf(container, 'docs-layout')).toHaveAttribute('data-active', 'true');
    expect(rowOf(container, 'docs-nav')).not.toHaveAttribute('data-active', 'true');
  });
});
