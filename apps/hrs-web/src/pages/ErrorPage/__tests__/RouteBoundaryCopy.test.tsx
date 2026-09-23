/**
 * @file RouteBoundaryCopy.test.tsx
 * @description 隔离验证 ErrorModal 的「复制」按钮已接入 clipboard-copy（不依赖会触发循环依赖的 barrel / appRouter）。
 * @author CodeBuddy
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { RouteErrorBoundary } from '../RouteBoundary';

// 1) 拦截真实 clipboard-copy，便于断言调用（vi.hoisted 使 mock 工厂可引用）
const { copyMock } = vi.hoisted(() => ({
  copyMock: vi.fn().mockResolvedValue(undefined),
}));
vi.mock('clipboard-copy', () => ({ default: copyMock }));

// 2) 拦截 barrel，避免其 transitive 引入 appRouter（既有循环依赖会让测试在加载阶段崩溃）
vi.mock('@components', () => {
  const Box = ({ children }: { children?: React.ReactNode }) => <div>{children}</div>;
  const Modal = Object.assign(Box, { Header: Box, Heading: Box, Body: Box, Footer: Box, Freedom: Box });
  return {
    Modal,
    HrsButton: ({ children, onClick }: { children?: React.ReactNode; onClick?: () => void }) => (
      <button onClick={onClick} type="button">
        {children}
      </button>
    ),
    ThemeToggle: () => null,
    LanguageSwitch: () => null,
  };
});

// 3) 提供 i18n key 透传，便于按文案定位元素
vi.mock('../../../contexts/UiLanguageContext', () => ({
  useUiLanguage: () => ({ t: (k: string) => k }),
}));


describe('RouteErrorBoundary 复制功能（clipboard-copy）', () => {
  beforeEach(() => copyMock.mockClear());

  it('点击复制会将 problemDetails 写入剪贴板', async () => {
    const Boom = () => {
      throw new Error('boom detail message');
    };
    const router = createMemoryRouter([
      { path: '/', element: <Boom />, errorElement: <RouteErrorBoundary /> },
    ]);
    render(<RouterProvider router={router} />);

    // 展开「查看详情」
    fireEvent.click(await screen.findByText(/exception\.routeBoundary\.details/));
    // 点击「复制」
    const copyBtn = await screen.findByText('exception.routeBoundary.copy');
    fireEvent.click(copyBtn);

    await waitFor(() =>
      expect(copyMock).toHaveBeenCalledWith(expect.stringContaining('boom detail message')),
    );
  });
});
