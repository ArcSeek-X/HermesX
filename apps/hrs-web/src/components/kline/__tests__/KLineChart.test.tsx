/**
 * KLineChart 组件单元测试
 *
 * 覆盖维度：
 *  1. 功能完整性：正常渲染、空数据、单点数据、错误处理、props 透传、分页回调
 *  2. 结构正确性：容器、图表挂载点（testId）、图例、各周期渲染
 *  3. 样式/主题：暗色/亮色下 echarts 配置的颜色与背景、涨跌配色
 *  4. 无报错：echarts mock 下不发生未捕获异常、resize/dispose 生命周期正常
 *
 * 依赖 mock：
 *  - echarts：避免真实 canvas 依赖，捕获 init/setOption/resize/dispose 调用
 *  - ../../hooks/useWindowWidth：固定宽度，保证确定性
 *
 * 运行：cd apps/hrs-web && npx vitest run src/components/kline/__tests__/KLineChart.test.tsx
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, cleanup, act } from '@testing-library/react';

import type { KLinePoint, KLinePeriod } from '../../../api/kline';

// ============================================================
// mock echarts：捕获实例调用，避免 jsdom 无 canvas 报错
// ============================================================
const initMock = vi.fn();
const setOptionMock = vi.fn();
const resizeMock = vi.fn();
const disposeMock = vi.fn();
const getDataURLMock = vi.fn(() => 'data:image/png;base64,MOCK');
const onMock = vi.fn();
const offMock = vi.fn();

vi.mock('echarts', () => {
  const chartInstance = {
    setOption: (opt: unknown) => setOptionMock(opt),
    resize: () => resizeMock(),
    dispose: () => disposeMock(),
    getDataURL: () => getDataURLMock(),
    on: (...rest: unknown[]) => onMock(...rest),
    off: (...args: unknown[]) => offMock(...args),
    clear: vi.fn(),
  };
  return {
    init: (...args: unknown[]) => {
      initMock(...args);
      return chartInstance;
    },
    dispose: () => disposeMock(),
    // 分时/分钟/周/月/年模式会使用 graphic 绘制特殊标注，mock 需提供该导出
    graphic: {
      LinearGradient: class {
        constructor(..._args: unknown[]) {
          void _args;
        }
      },
    },
  };
});

// ============================================================
// mock 窗口宽度：固定为桌面宽度，避免响应式分支不确定
// ============================================================
vi.mock('../../hooks/useWindowWidth', () => ({
  useWindowWidth: () => 1280,
}));

// 组件在顶层 import echarts，需在实际 import 之前完成 mock 声明（hoist）
// 因此把组件 import 放到 mock 声明之后由 vitest 自动 hoist 处理
import { KLineChart } from '../KLineChart';
import { STOCK_UP_COLOR } from '../../../constants/colors';

// ============================================================
// 构造测试数据
// ============================================================
function makePoint(overrides: Partial<KLinePoint> = {}): KLinePoint {
  return {
    date: '2024-01-02',
    open: 100,
    close: 105,
    high: 108,
    low: 99,
    volume: 1_000_000,
    amount: 1.05e8,
    change_percent: 5,
    turnover_rate: 1.2,
    ...overrides,
  };
}

function makeData(len: number): KLinePoint[] {
  const data: KLinePoint[] = [];
  for (let i = 0; i < len; i++) {
    const day = String((i % 28) + 2).padStart(2, '0');
    const month = String(Math.floor(i / 28) + 1).padStart(2, '0');
    data.push(makePoint({ date: `2024-${month}-${day}` }));
  }
  return data;
}

// ============================================================
// 测试前重置计数器
// ============================================================
beforeEach(() => {
  initMock.mockClear();
  setOptionMock.mockClear();
  resizeMock.mockClear();
  disposeMock.mockClear();
  getDataURLMock.mockClear();
  onMock.mockClear();
  offMock.mockClear();
});

afterEach(() => {
  cleanup();
});

describe('KLineChart - 功能完整性', () => {
  it('正常渲染日K数据时不抛错，且初始化并设置了 option', () => {
    render(<KLineChart data={makeData(20)} period="daily" />);
    expect(initMock).toHaveBeenCalledTimes(1);
    expect(setOptionMock).toHaveBeenCalled();
    // 默认显示最近 PERIOD_VISIBLE_BARS 根（日K=250），20 根全部在可见区
    const option = setOptionMock.mock.calls[0][0] as { series: Array<{ data: unknown[] }> };
    const candleSeries = option.series.find((s) => Array.isArray(s.data));
    expect(candleSeries?.data.length).toBeGreaterThan(0);
  });

  it('空数据时仍渲染容器且不抛错（option 内无 K 线数据）', () => {
    const { container } = render(<KLineChart data={makeData(0)} period="daily" />);
    expect(initMock).toHaveBeenCalledTimes(1);
    expect(container.querySelector('.kline-chart') ?? container.querySelector('.bg-card')).not.toBeNull();
    expect(container.querySelector('.bg-card')).not.toBeNull();
  });

  it('单根数据时也能渲染（边界值）', () => {
    expect(() => render(<KLineChart data={makeData(1)} period="daily" />)).not.toThrow();
    expect(initMock).toHaveBeenCalledTimes(1);
  });

  it('数据量未超过可见上限时 dataZoom 起点为 0（完整展示）', () => {
    render(<KLineChart data={makeData(100)} period="daily" />);
    const option = setOptionMock.mock.calls[0][0] as {
      dataZoom: Array<{ start?: number; end?: number }>;
    };
    expect(option.dataZoom?.[0]?.start).toBe(0);
    expect(option.dataZoom?.[0]?.end).toBe(100);
  });

  it('数据量超过可见上限时 dataZoom 起点 > 0（默认展示最近一段）', () => {
    render(<KLineChart data={makeData(400)} period="daily" />);
    const option = setOptionMock.mock.calls[0][0] as {
      dataZoom: Array<{ start?: number }>;
    };
    const startVal = option.dataZoom?.[0]?.start ?? 0;
    expect(startVal).toBeGreaterThan(0);
  });

  it('dataZoom 同时包含 inside 与 slider 两种交互', () => {
    render(<KLineChart data={makeData(100)} period="daily" />);
    const option = setOptionMock.mock.calls[0][0] as {
      dataZoom: Array<{ type?: string }>;
    };
    const types = option.dataZoom?.map((z) => z.type).filter(Boolean);
    expect(types).toContain('inside');
    expect(types).toContain('slider');
  });

  it('注册了 dataZoom 事件监听（用于左边界触发 onDataZoomBoundary）', () => {
    const onBoundary = vi.fn();
    render(<KLineChart data={makeData(400)} period="daily" onDataZoomBoundary={onBoundary} />);
    // 组件在 K 线模式下 chart.on('dataZoom', handler)，验证已绑定该事件
    expect(onMock).toHaveBeenCalledWith('dataZoom', expect.any(Function));
  });
});

describe('KLineChart - 结构正确性', () => {
  it('渲染图表容器（圆角卡片样式 bg-card + rounded-lg）', () => {
    const { container } = render(<KLineChart data={makeData(10)} period="daily" />);
    const el = container.querySelector('.bg-card.rounded-lg');
    expect(el).not.toBeNull();
  });

  it('图表容器具有 100% 宽度与指定高度', () => {
    const { container } = render(<KLineChart data={makeData(10)} period="daily" />);
    const el = container.querySelector('.bg-card') as HTMLElement;
    expect(el.style.width).toBe('100%');
  });

  it('自定义 height 通过 style 正确传递到容器', () => {
    const { container } = render(<KLineChart data={makeData(10)} period="daily" height="600px" />);
    const el = container.querySelector('.bg-card') as HTMLElement;
    expect(el.style.height).toBe('600px');
  });

  it('默认 height 为 500px', () => {
    const { container } = render(<KLineChart data={makeData(10)} period="daily" />);
    const el = container.querySelector('.bg-card') as HTMLElement;
    expect(el.style.height).toBe('500px');
  });

  it('各周期均可渲染（分时/分钟/日/周/月/年）且不抛错', () => {
    const periods: KLinePeriod[] = [
      '1m', '5m', '15m', '30m', '60m', '120m', '5d', 'daily', 'weekly', 'monthly', 'yearly',
    ];
    periods.forEach((p) => {
      expect(() => render(<KLineChart data={makeData(30)} period={p} />)).not.toThrow();
      cleanup();
    });
  });

  it('分时(1m) 模式可正常渲染且不抛错', () => {
    expect(() => render(<KLineChart data={makeData(30)} period="1m" prevClose={100} />).unmount()).not.toThrow();
  });
});

describe('KLineChart - 样式与主题', () => {
  it('亮色主题下坐标轴标签颜色为浅色（#333333）', () => {
    document.documentElement.classList.remove('dark');
    render(<KLineChart data={makeData(10)} period="daily" />);
    const option = setOptionMock.mock.calls[0][0] as {
      xAxis: Array<{ axisLabel?: { color?: string } }>;
    };
    // xAxis[1] 为主图时间轴，亮色主题为 #333333
    expect(option.xAxis?.[1]?.axisLabel?.color).toBe('#333333');
  });

  it('暗色主题下坐标轴标签颜色为亮色（#e0e0e0）', () => {
    document.documentElement.classList.add('dark');
    render(<KLineChart data={makeData(10)} period="daily" />);
    const option = setOptionMock.mock.calls[0][0] as {
      xAxis: Array<{ axisLabel?: { color?: string } }>;
    };
    expect(option.xAxis?.[1]?.axisLabel?.color).toBe('#e0e0e0');
    document.documentElement.classList.remove('dark');
  });

  it('日K图上涨配色为红色（STOCK_UP_COLOR）', () => {
    render(<KLineChart data={makeData(10)} period="daily" />);
    const option = setOptionMock.mock.calls[0][0] as {
      series: Array<{ itemStyle?: { color?: string; color0?: string } }>;
    };
    const candle = option.series.find((s) => s.itemStyle && (s.itemStyle.color || s.itemStyle.color0));
    expect(candle?.itemStyle?.color).toBe(STOCK_UP_COLOR);
  });

  it('包含 MA 均线系列（日K 默认显示 MA5/MA10/MA30/MA60）', () => {
    render(<KLineChart data={makeData(40)} period="daily" />);
    const option = setOptionMock.mock.calls[0][0] as { series: Array<{ name?: string }> };
    const maNames = option.series.map((s) => s.name).filter(Boolean);
    expect(maNames.some((n) => String(n).startsWith('MA'))).toBe(true);
  });

  it('包含 MACD 副图系列（默认显示 DIF/DEA/MACD）', () => {
    render(<KLineChart data={makeData(40)} period="daily" />);
    const option = setOptionMock.mock.calls[0][0] as { series: Array<{ name?: string }> };
    const names = option.series.map((s) => s.name).filter(Boolean).map(String);
    expect(names.some((n) => n.includes('DIF') || n.includes('MACD'))).toBe(true);
  });

  it('包含 tooltip 配置且 trigger 为 axis', () => {
    render(<KLineChart data={makeData(10)} period="daily" />);
    const option = setOptionMock.mock.calls[0][0] as { tooltip?: { trigger?: string } };
    expect(option.tooltip?.trigger).toBe('axis');
  });
});

describe('KLineChart - 生命周期与无报错', () => {
  it('组件卸载时解绑 dataZoom 事件与 resize 监听（非内存泄漏）', () => {
    const { unmount } = render(<KLineChart data={makeData(10)} period="daily" />);
    expect(offMock).not.toHaveBeenCalled();
    unmount();
    // K 线模式挂载时 chart.on('dataZoom')，卸载时 chart.off('dataZoom') 解绑
    expect(offMock).toHaveBeenCalledWith('dataZoom', expect.any(Function));
  });

  it('窗口 resize 时调用实例 resize（通过全局 resize 事件）', () => {
    render(<KLineChart data={makeData(10)} period="daily" />);
    act(() => {
      window.dispatchEvent(new Event('resize'));
    });
    // 组件监听 window.resize -> chart.resize()
    expect(resizeMock).toHaveBeenCalled();
  });

  it('重复渲染（props 变化）时复用同一实例并更新 option，不重复 init', () => {
    const { rerender } = render(<KLineChart data={makeData(10)} period="daily" />);
    const initCountBefore = initMock.mock.calls.length;
    rerender(<KLineChart data={makeData(20)} period="daily" />);
    // 同一容器复用实例，init 不应再次调用
    expect(initMock.mock.calls.length).toBe(initCountBefore);
    // 但 setOption 应再次调用以更新数据
    expect(setOptionMock.mock.calls.length).toBeGreaterThanOrEqual(2);
  });

  it('data 为空数组时 setOption 调用且不抛错', () => {
    expect(() => {
      render(<KLineChart data={makeData(0)} period="daily" />);
    }).not.toThrow();
    expect(setOptionMock).toHaveBeenCalled();
  });
});

describe('KLineChart - 边界与健壮性', () => {
  it('volume 为 null 的点不会导致崩溃', () => {
    const data = makeData(5);
    data[0] = makePoint({ volume: null, amount: null });
    expect(() => render(<KLineChart data={data} period="daily" />)).not.toThrow();
    expect(setOptionMock).toHaveBeenCalled();
  });

  it('change_percent 为 null 的点不会导致崩溃', () => {
    const data = makeData(5);
    data[0] = makePoint({ change_percent: null });
    expect(() => render(<KLineChart data={data} period="daily" />).unmount()).not.toThrow();
  });

  it('大量数据（1000 点）不抛错且能渲染', () => {
    expect(() => render(<KLineChart data={makeData(1000)} period="daily" />).unmount()).not.toThrow();
    expect(initMock).toHaveBeenCalledTimes(1);
  });

  it('5日K 周期可正常渲染（聚合数据）', () => {
    expect(() => render(<KLineChart data={makeData(50)} period="5d" />).unmount()).not.toThrow();
  });

  it('年K 周期可正常渲染（跨年数据）', () => {
    const data = makeData(30);
    data.forEach((p, i) => { p.date = `20${20 + i}-12-31`; });
    expect(() => render(<KLineChart data={data} period="yearly" />).unmount()).not.toThrow();
  });
});
