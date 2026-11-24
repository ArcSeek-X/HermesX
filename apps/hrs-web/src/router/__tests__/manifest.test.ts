import { describe, expect, it } from 'vitest';
import { MENU_MANIFEST } from '../manifest';
import { resolvePageImporter } from '../asyncRouteFactory';
import type { NavMenuNode } from '../../types/moduleMenu';

const flatten = (nodes: NavMenuNode[]): NavMenuNode[] =>
  nodes.flatMap((node) => [node, ...flatten(node.children ?? [])]);

const nodes = flatten(MENU_MANIFEST);

describe('统一菜单清单契约', () => {
  it('保留三个模块、13 个分组和 44 个页面，统一使用 menuCode/menuType', () => {
    expect(MENU_MANIFEST.map((node) => [node.menuCode, node.menuType])).toEqual([
      ['productModel', 'module'], ['developmentMode', 'module'], ['systemMode', 'module'],
    ]);
    expect(nodes.filter((node) => node.menuType === 'group')).toHaveLength(13);
    expect(nodes.filter((node) => node.menuType === 'page')).toHaveLength(44);
    expect(new Set(nodes.map((node) => node.menuCode)).size).toBe(nodes.length);
    for (const node of nodes) {
      expect(['module', 'group', 'page']).toContain(node.menuType);
      expect(node.menuName).toBeTypeOf('string');
      expect(node.menuDescription).toBeTypeOf('string');
      expect(node.menuStatus).toBe(1);
      expect(node.menuVisible).toBe(true);
      expect(node.menuExpanded).toBeTypeOf('boolean');
      expect(node.menuSort).toBeGreaterThanOrEqual(0);
      for (const oldField of ['moduleId', 'moduleName', 'moduleDescription', 'moduleIcon',
        'moduleGroupId', 'moduleGroupName', 'menuId', 'routePath', 'description', 'level']) {
        expect(node).not.toHaveProperty(oldField);
      }
      // 后端尚未接入，不用数组序号或字符串业务码伪造数据库主键。
      expect(node.id).toBeUndefined();
      expect(node.menuParentId).toBeUndefined();
    }
  });

  it('全部页面保留有效路由、登录策略及真实可解析的页面文件', () => {
    const pages = nodes.filter((node) => node.menuType === 'page');
    expect(new Set(pages.map((node) => node.menuRoutePath)).size).toBe(pages.length);
    for (const page of pages) {
      expect(page.menuRoutePath).toMatch(/^\//);
      expect(page.auth).toBe('protected');
      expect(resolvePageImporter(page.menuPagePath)).toBeTypeOf('function');
    }
    expect(pages.find((node) => node.menuCode === 'watchlist')).toMatchObject({
      menuRoutePath: '/watchlist', menuPagePath: 'pages/WatchlistPage/WatchlistPage',
    });
  });
});
