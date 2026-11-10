/**
 * @file stockMetricViewColumns.test.tsx
 * @description 股票度量视图列展示契约：代码 / 名称两列在 cn / hk / us 三市场一律加粗主题色，
 * 所属板块整列居中；同时守住「仅 A 股可跳转 K 线」不被视觉统一改动破坏。
 * 另守住逐列平铺后的列清单、列头 i18n 键、按市场裁剪、固定列连续性与 K 线跳转代码归一。
 * @author Lensgcx (GaoCangxiong)
 */
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { buildStockKlinePath, buildStockMetricViewColumns } from '../stockMetricViewColumns';
import type { StockMetricViewRow, StockMetricViewSupportedMarket } from '@/types/stockMetricView';

type StockMetricViewColumnOptions = Parameters<typeof buildStockMetricViewColumns>[0];

const translate: StockMetricViewColumnOptions['t'] = (key) => key;
const openKline: StockMetricViewColumnOptions['onOpenKline'] = () => undefined;

function buildRow(market: StockMetricViewSupportedMarket): StockMetricViewRow {
  return {
    id: `${market}:000001`,
    code: '000001',
    name: '示例股票',
    market,
    industry: '银行',
    price: 10.5,
    changePct: 1.2,
    volume: 1000,
    totalMarketCap: 1e8,
    peRatioTTM: 12,
    relativeVolume: 1.1,
    epsDiluted: 1.2,
    epsGrowthTtmYoyPct: null,
    dividendYieldPct: 3.5,
    analystRating: null,
  };
}

function buildColumns(market: StockMetricViewSupportedMarket) {
  return buildStockMetricViewColumns({
    t: translate,
    selectedMarket: market,
    onOpenKline: openKline,
  });
}

function renderColumnHtml(market: StockMetricViewSupportedMarket, key: string): string {
  const column = buildColumns(market).find((item) => item.key === key);
  expect(column?.render).toBeTypeOf('function');
  return renderToStaticMarkup(column?.render?.(buildRow(market)));
}

const MARKETS: StockMetricViewSupportedMarket[] = ['cn', 'hk', 'us'];

describe('股票度量视图列展示契约', () => {
  it.each(MARKETS)('%s：股票代码与股票名称均加粗并使用主题色', (market) => {
    for (const key of ['code', 'name']) {
      const html = renderColumnHtml(market, key);
      expect(html).toContain('font-semibold');
      expect(html).toContain('text-primary');
    }
  });

  it.each(MARKETS)('%s：所属板块整列居中', (market) => {
    expect(buildColumns(market).find((item) => item.key === 'industry')?.align).toBe('center');
  });

  it.each(MARKETS)('%s：仅 cn 渲染 K 线跳转链接', (market) => {
    expect(renderColumnHtml(market, 'code').startsWith('<a')).toBe(market === 'cn');
  });

  it.each([
    { value: 1.23, expected: 'stock-up', text: '1.23%' },
    { value: -0.85, expected: 'stock-down', text: '-0.85%' },
    { value: 0, expected: 'text-muted-text', text: '0.00%' },
    { value: null, expected: 'text-muted-text', text: '—' },
  ])('涨跌幅 $value → $expected', ({ value, expected, text }) => {
    const column = buildColumns('cn').find((item) => item.key === 'changePct');
    const html = renderToStaticMarkup(column?.render?.({ ...buildRow('cn'), changePct: value }));
    expect(html).toContain(expected);
    expect(html).toContain(text);
  });

  it.each(MARKETS)('%s：涨跌幅使用全站规范颜色类', (market) => {
    const column = buildColumns(market).find((item) => item.key === 'changePct');
    const html = renderToStaticMarkup(column?.render?.(buildRow(market)));
    expect(html).toContain('stock-up');
    expect(html).not.toMatch(/text-(red|green|emerald)-/);
  });
});

describe('股票度量视图列清单契约', () => {
  const CN_COLUMN_KEYS = [
    'market', 'code', 'name', 'price', 'changePct', 'volume', 'relativeVolume',
    'totalMarketCap', 'peRatioTTM', 'epsDiluted', 'epsGrowthTtmYoyPct',
    'dividendYieldPct', 'industry', 'analystRating',
  ];

  it('cn：14 个业务列逐列声明且顺序固定', () => {
    expect(buildColumns('cn').map(({ key }) => key)).toEqual(CN_COLUMN_KEYS);
  });

  it.each(['hk', 'us'] as const)('%s：仅 cn 可得的两个离线因子列整列隐藏', (market) => {
    expect(buildColumns(market).map(({ key }) => key)).toEqual(
      CN_COLUMN_KEYS.filter((key) => key !== 'epsGrowthTtmYoyPct' && key !== 'analystRating'),
    );
  });

  it.each(MARKETS)('%s：列头 i18n 键与列 key 一一对应，且每列都有渲染函数', (market) => {
    for (const column of buildColumns(market)) {
      expect(column.title).toBe(`stockMetricView.column.${column.key}`);
      expect(column.render).toBeTypeOf('function');
    }
  });

  it.each(MARKETS)('%s：仅前 3 个业务列连续左固定', (market) => {
    const columns = buildColumns(market);
    // true 与 'left' 都表示固定左侧，断言语义而非字面写法
    expect(columns.slice(0, 3).every(({ fixed }) => fixed === true || fixed === 'left')).toBe(true);
    expect(columns.slice(3).every(({ fixed }) => fixed == null)).toBe(true);
  });

  it.each([
    { key: 'price', text: '10.50' },
    { key: 'peRatioTTM', text: '12.00' },
    { key: 'totalMarketCap', text: '1.00亿' },
    { key: 'dividendYieldPct', text: '3.50%' },
    { key: 'epsDiluted', text: '1.20' },
    { key: 'volume', text: '1,000.00' },
    { key: 'industry', text: '银行' },
  ])('$key 渲染格式口径保持不变', ({ key, text }) => {
    expect(renderColumnHtml('cn', key)).toContain(text);
  });

  it.each([
    { market: 'cn', key: 'price', currency: 'CNY' },
    { market: 'cn', key: 'totalMarketCap', currency: 'CNY' },
    { market: 'cn', key: 'epsDiluted', currency: 'CNY' },
    { market: 'hk', key: 'price', currency: 'HKD' },
    { market: 'us', key: 'price', currency: 'USD' },
  ] as const)('$market / $key：原币单位 $currency 单独用小字号渲染', ({ market, key, currency }) => {
    expect(renderColumnHtml(market, key)).toContain(`<span class="text-[10px]">${currency}</span>`);
  });

  it('数值为 null 时只显示占位符，不附带原币单位', () => {
    const column = buildColumns('cn').find((item) => item.key === 'price');
    const html = renderToStaticMarkup(column?.render?.({ ...buildRow('cn'), price: null }));
    expect(html).toBe('—');
    expect(html).not.toContain('CNY');
  });

  it('分析师评级按 1–5 档位展示', () => {
    const column = buildColumns('cn').find((item) => item.key === 'analystRating');
    const html = renderToStaticMarkup(column?.render?.({ ...buildRow('cn'), analystRating: 4 }));
    expect(html).toContain('4 / 5');
  });
});

describe('股票度量视图 K 线跳转路径', () => {
  it.each([
    { code: '600519', expected: '/stock/kline?stockCode=600519' },
    { code: '600519.SH', expected: '/stock/kline?stockCode=600519' },
    { code: 'SH600519', expected: '/stock/kline?stockCode=600519' },
    { code: '000001.SZ', expected: '/stock/kline?stockCode=000001' },
    { code: 'AAPL', expected: '/stock/kline?stockCode=AAPL' },
    { code: 'BRK.B', expected: '/stock/kline?stockCode=BRK.B' },
  ])('$code → $expected', ({ code, expected }) => {
    expect(buildStockKlinePath(code)).toBe(expected);
  });

  it('代码经 encodeURIComponent 编码后拼入 URL', () => {
    expect(buildStockKlinePath('A B')).toBe('/stock/kline?stockCode=A%20B');
  });

  it('cn 代码列链接使用归一化后的代码', () => {
    const column = buildColumns('cn').find((item) => item.key === 'code');
    const html = renderToStaticMarkup(column?.render?.({ ...buildRow('cn'), code: '600519.SH' }));
    expect(html).toContain('stockCode=600519');
    expect(html).not.toContain('stockCode=600519.SH');
  });
});
