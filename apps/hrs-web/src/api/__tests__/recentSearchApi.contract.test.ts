/**
 * 最近搜索 / 批量行情的前端 API 契约测试。
 *
 * 目标（不联网）：
 * 1. recent-search 三条接口的 URL、snake_case 请求体与 camelCase 响应归一；
 * 2. batch-quote / batch-timeline 的 URL、代码去重、10 只上限与失败降级。
 *
 * 通过 mock apiClient 捕获真实发出的请求，断言前端调用契约正确。
 */
import { describe, expect, it, vi, beforeEach } from 'vitest';

const { getMock, postMock, deleteMock } = vi.hoisted(() => ({
  getMock: vi.fn(),
  postMock: vi.fn(),
  deleteMock: vi.fn(),
}));

vi.mock('../index', () => {
  const fakeClient = {
    get: (...args: unknown[]) => getMock(...args),
    post: (...args: unknown[]) => postMock(...args),
    delete: (...args: unknown[]) => deleteMock(...args),
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

import { clearRecentSearch, getRecentSearchList, recordRecentSearch } from '../recentSearch';
import { stocksApi } from '../stocks';

/** 后端返回的一条 snake_case 记录 */
function makeSnakeRecord() {
  return {
    id: 1,
    user_id: 'default',
    stock_code: '600519',
    stock_name: '贵州茅台',
    market: 'cn',
    create_date_time: '2026-11-11T02:13:00',
    update_date_time: '2026-11-11T03:20:00',
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  getMock.mockResolvedValue({ data: { items: [makeSnakeRecord()] } });
  postMock.mockResolvedValue({ data: { item: makeSnakeRecord() } });
  deleteMock.mockResolvedValue({ data: { success: true } });
});

describe('recent-search 接口契约', () => {
  it('列表：URL 正确且 snake_case 响应归一为 camelCase', async () => {
    const items = await getRecentSearchList();

    expect(getMock).toHaveBeenCalledWith('/api/v1/recent-search/list');
    expect(items).toEqual([{
      id: 1,
      userId: 'default',
      stockCode: '600519',
      stockName: '贵州茅台',
      market: 'cn',
      createDateTime: '2026-11-11T02:13:00',
      updateDateTime: '2026-11-11T03:20:00',
    }]);
  });

  it('列表：空 items 时返回空数组', async () => {
    getMock.mockResolvedValueOnce({ data: {} });
    await expect(getRecentSearchList()).resolves.toEqual([]);
  });

  it('记录：请求体为 snake_case，响应归一为 camelCase', async () => {
    const item = await recordRecentSearch({ stockCode: '600519', stockName: '贵州茅台', market: 'cn' });

    expect(postMock).toHaveBeenCalledWith('/api/v1/recent-search/record', {
      stock_code: '600519',
      stock_name: '贵州茅台',
      market: 'cn',
    });
    expect(item.stockCode).toBe('600519');
    expect(item.updateDateTime).toBe('2026-11-11T03:20:00');
  });

  it('记录：可选字段缺省时发送 null', async () => {
    await recordRecentSearch({ stockCode: 'AAPL' });
    expect(postMock).toHaveBeenCalledWith('/api/v1/recent-search/record', {
      stock_code: 'AAPL',
      stock_name: null,
      market: null,
    });
  });

  it('清空：URL 与 DELETE 方法正确', async () => {
    await expect(clearRecentSearch()).resolves.toBeUndefined();
    expect(deleteMock).toHaveBeenCalledWith('/api/v1/recent-search/clear');
  });
});

describe('批量行情接口契约', () => {
  it('batchQuote：URL 正确、代码去重，默认 limiteSize=12', async () => {
    postMock.mockResolvedValueOnce({ data: { items: [{ code: '600519', price: 1720 }] } });
    const codes = ['600519', '600519', ...Array.from({ length: 12 }, (_, index) => `CODE${index}`)];

    const quotes = await stocksApi.batchQuote(codes);

    expect(postMock).toHaveBeenCalledWith('/api/v1/stocks/batch-quote', {
      codes: [
        '600519', 'CODE0', 'CODE1', 'CODE2', 'CODE3', 'CODE4',
        'CODE5', 'CODE6', 'CODE7', 'CODE8', 'CODE9', 'CODE10',
      ],
      limiteSize: 12,
    });
    expect(quotes[0].code).toBe('600519');
  });

  it('batchQuote：limiteSize 可覆盖默认条数', async () => {
    postMock.mockResolvedValueOnce({ data: { items: [] } });

    await stocksApi.batchQuote(['600519', '000001', '300750', '600036'], 3);

    expect(postMock).toHaveBeenCalledWith('/api/v1/stocks/batch-quote', {
      codes: ['600519', '000001', '300750'],
      limiteSize: 3,
    });
  });

  it('batchQuote：空代码或请求失败均返回空数组', async () => {
    postMock.mockRejectedValueOnce(new Error('network error'));
    await expect(stocksApi.batchQuote([])).resolves.toEqual([]);
    await expect(stocksApi.batchQuote(['600519'])).resolves.toEqual([]);
  });

  it('batchTimeline：URL 正确且透传下采样点列与默认 limiteSize', async () => {
    const points = [{ date: '2026-11-11 09:30:00', close: 1700 }];
    postMock.mockResolvedValueOnce({
      data: { items: [{ code: '600519', name: '贵州茅台', prevClose: 1690, points }] },
    });

    const timelines = await stocksApi.batchTimeline(['600519', '600519']);

    expect(postMock).toHaveBeenCalledWith('/api/v1/stocks/batch-timeline', {
      codes: ['600519'],
      limiteSize: 12,
    });
    expect(timelines[0].prevClose).toBe(1690);
    expect(timelines[0].points).toEqual(points);
  });
});
