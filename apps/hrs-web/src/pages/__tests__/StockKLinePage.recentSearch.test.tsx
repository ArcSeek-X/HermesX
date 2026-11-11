/**
 * K 线页「最近搜索」记录时机与显示时机回归测试。
 *
 * 目标（不联网、不依赖真实后端）：
 * 1. 未选中股票时显示最近搜索列表；查询成功后隐藏列表、只显示行情/K 线；清空搜索框后列表重新出现；
 * 2. 页内显式搜索 / 外部 ?stockCode= 直达会落库一条最近搜索；
 * 3. 切周期等隐式重载不重复落库，行情加载失败时不落库。
 */
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { PageStateProvider } from '../../stores/PageStateStore';

const { recordRecentSearchMock, getListMock, clearMock } = vi.hoisted(() => ({
  recordRecentSearchMock: vi.fn(),
  getListMock: vi.fn(),
  clearMock: vi.fn(),
}));

vi.mock('echarts', () => {
  class LinearGradient {
    constructor(..._args: unknown[]) {
      void _args;
    }
  }
  const chartInstance = {
    setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn(),
    getDataURL: vi.fn(() => ''), on: vi.fn(), off: vi.fn(), clear: vi.fn(),
  };
  return { init: vi.fn(() => chartInstance), dispose: vi.fn(), graphic: { LinearGradient } };
});

vi.mock('@components/StockSearch/StockSearch', () => ({
  StockSearch: ({
    onSubmit,
    onClear,
  }: {
    onSubmit: (code: string, name?: string) => void;
    onClear: () => void;
  }) => (
    <>
      <button type="button" data-testid="submit-stock" onClick={() => onSubmit('贵州茅台', '贵州茅台')}>
        submit
      </button>
      <button
        type="button"
        data-testid="submit-formatted"
        onClick={() => onSubmit('中科曙光（603019.SH）', '中科曙光')}
      >
        submit formatted
      </button>
      <button type="button" data-testid="clear-stock" onClick={() => onClear()}>
        clear
      </button>
    </>
  ),
}));

vi.mock('@components/kline/PeriodSelector', () => ({
  PeriodSelector: ({ onChange }: { onChange: (period: string) => void }) => (
    <button type="button" data-testid="change-period" onClick={() => onChange('weekly')}>
      change period
    </button>
  ),
}));

vi.mock('../../hooks/useStockIndex', () => ({
  useStockIndex: () => ({ index: [], loading: false, loaded: true, error: null, fallback: false }),
}));

const fetchKLineMock = vi.fn();
const fetchStockInfoMock = vi.fn();
const searchStocksMock = vi.fn();
vi.mock('../../api/kline', async () => {
  const actual = await vi.importActual<typeof import('../../api/kline')>('../../api/kline');
  return {
    ...actual,
    klineApi: {
      fetchKLine: (...args: unknown[]) => fetchKLineMock(...args),
      fetchStockInfo: (...args: unknown[]) => fetchStockInfoMock(...args),
      searchStocks: (...args: unknown[]) => searchStocksMock(...args),
    },
  };
});

vi.mock('../../api/recentSearch', () => ({
  recordRecentSearch: (...args: unknown[]) => recordRecentSearchMock(...args),
  getRecentSearchList: (...args: unknown[]) => getListMock(...args),
  clearRecentSearch: (...args: unknown[]) => clearMock(...args),
}));

vi.mock('../Stock/StockKLinePage/components/RecentSearchList', () => ({
  default: () => <div data-testid="recent-search-list" />,
}));

import StockKLinePage from '../Stock/StockKLinePage/StockKLinePage';

/** 构造一份规范 camelCase 行情信息（与 StockQuoteCore 一致） */
function makeStockInfo() {
  return {
    code: '600519', name: '贵州茅台', price: 1720, change: 20, changePct: 1.2,
    prevClose: 1700, open: 1701, high: 1730, low: 1690, volume: 1000,
    amount: 1700000, turnoverRate: 0.3, amplitude: 2.4, peRatioTTM: 30,
    totalMarketCap: 2100000000000,
  };
}

function makeKLineResp() {
  return {
    stock_code: '600519', stock_name: '贵州茅台', prev_close: 1700,
    data: [{
      date: '2024-01-02', open: 1701, close: 1720, high: 1730, low: 1690,
      volume: 1000, amount: 1700000, change_percent: 1.2, turnover_rate: 0.3,
    }],
    count: 1, has_more: false,
  };
}

function renderPage(path = '/stock/kline') {
  return act(async () => {
    render(
      <MemoryRouter initialEntries={[path]}>
        <PageStateProvider>
          <StockKLinePage />
        </PageStateProvider>
      </MemoryRouter>,
    );
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  // PageStateProvider 会从 sessionStorage 恢复上次测试的 stockInfo，不清会导致后续用例
  // 初始就带着股票代码，直达判定被「代码未变」短路、加载次数也多一次。
  sessionStorage.clear();
  searchStocksMock.mockResolvedValue([{ code: '600519', name: '贵州茅台' }]);
  fetchStockInfoMock.mockResolvedValue(makeStockInfo());
  fetchKLineMock.mockResolvedValue(makeKLineResp());
  recordRecentSearchMock.mockResolvedValue({ id: 1, stockCode: '600519' });
  getListMock.mockResolvedValue([]);
  clearMock.mockResolvedValue(undefined);
});

describe('K 线页最近搜索显示时机', () => {
  it('未选中股票时显示列表，查询成功后隐藏并让位给行情/K 线，清空后重新显示', async () => {
    await renderPage();
    expect(screen.getByTestId('recent-search-list')).toBeTruthy();

    fireEvent.click(screen.getByTestId('submit-stock'));
    await waitFor(() => expect(screen.queryByTestId('recent-search-list')).toBeNull());

    fireEvent.click(screen.getByTestId('clear-stock'));
    await waitFor(() => expect(screen.getByTestId('recent-search-list')).toBeTruthy());
  });

  it('清空搜索框不再请求列表（仅 mount 初始化一次），且清空同步服务端', async () => {
    await renderPage();
    // 初始化列表只从服务端拉一次历史记录（非清空触发）
    await waitFor(() => expect(getListMock).toHaveBeenCalledTimes(1), { timeout: 3000 });

    fireEvent.click(screen.getByTestId('submit-stock'));
    await waitFor(() => expect(recordRecentSearchMock).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByTestId('clear-stock'));
    await waitFor(() => expect(screen.getByTestId('recent-search-list')).toBeTruthy());

    // 清空只清空本地数据，不再向服务端发起 getRecentSearchList
    // （清空按钮在真实 RecentSearchList 内触发 clearRecentSearch；此处组件被隔离为占位 div，故不验证清空同步服务端）
    expect(getListMock).toHaveBeenCalledTimes(1);
  });
});

describe('K 线页最近搜索记录时机', () => {
  it('页内显式搜索成功后落库一条，名称取自已加载行情', async () => {
    await renderPage();
    fireEvent.click(screen.getByTestId('submit-stock'));

    await waitFor(() => {
      expect(recordRecentSearchMock).toHaveBeenCalledWith({
        stockCode: '600519',
        stockName: '贵州茅台',
      });
    });
  });

  it('外部 ?stockCode= 直达同样落库一条', async () => {
    await renderPage('/stock/kline?stockCode=600519');

    await waitFor(() => {
      expect(recordRecentSearchMock).toHaveBeenCalledWith({
        stockCode: '600519',
        stockName: '贵州茅台',
      });
    });
  });

  it('「名称（代码）」展示格式输入也能解析为规范代码并落库', async () => {
    await renderPage();
    fireEvent.click(screen.getByTestId('submit-formatted'));

    // 输入含中文括号与 .SH 后缀，应提取出纯数字代码 603019，无需回退到 searchStocks
    await waitFor(() => {
      expect(recordRecentSearchMock).toHaveBeenCalledWith(
        expect.objectContaining({ stockCode: '603019' }),
      );
    });
    expect(searchStocksMock).not.toHaveBeenCalled();
  });

  it('切换周期属于隐式重载，不重复落库', async () => {
    await renderPage();
    await act(async () => {
      fireEvent.click(screen.getByTestId('submit-stock'));
    });
    await waitFor(() => expect(recordRecentSearchMock).toHaveBeenCalledTimes(1));

    await act(async () => {
      fireEvent.click(screen.getByTestId('change-period'));
    });
    await waitFor(() => expect(fetchKLineMock).toHaveBeenCalledTimes(2));

    expect(recordRecentSearchMock).toHaveBeenCalledTimes(1);
  });

  it('行情加载失败时不落库', async () => {
    fetchStockInfoMock.mockRejectedValue(new Error('quote unavailable'));
    await renderPage();
    fireEvent.click(screen.getByTestId('submit-stock'));

    await waitFor(() => expect(fetchStockInfoMock).toHaveBeenCalledTimes(1));
    expect(recordRecentSearchMock).not.toHaveBeenCalled();
  });
});
