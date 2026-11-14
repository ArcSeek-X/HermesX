/**
 * 个股 K 线页「持久化方案」7 场景验收测试。
 *
 * 判定规则（产品侧确认）：页面只认持久化 hrs-state-stockKLine 有没有值，
 * 有值恢复该股票、无值展示最近搜索列表，不区分进入方式。
 *
 * 模拟手法：
 * - 刷新 / 跳走跳回 = 卸载组件 → hydrateStockKLineInfo()（模拟模块重新加载读持久化）→ 重新挂载；
 * - 跳走跳回用无参数 URL（侧边栏 NavLink 的真实形态），刷新保留原 URL；
 * - 所有断言围绕「是否显示行情/K 线」与「是否显示最近搜索列表」，不依赖真实后端。
 *
 * 对应文档：documents/product/个股K线功能/个股K线功能持久化方案.md §6
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act, cleanup } from '@testing-library/react';
import { MemoryRouter, useSearchParams } from 'react-router-dom';
import { PageStateProvider } from '../../stores/PageStateStore';
import {
  getStockKLineInfo,
  hydrateStockKLineInfo,
  removeStockKLineInfo,
} from '../../stores/StockKLine';
import { getStorageItem } from '@utils/storage';

const {
  fetchStockInfoMock,
  fetchKLineMock,
  searchStocksMock,
  getListMock,
  clearMock,
  recordRecentSearchMock,
} = vi.hoisted(() => ({
  fetchStockInfoMock: vi.fn(),
  fetchKLineMock: vi.fn(),
  searchStocksMock: vi.fn(),
  getListMock: vi.fn(),
  clearMock: vi.fn(),
  recordRecentSearchMock: vi.fn(),
}));

vi.mock('echarts', () => {
  class LinearGradient {
    constructor(..._args: unknown[]) {
      void _args;
    }
  }
  return {
    init: vi.fn(() => ({
      setOption: vi.fn(), resize: vi.fn(), dispose: vi.fn(),
      getDataURL: vi.fn(() => ''), on: vi.fn(), off: vi.fn(), clear: vi.fn(),
    })),
    dispose: vi.fn(),
    graphic: { LinearGradient },
  };
});

/** 搜索框：提交携带规范代码与名称，清空按钮触发 onClear；展示值直接渲染便于断言 */
vi.mock('@components/StockSearch/StockSearch', () => ({
  StockSearch: ({
    value,
    displayValue,
    onSubmit,
    onClear,
  }: {
    value: string;
    displayValue?: string;
    onSubmit: (stock: { canonicalCode: string; name?: string }) => void;
    onClear: () => void;
  }) => (
    <>
      <input data-testid="search-input" readOnly value={displayValue || value} />
      <button
        type="button"
        data-testid="submit-stock"
        onClick={() => onSubmit({ canonicalCode: '中科曙光（603019.SH）', name: '中科曙光' })}
      >
        submit
      </button>
      <button type="button" data-testid="clear-stock" onClick={() => onClear()}>
        clear
      </button>
    </>
  ),
}));

/** 用轻量占位替代重组件，断言「K 线图和信息」是否呈现 */
vi.mock('@components/kline/StockInfoHeader', () => ({
  StockInfoHeader: ({ info }: { info: { name: string } }) => (
    <div data-testid="stock-info">{info.name}</div>
  ),
}));
vi.mock('@components/kline/KLineChart', () => ({
  KLineChart: ({ stockCode }: { stockCode: string }) => (
    <div data-testid="kline-chart" data-code={stockCode} />
  ),
}));
vi.mock('@components/kline/PeriodSelector', () => ({
  PeriodSelector: () => <div data-testid="period-selector" />,
}));
vi.mock('../../hooks/useStockIndex', () => ({
  useStockIndex: () => ({ index: [], loading: false, loaded: true, error: null, fallback: false }),
}));
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
vi.mock('../../api/stocks', async () => {
  const actual = await vi.importActual<typeof import('../../api/stocks')>('../../api/stocks');
  return {
    ...actual,
    stocksApi: { batchQuote: vi.fn(async () => []), batchTimeline: vi.fn(async () => []) },
  };
});
vi.mock('../Stock/StockKLinePage/components/RecentSearchStockList', () => ({
  default: () => <div data-testid="recent-search-list" />,
}));

import StockKLinePage from '../Stock/StockKLinePage/StockKLinePage';

/** 探针：暴露当前 MemoryRouter 的 search，验证 URL 镜像的写入与擦除 */
function LocationProbe() {
  const [params] = useSearchParams();
  return <div data-testid="location-search">{params.toString()}</div>;
}

const ENTRY_WITH_CODE = '/stock/kline?stockCode=603019';
const ENTRY_BARE = '/stock/kline';

function makeInfo(code: string, name: string) {
  return {
    code, name, price: 100, change: 1, changePct: 1,
    prevClose: 99, open: 99, high: 101, low: 98, volume: 1000,
    amount: 100000, turnoverRate: 0.3, amplitude: 2, peRatioTTM: 20,
    totalMarketCap: 1000000000,
  };
}

function makeKLine(code: string, name: string) {
  return {
    stock_code: code, stock_name: name, prev_close: 99,
    data: [{
      date: '2024-01-02', open: 99, close: 100, high: 101, low: 98,
      volume: 1000, amount: 100000, change_percent: 1, turnover_rate: 0.3,
    }],
    count: 1, has_more: false,
  };
}

/** 挂载页面（每次都是新 MemoryRouter，故 URL 由 path 显式指定，模拟真实浏览器地址栏） */
function mountPage(path = ENTRY_BARE) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <PageStateProvider>
        <LocationProbe />
        <StockKLinePage />
      </PageStateProvider>
    </MemoryRouter>,
  );
}

/** 模拟刷新 / 跨路由往返：卸载 → 从持久化重新 hydrate → 重新挂载 */
async function remount(path: string) {
  cleanup();
  hydrateStockKLineInfo();
  return act(async () => mountPage(path));
}

/** 等待「中科曙光」的行情与 K 线渲染完成 */
async function expectStockVisible() {
  await waitFor(() => {
    expect(screen.getByTestId('stock-info').textContent).toContain('中科曙光');
  });
  expect(screen.getByTestId('kline-chart').getAttribute('data-code')).toBe('603019');
  expect(screen.queryByTestId('recent-search-list')).toBeNull();
}

/** 等待「最近搜索股票列表」正常展示 */
async function expectRecentListVisible() {
  await waitFor(() => {
    expect(screen.getByTestId('recent-search-list')).toBeTruthy();
  });
  expect(screen.queryByTestId('stock-info')).toBeNull();
  expect(screen.queryByTestId('kline-chart')).toBeNull();
}

/** 点击搜索框 × */
async function clickClear() {
  await act(async () => {
    fireEvent.click(screen.getByTestId('clear-stock'));
  });
}

/** 页内搜索「中科曙光」 */
async function clickSubmit() {
  await act(async () => {
    fireEvent.click(screen.getByTestId('submit-stock'));
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  sessionStorage.clear();
  removeStockKLineInfo(); // 重置模块级单例内存态，保证用例隔离
  fetchStockInfoMock.mockImplementation(async (code: string) =>
    makeInfo(code, code === '603019' ? '中科曙光' : '贵州茅台'),
  );
  fetchKLineMock.mockImplementation(async (code: string) =>
    makeKLine(code, code === '603019' ? '中科曙光' : '贵州茅台'),
  );
  searchStocksMock.mockResolvedValue([{ code: '603019', name: '中科曙光' }]);
  getListMock.mockResolvedValue([]);
  clearMock.mockResolvedValue(undefined);
  recordRecentSearchMock.mockResolvedValue({ id: 1, stockCode: '603019' });
});

describe('个股 K 线持久化：7 场景验收', () => {
  // 场景 1
  it('1. 外部入口 ?stockCode= 进入后，刷新仍保留中科曙光的 K 线图与信息', async () => {
    await act(async () => mountPage(ENTRY_WITH_CODE));
    await expectStockVisible();
    expect(getStockKLineInfo()).toEqual({ code: '603019', name: '中科曙光' });

    // 刷新：URL 仍带参数，持久化应恢复同一只股票
    await remount(ENTRY_WITH_CODE);
    await expectStockVisible();
    expect(getStockKLineInfo()).toEqual({ code: '603019', name: '中科曙光' });
  });

  // 场景 2
  it('2. 外部入口进入后，删除搜索栏内容正常展示最近搜索列表', async () => {
    await act(async () => mountPage(ENTRY_WITH_CODE));
    await expectStockVisible();

    await clickClear();
    await expectRecentListVisible();
    expect(getStockKLineInfo()).toBeNull();
    expect(getStorageItem('stockKLine', 'session')).toBeNull();
    // URL 镜像同步擦除，刷新不会按参数重载
    await waitFor(() => {
      expect(screen.getByTestId('location-search').textContent).not.toContain('stockCode');
    });
  });

  // 场景 3
  it('3. 直接进入后页内搜索，刷新仍保留中科曙光的 K 线图与信息', async () => {
    await act(async () => mountPage(ENTRY_BARE));
    await expectRecentListVisible();

    await clickSubmit();
    await expectStockVisible();
    expect(getStorageItem('stockKLine', 'session')).toEqual({ code: '603019', name: '中科曙光' });
    // 页内搜索写入 URL 镜像，刷新后地址栏带参数
    await waitFor(() => {
      expect(screen.getByTestId('location-search').textContent).toContain('stockCode=603019');
    });

    await remount('/stock/kline?stockCode=603019');
    await expectStockVisible();
  });

  // 场景 4
  it('4. 直接进入后页内搜索，跳走再跳回（无参数）仍保留中科曙光', async () => {
    await act(async () => mountPage(ENTRY_BARE));
    await clickSubmit();
    await expectStockVisible();

    await remount(ENTRY_BARE); // 侧边栏 NavLink 是无参数固定路径
    await expectStockVisible();
    expect(getStockKLineInfo()).toEqual({ code: '603019', name: '中科曙光' });
  });

  // 场景 5
  it('5. 直接进入后页内搜索，删除搜索栏内容正常展示最近搜索列表', async () => {
    await act(async () => mountPage(ENTRY_BARE));
    await clickSubmit();
    await expectStockVisible();

    await clickClear();
    await expectRecentListVisible();
    expect(getStorageItem('stockKLine', 'session')).toBeNull();
  });

  // 场景 6
  it('6. 外部入口 → 清空 → 跳走再跳回，仍展示最近搜索列表（不复活）', async () => {
    await act(async () => mountPage(ENTRY_WITH_CODE));
    await expectStockVisible();

    await clickClear();
    await expectRecentListVisible();

    await remount(ENTRY_BARE);
    await expectRecentListVisible();
    expect(getStockKLineInfo()).toBeNull();
    expect(getStorageItem('stockKLine', 'session')).toBeNull();
  });

  // 场景 7
  it('7. 外部入口进入后，跳走再跳回（无参数）仍保留中科曙光', async () => {
    await act(async () => mountPage(ENTRY_WITH_CODE));
    await expectStockVisible();

    await remount(ENTRY_BARE);
    await expectStockVisible();
  });
});

describe('个股 K 线持久化：补充回归', () => {
  it('清空后刷新仍是最近搜索列表，且不会按残留参数重载股票', async () => {
    await act(async () => mountPage(ENTRY_WITH_CODE));
    await expectStockVisible();
    await clickClear();

    await remount(ENTRY_BARE);
    await expectRecentListVisible();
    expect(getStorageItem('stockKLine', 'session')).toBeNull();
  });

  it('外部入口只带 code 时，行情返回后把 name 补进持久化', async () => {
    await act(async () => mountPage(ENTRY_WITH_CODE));
    await expectStockVisible();
    await waitFor(() => {
      expect(getStockKLineInfo()).toEqual({ code: '603019', name: '中科曙光' });
    });
    expect(Object.keys(getStorageItem<Record<string, unknown>>('stockKLine', 'session') ?? {})).toEqual([
      'code',
      'name',
    ]);
  });

  it('URL 无参数时不把持久化清空（判定只看持久化）', async () => {
    await act(async () => mountPage(ENTRY_WITH_CODE));
    await expectStockVisible();

    await remount(ENTRY_BARE);
    expect(getStockKLineInfo()).toEqual({ code: '603019', name: '中科曙光' });
    expect(getStorageItem('stockKLine', 'session')).toEqual({ code: '603019', name: '中科曙光' });
  });
});
