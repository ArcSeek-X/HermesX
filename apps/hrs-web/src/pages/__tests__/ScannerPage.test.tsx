import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { UiLanguageProvider } from '../../contexts/UiLanguageContext';
import ScannerPage from '../Discover/ScannerPage/ScannerPage';

/**
 * 信号扫描页面冒烟：覆盖「配置 -> 提交任务 -> 轮询增量结果 -> 取消」主链路。
 * API 层统一 mock apiClient（scanner.ts 的请求出口），自选股接口单独 mock。
 */

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));

vi.mock('../../api/index', () => ({ default: { get, post } }));

// 固定界面语言为简体：jsdom 下浏览器语言推断会得到英文，断言文案需稳定
vi.mock('@utils/uiLanguage', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    getRuntimeInitialLanguage: () => 'zh',
    getUiLanguageStorage: () => 'local',
    persistUiLanguage: () => undefined,
  };
});

const { getWatchlistGroups, getAllWatchlistItems, createWatchlistItem } = vi.hoisted(() => ({
  getWatchlistGroups: vi.fn(),
  getAllWatchlistItems: vi.fn(),
  createWatchlistItem: vi.fn(),
}));

vi.mock('../../api/watchlist', () => ({
  getWatchlistGroups,
  getAllWatchlistItems,
  createWatchlistItem,
}));

const OPTIONS = {
  pool_sources: ['watchlist', 'ranking', 'limit_up'],
  ranking_fields: ['amount', 'change_percent', 'turnover_rate'],
  top_n_options: [20, 50, 100],
  signals: ['ma_golden', 'macd_golden'],
  defaults: {
    pool_source: 'watchlist',
    ranking_field: 'amount',
    top_n: 20,
    signals: ['ma_golden'],
  },
  max_pool_size: 300,
};

function taskStatus(phase: 'processing' | 'completed', results: unknown[]) {
  return {
    task_id: 'task-1',
    status: phase,
    progress: phase === 'completed' ? 100 : 40,
    message: phase === 'completed' ? '扫描完成，命中 2 只' : '技术信号扫描 1/2',
    error: null,
    pool_count: 2,
    scanned: phase === 'completed' ? 2 : 1,
    match_count: results.length,
    results,
    cancelled: false,
    finished: phase === 'completed',
  };
}

const ROW_A = { code: '600519', name: '贵州茅台', signals: ['ma_golden'], scanned_at: '2026-10-14 00:00:00' };
const ROW_B = { code: '000001', name: '平安银行', signals: ['macd_golden'], scanned_at: '2026-10-14 00:00:00' };

function renderPage() {
  return render(
    <UiLanguageProvider>
      <MemoryRouter>
        <ScannerPage />
      </MemoryRouter>
    </UiLanguageProvider>,
  );
}

describe('ScannerPage', () => {
  beforeEach(() => {
    get.mockReset();
    post.mockReset();
    getWatchlistGroups.mockReset();
    getAllWatchlistItems.mockReset();
    createWatchlistItem.mockReset();

    getWatchlistGroups.mockResolvedValue([{ id: 7, name: '默认', sortOrder: 0, groupCode: 'g1', itemCount: 1 }]);
    getAllWatchlistItems.mockResolvedValue([
      { id: 1, groupId: 7, stockCode: '600519.SH', stockName: '贵州茅台' },
    ]);

    get.mockImplementation(async (url: string) => {
      if (url.includes('/scanner/options')) return { data: OPTIONS };
      // 首次轮询返回「进行中 + 1 条增量结果」，之后返回完成态
      if (url.includes('/tasks/')) return { data: taskStatus('processing', [ROW_A]) };
      return { data: {} };
    });
    post.mockResolvedValue({ data: { task_id: 'task-1', status: 'pending', message: 'ok' } });
  });

  it('提交任务后轮询并渲染增量结果', async () => {
    renderPage();

    // 等待自选股池加载完成（页面表现为自选池说明文案）
    await waitFor(() => expect(getAllWatchlistItems).toHaveBeenCalledWith(7));

    // 点击「开始扫描」
    const startButton = await screen.findByRole('button', { name: /开始扫描/ });
    await act(async () => {
      fireEvent.click(startButton);
    });

    expect(post).toHaveBeenCalledWith(
      '/api/v1/scanner/tasks',
      expect.objectContaining({
        pool_source: 'watchlist',
        signals: ['ma_golden'],
        watchlist: [{ code: '600519', name: '贵州茅台' }],
      }),
    );

    // 运行中即渲染已命中的增量结果
    await waitFor(() => expect(screen.getByText('贵州茅台')).toBeTruthy(), { timeout: 4000 });

    // 切换为完成态后再轮询一次，第二条结果应出现
    get.mockImplementation(async (url: string) => {
      if (url.includes('/scanner/options')) return { data: OPTIONS };
      if (url.includes('/tasks/')) return { data: taskStatus('completed', [ROW_A, ROW_B]) };
      return { data: {} };
    });
    await waitFor(() => expect(screen.getByText('平安银行')).toBeTruthy(), { timeout: 4000 });
  });

  it('未选择信号模板时禁止开始扫描', async () => {
    renderPage();
    await waitFor(() => expect(getAllWatchlistItems).toHaveBeenCalledWith(7));

    // 取消唯一选中的 MA金叉
    const signalCard = await screen.findByText('MA金叉');
    await act(async () => {
      fireEvent.click(signalCard);
    });

    const startButton = await screen.findByRole('button', { name: /开始扫描/ });
    await act(async () => {
      fireEvent.click(startButton);
    });
    // 未选信号时开始按钮不可用，请求不得发出
    const disabled =
      startButton.hasAttribute('disabled') || startButton.getAttribute('aria-disabled') === 'true';
    expect(disabled).toBe(true);
    expect(post).not.toHaveBeenCalled();
  });

  it('运行中可请求取消', async () => {
    renderPage();
    await waitFor(() => expect(getAllWatchlistItems).toHaveBeenCalledWith(7));

    const startButton = await screen.findByRole('button', { name: /开始扫描/ });
    await act(async () => {
      fireEvent.click(startButton);
    });

    const cancelButton = await screen.findByRole('button', { name: /取消扫描/ });
    await act(async () => {
      fireEvent.click(cancelButton);
    });
    expect(post).toHaveBeenCalledWith('/api/v1/scanner/tasks/task-1/cancel');
  });

  it('加自选写入默认分组', async () => {
    renderPage();
    await waitFor(() => expect(getAllWatchlistItems).toHaveBeenCalledWith(7));

    const startButton = await screen.findByRole('button', { name: /开始扫描/ });
    await act(async () => {
      fireEvent.click(startButton);
    });
    await waitFor(() => expect(screen.getByText('贵州茅台')).toBeTruthy(), { timeout: 4000 });

    // 600519 已在默认分组内 -> 按钮为「已自选」且禁用
    const addedButton = await screen.findByRole('button', { name: /已自选/ });
    expect(addedButton).toBeTruthy();

    // 结果行整行点击跳转 K 线页（sessionStorage 写入目标代码，键名前缀由 storage 工具决定）
    const row = screen.getByText('贵州茅台');
    await act(async () => {
      fireEvent.click(row);
    });
    const stored = Object.keys(sessionStorage).map((key) => sessionStorage.getItem(key) ?? '');
    expect(stored.some((value) => value.includes('600519'))).toBe(true);
  });
});
