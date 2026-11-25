/**
 * @file ThemeSync.test.tsx
 * @description 主题桥接回归测试：setTheme 引用变化不应触发回写，避免跨标签页互相改写主题。
 */
import { render } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ThemeSync } from '../ThemeSync';

const { setThemeState, themeState, applyPrimaryColorMock } = vi.hoisted(() => ({
  setThemeState: { current: vi.fn() },
  themeState: { themeMode: 'light' as 'light' | 'dark' | 'system', themeColor: '#19B5C4' },
  applyPrimaryColorMock: vi.fn(),
}));

vi.mock('next-themes', () => ({
  useTheme: () => ({ setTheme: setThemeState.current }),
}));

vi.mock('../../../stores/themeStore', () => ({
  useThemeStore: (selector: (state: typeof themeState) => unknown) => selector(themeState),
}));

vi.mock('../../../utils/themeColor', () => ({
  applyPrimaryColor: applyPrimaryColorMock,
}));

describe('ThemeSync', () => {
  beforeEach(() => {
    setThemeState.current = vi.fn();
    themeState.themeMode = 'light';
    themeState.themeColor = '#19B5C4';
    applyPrimaryColorMock.mockClear();
  });

  it('只在 store 的 themeMode 变化时回写，setTheme 引用变化本身不回写', () => {
    const { rerender } = render(<ThemeSync />);
    expect(setThemeState.current).toHaveBeenCalledTimes(1);
    expect(setThemeState.current).toHaveBeenCalledWith('light');

    // 模拟跨标签页 storage 事件令 next-themes 更换 setTheme 引用：不应重新写入共享 key
    setThemeState.current = vi.fn();
    rerender(<ThemeSync />);
    expect(setThemeState.current).not.toHaveBeenCalled();

    // 真实偏好变化仍需同步
    themeState.themeMode = 'dark';
    rerender(<ThemeSync />);
    expect(setThemeState.current).toHaveBeenCalledTimes(1);
    expect(setThemeState.current).toHaveBeenCalledWith('dark');
  });

  it('主色变化应用到 CSS 变量', () => {
    const { rerender } = render(<ThemeSync />);
    expect(applyPrimaryColorMock).toHaveBeenCalledWith('#19B5C4');

    themeState.themeColor = '#FF0000';
    rerender(<ThemeSync />);
    expect(applyPrimaryColorMock).toHaveBeenLastCalledWith('#FF0000');
  });
});
