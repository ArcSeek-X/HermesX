/**
 * K 线页面接口契约 + 调用正确性测试
 *
 * 目标（功能级走查，不联网、无 AI 开销）：
 * 1. 验证前端对 3 个后端接口的调用是否正确（URL / Query 参数）
 *    - 搜索：GET /api/v1/kline/search?q=
 *    - K线： GET /api/v1/kline/{code}/kline?period&fqt&limit&page&before_date
 *    - 信息：GET /api/v1/kline/{code}/info
 * 2. 验证后端返回的数据结构（契约）能被前端正确解析
 *    - KLineResponse.data 为 KLinePoint[]（驼峰字段）
 *    - StockInfo 为蛇形字段
 *    - searchStocks 返回 StockSearchResult[]
 *
 * 通过 mock apiClient.get 捕获真实发出的请求参数，断言前端调用契约正确。
 */
import { describe, expect, it, vi, beforeEach } from 'vitest';

// 捕获 axios 实例上的 get 调用
const getMock = vi.fn();

vi.mock('../index', () => {
  const fakeClient = {
    get: (...args: unknown[]) => getMock(...args),
    interceptors: { request: { use: () => {} }, response: { use: () => {} } },
    defaults: {},
  };
  return {
    __esModule: true,
    default: fakeClient,
    apiClient: fakeClient,
    clearApiCache: () => {},
    clearAllApiCache: () => {},
  };
});

import { klineApi, type KLineResponse, type StockInfo, type StockSearchResult } from '../kline';

/** 构造一组合法的后端返回（契约样本），用于校验结构可被解析 */
function makeKLineResponse(): KLineResponse {
  return {
    stock_code: '603019',
    stock_name: '中科曙光',
    prev_close: 50.0,
    data: [
      {
        date: '2024-01-02',
        open: 50.1,
        close: 51.2,
        high: 51.8,
        low: 49.9,
        volume: 123456,
        amount: 6300000,
        change_percent: 2.4,
        turnover_rate: 1.2,
      },
    ],
    count: 1,
    has_more: false,
  };
}

function makeStockInfo(): StockInfo {
  return {
    stock_code: '603019',
    stock_name: '中科曙光',
    current_price: 51.2,
    change: 1.2,
    change_percent: 2.4,
    prev_close: 50.0,
    open: 50.1,
    high: 51.8,
    low: 49.9,
    volume: 123456,
    amount: 6300000,
    turnover_rate: 1.2,
    amplitude: 3.8,
    pe_ratio_ttm: 35.6,
    total_market_cap: 75000000000,
  };
}

beforeEach(() => {
  getMock.mockReset();
  // 默认所有请求返回结构化契约样本
  getMock.mockImplementation((url: string) => {
    if (url.includes('/kline/search')) {
      return Promise.resolve({ data: { query: 'x', results: [{ code: '603019', name: '中科曙光' }] } });
    }
    if (url.endsWith('/info')) {
      return Promise.resolve({ data: makeStockInfo() });
    }
    return Promise.resolve({ data: makeKLineResponse() });
  });
});

describe('接口调用正确性（URL / Query 参数）', () => {
  it('搜索接口：URL 与 q 参数正确', async () => {
    await klineApi.searchStocks('贵州茅台');
    expect(getMock).toHaveBeenCalledTimes(1);
    const [url, cfg] = getMock.mock.calls[0];
    expect(url).toBe('/api/v1/kline/search');
    expect(cfg.params.q).toBe('贵州茅台');
  });

  it('K线接口：默认参数拼装正确（period/fqt/limit）', async () => {
    await klineApi.fetchKLine('603019');
    const [url, cfg] = getMock.mock.calls[0];
    expect(url).toBe('/api/v1/kline/603019/kline');
    expect(cfg.params.period).toBe('daily');
    expect(cfg.params.fqt).toBe(1);
    expect(cfg.params.limit).toBe(500);
    expect(cfg.params.page).toBeUndefined();
    expect(cfg.params.before_date).toBeUndefined();
  });

  it('K线接口：全量模式 limit=10000 正确下发', async () => {
    await klineApi.fetchKLine('603019', 'daily', 10000);
    const [, cfg] = getMock.mock.calls[0];
    expect(cfg.params.limit).toBe(10000);
  });

  it('K线接口：分页游标 before_date 正确下发', async () => {
    await klineApi.fetchKLine('603019', 'daily', 250, '2024-01-02');
    const [, cfg] = getMock.mock.calls[0];
    expect(cfg.params.before_date).toBe('2024-01-02');
    expect(cfg.params.limit).toBe(250);
  });

  it('信息接口：URL 正确', async () => {
    await klineApi.fetchStockInfo('603019');
    const [url] = getMock.mock.calls[0];
    expect(url).toBe('/api/v1/kline/603019/info');
  });

  // ---- 全周期矩阵：覆盖功能要求的 11 种 period，断言 period 正确下发 ----
  const PERIODS = [
    '1m', '5m', '15m', '30m', '60m', '120m', '5d', 'daily', 'weekly', 'monthly', 'yearly',
  ] as const;
  PERIODS.forEach((period) => {
    it(`K线接口：period=${period} 正确下发`, async () => {
      await klineApi.fetchKLine('603019', period);
      const [, cfg] = getMock.mock.calls[0];
      expect(cfg.params.period).toBe(period);
    });
  });

  // ---- 搜索多条件：代码 / 拼音简拼 / 中文名 都能正确拼装 q ----
  const SEARCH_CASES: Array<[string, string]> = [
    ['代码', '600519'],
    ['拼音简拼', 'maotai'],
    ['中文名', '贵州茅台'],
    ['港股代码', '00700'],
    ['美股代码', 'AAPL'],
  ];
  SEARCH_CASES.forEach(([kind, q]) => {
    it(`搜索接口：${kind}（${q}）正确拼装 q`, async () => {
      await klineApi.searchStocks(q);
      const [url, cfg] = getMock.mock.calls[0];
      expect(url).toBe('/api/v1/kline/search');
      expect(cfg.params.q).toBe(q);
    });
  });

  // ---- limit 边界：最小(1) / 默认(500) / 全量(10000) ----
  it('K线接口：limit=1 最小边界正确下发', async () => {
    await klineApi.fetchKLine('603019', 'daily', 1);
    const [, cfg] = getMock.mock.calls[0];
    expect(cfg.params.limit).toBe(1);
  });
  it('K线接口：limit=10000 全量边界正确下发', async () => {
    await klineApi.fetchKLine('603019', 'daily', 10000);
    const [, cfg] = getMock.mock.calls[0];
    expect(cfg.params.limit).toBe(10000);
  });
  it('K线接口：不传 limit 使用默认 500', async () => {
    await klineApi.fetchKLine('603019', 'daily');
    const [, cfg] = getMock.mock.calls[0];
    expect(cfg.params.limit).toBe(500);
  });
});

describe('返回数据结构契约（前端可正确解析）', () => {
  it('searchStocks 返回 StockSearchResult[] 且字段可读取', async () => {
    const results: StockSearchResult[] = await klineApi.searchStocks('中科曙光');
    expect(Array.isArray(results)).toBe(true);
    expect(results[0].code).toBe('603019');
    expect(results[0].name).toBe('中科曙光');
  });

  it('fetchKLine 返回的 KLineResponse.data 为 KLinePoint[]（驼峰字段可被 KLineChart 读取）', async () => {
    const resp: KLineResponse = await klineApi.fetchKLine('603019');
    expect(Array.isArray(resp.data)).toBe(true);
    const p = resp.data[0];
    // KLineChart 实际读取的字段
    expect(p.date).toBe('2024-01-02');
    expect(p.open).toBe(50.1);
    expect(p.close).toBe(51.2);
    expect(p.high).toBe(51.8);
    expect(p.low).toBe(49.9);
    expect(p.volume).toBe(123456);
    expect(p.change_percent).toBe(2.4);
    // prev_close 用于前收价参考
    expect(resp.prev_close).toBe(50.0);
  });

  it('fetchStockInfo 返回的 StockInfo 为蛇形字段（与 StockInfoHeader 读取一致）', async () => {
    const info: StockInfo = await klineApi.fetchStockInfo('603019');
    expect(info.stock_name).toBe('中科曙光');
    expect(info.current_price).toBe(51.2);
    expect(info.change_percent).toBe(2.4);
    expect(info.prev_close).toBe(50.0);
    expect(info.pe_ratio_ttm).toBe(35.6);
    expect(info.total_market_cap).toBe(75000000000);
  });
});

describe('接口异常路径', () => {
  it('K线接口失败时向上抛出，由页面层处理错误态', async () => {
    getMock.mockImplementationOnce(() => Promise.reject(new Error('network error')));
    await expect(klineApi.fetchKLine('603019')).rejects.toThrow('network error');
  });
});
