/**
 * @file asyncRouteFactory.test.ts
 * @description buildAsyncRoutes 纯函数单测：验证路径去前导斜杠、handle 元数据承载，
 *   以及 page（路由级 lazy）/ redirect（loader 重定向）两类节点正确区分。
 */
import { describe, expect, it } from 'vitest';
import type { AsyncRouteNode } from '../../types/router';
import { buildAsyncRoutes, resolvePageImporter } from '../asyncRouteFactory';

const pageNode: AsyncRouteNode = {
  routerKey: 'home',
  routerName: '首页',
  routerPath: '/home',
  routerPagePath: 'pages/Home/HomePage',
  routerType: 'page',
  routerDescription: '首页描述',
};

const redirectNode: AsyncRouteNode = {
  routerKey: 'go',
  routerName: '跳转',
  routerPath: '/go',
  routerPagePath: '',
  routerType: 'redirect',
  redirect: '/home',
  routerDescription: '',
};

describe('resolvePageImporter', () => {
  // 通过 Vite 实际展开的文件映射验证，避免 mock 掉构建期扫描边界。
  const pagePaths = Object.keys(import.meta.glob('../../pages/**/*.tsx'));

  it.each(pagePaths)('按生产页面边界解析 %s', (path) => {
    const pagePath = path.replace('../../', '').replace(/\.tsx$/, '');
    const isTest = /\/(?:__tests__|tests)\//.test(path) || /\.(?:test|spec)\.tsx$/.test(path);

    if (isTest) {
      expect(resolvePageImporter(pagePath)).toBeUndefined();
    } else {
      expect(resolvePageImporter(pagePath)).toBeTypeOf('function');
    }
  });

  it('未指定页面时不返回导入器', () => {
    expect(resolvePageImporter()).toBeUndefined();
  });
});

describe('buildAsyncRoutes', () => {
  it('空输入返回空数组', () => {
    expect(buildAsyncRoutes([])).toEqual([]);
  });

  it('剥离前导斜杠、承载 handle，并区分 page 与 redirect', () => {
    const routes = buildAsyncRoutes([pageNode, redirectNode]);
    expect(routes).toHaveLength(2);

    const [page, redirect] = routes as Array<{
      path: string;
      handle?: { routerName?: string; routerDescription?: string };
      lazy?: unknown;
      loader?: unknown;
    }>;

    expect(page.path).toBe('home');
    expect(page.handle).toEqual({ routerName: '首页', routerDescription: '首页描述' });
    expect(typeof page.lazy).toBe('function');
    expect(page.loader).toBeUndefined();

    expect(redirect.path).toBe('go');
    expect(typeof redirect.loader).toBe('function');
    expect(redirect.lazy).toBeUndefined();
  });
});
