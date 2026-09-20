/**
 * @file RouteBoundary.test.tsx
 * @description RouteBoundary 路由边界组件的单元测试：覆盖错误边界的模态回退与路由切换后的自动重置。
 * @author Lensgcx (GaoCangxiong)
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { lazy } from 'react';
import type React from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import { useMenuStore } from '../../../stores/MenuStore';
import { RouteOutletBoundary } from '../RouteBoundary';
import { Shell } from '../Shell';

vi.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({
    authEnabled: false,
    logout: vi.fn().mockResolvedValue(undefined),
  }),
}));

vi.mock('../../../stores/agentChatStore', () => {
  const state = { completionBadge: false };

  return {
    useAgentChatStore: (selector?: (value: typeof state) => unknown) => (
      selector ? selector(state) : state
    ),
  };
});

describe('RouteOutletBoundary', () => {
  // 侧栏菜单由 MenuStore 承载（未登录时为空），先构建菜单才能断言导航项
  beforeAll(() => {
    useMenuStore.getState().buildMenuData();
  });

  it('catches rejected lazy route imports inside the shell and resets on navigation', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const BrokenLazyRoute = lazy(() => (
      Promise.reject(new Error('chunk load failed')) as Promise<{ default: React.ComponentType }>
    ));

    try {
      render(
        <MemoryRouter initialEntries={['/chat']}>
          <Routes>
            <Route
              element={(
                <Shell>
                  <RouteOutletBoundary />
                </Shell>
              )}
            >
              <Route path="/chat" element={<BrokenLazyRoute />} />
              <Route path="/portfolio" element={<div data-testid="portfolio-page">Portfolio</div>} />
            </Route>
          </Routes>
        </MemoryRouter>,
      );

      expect(screen.getByRole('navigation', { name: '主导航' })).toBeInTheDocument();
      expect(await screen.findByRole('heading', { name: '页面加载失败' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '重新加载页面' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '返回首页' })).toBeInTheDocument();

      // 错误态是模态框，打开期间页面其余部分被 aria-hidden，
      // 无法用 role 查询导航链接，这里直接取 DOM 节点模拟点击跳转。
      const portfolioLink = document.querySelector<HTMLAnchorElement>('a[href="/portfolio"]');
      expect(portfolioLink).not.toBeNull();
      fireEvent.click(portfolioLink as HTMLAnchorElement);

      expect(await screen.findByTestId('portfolio-page')).toBeInTheDocument();
      expect(screen.queryByRole('heading', { name: '页面加载失败' })).not.toBeInTheDocument();
    } finally {
      consoleError.mockRestore();
    }
  });
});
