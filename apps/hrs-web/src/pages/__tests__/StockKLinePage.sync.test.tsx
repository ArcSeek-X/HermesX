/**
 * K 线页面导航直达同步回归测试
 *
 * 覆盖：从自选股等入口以 ?stockCode= 直达 /stock/kline 后，搜索框展示标签
 * 必须与下方行情头上下一致（同一只股票）。
 *
 * 关键回归点（曾经的线上 bug）：
 * - 搜索框展示来自 sessionStorage 的 displayValue 缓存，导航直达时若不更新，
 *   会残留上一只股票的「名称（代码）」，导致与行情头不一致；
 * - 展示标签以本地股票索引反查后缀，但索引异步加载常晚于 stockInfo 到达，
 *   早退逻辑会永久停留在退化标签——现实现以 stockInfo 为准，索引后到自动补后缀。
 */
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { PageStateProvider } from '../../stores/PageStateStore';
import type { StockIndexItem } from '../../types/stockIndex';

vi.mock('echarts', () => {
  class LinearGradient { constructor(..._a: unknown[]) { void _a; } }
  const inst = { setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn(), getDataURL: vi.fn(() => ''), on: vi.fn(), off: vi.fn(), clear: vi.fn() };
  return { init: vi.fn(() => inst), dispose: vi.fn(), graphic: { LinearGradient }, __inst: inst };
});

// 用真实 displayValue 透传到 input，便于断言页面传给 StockSearch 的展示值
vi.mock('@components/StockSearch/StockSearch', () => ({
  StockSearch: ({ displayValue, value }: { displayValue?: string; value: string }) => (
    <input data-testid="search-input" value={displayValue || value || ''} readOnly />
  ),
}));

// 可控的股票索引 mock：用于模拟「索引晚于 stockInfo 到达」的时序
let currentIndex: StockIndexItem[] = [];
vi.mock('../../hooks/useStockIndex', () => ({
  useStockIndex: () => ({ index: currentIndex, loading: false, loaded: true, error: null, fallback: false }),
}));

const fetchKLineMock = vi.fn();
const fetchStockInfoMock = vi.fn();
vi.mock('../../api/kline', () => ({
  klineApi: {
    fetchKLine: (...a: unknown[]) => fetchKLineMock(...a),
    fetchStockInfo: (...a: unknown[]) => fetchStockInfoMock(...a),
    searchStocks: () => Promise.resolve([]),
  },
}));

import StockKLinePage from '../Stock/StockKLinePage/StockKLinePage';

const INDEX_HIT: StockIndexItem = {
  canonicalCode: '600519.SH',
  displayCode: '600519',
  nameZh: '贵州茅台',
  market: 'CN',
  assetType: 'stock',
  active: true,
};

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <PageStateProvider>
        <StockKLinePage />
      </PageStateProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  currentIndex = [INDEX_HIT];
  fetchStockInfoMock.mockResolvedValue({ stock_code: '600519', stock_name: '贵州茅台', current_price: 1720, change: 20, change_percent: 1.2, prev_close: 1700, open: 1701, high: 1730, low: 1690, volume: 1000, amount: 1700000, turnover_rate: 0.3, amplitude: 2.4, pe_ratio_ttm: 30, total_market_cap: 2100000000000 });
  fetchKLineMock.mockResolvedValue({ stock_code: '600519', stock_name: '贵州茅台', prev_close: 1700, data: [{ date: '2024-01-02', open: 1701, close: 1720, high: 1730, low: 1690, volume: 1000, amount: 1700000, change_percent: 1.2, turnover_rate: 0.3 }], count: 1, has_more: false });
});

describe('K 线页导航直达后搜索框同步', () => {
  it('?stockCode=600519 直达，搜索框回填「贵州茅台（600519.SH）」', async () => {
    renderAt('/stock/kline?stockCode=600519');
    await waitFor(() => {
      const input = screen.getByTestId('search-input') as HTMLInputElement;
      expect(input.value).toBe('贵州茅台（600519.SH）');
    });
  });

  it('索引晚于 stockInfo 到达：最终标签补出市场后缀，股票名始终正确', async () => {
    // 模拟真实时序：stockInfo 先到、股票索引后到
    currentIndex = [];
    const { rerender } = renderAt('/stock/kline?stockCode=600519');

    // info 先到：退化标签应仍是正确股票名（无后缀），不会残留旧股票
    await waitFor(() => {
      const input = screen.getByTestId('search-input') as HTMLInputElement;
      expect(input.value).toContain('贵州茅台');
    });

    // 索引后到：重算标签应补出后缀
    currentIndex = [INDEX_HIT];
    rerender(
      <MemoryRouter initialEntries={['/stock/kline?stockCode=600519']}>
        <PageStateProvider>
          <StockKLinePage />
        </PageStateProvider>
      </MemoryRouter>,
    );
    await waitFor(() => {
      const input = screen.getByTestId('search-input') as HTMLInputElement;
      expect(input.value).toBe('贵州茅台（600519.SH）');
    });
  });
});
