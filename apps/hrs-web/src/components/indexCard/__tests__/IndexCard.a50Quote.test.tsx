/**
 * IndexCard 富时中国 A50 行情来源标记回归测试。
 *
 * A 股时段卡片标注「指数 + 行情时间」，休市 / SGX 夜盘标注「期指 + 行情时间」，
 * 其余指数卡片保持无标记。时间按浏览器本地时区渲染，断言只校验格式，
 * 不依赖运行测试的机器时区。
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import IndexCard from '../IndexCard';
import type { MarketIndexItem } from '../../../api/sectorData';

const a50Index: MarketIndexItem = {
  name: '富时中国A50',
  code: 'XIN9',
  price: 13027,
  changePct: 0.94,
  change: 121,
  amount: null,
  high: 13059,
  low: 12901,
  prevClose: 12906,
};

describe('IndexCard 富时中国 A50 行情来源标记', () => {
  it('夜盘期指卡片显示「期指 + 行情时间」', () => {
    render(
      <IndexCard
        index={{ ...a50Index, quoteAsOf: '2026-11-10T23:47:00+08:00', quoteSource: 'futures' }}
      />
    );

    expect(screen.getByText(/^期指 \d{2}:\d{2}$/)).toBeInTheDocument();
  });

  it('A 股时段现货卡片显示「指数 + 行情时间」', () => {
    render(
      <IndexCard
        index={{ ...a50Index, quoteAsOf: '2026-11-10T10:06:00+08:00', quoteSource: 'index' }}
      />
    );

    expect(screen.getByText(/^指数 \d{2}:\d{2}$/)).toBeInTheDocument();
  });

  it('行情时间无法解析时只显示来源名', () => {
    render(<IndexCard index={{ ...a50Index, quoteAsOf: 'invalid', quoteSource: 'futures' }} />);

    expect(screen.getByText('期指')).toBeInTheDocument();
  });

  it('普通指数卡片不显示 A50 专属标记', () => {
    render(<IndexCard index={{ ...a50Index, name: '上证指数' }} />);

    expect(screen.queryByText(/^(期指|指数) \d{2}:\d{2}$/)).toBeNull();
    expect(screen.queryByText('期指')).toBeNull();
  });
});
