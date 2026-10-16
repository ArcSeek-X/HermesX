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
import { render, cleanup, act } from '@testing-library/react';

import type { KLinePoint } from '../../../api/kline';
import { STOCK_UP_COLOR, STOCK_DOWN_COLOR } from '../../../constants/stockColor';

// ============================================================
// mock lightweight-charts：捕获实例调用，避免 jsdom 无 canvas 报错
// ============================================================
const createChartMock = vi.fn();
const addSeriesMock = vi.fn();
const addSeriesOptionsMock = vi.fn();
const setDataMock = vi.fn();
const applyOptionsMock = vi.fn();
const setMarkersMock = vi.fn();
const createSeriesMarkersMock = vi.fn();
const createPriceLineMock = vi.fn();
const removePriceLineMock = vi.fn();
const fitContentMock = vi.fn();
const removeMock = vi.fn();
const priceLineApplyOptionsMock = vi.fn();
const subscribeCrosshairMoveMock = vi.fn();
const unsubscribeCrosshairMoveMock = vi.fn();

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
        addSeries: (type: unknown, options: unknown) => {
          addSeriesMock();
          addSeriesOptionsMock(type, options);
          return seriesInstance;
        },
        timeScale: () => ({ fitContent: () => fitContentMock() }),
        subscribeCrosshairMove: (handler: unknown) => subscribeCrosshairMoveMock(handler),
        unsubscribeCrosshairMove: (handler: unknown) => unsubscribeCrosshairMoveMock(handler),
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
    CrosshairMode: { Hidden: 2, Normal: 0, Magnet: 1 },
    LineStyle: { Dashed: 2 },
    LineType: { Curved: 2 },
  };
});

// ============================================================
// IntersectionObserver 可控 mock：
//   默认「已在视口」立即触发；懒加载用例切换为「等手动触发」模式
// ============================================================
/** 懒加载用例使用：置位后可由测试手动触发一次「进入视口」回调 */
let triggerIntersection: (() => void) | null = null;
/** 原始 IntersectionObserver（setupTests.ts 注入的 no-op mock），用例结束后还原 */
let OriginalIntersectionObserver: unknown = null;

class ImmediateIntersectionObserver {
  readonly root = null;
  readonly rootMargin = '';
  readonly thresholds = [0];

  constructor(private readonly callback: IntersectionObserverCallback) {}

  observe(target: Element) {
    this.callback(
      [{ isIntersecting: true, target } as unknown as IntersectionObserverEntry],
      this as unknown as IntersectionObserver,
    );
  }

  unobserve() {}
  disconnect() {}
  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }
}

class DeferredIntersectionObserver {
  readonly root = null;
  readonly rootMargin = '';
  readonly thresholds = [0];
  private readonly callback: IntersectionObserverCallback;
  private target: Element | null = null;

  constructor(callback: IntersectionObserverCallback) {
    this.callback = callback;
  }

  observe(target: Element) {
    this.target = target;
    triggerIntersection = () => {
      this.callback(
        [{ isIntersecting: true, target } as unknown as IntersectionObserverEntry],
        this as unknown as IntersectionObserver,
      );
    };
  }

  unobserve() {}
  disconnect() {}
  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }
}

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
  addSeriesOptionsMock.mockClear();
  setDataMock.mockClear();
  applyOptionsMock.mockClear();
  setMarkersMock.mockClear();
  createSeriesMarkersMock.mockClear();
  createPriceLineMock.mockClear();
  removePriceLineMock.mockClear();
  fitContentMock.mockClear();
  removeMock.mockClear();
  priceLineApplyOptionsMock.mockClear();
  subscribeCrosshairMoveMock.mockClear();
  unsubscribeCrosshairMoveMock.mockClear();
  triggerIntersection = null;
  // 默认「已在视口」：与真实浏览器中首屏可见的图表行为一致。
  // 注意：setupTests.ts 用 Object.defineProperty 注入了不可配置的 IntersectionObserver，
  // vi.stubGlobal 会抛「Cannot redefine property」，这里用直接赋值（属性 writable: true）。
  OriginalIntersectionObserver = (globalThis as { IntersectionObserver?: unknown }).IntersectionObserver;
  (globalThis as { IntersectionObserver?: unknown }).IntersectionObserver = ImmediateIntersectionObserver;
});

afterEach(() => {
  cleanup();
  (globalThis as { IntersectionObserver?: unknown }).IntersectionObserver = OriginalIntersectionObserver;
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

describe('KLineView - 价格轴范围锁定（回归）', () => {
  /**
   * 取趋势线系列上带 autoscaleInfoProvider 的 applyOptions 调用。
   * mock 中两个系列共用同一实例，需按字段过滤（均价线的 applyOptions 只有 visible）。
   */
  const rangeProviderCalls = () =>
    applyOptionsMock.mock.calls
      .map((call) => call[0] as {
        autoscaleInfoProvider?: () => { priceRange: { minValue: number; maxValue: number } };
      })
      .filter((opt) => opt && typeof opt.autoscaleInfoProvider === 'function');

  const lastRange = () => {
    const calls = rangeProviderCalls();
    expect(calls.length).toBeGreaterThan(0);
    return calls[calls.length - 1].autoscaleInfoProvider!().priceRange;
  };

  it('末端圆点标记不再撑大价格轴：范围锁定为「数据区间 + 可见昨收基准线」', () => {
    // 回归：lightweight-charts 的 series markers 会参与价格轴 autoscale，且按像素换算，
    // 图表越矮拉伸越狠——36px 缩略图被拉到约 6 倍数据宽度，全天 3% 起伏被压成一条直线。
    // 修复：用 autoscaleInfoProvider 显式锁定范围，渲染结果与高度 / 标记无关。
    render(<KLineView timeline={makeTimeline()} prevClose={10} height={36} />);
    const range = lastRange();
    expect(range.minValue).toBe(10); // 数据最低价
    expect(range.maxValue).toBe(12); // 数据最高价
  });

  it('昨收高于数据最高价时纳入范围，保证昨收基准虚线可见', () => {
    render(<KLineView timeline={makeTimeline()} prevClose={15} height={36} />);
    const range = lastRange();
    expect(range.minValue).toBe(10);
    expect(range.maxValue).toBe(15);
  });

  it('昨收无效（0/负数）时范围仅为数据区间', () => {
    render(<KLineView timeline={makeTimeline()} prevClose={0} height={36} />);
    const range = lastRange();
    expect(range.minValue).toBe(10);
    expect(range.maxValue).toBe(12);
  });

  it('showPrevCloseBaseline=false 时范围不含昨收', () => {
    render(<KLineView timeline={makeTimeline()} prevClose={15} height={36} showPrevCloseBaseline={false} />);
    const range = lastRange();
    expect(range.maxValue).toBe(12);
  });

  it('数据变化时范围随之更新（复用同一图表实例）', () => {
    const { rerender } = render(<KLineView timeline={makeTimeline()} prevClose={10} height={36} />);
    rerender(<KLineView timeline={makeTimeline().slice(0, 2)} prevClose={10} height={36} />);
    const range = lastRange();
    expect(range.minValue).toBe(10);
    expect(range.maxValue).toBe(11);
    expect(createChartMock).toHaveBeenCalledTimes(1);
  });

  it('数据全平（停牌 / 一字板）时撑开非零区间，避免零高度区间', () => {
    const flat = [
      makePoint({ date: '2026-10-12 09:30:00', close: 10 }),
      makePoint({ date: '2026-10-12 09:31:00', close: 10 }),
    ];
    render(<KLineView timeline={flat} prevClose={10} height={36} />);
    const range = lastRange();
    expect(range.maxValue).toBeGreaterThan(range.minValue);
  });
});

describe('KLineView - interactive 参数（缩略图 / 交互双模式）', () => {
  /** 取 createChart 的配置参数（第二个入参，第一个是容器 DOM） */
  const chartOptions = () => createChartMock.mock.calls[0][1] as Record<string, unknown>;
  /** 取趋势线（Area）系列的创建选项 */
  const trendSeriesOptions = () =>
    addSeriesOptionsMock.mock.calls[0][1] as Record<string, unknown>;

  it('默认（不传 interactive）：纯缩略图——十字光标隐藏、无坐标轴、禁用平移缩放', () => {
    render(<KLineView timeline={makeTimeline()} prevClose={10} height={36} />);
    const opts = chartOptions();
    expect(opts.crosshair).toMatchObject({ mode: 2 }); // CrosshairMode.Hidden
    expect((opts.rightPriceScale as { visible: boolean }).visible).toBe(false);
    expect((opts.timeScale as { visible: boolean }).visible).toBe(false);
    expect((opts.grid as { vertLines: { visible: boolean } }).vertLines.visible).toBe(false);
    // 禁用平移与缩放：不劫持卡片点击 / 页面滚动
    expect(opts.handleScroll).toBe(false);
    expect(opts.handleScale).toBe(false);
    // 不订阅十字光标移动（无任何鼠标反馈）
    expect(subscribeCrosshairMoveMock).not.toHaveBeenCalled();
    // 不渲染悬浮明细节点
    expect(document.querySelector('[aria-hidden="true"].pointer-events-none')).toBeNull();
  });

  it('interactive=true：磁吸十字光标、坐标轴与网格可见、允许平移缩放、订阅十字光标', () => {
    render(<KLineView timeline={makeTimeline()} prevClose={10} height={320} interactive />);
    const opts = chartOptions();
    // 磁吸模式 + 横竖线及标签可见
    expect(opts.crosshair).toMatchObject({ mode: 1 }); // CrosshairMode.Magnet
    expect((opts.crosshair as { vertLine: { visible: boolean; labelVisible: boolean } }).vertLine)
      .toMatchObject({ visible: true, labelVisible: true });
    // 价格轴 / 时间轴 / 网格可见
    expect((opts.rightPriceScale as { visible: boolean }).visible).toBe(true);
    expect((opts.timeScale as { visible: boolean }).visible).toBe(true);
    expect((opts.grid as { horzLines: { visible: boolean } }).horzLines.visible).toBe(true);
    // 滚轮缩放 / 拖拽平移开启
    expect(opts.handleScroll).toMatchObject({ mouseWheel: true, pressedMouseMove: true });
    expect(opts.handleScale).toMatchObject({ mouseWheel: true, pinch: true });
    // 订阅十字光标以驱动悬浮明细
    expect(subscribeCrosshairMoveMock).toHaveBeenCalledTimes(1);
    // 悬浮明细节点存在且默认隐藏（Tailwind opacity-0，进入图表区后由 JS 置为 1）
    const tooltip = document.querySelector<HTMLElement>('[aria-hidden="true"].pointer-events-none');
    expect(tooltip).not.toBeNull();
    expect(tooltip?.className).toContain('opacity-0');
    expect(tooltip?.style.opacity).toBe('');
  });

  it('interactive=true 时趋势线启用最新价标签与悬停数据点高亮', () => {
    render(<KLineView timeline={makeTimeline()} prevClose={10} height={320} interactive />);
    expect(addSeriesMock).toHaveBeenCalledTimes(2); // 趋势线 + 均价线
    // 趋势线（Area）系列：交互模式显示最新价标签与悬停数据点
    expect(trendSeriesOptions()).toMatchObject({ lastValueVisible: true, crosshairMarkerVisible: true });
  });

  it('缩略图模式趋势线不显示最新价标签与悬停高亮', () => {
    render(<KLineView timeline={makeTimeline()} prevClose={10} height={36} />);
    expect(trendSeriesOptions()).toMatchObject({
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    });
  });

  it('interactive=true 默认高度 320，缩略图模式默认高度 120', () => {
    const { container: interactiveBox } = render(
      <KLineView timeline={makeTimeline()} prevClose={10} interactive />,
    );
    expect((interactiveBox.firstElementChild as HTMLElement).style.height).toBe('320px');
    cleanup();
    const { container: thumbBox } = render(<KLineView timeline={makeTimeline()} prevClose={10} />);
    expect((thumbBox.firstElementChild as HTMLElement).style.height).toBe('120px');
  });

  it('显式 height 在两种模式下都优先生效', () => {
    const { container } = render(
      <KLineView timeline={makeTimeline()} prevClose={10} height={44} interactive />,
    );
    expect((container.firstElementChild as HTMLElement).style.height).toBe('44px');
  });

  it('交互模式切换会重建图表并在卸载时退订十字光标', () => {
    const { rerender, unmount } = render(
      <KLineView timeline={makeTimeline()} prevClose={10} height={320} />,
    );
    expect(createChartMock).toHaveBeenCalledTimes(1);
    rerender(<KLineView timeline={makeTimeline()} prevClose={10} height={320} interactive />);
    // 旧实例销毁 + 新实例创建
    expect(removeMock).toHaveBeenCalledTimes(1);
    expect(createChartMock).toHaveBeenCalledTimes(2);
    unmount();
    expect(unsubscribeCrosshairMoveMock).toHaveBeenCalled();
  });

  it('缩略图模式卸载时不退订十字光标（从未订阅）', () => {
    const { unmount } = render(<KLineView timeline={makeTimeline()} prevClose={10} height={36} />);
    unmount();
    expect(unsubscribeCrosshairMoveMock).not.toHaveBeenCalled();
  });
});

describe('KLineView - 性能：视口懒加载与 memo', () => {
  it('容器未进入视口时不创建图表实例（无 canvas 开销）', () => {
    (globalThis as { IntersectionObserver?: unknown }).IntersectionObserver = DeferredIntersectionObserver;
    render(<KLineView timeline={makeTimeline()} prevClose={10} height={36} />);
    expect(createChartMock).not.toHaveBeenCalled();
    expect(setDataMock).not.toHaveBeenCalled();

    // 进入视口后才创建并写入数据
    act(() => {
      triggerIntersection?.();
    });
    expect(createChartMock).toHaveBeenCalledTimes(1);
    expect(setDataMock).toHaveBeenCalled();
  });

  it('进入视口后不再反复创建（只置位不复位）', () => {
    (globalThis as { IntersectionObserver?: unknown }).IntersectionObserver = DeferredIntersectionObserver;
    const { rerender } = render(<KLineView timeline={makeTimeline()} prevClose={10} height={36} />);
    act(() => {
      triggerIntersection?.();
    });
    expect(createChartMock).toHaveBeenCalledTimes(1);
    // 触发第二次相交（同一次 observe 内的重复回调）不应重建
    act(() => {
      triggerIntersection?.();
    });
    expect(createChartMock).toHaveBeenCalledTimes(1);
    rerender(<KLineView timeline={makeTimeline()} prevClose={10} height={36} />);
    expect(createChartMock).toHaveBeenCalledTimes(1);
  });

  it('空数据占位态不创建图表，也不注册视口观察', () => {
    render(<KLineView timeline={[]} height={36} />);
    expect(createChartMock).not.toHaveBeenCalled();
  });

  it('memo：props 未变时父组件重渲染不重新 reconcile（不重复 setData）', () => {
    const timeline = makeTimeline();
    const { rerender } = render(<KLineView timeline={timeline} prevClose={10} height={36} />);
    expect(setDataMock).toHaveBeenCalledTimes(2); // 趋势线 + 均价线各一次
    rerender(<KLineView timeline={timeline} prevClose={10} height={36} />);
    // props 引用未变 -> 组件整体跳过渲染，不会再次写数据
    expect(setDataMock).toHaveBeenCalledTimes(2);
    expect(createChartMock).toHaveBeenCalledTimes(1);
  });
});
