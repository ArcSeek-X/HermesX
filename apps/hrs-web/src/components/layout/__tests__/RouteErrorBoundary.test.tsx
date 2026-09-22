/**
 * @file RouteErrorBoundary.test.tsx
 * @description RouteErrorBoundary（轻量错误边界）单测：验证其读取 useRouteError 并展示错误描述与重新加载按钮。
 */
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import type React from 'react';
import { RouteErrorBoundary } from '../../../pages/ErrorPage/RouteBoundary';

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return {
    ...actual,
    useRouteError: () => new Error('boom'),
    isRouteErrorResponse: () => false,
  };
});

vi.mock('../../../contexts/UiLanguageContext', () => ({
  useUiLanguage: () => ({ t: (key: string) => key }),
}));

describe('RouteErrorBoundary（轻量）', () => {
  it('渲染 useRouteError 的错误描述、重新加载与返回登录按钮', () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined);
    render(<RouteErrorBoundary />);
    expect(screen.getByText('boom')).toBeInTheDocument();
    // 重新加载按钮存在（i18n 已被 mock 为原 key）
    expect(screen.getByText('routeError.reload')).toBeInTheDocument();
    // 返回登录按钮存在
    expect(screen.getByText('routeError.backToLogin')).toBeInTheDocument();
  });
});
