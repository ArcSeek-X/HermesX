/**
 * @file useNavThumb.test.ts
 * @description 侧栏高亮/落点判定单元测试：路由匹配原语 matchPath 与滑行玻璃落点解析 resolveHighlightMenuCode
 *   （二者现均由 ./SideBar/useNavThumb 导出，原 menuPath.ts 已并入）。
 *   重点锁定落点契约：命中项被折叠祖先隐藏时上移到该祖先（玻璃落到一级菜单行）、
 *   祖先重新展开后回落到命中项、并列命中时的确定性裁决、无命中时无落点（玻璃隐藏）。
 */
import { describe, expect, it } from 'vitest';
import { matchPath, resolveHighlightMenuCode } from '../SideBar/useNavThumb';
import type { NavMenuNode } from '../../../types/moduleMenu';

/** 构造测试节点：只填必填字段，再按用例覆写关心字段，避免 fixtures 噪声 */
const menuNode = (node: Partial<NavMenuNode> & Pick<NavMenuNode, 'menuCode'>): NavMenuNode => ({
  menuName: '',
  menuType: 'page',
  menuSort: 0,
  menuStatus: 1,
  menuVisible: true,
  menuPosition: 'content',
  menuExpanded: false,
  menuDescription: '',
  ...node,
});

/** 按节点 menuExpanded 派生展开判定；显式状态优先（等价于 SidebarNav 的 userExpanded 覆盖语义） */
const expandedBy = (override: Record<string, boolean> = {}) => (node: NavMenuNode) =>
  override[node.menuCode] ?? node.menuExpanded;

// 文档页侧栏结构（对齐 MENU_MANIFEST）：可折叠一级菜单「导航」只承载子项（自身无 menuRoutePath），
// 其下两个二级页；同级另有不可折叠的一级页
const docsMenu: NavMenuNode[] = [
  menuNode({
    menuCode: 'nav',
    menuRoutePath: '',
    menuExpanded: true,
    children: [
      menuNode({ menuCode: 'sidebar', menuRoutePath: '/docs/component/sideBar', }),
      menuNode({ menuCode: 'tabNav', menuRoutePath: '/docs/component/tabNav', }),
    ],
  }),
  menuNode({ menuCode: 'layout', menuRoutePath: '/docs/component/layout' }),
  menuNode({ menuCode: 'overlay', menuRoutePath: '/docs/component/overlay' }),
];

// 三级链：验证「链上第一个折叠的祖先」而非「任意折叠节点」；
// 中间层路由 /deep 是叶子路由 /deep/leaf 的前缀（祖先与后代同时命中，用于验证更深者优先）
const deepMenu: NavMenuNode[] = [
  menuNode({
    menuCode: 'root',
    menuRoutePath: '',
    menuExpanded: true,
    children: [
      menuNode({
        menuCode: 'mid',
        menuRoutePath: '/deep',
        menuExpanded: true,
        children: [menuNode({ menuCode: 'leaf', menuRoutePath: '/deep/leaf', })],
      }),
    ],
  }),
];

// 容器以路径前缀注册时与同级页面的竞争（容器先出现，落点不得被它抢占）
const prefixMenu: NavMenuNode[] = [
  menuNode({
    menuCode: 'container',
    menuRoutePath: '/docs/component',
    menuExpanded: true,
    children: [menuNode({ menuCode: 'inner', menuRoutePath: '/docs/component/inner', })],
  }),
  menuNode({ menuCode: 'layout', menuRoutePath: '/docs/component/layout' }),
];

describe('matchPath', () => {
  it('非精确匹配时子路径也算命中', () => {
    expect(matchPath('/docs/component', false, '/docs/component/sideBar')).toBe(true);
  });

  it('精确匹配时子路径不算命中', () => {
    expect(matchPath('/docs/component', true, '/docs/component/sideBar')).toBe(false);
    expect(matchPath('/docs/component', true, '/docs/component')).toBe(true);
  });

  it('无路由的菜单项一律不命中', () => {
    expect(matchPath(undefined, false, '/docs/component')).toBe(false);
    expect(matchPath('', false, '/docs/component')).toBe(false);
  });
});

describe('resolveHighlightMenuCode', () => {
  it('命中二级菜单时落点为该二级菜单', () => {
    expect(resolveHighlightMenuCode(docsMenu, '/docs/component/sideBar', expandedBy())).toBe('sidebar');
  });

  it('命中项被折叠的一级菜单隐藏时，落点上移到该一级菜单', () => {
    expect(resolveHighlightMenuCode(docsMenu, '/docs/component/sideBar', expandedBy({ nav: false }))).toBe('nav');
  });

  it('一级菜单重新展开后，落点回落到激活的二级菜单', () => {
    expect(resolveHighlightMenuCode(docsMenu, '/docs/component/sideBar', expandedBy({ nav: true }))).toBe('sidebar');
  });

  it('命中的是同层一级页（无子级）时落点为它自身', () => {
    expect(resolveHighlightMenuCode(docsMenu, '/docs/component/layout', expandedBy())).toBe('layout');
  });

  it('多级链上只上移到「第一个折叠的祖先」（更靠内的折叠节点被它一并隐藏）', () => {
    // 全部展开：/deep 与 /deep/leaf 同时命中，落点取更深的叶子
    expect(resolveHighlightMenuCode(deepMenu, '/deep/leaf', expandedBy())).toBe('leaf');
    expect(resolveHighlightMenuCode(deepMenu, '/deep/leaf', expandedBy({ mid: false }))).toBe('mid');
    expect(resolveHighlightMenuCode(deepMenu, '/deep/leaf', expandedBy({ root: false }))).toBe('root');
    expect(resolveHighlightMenuCode(deepMenu, '/deep/leaf', expandedBy({ root: false, mid: false }))).toBe('root');
  });

  it('容器以路径前缀注册时不抢占同级页面（完全相等者优先，与数组顺序无关）', () => {
    expect(resolveHighlightMenuCode(prefixMenu, '/docs/component/layout', expandedBy())).toBe('layout');
  });

  it('命中容器自身路由时落点为该容器（即使它处于折叠态）', () => {
    expect(resolveHighlightMenuCode(prefixMenu, '/docs/component', expandedBy({ container: false }))).toBe(
      'container',
    );
  });

  it('无菜单命中当前路由时无落点（调用方隐藏玻璃）', () => {
    expect(resolveHighlightMenuCode(docsMenu, '/chat', expandedBy())).toBeNull();
  });
});
