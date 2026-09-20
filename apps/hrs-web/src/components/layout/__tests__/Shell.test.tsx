/**
 * @file Shell.test.tsx
 * @description Shell 应用外壳组件的单元测试：覆盖退出登录二次确认链路（含头部个人设置菜单）。
 * @author Lensgcx (GaoCangxiong)
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import { ThemeProvider } from '../../theme/ThemeProvider';
import { useMenuStore } from '../../../stores/MenuStore';
import { Shell } from '../Shell';

const mockLogout = vi.fn().mockResolvedValue(undefined);

vi.mock('../../../contexts/AuthContext', () => ({
  useAuth: () => ({
    authEnabled: true,
    logout: mockLogout,
  }),
}));

vi.mock('../../../stores/agentChatStore', () => ({
  useAgentChatStore: (selector: (state: { completionBadge: boolean }) => unknown) =>
    selector({ completionBadge: true }),
}));

beforeAll(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: query === '(prefers-color-scheme: dark)',
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
});

/** 渲染应用外壳；菜单数据由 MenuStore 构建，未登录时侧栏为空，故先模拟登录后的建菜单动作。 */
function renderShell() {
  useMenuStore.getState().buildMenuData();

  return render(
    <MemoryRouter initialEntries={['/chat']}>
      <ThemeProvider>
        <Shell>
          <div>page content</div>
        </Shell>
      </ThemeProvider>
    </MemoryRouter>,
  );
}

describe('Shell', () => {
  it('renders the shell chrome with the page content', () => {
    renderShell();

    expect(screen.getByText('page content')).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: '主导航' })).toBeInTheDocument();
  });

  it('shows a confirmation dialog before logout', async () => {
    renderShell();

    // 退出入口位于头部「个人设置」下拉菜单内，需先展开菜单
    fireEvent.click(screen.getByRole('button', { name: '个人设置' }));
    fireEvent.click(screen.getByRole('menuitem', { name: '退出' }));

    expect(await screen.findByRole('heading', { name: '退出登录' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '确认退出' }));
    expect(mockLogout).toHaveBeenCalled();
  });

  it('keeps the session when the logout confirmation is cancelled', async () => {
    mockLogout.mockClear();
    renderShell();

    fireEvent.click(screen.getByRole('button', { name: '个人设置' }));
    fireEvent.click(screen.getByRole('menuitem', { name: '退出' }));

    expect(await screen.findByRole('heading', { name: '退出登录' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '取消' }));

    expect(mockLogout).not.toHaveBeenCalled();
  });
});
