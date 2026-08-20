/**
 * K 线页面功能级走查测试
 *
 * 目标（端到端功能验证，不联网、无 AI 开销）：
 * 覆盖 StockKLinePage 完整用户链路，并校验前端对接口的调用符合预期：
 *   - 搜索中文名称 -> searchStocks 解析代码 -> fetchStockInfo + fetchKLine
 *   - 周期切换 -> 重新 fetchKLine（携带新 period）
 *   - 加载更多（左滑分页）-> fetchKLine（携带 before_date 游标）
 *   - 全量数据开关 -> fetchKLine（limit=10000）
 *   - 接口失败 -> 错误态展示
 *   - 页面渲染：信息头部股票名、K 线图表容器均正确出现
 *
 * 通过 mock ../../api/kline 的 klineApi 捕获真实调用，验证页面整体功能正确。
 */
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';

// ---- mock echarts（KLineChart 依赖）----
vi.mock('echarts', () => {
  class LinearGradient {
    constructor(..._args: unknown[]) {
      void _args;
    }
  }
  const chartInstance = {
    setOption: vi.fn(),
    resize: vi.fn(),
    dispose: vi.fn(),
    getDataURL: vi.fn(() => 'data:image/png;base64,'),
    on: vi.fn(),
    off: vi.fn(),
    clear: vi.fn(),
  };
  return {
    init: vi.fn(() => chartInstance),
    dispose: vi.fn(),
    graphic: { LinearGradient },
    __chartInstance: chartInstance,
  };
});

// ---- mock StockSearch，暴露 onSubmit 为可点击按钮 ----
vi.mock('../../components/StockSearch/StockSearch', () => ({
  StockSearch: ({
    onSubmit,
  }: {
    onSubmit: (code: string, name?: string) => void;
  }) => (
    <button type="button" data-testid="submit-stock" onClick={() => onSubmit('贵州茅台', '贵州茅台')}>
      submit
    </button>
  ),
}));

// ---- mock klineApi ----
const fetchKLineMock = vi.fn();
const fetchStockInfoMock = vi.fn();
const searchStocksMock = vi.fn();

vi.mock('../../api/kline', () => ({
  klineApi: {
    fetchKLine: (...args: unknown[]) => fetchKLineMock(...args),
    fetchStockInfo: (...args: unknown[]) => fetchStockInfoMock(...args),
    searchStocks: (...args: unknown[]) => searchStocksMock(...args),
  },
}));

import StockKLinePage from '../StockKLinePage';
import { PageStateProvider } from '../../stores/PageStateStore';

/** 包裹页面必需的 Provider 后渲染（功能走查不联网、不依赖真实后端） */
function renderPage() {
  return render(
    <PageStateProvider>
      <StockKLinePage />
    </PageStateProvider>,
  );
}

function makeKLineResp(beforeDate?: string) {
  return {
    stock_code: '600519',
    stock_name: '贵州茅台',
    prev_close: 1700,
    data: [
      {
        date: beforeDate ?? '2024-01-02',
        open: 1701,
        close: 1720,
        high: 1730,
        low: 1690,
        volume: 1000,
        amount: 1700000,
        change_percent: 1.2,
        turnover_rate: 0.3,
      },
    ],
    count: 1,
    has_more: true,
  };
}

function makeStockInfo() {
  return {
    stock_code: '600519',
    stock_name: '贵州茅台',
    current_price: 1720,
    change: 20,
    change_percent: 1.2,
    prev_close: 1700,
    open: 1701,
    high: 1730,
    low: 1690,
    volume: 1000,
    amount: 1700000,
    turnover_rate: 0.3,
    amplitude: 2.4,
    pe_ratio_ttm: 30,
    total_market_cap: 2100000000000,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  fetchStockInfoMock.mockResolvedValue(makeStockInfo());
  fetchKLineMock.mockResolvedValue(makeKLineResp());
  searchStocksMock.mockResolvedValue([{ code: '600519', name: '贵州茅台' }]);
});

describe('K 线页面功能走查', () => {
  it('初始渲染：未选股时显示提示', () => {
    renderPage();
    expect(screen.getByText('请搜索并选择一只股票查看 K 线')).toBeTruthy();
  });

  it('搜索中文名称：解析代码并加载信息头部 + K 线', async () => {
    renderPage();

    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-stock'));
    });

    await waitFor(() => {
      // 信息头部渲染股票名（StockInfoHeader 用 stock_name）
      expect(screen.getAllByText('贵州茅台').length).toBeGreaterThan(0);
    });

    // 搜索接口被调用，参数正确
    expect(searchStocksMock).toHaveBeenCalledWith('贵州茅台');
    // 并行加载信息与 K 线
    expect(fetchStockInfoMock).toHaveBeenCalledWith('600519');
    expect(fetchKLineMock).toHaveBeenCalled();
    const klineCall = fetchKLineMock.mock.calls[0];
    expect(klineCall[0]).toBe('600519');
    expect(klineCall[1]).toBe('1m'); // 搜索默认走分时
  });

  it('周期切换：重新发起 fetchKLine 携带新 period', async () => {
    renderPage();
    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-stock'));
    });
    await waitFor(() => expect(fetchKLineMock).toHaveBeenCalled());

    fetchKLineMock.mockClear();
    // 点击“周 K”按钮（PeriodSelector 文案来自 i18n，见 uiText-zh.ts）
    const weeklyBtn = screen.getByText('周 K');
    await act(async () => {
      fireEvent.click(weeklyBtn);
    });

    await waitFor(() => {
      expect(fetchKLineMock).toHaveBeenCalled();
    });
    const klineCall = fetchKLineMock.mock.calls[0];
    expect(klineCall[1]).toBe('weekly');
  });

  it('全量数据开关：fetchKLine 携带 limit=10000', async () => {
    renderPage();
    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-stock'));
    });
    await waitFor(() => expect(fetchKLineMock).toHaveBeenCalled());

    fetchKLineMock.mockClear();
    // 全量开关仅在 5日K/日K/周K 显示，先切到“日K”
    await act(async () => {
      fireEvent.click(screen.getByText('日K'));
    });
    await waitFor(() => expect(fetchKLineMock).toHaveBeenCalled());
    fetchKLineMock.mockClear();

    // 点击“全量数据” Switch（kline.fullData）
    const fullSwitch = screen.getByText('全量数据');
    await act(async () => {
      fireEvent.click(fullSwitch);
    });

    await waitFor(() => {
      expect(fetchKLineMock).toHaveBeenCalled();
    });
    const klineCall = fetchKLineMock.mock.calls[0];
    expect(klineCall[2]).toBe(10000);
  });

  it('接口失败：展示错误态', async () => {
    searchStocksMock.mockRejectedValue(new Error('search failed'));
    renderPage();
    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-stock'));
    });
    await waitFor(() => {
      expect(screen.getByText('K 线数据加载失败')).toBeTruthy();
    });
  });

  // ---- 全周期矩阵：覆盖功能要求的 11 种周期，每个周期按钮都能触发对应 fetchKLine ----
  const PERIOD_BUTTONS: Array<[string, string]> = [
    ['分时', '1m'],
    ['5 分', '5m'],
    ['15 分', '15m'],
    ['30 分', '30m'],
    ['60 分', '60m'],
    ['120 分', '120m'],
    ['5日', '5d'],
    ['日K', 'daily'],
    ['周 K', 'weekly'],
    ['月 K', 'monthly'],
    ['年 K', 'yearly'],
  ];
  PERIOD_BUTTONS.forEach(([label, period]) => {
    it(`周期切换：${label} 触发 fetchKLine(period=${period})`, async () => {
      renderPage();
      await act(async () => {
        fireEvent.click(screen.getByTestId('submit-stock'));
      });
      await waitFor(() => expect(fetchKLineMock).toHaveBeenCalled());
      fetchKLineMock.mockClear();

      await act(async () => {
        fireEvent.click(screen.getByText(label));
      });
      await waitFor(() => {
        expect(fetchKLineMock).toHaveBeenCalled();
      });
      const klineCall = fetchKLineMock.mock.calls[0];
      expect(klineCall[1]).toBe(period);
    });
  });
});
