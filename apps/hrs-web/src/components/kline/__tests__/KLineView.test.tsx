/**
 * KLineView 组件单元测试
 *
 * 覆盖维度：
 *  1. 功能完整性：正常渲染、空数据占位、均线开关、昨收基准线创建/移除、高度透传
 *  2. 数据契约：分时点 -> 折线数据的转换（无效点过滤、时间升序、累计均价口径）
 *  3. 生命周期：图表创建、数据更新、卸载时 remove 实例（无内存泄漏）
 *
 * 依赖 mock：
 *  - lightweight-charts：避免 jsdom 无 canvas 报错，捕获 createChart/addSeries/setData/remove 调用
 *
 * 运行：cd apps/hrs-web && npx vitest run src/components/kline/__tests__/KLineView.test.tsx
 *
 * @author Lensgcx (GaoCangxiong)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';

import type { KLinePoint } from '../../../api/kline';
import { STOCK_UP_COLOR, STOCK_DOWN_COLOR } from '../../../constants/stockColor';

// ============================================================
// mock lightweight-charts：捕获实例调用，避免 jsdom 无 canvas 报错
// ============================================================
const createChartMock = vi.fn();
const addSeriesMock = vi.fn();
const setDataMock = vi.fn();
const applyOptionsMock = vi.fn();
const setMarkersMock = vi.fn();
const createSeriesMarkersMock = vi.fn();
const createPriceLineMock = vi.fn();
const removePriceLineMock = vi.fn();
const fitContentMock = vi.fn();
const removeMock = vi.fn();
const priceLineApplyOptionsMock = vi.fn();

vi.mock('lightweight-charts', () => {
  const seriesInstance = {
    setData: (data: unknown) => setDataMock(data),
    applyOptions: (options: unknown) => applyOptionsMock(options),
    setMarkers: (markers: unknown) => setMarkersMock(markers),
    createPriceLine: (options: unknown) => {
      createPriceLineMock(options);
      return {
        applyOptions: (opts: unknown) => priceLineApplyOptionsMock(opts),
        options: () => ({}),
      };
    },
    removePriceLine: (line: unknown) => removePriceLineMock(line),
  };
  return {
    createChart: (...args: unknown[]) => {
      createChartMock(...args);
      return {
        addSeries: () => {
          addSeriesMock();
          return seriesInstance;
        },
        timeScale: () => ({ fitContent: () => fitContentMock() }),
        remove: () => removeMock(),
      };
    },
    // v5 标记插件：createSeriesMarkers(series) 返回带 setMarkers 的插件实例
    createSeriesMarkers: (...args: unknown[]) => {
      createSeriesMarkersMock(...args);
      return {
        setMarkers: (markers: unknown) => setMarkersMock(markers),
        markers: () => [],
        detach: () => undefined,
      };
    },
    AreaSeries: 'AreaSeries',
    LineSeries: 'LineSeries',
    CrosshairMode: { Hidden: 2 },
    LineStyle: { Dashed: 2 },
    LineType: { Curved: 2 },
  };
});

import { KLineView } from '../KLineView';

// ============================================================
// 构造测试数据：3 个分时点，含累计均价计算所需 volume/amount
// ============================================================
function makePoint(overrides: Partial<KLinePoint> = {}): KLinePoint {
  return {
    date: '2026-10-12 09:30:00',
    open: 10,
    close: 10,
    high: 10,
    low: 10,
    volume: 100,
    amount: 1000,
    change_percent: 0,
    turnover_rate: 1,
    ...overrides,
  };
}

function makeTimeline(): KLinePoint[] {
  return [
    makePoint({ date: '2026-10-12 09:30:00', close: 10, volume: 100, amount: 1000 }),
    makePoint({ date: '2026-10-12 09:31:00', close: 11, volume: 100, amount: 1100 }),
    makePoint({ date: '2026-10-12 09:32:00', close: 12, volume: 200, amount: 2400 }),
  ];
}

beforeEach(() => {
  createChartMock.mockClear();
  addSeriesMock.mockClear();
  setDataMock.mockClear();
  applyOptionsMock.mockClear();
  setMarkersMock.mockClear();
  createSeriesMarkersMock.mockClear();
  createPriceLineMock.mockClear();
  removePriceLineMock.mockClear();
  fitContentMock.mockClear();
  removeMock.mockClear();
  priceLineApplyOptionsMock.mockClear();
});

afterEach(() => {
  cleanup();
});

describe('KLineView - 功能完整性', () => {
  it('正常分时数据：创建图表、添加两个系列并写入数据', () => {
    render(<KLineView timeline={makeTimeline()} prevClose={10} />);
    expect(createChartMock).toHaveBeenCalledTimes(1);
    // 趋势线（Area）+ 均价线（Line）两个系列
    expect(addSeriesMock).toHaveBeenCalledTimes(2);
    // 每次渲染两个系列各 setData 一次
    expect(setDataMock).toHaveBeenCalledTimes(2);
  });

  it('折线数据按时间升序且值为收盘价', () => {
    render(<KLineView timeline={makeTimeline()} prevClose={10} />);
    const trendData = setDataMock.mock.calls[0][0] as Array<{ time: number; value: number }>;
    const times = trendData.map((d) => d.time);
    expect(times).toEqual([...times].sort((a, b) => a - b));
    expect(trendData.map((d) => d.value)).toEqual([10, 11, 12]);
  });

  it('均价线为累计成交额 / 累计成交量（10、10.5、11.25）', () => {
    render(<KLineView timeline={makeTimeline()} prevClose={10} />);
    const avgData = setDataMock.mock.calls[1][0] as Array<{ value: number }>;
    expect(avgData.map((d) => d.value)).toEqual([10, 10.5, 11.25]);
  });

  it('时间或收盘价无效的点被过滤', () => {
    const timeline = [
      makePoint({ date: '2026-10-12 09:30:00', close: 10 }),
      makePoint({ date: 'bad-date', close: 11 }),
      makePoint({ date: '2026-10-12 09:32:00', close: null }),
      makePoint({ date: '2026-10-12 09:33:00', close: 12 }),
    ];
    render(<KLineView timeline={timeline} prevClose={10} />);
    const trendData = setDataMock.mock.calls[0][0] as Array<{ value: number }>;
    expect(trendData.map((d) => d.value)).toEqual([10, 12]);
  });

  it('空数据渲染占位块且不创建图表', () => {
    const { container } = render(<KLineView timeline={[]} />);
    expect(createChartMock).not.toHaveBeenCalled();
    expect(container.textContent).toBe('-');
  });

  it('有效昨收价时创建基准虚线，无效昨收价（0/负数/null）不创建', () => {
    const { unmount } = render(<KLineView timeline={makeTimeline()} prevClose={10} />);
    expect(createPriceLineMock).toHaveBeenCalledTimes(1);
    expect(createPriceLineMock).toHaveBeenCalledWith(
      expect.objectContaining({ price: 10, axisLabelVisible: false }),
    );
    unmount();

    createPriceLineMock.mockClear();
    render(<KLineView timeline={makeTimeline()} prevClose={0} />);
    expect(createPriceLineMock).not.toHaveBeenCalled();
  });

  it('showAvgPrice=false 时隐藏均价系列', () => {
    render(<KLineView timeline={makeTimeline()} prevClose={10} showAvgPrice={false} />);
    expect(applyOptionsMock).toHaveBeenCalledWith({ visible: false });
  });

  it('height 数字按 px 应用到容器，字符串高度原样透传', () => {
    const { container: c1 } = render(<KLineView timeline={makeTimeline()} height={150} />);
    expect((c1.firstElementChild as HTMLElement).style.height).toBe('150px');
    cleanup();
    const { container: c2 } = render(<KLineView timeline={makeTimeline()} height="88px" />);
    expect((c2.firstElementChild as HTMLElement).style.height).toBe('88px');
  });

  it('默认高度为 120px', () => {
    const { container } = render(<KLineView timeline={makeTimeline()} />);
    expect((container.firstElementChild as HTMLElement).style.height).toBe('120px');
  });
});

describe('KLineView - 生命周期', () => {
  it('数据变化时复用同一实例并更新系列数据，不重复创建图表', () => {
    const { rerender } = render(<KLineView timeline={makeTimeline()} prevClose={10} />);
    expect(createChartMock).toHaveBeenCalledTimes(1);
    rerender(<KLineView timeline={makeTimeline().slice(0, 2)} prevClose={10} />);
    expect(createChartMock).toHaveBeenCalledTimes(1);
    expect(setDataMock.mock.calls.length).toBeGreaterThan(2);
  });

  it('卸载时销毁图表实例', () => {
    const { unmount } = render(<KLineView timeline={makeTimeline()} prevClose={10} />);
    expect(removeMock).not.toHaveBeenCalled();
    unmount();
    expect(removeMock).toHaveBeenCalledTimes(1);
  });

  it('数据晚到时完成图表初始化（占位 -> 图表切换）', () => {
    const { rerender } = render(<KLineView timeline={[]} />);
    expect(createChartMock).not.toHaveBeenCalled();
    rerender(<KLineView timeline={makeTimeline()} prevClose={10} />);
    expect(createChartMock).toHaveBeenCalledTimes(1);
    expect(setDataMock).toHaveBeenCalled();
  });
});

describe('KLineView - 涨跌方向配色与样式透传', () => {
  /** 取趋势线系列的 applyOptions 调用（含 lineColor 字段） */
  const trendColorCalls = () =>
    applyOptionsMock.mock.calls
      .map((call) => call[0] as { lineColor?: string })
      .filter((opt) => opt && typeof opt.lineColor === 'string');

  it('末站上穿昨收时趋势线为上涨色（STOCK_UP_COLOR）', () => {
    render(<KLineView timeline={makeTimeline()} prevClose={10} />);
    expect(trendColorCalls()[0]?.lineColor).toBe(STOCK_UP_COLOR);
  });

  it('末站低于昨收时趋势线为下跌色（STOCK_DOWN_COLOR）', () => {
    const timeline = [
      makePoint({ date: '2026-10-12 09:30:00', close: 12 }),
      makePoint({ date: '2026-10-12 09:31:00', close: 11 }),
      makePoint({ date: '2026-10-12 09:32:00', close: 10 }),
    ];
    render(<KLineView timeline={timeline} prevClose={11} />);
    expect(trendColorCalls()[0]?.lineColor).toBe(STOCK_DOWN_COLOR);
  });

  it('昨收缺失时退化为首末收盘价比较（首 12 末 10 -> 下跌色）', () => {
    const timeline = [
      makePoint({ date: '2026-10-12 09:30:00', close: 12 }),
      makePoint({ date: '2026-10-12 09:31:00', close: 11 }),
      makePoint({ date: '2026-10-12 09:32:00', close: 10 }),
    ];
    render(<KLineView timeline={timeline} />);
    expect(trendColorCalls()[0]?.lineColor).toBe(STOCK_DOWN_COLOR);
  });

  it('末端圆点标记：单个 circle，位置在最后一点，颜色跟随涨跌方向', () => {
    render(<KLineView timeline={makeTimeline()} prevClose={10} />);
    expect(createSeriesMarkersMock).toHaveBeenCalledTimes(1);
    expect(setMarkersMock).toHaveBeenCalledTimes(1);
    const markers = setMarkersMock.mock.calls[0][0] as Array<{
      time: number;
      shape: string;
      color: string;
      size: number;
    }>;
    expect(markers).toHaveLength(1);
    expect(markers[0].shape).toBe('circle');
    expect(markers[0].color).toBe(STOCK_UP_COLOR);
    expect(markers[0].size).toBe(1);
    const trendData = setDataMock.mock.calls[0][0] as Array<{ time: number }>;
    expect(markers[0].time).toBe(trendData[trendData.length - 1].time);
  });

  it('className 透传到图表容器', () => {
    const { container } = render(
      <KLineView timeline={makeTimeline()} className="border-none bg-transparent" />,
    );
    expect((container.firstElementChild as HTMLElement).className).toContain('border-none');
    expect((container.firstElementChild as HTMLElement).className).toContain('bg-transparent');
  });

  it('className 同样透传到空数据占位块', () => {
    const { container } = render(<KLineView timeline={[]} className="border-none" />);
    expect((container.firstElementChild as HTMLElement).className).toContain('border-none');
  });
});
