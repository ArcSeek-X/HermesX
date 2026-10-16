/**
 * @file KLineView.tsx
 * @description 股票卡片内的分时走势图，基于 lightweight-charts 封装。两种模式：
 *
 *   1. 缩略图模式（默认，interactive=false）：只渲染「价格趋势线 + 均价线 + 昨收基准虚线 + 末端圆点」
 *      的大致形状，趋势线配色跟随涨跌方向（红涨绿跌），不渲染坐标轴 / 网格 / 十字光标，
 *      并锁定平移缩放——**不响应任何鼠标操作**，用于尾盘选股结果卡片、自选股列表等
 *      「一眼看走势」的轻量场景；
 *   2. 交互模式（interactive=true）：完整可交互分时图——磁吸十字光标（带价格 / 时间标签）、
 *      可见价格轴与时间轴、淡网格、滚轮缩放与拖拽平移、跟随光标的悬浮明细（时间 / 价格 / 均价 / 涨跌幅）。
 *
 *   价格轴范围经 autoscaleInfoProvider 显式锁定为「趋势线数据区间 + 可见昨收基准线」，
 *   避免 series markers 参与 autoscale 导致矮图表（如自选股列表 36px 缩略图）把走势压成直线。
 *   需要完整 K 线 / 多周期 / 指标能力时使用 KLineChart（eCharts）。
 *
 * 性能设计（面向「一屏多图」的列表 / 卡片场景）：
 *   - React.memo：父组件重渲染时 props 未变则整体跳过；
 *   - IntersectionObserver 懒创建：图表实例只在容器进入视口（预留 160px）时才创建，
 *     视口外 / 后台标签页中的图不产生任何 canvas 与实例开销；
 *   - 悬浮明细用 O(1) 查找表 + 直接操作 DOM（不触发 React 重渲染），十字光标移动时零渲染开销。
 *
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-10-12
 */

import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
  MouseEventParams,
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
/** 价格轴锁定范围的退化保护：数据全平时按该相对比例撑开一个非零区间，避免零高度区间渲染异常 */
const FLAT_RANGE_PAD_RATIO = 0.001;

/** 缩略图模式默认高度（与股票卡片内原分时图高度一致） */
const THUMBNAIL_DEFAULT_HEIGHT = 120;
/** 交互模式默认高度：完整可交互分时图需要足够纵向空间看清走势与坐标轴 */
const INTERACTIVE_DEFAULT_HEIGHT = 320;
/** 懒创建预加载边距（px）：容器进入视口前该距离即开始创建图表，避免滚到眼前才出现 */
const VIEWPORT_PRELOAD_MARGIN = 160;

/** 交互模式网格线颜色：低对比度灰，仅作定位参考 */
const INTERACTIVE_GRID_COLOR = 'rgba(125, 135, 150, 0.16)';
/** 交互模式十字光标颜色 */
const INTERACTIVE_CROSSHAIR_COLOR = 'rgba(125, 135, 150, 0.6)';
/** 交互模式坐标轴 / 十字光标标签底色：与悬浮明细同色，保持视觉一致 */
const INTERACTIVE_LABEL_BG = 'rgba(38, 42, 50, 0.92)';

/** KLineView 组件 Props */
export interface KLineViewProps {
  /** 分时数据点（KLinePoint 形态，date 为 'YYYY-MM-DD HH:mm:ss'），必填；时间或收盘价无效的点会被过滤，全部无效时展示占位 */
  timeline: KLinePoint[];
  /** 昨收价，用于绘制昨收水平基准虚线并作为涨跌方向基准；传 null / undefined 或非正数时不绘制基准线，方向退化为首末收盘价比较 */
  prevClose?: number | null;
  /** 图表高度，数字按 px 处理；不传时缩略图模式默认 120，交互模式默认 320 */
  height?: number | string;
  /** 是否叠加均价线（VWAP，橙色细线），默认 true */
  showAvgPrice?: boolean;
  /** 是否绘制昨收水平基准虚线，默认 true */
  showPrevCloseBaseline?: boolean;
  /** 附加到图表容器的 class；嵌入浅色底走势区时传 'border-none bg-transparent' 去掉默认边框背景 */
  className?: string;
  /**
   * 是否启用完整交互（磁吸十字光标、坐标轴、网格、滚轮缩放 / 拖拽平移、悬浮明细）。
   * 默认 false：纯缩略图，不响应任何鼠标操作（无十字光标、无 tooltip、无平移缩放）。
   */
  interactive?: boolean;
}

/**
 * 解析分时时间字符串为 Unix 秒。
 *
 * 注意用 Date.UTC 构造：lightweight-charts 把 UTCTimestamp 的「UTC 墙上时间」当本地时间展示
 * （内部先取 UTC 分量再按本地时区格式化），因此这里必须给出「墙上时间对应的真 UTC 秒」，
 * 轴刻度 / 十字光标标签才能显示 09:37 而不是被时区偏移成 01:37，且与用户所在时区无关。
 *
 * @param dateStr - 'YYYY-MM-DD HH:mm:ss' 或 'YYYY-MM-DDTHH:mm:ss' 形式的时间串
 * @returns Unix 秒；格式非法时返回 null
 */
function parseTimelineTime(dateStr: string): number | null {
  const matched = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?$/.exec(dateStr);
  if (!matched) return null;
  const [, year, month, day, hour, minute, second] = matched;
  const ms = Date.UTC(
    Number(year),
    Number(month) - 1,
    Number(day),
    Number(hour),
    Number(minute),
    Number(second ?? 0),
  );
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
 * 交互模式的时间标签格式化（HH:mm）。
 *
 * 分时时间戳由 parseTimelineTime 以「墙上时间对应的真 UTC 秒」构造，因此这里用 UTC getter
 * 取回墙上时间，与 lightweight-charts 内部默认格式化口径一致（跨时区显示同一结果）。
 */
function formatTimelineTime(seconds: number): string {
  if (!Number.isFinite(seconds)) return '';
  const date = new Date(seconds * 1000);
  const hh = String(date.getUTCHours()).padStart(2, '0');
  const mm = String(date.getUTCMinutes()).padStart(2, '0');
  return `${hh}:${mm}`;
}

/** 价格格式化：两位小数（分时价格量级下足够，且与卡片 / 列表口径一致） */
function formatPrice(value: number): string {
  return value.toFixed(2);
}

/** 涨跌幅格式化：带符号与百分号 */
function formatChangePercent(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

/** 交互模式悬浮明细的一条数据 */
interface TooltipRow {
  label: string;
  value: string;
  /** 涨跌幅行的颜色（红涨绿跌）；普通行为空使用默认文字色 */
  color?: string;
}

/**
 * 股票分时图组件（缩略图 / 交互双模式）。
 *
 * 实现要点：
 * - 挂载期创建图表实例与系列（依赖 hasTimeline / everVisible / interactive，数据晚到时也能完成初始化）；
 * - 数据期写入系列数据、涨跌方向配色、均线可见性、昨收基准线与价格轴范围锁定；
 * - 交互期订阅十字光标移动，按 O(1) 查找表更新悬浮明细（直接操作 DOM，不触发 React 重渲染）。
 */
function KLineViewComponent({
  timeline,
  prevClose = null,
  height,
  showAvgPrice = true,
  showPrevCloseBaseline = true,
  className,
  interactive = false,
}: KLineViewProps) {
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
  /** 交互模式悬浮明细 DOM 引用（直接改样式 / 内容，避免 mousemove 触发 React 重渲染） */
  const tooltipRef = useRef<HTMLDivElement | null>(null);
  /** time(Unix 秒) -> { 收盘价, 均价 } 查找表：十字光标移动时 O(1) 取数 */
  const pointIndexRef = useRef<Map<number, { close: number; avg: number | null }>>(new Map());
  /** 悬浮明细需要的昨收价（经 ref 传递，避免写入挂载 effect 依赖导致图表重复创建） */
  const tooltipPrevCloseRef = useRef<number | null>(null);

  const { trendPoints, avgPoints } = useMemo(() => buildTimelineSeries(timeline), [timeline]);
  const hasTimeline = trendPoints.length > 0;
  const resolvedHeight = height ?? (interactive ? INTERACTIVE_DEFAULT_HEIGHT : THUMBNAIL_DEFAULT_HEIGHT);
  const containerHeight = typeof resolvedHeight === 'number' ? `${resolvedHeight}px` : resolvedHeight;
  /** 有效昨收价：null / 非有限值 / 非正数视为无效，不画基准线 */
  const validPrevClose =
    prevClose !== null && Number.isFinite(prevClose) && prevClose > 0 ? prevClose : null;

  /**
   * 容器是否曾进入过视口：未进入前不创建图表实例（懒加载，见文件头性能设计）。
   * 不支持 IntersectionObserver 的环境（jsdom / SSR / 老浏览器）直接按可见处理，
   * 避免为懒加载多付一次渲染往返。
   */
  const [everVisible, setEverVisible] = useState(
    () => typeof window !== 'undefined' && typeof IntersectionObserver === 'undefined',
  );

  // 同步悬浮明细上下文（昨收价），避免把易变值关进创建图表的 effect 依赖里
  useEffect(() => {
    tooltipPrevCloseRef.current = validPrevClose;
  }, [validPrevClose]);

  // 视口懒加载：容器进入视口（预留 160px）即置位；只置位不复位，避免反复创建 / 销毁图表
  useEffect(() => {
    if (!hasTimeline || everVisible) return;
    const container = containerRef.current;
    // 无容器（空数据占位态）或不支持 IntersectionObserver（SSR / 老浏览器）时按可见处理
    if (!container || typeof IntersectionObserver === 'undefined') {
      setEverVisible(true);
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setEverVisible(true);
          observer.disconnect();
        }
      },
      { root: null, rootMargin: `${VIEWPORT_PRELOAD_MARGIN}px`, threshold: 0 },
    );
    observer.observe(container);
    return () => observer.disconnect();
  }, [hasTimeline, everVisible]);

  /**
   * 更新交互模式悬浮明细：内容与定位都直接操作 DOM。
   * 离开图表区 / 无对应数据点时隐藏，避免残留。
   */
  const updateTooltip = useCallback((param: MouseEventParams) => {
    const tooltip = tooltipRef.current;
    const container = containerRef.current;
    if (!tooltip || !container) return;

    const point = param.point;
    const time = param.time;
    if (
      !point ||
      time === undefined ||
      point.x < 0 ||
      point.y < 0 ||
      point.x > container.clientWidth ||
      point.y > container.clientHeight
    ) {
      tooltip.style.opacity = '0';
      return;
    }

    const entry = pointIndexRef.current.get(Number(time));
    if (!entry) {
      tooltip.style.opacity = '0';
      return;
    }

    const prevCloseValue = tooltipPrevCloseRef.current;
    const rows: TooltipRow[] = [
      { label: '时间', value: formatTimelineTime(Number(time)) },
      { label: '价格', value: formatPrice(entry.close) },
    ];
    if (entry.avg !== null) {
      rows.push({ label: '均价', value: formatPrice(entry.avg) });
    }
    if (prevCloseValue !== null && prevCloseValue > 0) {
      const changePercent = ((entry.close - prevCloseValue) / prevCloseValue) * 100;
      rows.push({
        label: '涨跌',
        value: formatChangePercent(changePercent),
        color: changePercent >= 0 ? STOCK_UP_COLOR : STOCK_DOWN_COLOR,
      });
    }

    // 数值均为本组件格式化结果，无用户输入，可直接拼装
    tooltip.innerHTML = rows
      .map(
        (row) =>
          `<span class="flex items-center justify-between gap-3">` +
          `<span class="text-muted-text">${row.label}</span>` +
          `<span class="font-medium"${row.color ? ` style="color:${row.color}"` : ''}>${row.value}</span>` +
          `</span>`,
      )
      .join('');

    // 定位：贴住十字光标，靠近右 / 下边界时翻到另一侧，并整体钳制在容器内，防止溢出
    const tipWidth = tooltip.offsetWidth;
    const tipHeight = tooltip.offsetHeight;
    const maxWidth = Math.max(container.clientWidth - 8, 0);
    const maxHeight = Math.max(container.clientHeight - 8, 0);
    const clamp = (value: number, size: number, max: number) =>
      Math.min(Math.max(value, 4), Math.max(max - size, 4));
    let x = point.x + 12;
    if (x + tipWidth > container.clientWidth - 4) x = point.x - tipWidth - 12;
    let y = point.y - tipHeight - 12;
    if (y < 4) y = point.y + 12;
    tooltip.style.transform = `translate(${clamp(x, tipWidth, maxWidth)}px, ${clamp(y, tipHeight, maxHeight)}px)`;
    tooltip.style.opacity = '1';
  }, []);

  // 挂载期创建图表实例与系列；hasTimeline / everVisible 保证数据晚到、进入视口时也能完成初始化
  useEffect(() => {
    const container = containerRef.current;
    if (!hasTimeline || !everVisible || !container) return undefined;

    const chart = createChart(container, {
      autoSize: true,
      layout: {
        background: { color: 'transparent' },
        // 关闭库自带 attribution 角标：缩略图内不应出现任何非业务元素
        attributionLogo: false,
      },
      rightPriceScale: interactive
        ? {
            visible: true,
            borderVisible: true,
            scaleMargins: { top: TREND_SCALE_MARGIN, bottom: TREND_SCALE_MARGIN },
          }
        // 缩略图不需要任何坐标轴，仅保留价格刻度（隐藏）用于计算绘图边距
        : { visible: false, scaleMargins: { top: TREND_SCALE_MARGIN, bottom: TREND_SCALE_MARGIN } },
      leftPriceScale: { visible: false },
      timeScale: interactive
        ? {
            visible: true,
            timeVisible: true,
            secondsVisible: false,
            borderVisible: true,
            // 交互模式允许左右拖动查看，不锁边
            fixLeftEdge: false,
            fixRightEdge: false,
            rightOffset: 2,
            // 时间戳为「本地墙上时间按 UTC 秒存储」，需用 UTC getter 还原为 HH:mm
            tickMarkFormatter: (time) => formatTimelineTime(Number(time)),
          }
        : { visible: false, fixLeftEdge: true, fixRightEdge: true, rightOffset: 0 },
      grid: interactive
        ? {
            vertLines: { visible: true, color: INTERACTIVE_GRID_COLOR },
            horzLines: { visible: true, color: INTERACTIVE_GRID_COLOR },
          }
        : { vertLines: { visible: false }, horzLines: { visible: false } },
      crosshair: interactive
        ? {
            // 磁吸：十字光标横向贴到最近的数据点，读数更准
            mode: CrosshairMode.Magnet,
            vertLine: {
              visible: true,
              labelVisible: true,
              width: 1,
              style: LineStyle.Dashed,
              color: INTERACTIVE_CROSSHAIR_COLOR,
              labelBackgroundColor: INTERACTIVE_LABEL_BG,
            },
            horzLine: {
              visible: true,
              labelVisible: true,
              width: 1,
              style: LineStyle.Dashed,
              color: INTERACTIVE_CROSSHAIR_COLOR,
              labelBackgroundColor: INTERACTIVE_LABEL_BG,
            },
          }
        : {
            mode: CrosshairMode.Hidden,
            vertLine: { visible: false, labelVisible: false },
            horzLine: { visible: false, labelVisible: false },
          },
      // 缩略图纯展示：禁用平移与缩放，避免卡片点击 / 页面滚动等手势被图表劫持
      handleScroll: interactive
        ? { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: true }
        : false,
      handleScale: interactive ? { mouseWheel: true, pinch: true, axisPressedMouseMove: true } : false,
      localization: interactive
        ? { timeFormatter: (time) => formatTimelineTime(Number(time)) }
        : undefined,
    });
    chartRef.current = chart;

    trendSeriesRef.current = chart.addSeries(AreaSeries, {
      // 初始色占位（涨红跌绿）：数据 effect 会按涨跌方向立即覆写为实际颜色
      lineColor: STOCK_UP_COLOR,
      topColor: `${STOCK_UP_COLOR}${TREND_AREA_TOP_ALPHA}`,
      bottomColor: `${STOCK_UP_COLOR}${TREND_AREA_BOTTOM_ALPHA}`,
      lineWidth: 2,
      lineType: LineType.Curved,
      // 最新价标签 / 悬停数据点高亮仅交互模式需要
      lastValueVisible: interactive,
      priceLineVisible: false,
      crosshairMarkerVisible: interactive,
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

    // 交互模式：订阅十字光标移动，驱动悬浮明细（直接操作 DOM，不触发 React 重渲染）
    let unsubscribeCrosshair: (() => void) | null = null;
    if (interactive) {
      chart.subscribeCrosshairMove(updateTooltip);
      unsubscribeCrosshair = () => chart.unsubscribeCrosshairMove(updateTooltip);
    }

    return () => {
      unsubscribeCrosshair?.();
      prevCloseLineRef.current = null;
      markersPluginRef.current = null;
      trendSeriesRef.current = null;
      avgSeriesRef.current = null;
      chartRef.current = null;
      chart.remove();
    };
  }, [hasTimeline, everVisible, interactive, updateTooltip]);

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

    // 锁定价格轴范围：只覆盖「趋势线数据区间 + 可见的昨收基准线」。
    //
    // 背景：lightweight-charts 的 series markers（末端圆点）会参与价格轴 autoscale，
    // 且换算依赖图表像素高度——图表越矮，标记撑出的价格范围越大。36px 的自选股缩略图
    // 因此被拉到约 6 倍数据宽度，全天 3% 的涨跌起伏被压成一条直线（16.1% 占高）。
    // 这里用 autoscaleInfoProvider 显式给出范围，使渲染结果与图表高度、标记/均线无关。
    const trendValues = trendPoints.map((point) => point.value);
    const dataMin = Math.min(...trendValues);
    const dataMax = Math.max(...trendValues);
    let rangeMin = dataMin;
    let rangeMax = dataMax;
    if (showPrevCloseBaseline && validPrevClose !== null) {
      rangeMin = Math.min(rangeMin, validPrevClose);
      rangeMax = Math.max(rangeMax, validPrevClose);
    }
    if (rangeMax - rangeMin <= 0) {
      // 全天收盘价完全相同（停牌 / 一字板）：按比例撑开非零区间
      const pad = Math.max(Math.abs(rangeMax) * FLAT_RANGE_PAD_RATIO, Number.EPSILON);
      rangeMin -= pad;
      rangeMax += pad;
    }
    trendSeries.applyOptions({
      autoscaleInfoProvider: () => ({ priceRange: { minValue: rangeMin, maxValue: rangeMax } }),
    });

    // 悬浮明细查找表：time -> { 收盘价, 均价 }，供十字光标移动时 O(1) 取数
    const pointIndex = new Map<number, { close: number; avg: number | null }>();
    for (const point of trendPoints) {
      pointIndex.set(Number(point.time), { close: point.value, avg: null });
    }
    for (const point of avgPoints) {
      const entry = pointIndex.get(Number(point.time));
      if (entry) entry.avg = point.value;
    }
    pointIndexRef.current = pointIndex;

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
  }, [
    hasTimeline,
    everVisible,
    interactive,
    trendPoints,
    avgPoints,
    showAvgPrice,
    showPrevCloseBaseline,
    validPrevClose,
  ]);

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
      // 交互模式需承载绝对定位的悬浮明细；缩略图模式不需要定位上下文
      style={{ position: interactive ? 'relative' : undefined, width: '100%', height: containerHeight }}
    >
      {/* 交互模式悬浮明细：直接操作 DOM 更新，pointer-events-none 不挡图表交互 */}
      {interactive && (
        <div
          ref={tooltipRef}
          aria-hidden="true"
          className="pointer-events-none absolute left-0 top-0 z-10 flex w-28 flex-col gap-0.5 rounded-md border border-border/60 px-2 py-1 text-[11px] leading-tight text-foreground shadow-lg opacity-0"
          style={{ backgroundColor: 'hsl(var(--elevated) / 0.95)' }}
        />
      )}
    </div>
  );
}

/**
 * 股票分时图组件（缩略图 / 交互双模式）。
 *
 * memo 化原因：自选股表格、尾盘选股卡片网格都是「一屏多图」，父组件刷新行情 /
 * 编辑备注 / 排序时会整体重渲染，props 未变的图应被完全跳过（canvas 与 lightweight-charts
 * 实例都不该被重新 reconcile）。
 */
export const KLineView = memo(KLineViewComponent);

export default KLineView;
