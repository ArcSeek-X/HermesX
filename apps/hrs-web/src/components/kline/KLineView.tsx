/**
 * @file KLineView.tsx
 * @description 股票卡片内的分时缩略走势图。基于 lightweight-charts 封装，只渲染「价格趋势线 + 均价线 + 昨收基准虚线 + 末端圆点」的大致形状：
 *   趋势线配色跟随涨跌方向（红涨绿跌），不渲染左右 Y 轴 / X 轴 / 网格 / 十字光标 / 最高最低点标注，
 *   并锁定平移缩放交互，用于尾盘选股结果卡片等「一眼看走势」的轻量场景；
 *   完整 K 线 / 分时能力仍由 KLineChart（eCharts）承担。
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-10-12
 */

import type React from 'react';
import { useEffect, useMemo, useRef } from 'react';
import {
  AreaSeries,
  CrosshairMode,
  LineSeries,
  LineStyle,
  LineType,
  createChart,
  createSeriesMarkers,
} from 'lightweight-charts';
import type {
  IChartApi,
  IPriceLine,
  ISeriesApi,
  ISeriesMarkersPluginApi,
  LineData,
  Time,
  UTCTimestamp,
} from 'lightweight-charts';
import type { KLinePoint } from '../../api/kline';
import { cn } from '../../utils/cn';
import { STOCK_UP_COLOR, STOCK_DOWN_COLOR } from '../../constants/stockColor';

/** 均价线（VWAP）颜色：橙色细线。卡片图例需与均价线同色，故导出共用 */
export const AVG_PRICE_LINE_COLOR = '#FFB74D';
/** 昨收基准虚线颜色：中性灰，弱化处理避免干扰走势主体 */
const PREV_CLOSE_LINE_COLOR = '#999999';
/** 趋势线面积填充顶部色透明度（叠加在涨跌色上的十六进制 alpha，约 25%） */
const TREND_AREA_TOP_ALPHA = '40';
/** 趋势线面积填充底部色透明度：近全透明，形成渐变消失效果 */
const TREND_AREA_BOTTOM_ALPHA = '08';
/** 缩略图上下留白比例：避免折线贴边被裁切 */
const TREND_SCALE_MARGIN = 0.1;
/** 末端圆点标记尺寸（1 为库默认最小档，缩略图只作点缀） */
const END_DOT_MARKER_SIZE = 1;

/** KLineView 组件 Props */
export interface KLineViewProps {
  /** 分时数据点（KLinePoint 形态，date 为 'YYYY-MM-DD HH:mm:ss'），必填；时间或收盘价无效的点会被过滤，全部无效时展示占位 */
  timeline: KLinePoint[];
  /** 昨收价，用于绘制昨收水平基准虚线并作为涨跌方向基准；传 null / undefined 或非正数时不绘制基准线，方向退化为首末收盘价比较 */
  prevClose?: number | null;
  /** 图表高度，数字按 px 处理，默认 120（与股票卡片内原分时图高度一致） */
  height?: number | string;
  /** 是否叠加均价线（VWAP，橙色细线），默认 true */
  showAvgPrice?: boolean;
  /** 是否绘制昨收水平基准虚线，默认 true */
  showPrevCloseBaseline?: boolean;
  /** 附加到图表容器的 class；嵌入浅色底走势区时传 'border-none bg-transparent' 去掉默认边框背景 */
  className?: string;
}

/**
 * 解析分时时间字符串为 Unix 秒（本地时区）。
 *
 * @param dateStr - 'YYYY-MM-DD HH:mm:ss' 或 'YYYY-MM-DDTHH:mm:ss' 形式的时间串
 * @returns Unix 秒；格式非法时返回 null
 */
function parseTimelineTime(dateStr: string): number | null {
  const matched = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?$/.exec(dateStr);
  if (!matched) return null;
  const [, year, month, day, hour, minute, second] = matched;
  const ms = new Date(
    Number(year),
    Number(month) - 1,
    Number(day),
    Number(hour),
    Number(minute),
    Number(second ?? 0),
  ).getTime();
  return Number.isNaN(ms) ? null : Math.floor(ms / 1000);
}

/**
 * 将后端分时点转换为 lightweight-charts 折线系列数据。
 *
 * 处理规则：
 * - 时间串解析为本地时区 Unix 秒（分时数据要求 UTCTimestamp）；
 * - 过滤时间或收盘价无效的点；同一时间戳重复时保留最后一条（库要求时间唯一）；
 * - 输出按时间升序（库要求数据有序）；
 * - 均价线按「累计成交额 / 累计成交量」逐点累计，与 KLineChart 分时均价口径一致。
 *
 * @param timeline - 分时数据点数组，可为空数组
 * @returns trendPoints 价格趋势线数据；avgPoints 均价线数据（无有效成交量时为空数组）
 */
function buildTimelineSeries(timeline: KLinePoint[]): {
  trendPoints: LineData<Time>[];
  avgPoints: LineData<Time>[];
} {
  const barsByTime = new Map<number, { close: number; amount: number; volume: number }>();
  for (const point of timeline) {
    const time = parseTimelineTime(point.date);
    if (time === null || point.close === null || point.close === undefined || Number.isNaN(point.close)) {
      continue;
    }
    barsByTime.set(time, {
      close: point.close,
      amount: point.amount ?? 0,
      volume: point.volume ?? 0,
    });
  }

  const trendPoints: LineData<Time>[] = [];
  const avgPoints: LineData<Time>[] = [];
  let cumAmount = 0;
  let cumVolume = 0;
  for (const time of [...barsByTime.keys()].sort((a, b) => a - b)) {
    const bar = barsByTime.get(time)!;
    cumAmount += bar.amount;
    cumVolume += bar.volume;
    trendPoints.push({ time: time as UTCTimestamp, value: bar.close });
    if (cumVolume > 0) {
      avgPoints.push({ time: time as UTCTimestamp, value: cumAmount / cumVolume });
    }
  }
  return { trendPoints, avgPoints };
}

/**
 * 股票卡片分时缩略走势图组件。
 *
 * 基于 lightweight-charts（canvas 渲染，体量远小于 eCharts）封装，面向卡片网格这类
 * 「一屏多图」的轻量场景：仅保留价格趋势线（面积填充，红涨绿跌）、均价线（橙色）、
 * 昨收基准虚线与末端圆点，去掉全部坐标轴、网格、十字光标与高低点标注，并禁用平移 / 缩放交互。
 * 需要完整分时 / K 线能力（周期切换、指标、tooltip）时使用 KLineChart。
 */
export const KLineView: React.FC<KLineViewProps> = ({
  timeline,
  prevClose = null,
  height = 120,
  showAvgPrice = true,
  showPrevCloseBaseline = true,
  className,
}) => {
  /** 图表容器 DOM 引用 */
  const containerRef = useRef<HTMLDivElement>(null);
  /** lightweight-charts 实例引用，挂载时创建、卸载时销毁 */
  const chartRef = useRef<IChartApi | null>(null);
  /** 价格趋势线系列引用（Area 系列，兼作昨收基准线的宿主） */
  const trendSeriesRef = useRef<ISeriesApi<'Area'> | null>(null);
  /** 均价线系列引用 */
  const avgSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  /** 末端圆点标记插件引用（v5 标记能力经 createSeriesMarkers 插件挂载到系列上） */
  const markersPluginRef = useRef<ISeriesMarkersPluginApi<Time> | null>(null);
  /** 昨收基准虚线引用，用于价格变化时更新、开关关闭时移除 */
  const prevCloseLineRef = useRef<IPriceLine | null>(null);

  const { trendPoints, avgPoints } = useMemo(() => buildTimelineSeries(timeline), [timeline]);
  const hasTimeline = trendPoints.length > 0;
  const containerHeight = typeof height === 'number' ? `${height}px` : height;
  /** 有效昨收价：null / 非有限值 / 非正数视为无效，不画基准线 */
  const validPrevClose =
    prevClose !== null && Number.isFinite(prevClose) && prevClose > 0 ? prevClose : null;

  // 挂载期创建图表实例与系列；hasTimeline 作为依赖，保证数据晚到时也能完成初始化
  useEffect(() => {
    const container = containerRef.current;
    if (!hasTimeline || !container) return undefined;

    const chart = createChart(container, {
      autoSize: true,
      layout: {
        background: { color: 'transparent' },
        // 关闭库自带 attribution 角标：缩略图内不应出现任何非业务元素
        attributionLogo: false,
      },
      // 缩略图不需要任何坐标轴与网格，仅保留价格刻度（隐藏）用于计算绘图边距
      rightPriceScale: { visible: false, scaleMargins: { top: TREND_SCALE_MARGIN, bottom: TREND_SCALE_MARGIN } },
      leftPriceScale: { visible: false },
      timeScale: { visible: false, fixLeftEdge: true, fixRightEdge: true, rightOffset: 0 },
      grid: { vertLines: { visible: false }, horzLines: { visible: false } },
      crosshair: {
        mode: CrosshairMode.Hidden,
        vertLine: { visible: false, labelVisible: false },
        horzLine: { visible: false, labelVisible: false },
      },
      // 纯展示：禁用平移与缩放，避免卡片点击 / 页面滚动等手势被图表劫持
      handleScroll: false,
      handleScale: false,
    });
    chartRef.current = chart;

    trendSeriesRef.current = chart.addSeries(AreaSeries, {
      // 初始色占位（涨红跌绿）：数据 effect 会按涨跌方向立即覆写为实际颜色
      lineColor: STOCK_UP_COLOR,
      topColor: `${STOCK_UP_COLOR}${TREND_AREA_TOP_ALPHA}`,
      bottomColor: `${STOCK_UP_COLOR}${TREND_AREA_BOTTOM_ALPHA}`,
      lineWidth: 2,
      lineType: LineType.Curved,
      lastValueVisible: false,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
      pointMarkersVisible: false,
    });
    avgSeriesRef.current = chart.addSeries(LineSeries, {
      color: AVG_PRICE_LINE_COLOR,
      lineWidth: 1,
      lineType: LineType.Curved,
      lastValueVisible: false,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
      pointMarkersVisible: false,
    });
    // 末端圆点标记插件：挂到趋势线系列上，数据 effect 通过 setMarkers 更新
    markersPluginRef.current = createSeriesMarkers(trendSeriesRef.current);

    return () => {
      prevCloseLineRef.current = null;
      markersPluginRef.current = null;
      trendSeriesRef.current = null;
      avgSeriesRef.current = null;
      chartRef.current = null;
      chart.remove();
    };
  }, [hasTimeline]);

  // 数据 / 配置更新：写入系列数据、涨跌方向配色、均线可见性与昨收基准线
  useEffect(() => {
    const chart = chartRef.current;
    const trendSeries = trendSeriesRef.current;
    const avgSeries = avgSeriesRef.current;
    if (!chart || !trendSeries || !avgSeries || !hasTimeline) return;

    // 趋势线配色跟随涨跌方向（红涨绿跌，与卡片徽章 / 图例一致）：
    // 以昨收价为基准；昨收缺失时退化为「末日收盘 vs 首日收盘」的趋势方向
    const lastValue = trendPoints[trendPoints.length - 1]?.value;
    const firstValue = trendPoints[0]?.value;
    const baseline = validPrevClose ?? firstValue ?? 0;
    const trendColor = (lastValue ?? 0) >= baseline ? STOCK_UP_COLOR : STOCK_DOWN_COLOR;

    trendSeries.setData(trendPoints);
    trendSeries.applyOptions({
      lineColor: trendColor,
      topColor: `${trendColor}${TREND_AREA_TOP_ALPHA}`,
      bottomColor: `${trendColor}${TREND_AREA_BOTTOM_ALPHA}`,
    });
    // 末端圆点标记：标注最新价位置，颜色随涨跌方向（经标记插件写入）
    markersPluginRef.current?.setMarkers([
      {
        time: trendPoints[trendPoints.length - 1].time,
        position: 'inBar',
        shape: 'circle',
        color: trendColor,
        size: END_DOT_MARKER_SIZE,
      },
    ]);
    avgSeries.setData(avgPoints);
    // 无有效均价数据（如 volume 全缺）时隐藏均线，避免空系列占位
    avgSeries.applyOptions({ visible: showAvgPrice && avgPoints.length > 0 });
    chart.timeScale().fitContent();

    // 昨收基准虚线：随开关与昨收价变化创建、更新或移除
    if (!showPrevCloseBaseline || validPrevClose === null) {
      if (prevCloseLineRef.current) {
        trendSeries.removePriceLine(prevCloseLineRef.current);
        prevCloseLineRef.current = null;
      }
    } else if (prevCloseLineRef.current) {
      prevCloseLineRef.current.applyOptions({ price: validPrevClose });
    } else {
      prevCloseLineRef.current = trendSeries.createPriceLine({
        price: validPrevClose,
        color: PREV_CLOSE_LINE_COLOR,
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: false,
        title: '',
      });
    }
  }, [hasTimeline, trendPoints, avgPoints, showAvgPrice, showPrevCloseBaseline, validPrevClose]);

  // 无有效分时数据：渲染占位块，保持卡片高度稳定
  if (!hasTimeline) {
    return (
      <div
        className={cn(
          'flex items-center justify-center rounded-lg border border-subtle bg-card text-xs text-muted-text',
          className,
        )}
        style={{ height: containerHeight }}
      >
        -
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={cn('rounded-lg border border-subtle bg-card', className)}
      style={{ width: '100%', height: containerHeight }}
    />
  );
};

export default KLineView;
