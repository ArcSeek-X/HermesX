/**
 * @file KeepAliveOutlet.test.tsx
 * @description 路由缓存出口集成测试（基于 keepalive-for-react / keepalive-for-react-router）：
 *   缓存页切回后组件实例与本地状态保留（不重新挂载）、黑名单页离开即销毁、
 *   缓存键含 hash（hash 变化触发重挂载）。
 */
import { beforeEach, describe, expect, it } from 'vitest';
import { useEffect, useRef, useState } from 'react';
import { act, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { KeepAliveOutlet } from '../KeepAliveOutlet';
import { ScrollContainerProvider } from '../../../contexts/ScrollContainerContext';

/** 各页面存活挂载数：实例被保留时应恒为 1，被销毁重挂载时递增 */
const aliveMounts = new Map<string, number>();

const CounterPage: React.FC<{ label: string }> = ({ label }) => {
  const [count, setCount] = useState(0);
  useEffect(() => {
    aliveMounts.set(label, (aliveMounts.get(label) ?? 0) + 1);
    return () => {
      aliveMounts.set(label, Math.max((aliveMounts.get(label) ?? 1) - 1, 0));
    };
  }, [label]);
  return (
    <div data-testid={`page-${label}`}>
      <span data-testid={`count-${label}`}>{count}</span>
      <button type="button" onClick={() => setCount((c) => c + 1)}>{`inc-${label}`}</button>
    </div>
  );
};

/** 测试布局：复刻 Shell 结构（滚动容器经 Context 下发 + 缓存出口） */
const TestLayout: React.FC = () => {
  const scrollRef = useRef<HTMLElement>(null);
  const navigate = useNavigate();
  const location = useLocation();
  return (
    <ScrollContainerProvider value={scrollRef}>
      <main ref={scrollRef} className="hrs-page-container">
        <nav>
          <button type="button" onClick={() => navigate('/a')}>go-a</button>
          <button type="button" onClick={() => navigate('/b')}>go-b</button>
          <button type="button" onClick={() => navigate('/docs/x')}>go-docs</button>
          <button type="button" onClick={() => navigate('/docsX')}>go-docsX</button>
          <button type="button" onClick={() => navigate('/a#two')}>go-a-hash</button>
        </nav>
        <span data-testid="current-path">{location.pathname}</span>
        <KeepAliveOutlet />
      </main>
    </ScrollContainerProvider>
  );
};

const renderApp = (initial: string) =>
  render(
    <MemoryRouter initialEntries={[initial]}>
      <Routes>
        <Route element={<TestLayout />}>
          <Route path="a" element={<CounterPage label="a" />} />
          <Route path="b" element={<CounterPage label="b" />} />
          <Route path="docs/x" element={<CounterPage label="docs" />} />
          <Route path="docsX" element={<CounterPage label="docsX" />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );

/** 刷新宏任务：库对失活页的销毁走 setTimeout(0) */
const flushTimers = async () => {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
};

const clickButton = (name: string) => {
  act(() => {
    screen.getByRole('button', { name }).click();
  });
};

beforeEach(() => {
  aliveMounts.clear();
});

describe('KeepAliveOutlet 路由缓存', () => {
  it('缓存页切回后保留实例与本地状态，不重新挂载', () => {
    renderApp('/a');
    expect(screen.getByTestId('page-a')).toBeTruthy();

    clickButton('inc-a');
    expect(screen.getByTestId('count-a').textContent).toBe('1');

    clickButton('go-b');
    expect(screen.getByTestId('page-b')).toBeTruthy();
    expect(aliveMounts.get('a')).toBe(1);

    clickButton('go-a');
    expect(screen.getByTestId('count-a').textContent).toBe('1');
    expect(aliveMounts.get('a')).toBe(1);
  });

  it('黑名单页（/docs/*）离开即销毁，返回后重新挂载、状态不保留', async () => {
    renderApp('/a');

    clickButton('go-docs');
    expect(screen.getByTestId('page-docs')).toBeTruthy();
    clickButton('inc-docs');
    expect(screen.getByTestId('count-docs').textContent).toBe('1');

    clickButton('go-a');
    await flushTimers();

    clickButton('go-docs');
    expect(screen.getByTestId('count-docs').textContent).toBe('0');
  });

  it('缓存键含 hash：hash 变化触发重挂载', () => {
    renderApp('/a');
    clickButton('inc-a');
    expect(screen.getByTestId('count-a').textContent).toBe('1');

    clickButton('go-a-hash');
    expect(screen.getByTestId('count-a').textContent).toBe('0');
  });

  it('前缀规则不误伤同前缀路径：/docsX 仍参与缓存（toMatchRules 精度行为覆盖）', () => {
    renderApp('/a');

    clickButton('go-docsX');
    expect(screen.getByTestId('page-docsX')).toBeTruthy();
    clickButton('inc-docsX');
    expect(screen.getByTestId('count-docsX').textContent).toBe('1');

    clickButton('go-a');
    clickButton('go-docsX');
    expect(screen.getByTestId('count-docsX').textContent).toBe('1');
  });
});
