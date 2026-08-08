/**
 * K 线图组件
 *
 * 使用 ECharts 实现多层网格布局，支持两种模式：
 *
 * 【分时模式（period === '1m'）】三层网格：
 *   - 上层 62%：分时折线面积图 + 均价线 + 昨收基准线 + 午休分界线
 *   - 中层 24%：成交量柱状图（红涨绿跌）
 *   - 下层  7%：时间轴（仅显示标签，不参与联动）
 *   - 双 Y 轴：左侧绝对价格（正红负绿），右侧涨跌幅百分比
 *   - 四角标注：左上最高价、左下最低价、右上最大涨幅、右下最大跌幅
 *
 * 【非分时模式（日K/周K/月K/年K/5m~120m）】四层网格：
 *   - 上层 42%：K 线蜡烛图 + MA5/MA10/MA30/MA60 均线
 *   - 中层 14%：成交量柱状图（红涨绿跌）
 *   - 下层 12%：MACD 指标（DIF/DEA 线 + MACD 柱）
 *   - 底部  6%：时间轴
 *   - dataZoom：支持鼠标滚轮/触摸滑动缩放，联动所有 4 个 X 轴
 *
 * 通用特性：
 * - 颜色适配主题（红涨绿跌），使用全局颜色常量（STOCK_UP_COLOR / STOCK_DOWN_COLOR）
 * - 所有 tooltip 文字支持中英文切换
 * - 分钟线自动添加 11:30 / 13:00 交易时段分割线
 * - 时间轴标签自适应密度（预计算 + 缓存策略，避免 interval 重复计算）
 *   - 非分时模式下（初始状态 + 在滑块左右滑动的过程中）
 *     - 等距定位算法，首尾对齐，确保标签均匀分布
 *     - 一般情况下，时间轴时间标签的个数不能太少，具体你根据情况可以调整
 *     - 屏幕-大屏（≥1000px），目标标签数：LABEL_TARGET_LARGE 个，屏幕-小屏（<1000px），目标标签数：LABEL_TARGET_SMALL 个
 *     - 当K线图可见柱子数 ≤ LABEL_SHOW_ALL_THRESHOLD，那么每个柱子下面都要有对应的时间轴时间标签  
 *     - 时间轴时间标签的字体大小要合理，时间轴时间标签绝对不能出现重叠，逃逸出图形的情况
 * - 支持全量数据模式（showAllData），开启后加载从上市至今所有数据
 * - 支持分页加载（onDataZoomBoundary），拖动到左边界时触发
 * - Tooltip 显示顺序：日期、涨跌幅、开盘、收盘、最高、最低、成交量、成交额、换手率、MA、MACD、DIF、DEA
 */

import type React from 'react';
import { useEffect, useRef, useCallback } from 'react';
import * as echarts from 'echarts';
import type { KLinePoint, KLinePeriod } from '../../api/kline';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { useWindowWidth } from '../../hooks/useWindowWidth';
import { STOCK_UP_COLOR, STOCK_DOWN_COLOR, getThemeColors } from '../../constants/colors';

/** 各周期初始可见柱子数量（一屏显示） */
const PERIOD_VISIBLE_BARS: Record<string, number> = {
  '1m':    240,   // 分时：全部显示
  '5m':    100,
  '15m':   100,
  '30m':   100,
  '60m':   80,
  '120m':  70,
  '5d':    70,
  'daily': 100,
  'weekly': 70,
  'monthly': 50,
  'yearly': 30,
};

// ===== 时间轴标签密度配置（可直接修改调试） =====
/** 大屏（≥1000px）目标标签数 */
const LABEL_TARGET_LARGE = 6;
/** 小屏（<1000px）目标标签数 */
const LABEL_TARGET_SMALL = 5;
/** 可见柱子数 ≤ 此值时，每个柱子下都显示标签 */
const LABEL_SHOW_ALL_THRESHOLD = 6;

// ===== 分时图标注相关公共配置 =====
/**
 * 生成 markPoint 标签的富文本配置
 * @param color - 文字颜色
 * @param pos - 标签位置（'top' | 'bottom'）
 */
const getMarkLabelConfig = (color: string, pos: 'top' | 'bottom') => ({
  show: true,
  position: pos,
  distance: 5,
  formatter: (params: { name: string; value: number }) => `{b|${params.name}}\n{c|${params.value.toFixed(2)}}`,
  rich: {
    b: { color, fontSize: 10, fontWeight: 'bold' },
    c: { color, fontSize: 11, fontWeight: 'bold' },
  },
});

/**
 * 安全获取时间索引，兜底 0 防止 -1 跑出画布
 * @param timeStr - 目标时间字符串
 * @param dateList - 时间轴数组
 */
function getSafeTimeIndex(timeStr: string, dateList: string[]) {
  const idx = dateList.findIndex(item => item.includes(timeStr) || item === timeStr);
  return Math.max(idx, 0);
}

/**
 * 根据股票代码判断每日涨跌幅限制（百分比）
 * - 主板（60/00 开头）：±10%
 * - 创业板（30 开头）/ 科创板（68 开头）：±20%
 * - 北交所（8/4 开头）：±30%
 * @param stockCode - 纯数字股票代码（如 "600580"）
 */
function getDailyLimit(stockCode: string): number {
  const code = stockCode.replace(/^(SH|SZ|BJ)/i, '');
  if (code.startsWith('30') || code.startsWith('68')) return 20;
  if (code.startsWith('8') || code.startsWith('4')) return 30;
  return 10; // 主板默认 10%
}

/** K 线图组件 Props */
type KLineChartProps = {
  /** K 线数据点数组，由父组件从 API 获取后传入 */
  data: KLinePoint[];
  /** 当前周期：'1m'分时 | '5m'~'120m'分钟线 | 'day'日K | 'week'周K | 'month'月K | 'year'年K | '5day'五日 */
  period: KLinePeriod;
  /** 图表高度，默认 '500px' */
  height?: string;
  /** 昨收价，分时模式下用于计算涨跌幅和绘制基准线；非分时可传空 */
  prevClose?: number | null;
  /** 股票代码（用于判断板块涨跌幅限制） */
  stockCode?: string;
  /** 当 dataZoom 拖动到左边界时触发（用于分页加载历史数据） */
  onDataZoomBoundary?: () => void;
  /** 是否显示全部数据（全量数据模式）。为 true 时 dzStart=0，显示从上市至今所有数据；为 false 时按 PERIOD_VISIBLE_BARS 显示最近 N 根 */
  showAllData?: boolean;
};

/**
 * 计算移动平均线（MA）
 *
 * 算法：滑动窗口求均值，前 period-1 个点数据不足返回 null
 * @param data - 收盘价数组
 * @param period - 均线周期（5/10/30/60）
 * @returns 与 data 等长的数组，前 period-1 项为 null
 */
function computeMA(data: number[], period: number): (number | null)[] {
  return data.map((_, i) => {
    if (i < period - 1) return null;
    let sum = 0;
    for (let j = i - period + 1; j <= i; j++) sum += data[j];
    return sum / period;
  });
}

/**
 * 计算 MACD 指标（Moving Average Convergence Divergence）
 *
 * 算法步骤：
 * 1. 计算 EMA12 和 EMA26（指数移动平均线）
 * 2. DIF = EMA12 - EMA26（快线减慢线）
 * 3. DEA = DIF 的 9 周期 EMA（信号线）
 * 4. MACD 柱 = (DIF - DEA) × 2
 *
 * @param closes - 收盘价数组
 * @returns { dif: DIF 线, dea: DEA 线, macd: MACD 柱状值 }
 */
function computeMACD(closes: number[]): { dif: number[]; dea: number[]; macd: number[] } {
  const ema12: number[] = [];
  const ema26: number[] = [];
  const dif: number[] = [];
  const dea: number[] = [];
  const macd: number[] = [];

  const k12 = 2 / 13;
  const k26 = 2 / 27;
  const k9 = 2 / 10;

  for (let i = 0; i < closes.length; i++) {
    if (i === 0) {
      ema12.push(closes[i]);
      ema26.push(closes[i]);
    } else {
      ema12.push(closes[i] * k12 + ema12[i - 1] * (1 - k12));
      ema26.push(closes[i] * k26 + ema26[i - 1] * (1 - k26));
    }
    dif.push(ema12[i] - ema26[i]);
  }

  for (let i = 0; i < dif.length; i++) {
    if (i === 0) {
      dea.push(dif[i]);
    } else {
      dea.push(dif[i] * k9 + dea[i - 1] * (1 - k9));
    }
    macd.push((dif[i] - dea[i]) * 2);
  }

  return { dif, dea, macd };
}

/** 格式化成交量：原始值（手）→ 万手，保留 2 位小数 */
function formatVolume(vol: number | null): string {
  if (vol === null || vol === undefined) return '-';
  // 原始 volume 单位为"手"，直接转万手
  const wanShou = vol / 10000;
  return wanShou.toFixed(2);
}

/** 格式化成交额：原始值（元）→ 万/亿，保留 2 位小数 */
function formatAmount(amount: number | null): { value: string; unit: string } {
  if (amount === null || amount === undefined) return { value: '-', unit: '' };
  if (amount >= 1e8) {
    return { value: (amount / 1e8).toFixed(2), unit: '亿' };
  }
  return { value: (amount / 1e4).toFixed(2), unit: '万' };
}

/** 格式化涨跌幅，带正负号和百分号 */
function formatChange(change: number | null): string {
  if (change === null || change === undefined) return '-';
  const sign = change > 0 ? '+' : '';
  return `${sign}${change.toFixed(2)}%`;
}

/** 获取涨跌幅颜色：涨红跌绿 */
function getUpDownColor(change: number | null): string {
  if (change === null || change === undefined) return '#999';
  return change >= 0 ? STOCK_UP_COLOR : STOCK_DOWN_COLOR;
}

/**
 * 根据周期类型返回时间轴标签格式化函数
 *
 * @param period - 当前周期
 * @param isSmallScreen - 是否小屏幕（<1000px）
 * @returns { formatter: (value: string) => string }
 */
function computeTimeAxisLabels(
  _data: KLinePoint[],
  period: KLinePeriod,
  isSmallScreen: boolean,
): { formatter: (value: string) => string } {
  const formatter = (value: string): string => {
    // 判断是否为分钟线（含时间部分）
    const isIntraday = ['1m', '5m', '15m', '30m', '60m', '120m'].includes(period);

    if (period === '1m') {
      // 分时：只显示时间 HH:mm
      const timePart = value.split(' ')[1];
      if (!timePart) return value;
      const [h, m] = timePart.split(':');
      return `${h}:${m}`;
    }

    if (isIntraday) {
      // 分钟线（5m~120m）
      const parts = value.split(' ');
      const datePart = parts[0] || ''; // "2026-07-31"
      const timePart = parts[1] || ''; // "09:35:00"

      if (period === '120m') {
        // 120分钟：显示完整日期+时间 YYYY-MM-DD HH:mm
        return `${datePart} ${timePart.slice(0, 5)}`;
      }

      // 其他分钟线：小屏幕省略时间，只显示 MM-DD
      if (isSmallScreen) {
        return datePart.slice(5); // "07-31"
      }
      // 大屏幕：显示 MM-DD HH:mm
      return `${datePart.slice(5)} ${timePart.slice(0, 5)}`; // "07-31 09:35"
    }

    // 日K/周K/月K/年K/5日：始终显示完整日期 YYYY-MM-DD
    return value; // "2025-07-28"
  };

  return { formatter };
}

export const KLineChart: React.FC<KLineChartProps> = ({
  data,
  period,
  height = '500px',
  prevClose = null,
  stockCode,
  onDataZoomBoundary,
  showAllData = false,
}) => {
  /** ECharts 容器 DOM 引用 */
  const chartRef = useRef<HTMLDivElement>(null);
  /** ECharts 实例引用，避免重复 init */
  const chartInstance = useRef<echarts.ECharts | null>(null);
  const { t, language } = useUiLanguage();

  /** 监听窗口宽度变化，小屏幕时减少时间轴刻度数量（阈值 1000px） */
  const windowWidth = useWindowWidth();
  const isSmallScreen = windowWidth < 1000;

  // 缩放后可见数据点数（用于自适应时间轴刻度密度）
  // 使用 useRef 避免 setState 触发重渲染导致 setOption 重置图表
  // 初始化时根据周期计算实际可见柱子数
  // 全量数据模式下，visibleBars 仍按 PERIOD_VISIBLE_BARS 计算，但 dzStart=0 显示全部
  const visibleBars = PERIOD_VISIBLE_BARS[period] || 100;
  const initialVisible = Math.min(visibleBars, data.length);
  const visibleCountRef = useRef<number>(initialVisible);
  /** 可见范围起始索引（用于动态计算时间轴标签密度） */
  const visibleStartRef = useRef<number>(
    data.length > visibleBars ? data.length - visibleBars : 0,
  );

  /** 缓存的时间轴标签索引集合（预计算策略核心）
   *  - 存储当前应显示标签的索引（Set<number>）
   *  - interval 函数通过 labelIndicesRef.current.has(index) 快速查找
   *  - 避免每次 interval 调用都重新计算，提升性能
   */
  const labelIndicesRef = useRef<Set<number>>(new Set());

/**
 * 预计算当前可见范围内应显示标签的索引集合
 *
 * 算法策略：
 * 1. 使用 useRef 缓存标签索引集合（labelIndicesRef），避免 interval 每次重复计算
 * 2. 在数据/周期/缩放变化时一次性计算，interval 函数仅做 Set.has() 查找
 * 3. 等距定位算法：step = (visCount-1)/(n-1)，确保首尾对齐
 *
 * 遵循原则：
 * - 均匀分布：等距选取标签位置
 * - 左右对齐：首尾柱子必有标签
 * - 少量全显：可见柱子数 ≤ LABEL_SHOW_ALL_THRESHOLD 时每个都显示
 * - 密度控制：根据屏幕宽度和标签文本长度动态限制最大标签数
 * - 防止重叠：maxLabelsByWidth 确保标签不超出可用宽度
 *
 * 触发时机：
 * - 数据加载/周期切换时（useEffect 中）
 * - 用户拖动滑块时（handleDataZoom 中）
 */
  const recomputeLabelIndices = useCallback(() => {
    const total = data.length;
    if (total === 0) { labelIndicesRef.current = new Set(); return; }

    const visStart = Math.max(0, Math.min(visibleStartRef.current, total - 1));
    const visCount = Math.max(1, Math.min(visibleCountRef.current, total - visStart));

    // 原则3：≤LABEL_SHOW_ALL_THRESHOLD根柱子时每个都显示
    if (visCount <= LABEL_SHOW_ALL_THRESHOLD) {
      const s = new Set<number>();
      for (let i = visStart; i < visStart + visCount; i++) s.add(i);
      labelIndicesRef.current = s;
      return;
    }

    // 计算可用像素宽度
    const cw = windowWidth || 1200;
    const availableWidth = cw * 0.88;
    const isIntraday = ['1m', '5m', '15m', '30m', '60m', '120m'].includes(period);
    const labelWidth = isIntraday ? 90 : 80;
    const maxLabelsByWidth = Math.max(LABEL_TARGET_LARGE, Math.floor(availableWidth / labelWidth));

    // 目标标签数：大屏LABEL_TARGET_LARGE个，小屏LABEL_TARGET_SMALL个
    const targetLabels = isSmallScreen ? LABEL_TARGET_SMALL : LABEL_TARGET_LARGE;
    const n = Math.min(targetLabels, maxLabelsByWidth, visCount);

    const s = new Set<number>();
    if (n <= 1) {
      s.add(visStart);
    } else {
      // 等距定位，首尾对齐
      for (let i = 0; i < n; i++) {
        s.add(visStart + Math.round((i * (visCount - 1)) / (n - 1)));
      }
    }
    labelIndicesRef.current = s;
  }, [data.length, period, windowWidth, isSmallScreen]);

  // 获取主题颜色（使用全局颜色常量）
  const getThemeColorsLocal = useCallback(() => {
    return getThemeColors();
  }, []);

  /**
   * 核心渲染逻辑：根据 data / period / 主题 / 屏幕宽度 重新计算并绘制图表
   *
   * 依赖项：data, period, 主题颜色, 语言, 窗口宽度, 昨收价
   * 任一变化都会触发重新渲染
   */
  useEffect(() => {
    if (!chartRef.current) return;

    // 数据或周期变化时，同步更新可见范围 refs 和标签索引
    // 确保 interval 函数始终使用正确的可见范围计算标签密度
    // 全量数据模式下，visibleBars 仍按周期默认值计算（用于 dzStart），但数据量可能更多
    const currentVisibleBars = PERIOD_VISIBLE_BARS[period] || 100;
    const currentVisibleCount = Math.min(currentVisibleBars, data.length);
    const currentVisibleStart = data.length > currentVisibleBars ? data.length - currentVisibleBars : 0;
    visibleCountRef.current = currentVisibleCount;
    visibleStartRef.current = currentVisibleStart;
    recomputeLabelIndices();

    // 初始化 ECharts 实例
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    const chart = chartInstance.current;

    // ===== 构建完整 option 配置 =====
    const colors = getThemeColorsLocal();
    const isIntraday = period === '1m';
    const isMinuteLine = ['1m', '5m', '15m', '30m', '60m', '120m'].includes(period);

    // 国际化标签
    const labels = {
      date: t('kline.tooltip.date'),
      open: t('kline.tooltip.open'),
      close: t('kline.tooltip.close'),
      high: t('kline.tooltip.high'),
      low: t('kline.tooltip.low'),
      change: t('kline.tooltip.change'),
      volume: t('kline.tooltip.volume'),
      amount: t('kline.tooltip.amount'),
      ma5: t('kline.tooltip.ma5'),
      ma10: t('kline.tooltip.ma10'),
      ma30: t('kline.tooltip.ma30'),
      ma60: t('kline.tooltip.ma60'),
      dif: t('kline.tooltip.dif'),
      dea: t('kline.tooltip.dea'),
      macd: t('kline.tooltip.macd'),
      avgPrice: '均价',
      turnoverRate: '换手率',
    };

    // 提取数据
    const dates = data.map((d) => d.date);
    const closes = data.map((d) => d.close);
    const volumes = data.map((d) => d.volume ?? 0);
    
    // 找到交易时段分割线的索引
    const midday1130Index = dates.findIndex((d) => d.includes('11:30'));
    const midday1300Index = dates.findIndex((d) => d.includes('13:00'));

    // 按周期自适应计算时间轴标签格式化函数
    const { formatter: timeAxisFormatter } =
      computeTimeAxisLabels(data, period, isSmallScreen);

    // 计算 MA 均线（MA5/MA10/MA30/MA60）
    const ma5 = computeMA(closes, 5);
    const ma10 = computeMA(closes, 10);
    const ma30 = computeMA(closes, 30);
    const ma60 = computeMA(closes, 60);

    // 计算 MACD
    const { dif, dea, macd } = computeMACD(closes);

    // K 线数据 [开盘，收盘，最低，最高]
    const klineData = data.map((d) => [d.open, d.close, d.low, d.high]);

    // 成交量颜色（红涨绿跌）
    const volumeColors = data.map((d, i) => {
      if (i === 0) return colors.upColor;
      return d.close >= data[i - 1].close ? colors.upColor : colors.downColor;
    });

    // MACD 柱颜色
    const macdColors = macd.map((v) =>
      v >= 0 ? colors.macdUpColor : colors.macdDownColor,
    );

    // ===== 分时图专用计算 =====
    // 均价线：累计成交金额 / 累计成交量，反映市场平均持仓成本
    const avgPriceLine: (number | null)[] = [];
    let cumAmount = 0;
    let cumVolume = 0;
    for (let i = 0; i < data.length; i++) {
      cumAmount += data[i].amount ?? 0;
      cumVolume += data[i].volume ?? 0;
      avgPriceLine.push(cumVolume > 0 ? cumAmount / cumVolume : null);
    }

    // 涨跌幅百分比（基于昨收价）— 用于右侧 Y 轴刻度映射
    // 先计算实际最大偏差，再用 "Nice number" 算法取整，确保刻度间隔美观
    const minPrice = Math.min(...closes);
    const maxPrice = Math.max(...closes);
    
    // 当日真实最高/最低价（盘口极值，包含集合竞价），用于标注
    const trueHighPrice = Math.max(...data.map(d => d.high));
    const trueLowPrice = Math.min(...data.map(d => d.low));
    // 找到真实最高/最低价对应的时间索引（用于 markPoint 定位）
    const trueHighIndex = data.findIndex(d => d.high === trueHighPrice);
    const trueLowIndex = data.findIndex(d => d.low === trueLowPrice);
    const trueHighTime = trueHighIndex >= 0 ? data[trueHighIndex].date : '';
    const trueLowTime = trueLowIndex >= 0 ? data[trueLowIndex].date : '';
    
    // 计算实际最大偏差（距昨收价）
    const actualMaxDeviation = prevClose && prevClose > 0
      ? Math.max(Math.abs(maxPrice - prevClose), Math.abs(minPrice - prevClose))
      : Math.max(maxPrice - minPrice, 1) / 2;
    
    // "Nice number" 算法：将偏差向上取整到干净的数值，确保刻度间隔美观
    // 目标：7个刻度（0轴 + 上下各3个），间隔均匀
    const getNiceInterval = (range: number, targetTicks: number): number => {
      const rough = range / targetTicks;
      const magnitude = Math.pow(10, Math.floor(Math.log10(rough)));
      const normalized = rough / magnitude;
      let nice: number;
      if (normalized <= 1.5) nice = 1;
      else if (normalized <= 3) nice = 2;
      else if (normalized <= 7) nice = 5;
      else nice = 10;
      return nice * magnitude;
    };
    
    // 计算干净的间隔（目标 3 个刻度在 0 轴上方）
    const niceInterval = getNiceInterval(actualMaxDeviation, 3);
    // 对称范围：向上取整到间隔的整数倍
    const niceMaxDeviation = Math.ceil(actualMaxDeviation / niceInterval) * niceInterval;
        
    // 根据股票代码判断板块，应用涨跌幅限制
    // 主板（60/00 开头）：±10%；创业板/科创板（30/68 开头）：±20%；北交所（8/4 开头）：±30%
    const dailyLimitPct = stockCode ? getDailyLimit(stockCode) : 10;
    const maxAllowedDeviation = prevClose ? (prevClose * dailyLimitPct / 100) : Infinity;
    
    const yMin = prevClose ? prevClose - niceMaxDeviation : minPrice;
    const yMax = prevClose ? prevClose + niceMaxDeviation : maxPrice;
    
    // 右Y轴百分比范围：被截断时用 pctInterval 的整数倍确保 0 轴精确对齐
    let minPct: number, maxPct: number, pctInterval: number | undefined;
    if (niceMaxDeviation > maxAllowedDeviation) {
      // 被涨跌幅限制截断：直接用 dailyLimitPct/3 作为百分比间隔
      pctInterval = parseFloat((dailyLimitPct / 3).toFixed(2));
      minPct = -pctInterval * 3;
      maxPct = pctInterval * 3;
    } else {
      // 未被截断：从价格范围换算百分比，然后调整 minPct/maxPct 为 pctInterval 的整数倍，确保 0 轴精确对齐
      const rawMaxPct = prevClose && prevClose > 0 ? parseFloat((((yMax - prevClose) / prevClose) * 100).toFixed(2)) : 5;
      pctInterval = parseFloat((rawMaxPct / 3).toFixed(2));
      minPct = -pctInterval * 3;
      maxPct = pctInterval * 3;
    }
    
    // 最高/最低价在 Y 轴范围中的位置比例（0=底部，1=顶部），
    // 用于 markPoint 标签位置自适应，防止标签溢出图表边界被遮挡
    const yRange = yMax - yMin || 1;
    const highPosRatio = (trueHighPrice - yMin) / yRange;
    const lowPosRatio = (trueLowPrice - yMin) / yRange;



    // 非分时蜡烛图 tooltip（显示：日期、涨跌幅、开盘价、收盘价、最高价、最低价、成交量、成交额、换手率、MA5、MA10、MA30、MA60、MACD、DIF、DEA）
    const candlestickTooltipFormatter = (params: echarts.TopLevelFormatterParams) => {
      if (!params || params.length === 0) return '';
      const dataIndex = params[0]?.dataIndex;
      if (dataIndex === undefined || dataIndex < 0 || dataIndex >= data.length) return '';
      const point = data[dataIndex];
      const change = point.change_percent;
      const changeColor = getUpDownColor(change);
      const amountFormatted = formatAmount(point.amount);
      let html = `<div style="font-size:12px;color:#fff;line-height:1.8;min-width:180px;">`;
      html += `<div><span style="color:#aaa;">${labels.date}:</span> <span style="font-weight:bold;">${point.date}</span></div>`;
      html += `<div><span style="color:#aaa;">${labels.change}:</span> <span style="color:${changeColor};font-weight:bold;">${formatChange(change)}</span></div>`;
      html += `<div><span style="color:#aaa;">${labels.open}:</span> ${Number(point.open).toFixed(2)}</div>`;
      html += `<div><span style="color:#aaa;">${labels.close}:</span> <span style="color:${changeColor};font-weight:bold;">${Number(point.close).toFixed(2)}</span></div>`;
      html += `<div><span style="color:#aaa;">${labels.high}:</span> <span style="color:${STOCK_UP_COLOR};">${Number(point.high).toFixed(2)}</span></div>`;
      html += `<div><span style="color:#aaa;">${labels.low}:</span> <span style="color:${STOCK_DOWN_COLOR};">${Number(point.low).toFixed(2)}</span></div>`;
      html += `<div><span style="color:#aaa;">${labels.volume}:</span> ${formatVolume(point.volume)} 万手</div>`;
      html += `<div><span style="color:#aaa;">${labels.amount}:</span> ${amountFormatted.value} ${amountFormatted.unit}</div>`;
      if (point.turnover_rate !== null && point.turnover_rate !== undefined) {
        html += `<div><span style="color:#aaa;">${labels.turnoverRate}:</span> ${Number(point.turnover_rate).toFixed(2)}%</div>`;
      }
      const maValues = [
        { label: labels.ma5, value: ma5[dataIndex], color: colors.ma5Color },
        { label: labels.ma10, value: ma10[dataIndex], color: colors.ma10Color },
        { label: labels.ma30, value: ma30[dataIndex], color: colors.ma30Color },
        { label: labels.ma60, value: ma60[dataIndex], color: colors.ma60Color },
      ];
      for (const ma of maValues) {
        if (ma.value !== null && ma.value !== undefined) {
          html += `<div><span style="color:${ma.color};">●</span> <span style="color:${ma.color};">${ma.label}:</span> ${ma.value.toFixed(2)}</div>`;
        } else {
          html += `<div><span style="color:${ma.color};">●</span> <span style="color:${ma.color};">${ma.label}:</span> -</div>`;
        }
      }
      const macdVal = macd[dataIndex];
      const difVal = dif[dataIndex];
      const deaVal = dea[dataIndex];
      const macdColor = macdVal >= 0 ? colors.macdUpColor : colors.macdDownColor;
      html += `<div><span style="color:${macdColor};">●</span> <span style="color:${macdColor};">${labels.macd}:</span> ${macdVal.toFixed(2)}</div>`;
      html += `<div><span style="color:${colors.difColor};">●</span> <span style="color:${colors.difColor};">${labels.dif}:</span> ${difVal.toFixed(2)}</div>`;
      html += `<div><span style="color:${colors.deaColor};">●</span> <span style="color:${colors.deaColor};">${labels.dea}:</span> ${deaVal.toFixed(2)}</div>`;
      html += `</div>`;
      return html;
    };

    // ===== 分时图配置（period === '1m'） =====
    // 布局：3 个 grid（主图 62% + 成交量 24% + 时间轴 7%）
    // X 轴：3 个（主图/成交量/时间轴），时间轴不参与联动
    // Y 轴：4 个（左价格/右百分比/成交量/时间轴隐藏）
    // Series：分时折线面积图 + 均价线 + 成交量柱
    // 特殊：昨收基准线、11:30 午休分界线、四角最高/最低标注
    if (isIntraday) {
      // 生成完整的交易日时间轴
      const generateFullTimeAxis = (): string[] => {
        const fullTimes: string[] = [];
        // 获取数据中的日期部分
        const datePart = data.length > 0 ? data[0].date.split(' ')[0] : new Date().toISOString().split('T')[0];
        
        // 上午 09:30-11:30
        for (let h = 9; h <= 11; h++) {
          const startMin = h === 9 ? 30 : 0;
          const endMin = h === 11 ? 30 : 59;
          for (let m = startMin; m <= endMin; m++) {
            fullTimes.push(`${datePart} ${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:00`);
          }
        }
        // 下午 13:00-15:00
        for (let h = 13; h <= 15; h++) {
          const endMin = h === 15 ? 0 : 59;
          for (let m = 0; m <= endMin; m++) {
            fullTimes.push(`${datePart} ${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:00`);
          }
        }
        return fullTimes;
      };
      
      // 构建数据映射
      const dataMap = new Map<string, typeof data[0]>();
      data.forEach(d => dataMap.set(d.date, d));
      
      // 生成完整时间轴和对应的填充数据
      const fullDates = generateFullTimeAxis();
      const fullCloses: (number | null)[] = [];
      const fullVolumes: (number | null)[] = [];
      const fullAvgPriceLine: (number | null)[] = [];
      
      let cumAmount = 0;
      let cumVolume = 0;
      
      fullDates.forEach(timeStr => {
        const d = dataMap.get(timeStr);
        if (d) {
          fullCloses.push(d.close);
          fullVolumes.push(d.volume ?? 0);
          cumAmount += d.amount ?? 0;
          cumVolume += d.volume ?? 0;
          fullAvgPriceLine.push(cumVolume > 0 ? cumAmount / cumVolume : null);
        } else {
          fullCloses.push(null);
          fullVolumes.push(null);
          fullAvgPriceLine.push(null);
        }
      });
      
      const option = {
        animation: false,
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'cross' },
          backgroundColor: 'rgba(30, 30, 30, 0.92)',
          borderColor: '#555',
          borderWidth: 1,
          textStyle: { color: '#fff', fontSize: 12 },
          confine: true,
          formatter: (params: echarts.TopLevelFormatterParams) => {
            if (!params || params.length === 0) return '';
            const dataIndex = params[0]?.dataIndex;
            if (dataIndex === undefined || dataIndex < 0 || dataIndex >= fullDates.length) return '';
            const timeStr = fullDates[dataIndex];
            const d = dataMap.get(timeStr);
            if (!d) return '';
            
            const price = d.close;
            const pct = prevClose && prevClose > 0 ? ((price - prevClose) / prevClose) * 100 : 0;
            const avgP = fullAvgPriceLine[dataIndex];
            const pctColor = pct >= 0 ? colors.upColor : colors.downColor;
            const sign = pct >= 0 ? '+' : '';
            const amountFormatted = formatAmount(d.amount);
            
            let html = `<div style="font-size:12px;color:#fff;line-height:1.8;min-width:180px;">`;
            html += `<div><span style="color:#aaa;">${labels.date}:</span> <span style="font-weight:bold;">${timeStr}</span></div>`;
            html += `<div><span style="color:#aaa;">${labels.close}:</span> <span style="color:${pctColor};font-weight:bold;">${price.toFixed(2)}</span></div>`;
            html += `<div><span style="color:#aaa;">${labels.change}:</span> <span style="color:${pctColor};font-weight:bold;">${sign}${pct.toFixed(2)}%</span></div>`;
            if (avgP !== null) {
              html += `<div><span style="color:#FFB74D;">●</span> <span style="color:#FFB74D;">${labels.avgPrice}:</span> ${avgP.toFixed(2)}</div>`;
            }
            html += `<div><span style="color:#aaa;">${labels.volume}:</span> ${formatVolume(d.volume)} 万手</div>`;
            html += `<div><span style="color:#aaa;">${labels.amount}:</span> ${amountFormatted.value} ${amountFormatted.unit}</div>`;
            html += `</div>`;
            return html;
          },
        },
        axisPointer: {
          link: [{ xAxisIndex: [0, 1] }],
          label: { backgroundColor: '#777' },
        },
        // 分时模式：三行网格布局
        // [0] 主图区（62%）：分时折线 + 均价线 + 昨收基准线
        // [1] 成交量区（24%）：成交量柱状图，红涨绿跌
        // [2] 时间轴区（ 7%）：仅显示时间标签，不参与 axisPointer 联动
        grid: [
          { left: '6%', right: '6%', top: '2%', height: '66%' },    // [0] 分时主图
          { left: '6%', right: '6%', top: '70%', height: '20%' },   // [1] 成交量
          { left: '6%', right: '6%', top: '86%', height: '6%' },    // [2] 时间轴
        ],
      
        // X 轴：3 个分类轴，分别对应 3 个 grid
        // [0] 主图 X 轴：隐藏标签，显示 axisPointer 标签（时间）
        // [1] 成交量 X 轴：隐藏标签，axisPointer 标签显示成交额（formatAmount 格式化）
        // [2] 时间轴 X 轴：显示时间标签（HH:mm），自适应屏幕宽度（大屏 8 个，小屏 4 个）
        xAxis: [
          {
            type: 'category', data: fullDates, gridIndex: 0, axisLabel: { show: false },
            axisLine: { lineStyle: { color: colors.axisLineColor } }, splitLine: { show: false },
            axisPointer: { label: { backgroundColor: '#777' } },
          },
          {
            type: 'category', data: fullDates, gridIndex: 1, axisLabel: { show: false },
            axisLine: { lineStyle: { color: colors.axisLineColor } }, splitLine: { show: false },
            axisPointer: {
              label: {
                backgroundColor: '#777',
                formatter: (params: { value: string }) => {
                  const d = dataMap.get(params.value);
                  if (!d) return params.value;
                  const amt = formatAmount(d.amount);
                  return `${amt.value} ${amt.unit}`;
                },
              },
            },
          },
          {
            type: 'category', data: fullDates, gridIndex: 2,
            axisLabel: {
              color: colors.textColor, fontSize: 11,
              formatter: (value: string) => {
                const timePart = value.split(' ')[1];
                if (!timePart) return value;
                const [h, m] = timePart.split(':');
                return `${h}:${m}`;
              },
              interval: (index: number) => {
                const total = fullDates.length;
                const labelCount = isSmallScreen ? 4 : 8;
                const step = Math.max(1, Math.floor(total / labelCount));
                return index % step === 0 || index === total - 1;
              },
            },
            axisTick: { show: true, alignWithLabel: true, lineStyle: { color: colors.axisLineColor }, length: 4 },
            axisLine: { lineStyle: { color: colors.axisLineColor } },
            splitLine: { show: false },
          },
        ],
        yAxis: [
          // [0] 左Y轴：绝对价格（正红负绿颜色区分 + 最大值/最小值标记）
          {
            scale: true, gridIndex: 0, position: 'left',
            min: yMin,
            max: yMax,
            interval: niceInterval,
            splitArea: { show: false },
            axisLine: { show: false }, axisTick: { show: false },
            splitLine: { lineStyle: { color: colors.splitLineColor, type: 'dashed' } },
            axisLabel: {
              color: colors.textColor, fontSize: 11,
              formatter: (v: number) => {
                if (prevClose && prevClose > 0) {
                  const pct = ((v - prevClose) / prevClose) * 100;
                  // 浮点精度容差：接近 0 的值视为 0
                  if (Math.abs(pct) < 0.005) return `{zero|${v.toFixed(2)}}`;
                  if (pct > 0) return `{up|${v.toFixed(2)}}`;
                  return `{down|${v.toFixed(2)}}`;
                }
                return v.toFixed(2);
              },
              rich: {
                up: { color: STOCK_UP_COLOR, fontWeight: 'bold', fontSize: 11 },
                down: { color: STOCK_DOWN_COLOR, fontWeight: 'bold', fontSize: 11 },
                zero: { color: '#999999', fontWeight: 'bold', fontSize: 11 },
              },
            },
          },
          // [1] 右Y轴：涨跌幅百分比（正红负绿 + 最大值/最小值标记）
          {
            scale: true, gridIndex: 0, position: 'right',
            min: minPct,
            max: maxPct,
            interval: prevClose && prevClose > 0 ? (pctInterval ?? parseFloat((((niceInterval / prevClose) * 100).toFixed(2)))) : undefined,
            splitArea: { show: false },
            axisLine: { show: false }, axisTick: { show: false },
            splitLine: { show: false },
            axisLabel: {
              color: colors.textColor, fontSize: 11,
              formatter: (v: number) => {
                // 浮点精度容差：接近 0 的值视为 0（避免显示 0.01% 且标红）
                if (Math.abs(v) < 0.005) return `{zero|0.00%}`;
                if (v > 0) return `{up|${v.toFixed(2)}%}`;
                return `{down|${v.toFixed(2)}%}`;
              },
              rich: {
                up: { color: STOCK_UP_COLOR, fontWeight: 'bold', fontSize: 11 },
                down: { color: STOCK_DOWN_COLOR, fontWeight: 'bold', fontSize: 11 },
                zero: { color: '#999999', fontWeight: 'bold', fontSize: 11 },
              },
            },
          },
          // [2] 成交量Y轴
          {
            scale: true, gridIndex: 1, splitNumber: 2,
            axisLabel: { show: false }, axisLine: { show: false }, axisTick: { show: false },
            splitLine: { show: false },
          },
          // [3] 时间轴 Y 轴（gridIndex:2）：完全隐藏
          { gridIndex: 2, show: false },
        ],
        dataZoom: [],  // 分时模式无缩放
        // 四角标注：用 graphic 组件在图表四角放置文字，不随缩放变化
        // 左上：最高价（红）  左下：最低价（绿）
        // 右上：最大涨幅（红）  右下：最大跌幅（绿）
        graphic: [
        
        ],
        // Series：3 个系列
        // [0] 分时折线面积图：蓝色渐变填充，connectNulls 连接午休空缺
        // [1] 均价线：橙色，累计成交额/累计成交量
        // [2] 成交量柱：红涨绿跌，绑定成交量 grid
        series: [
          {
            name: labels.close,
            type: 'line',
            data: fullCloses,
            smooth: true,
            showSymbol: false,
            symbolSize: 0,
            lineStyle: { width: 1.5, color: '#42A5F5' },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(66, 165, 245, 0.35)' },
                { offset: 1, color: 'rgba(66, 165, 245, 0.02)' },
              ]),
            },
            xAxisIndex: 0,
            yAxisIndex: 0,
            connectNulls: true,  // 连接 null 值，保持数据连续
            // 当日真实最高/最低价格标注点（盘口极值，包含集合竞价）
            // 标签位置自适应：最高价接近 Y 轴顶部时标签放到点下方，
            // 最低价接近 Y 轴底部时标签放到点上方，避免标签溢出图表边界被遮挡
            markPoint: {
              symbol: 'circle',
              symbolSize: 6,
              zlevel: 6, // 提高层级，避免被K线遮挡
              data: [
                {
                  name: labels.high,
                  value: trueHighPrice,
                  coord: [getSafeTimeIndex(trueHighTime, fullDates), trueHighPrice],
                  itemStyle: { color: STOCK_UP_COLOR },
                  label: getMarkLabelConfig(STOCK_UP_COLOR, highPosRatio > 0.8 ? 'bottom' : 'top'),
                },
                {
                  name: labels.low,
                  value: trueLowPrice,
                  coord: [getSafeTimeIndex(trueLowTime, fullDates), trueLowPrice],
                  itemStyle: { color: STOCK_DOWN_COLOR },
                  label: getMarkLabelConfig(STOCK_DOWN_COLOR, lowPosRatio < 0.2 ? 'top' : 'bottom'),
                },
              ],
            },
            // 昨收价基准线（0.00%位置）+ 交易时段标记
            markLine: {
              silent: true,
              symbol: 'none',
              lineStyle: { type: 'dashed', width: 1 },
              data: [
                // 昨收价基准线（水平虚线）
                {
                  yAxis: prevClose ?? (data[0]?.close ?? 0),
                  lineStyle: { color: '#999', type: 'dashed' },
                  label: { show: false },
                },
                // 11:30 午休分界线（有且只有一条）
                {
                  xAxis: fullDates.findIndex((d) => d.includes('11:30')),
                  lineStyle: { color: colors.axisLineColor, type: 'dotted', width: 1 },
                  label: { show: false },
                },
              ],
            },
          },
          // 均价线（橙色）
          {
            name: labels.avgPrice,
            type: 'line',
            data: fullAvgPriceLine,
            smooth: true,
            showSymbol: false,
            symbolSize: 0,
            lineStyle: { width: 1.5, color: '#FFB74D' },
            xAxisIndex: 0,
            yAxisIndex: 0,
            connectNulls: true,  // 连接 null 值，保持数据连续
          },
          // 成交量
          {
            name: labels.volume,
            type: 'bar',
            data: fullVolumes.map((v, i) => {
              const timeStr = fullDates[i];
              const d = dataMap.get(timeStr);
              let color = '#ccc';
              if (d) {
                const prevIdx = data.findIndex(x => x.date === d.date) - 1;
                if (prevIdx >= 0) {
                  color = d.close >= data[prevIdx].close ? colors.upColor : colors.downColor;
                } else {
                  color = colors.upColor;
                }
              }
              return {
                value: v,
                itemStyle: { color: v !== null ? color : 'transparent' },
              };
            }),
            xAxisIndex: 1,
            yAxisIndex: 2,
          },
        ],
      };
      chart.setOption(option, true);
    } else {
      // 非分时图配置（日 K/周 K/月 K/年 K/5m~120m）
      // 布局：4 个 grid（K 线主图 48% + 时间轴 6% + 成交量 12% + MACD 12%）
      // X 轴：4 个（主图/时间轴/成交量/MACD），K 线 + 成交量联动，MACD+ 时间轴不联动
      // Y 轴：4 个（主图价格/时间轴隐藏/成交量万手/MACD）
      // Series：蜡烛图 + MA5/10/30/60 + 成交量柱 + DIF/DEA 线 + MACD 柱
      // dataZoom：inside（鼠标滚轮）+ slider（底部滑块），联动所有 4 个 X 轴
      // 分钟线额外添加 11:30/13:00 交易时段分割线
      //
      // 初始可见范围计算：
      // - 默认模式：dzStart 按 PERIOD_VISIBLE_BARS 计算，只显示最近 N 根
      // - 全量数据模式（showAllData=true）：dzStart=0，显示从上市至今所有数据
      //   但初始视图仍按 visibleBars 计算，用户可通过滑块浏览更早数据
      const totalBars = data.length;
      const dzStart = totalBars > visibleBars
        ? ((totalBars - visibleBars) / totalBars) * 100
        : 0;
      const option = {
        animation: false,
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'cross' },
          backgroundColor: 'rgba(30, 30, 30, 0.92)',
          borderColor: '#555',
          borderWidth: 1,
          textStyle: { color: '#fff', fontSize: 12 },
          confine: true,
          formatter: candlestickTooltipFormatter,
        },
        axisPointer: {
          link: [{ xAxisIndex: [0, 2] }],
          label: { backgroundColor: '#777' },
        },
        // 非分时模式：四行网格布局（视觉顺序：K线主图 → 时间轴 → 成交量 → MACD）
        // [0] K线主图区（48%）：蜡烛图 + MA 均线
        // [3] 时间轴区（ 6%）：仅显示时间标签，不参与联动（视觉上紧跟主图）
        // [1] 成交量区（12%）：成交量柱状图，红涨绿跌
        // [2] MACD 区（12%）：DIF/DEA 线 + MACD 柱
        grid: [
          { left: '6%', right: '6%', top: '2%', height: '48%' },    // [0] K线主图
          { left: '6%', right: '6%', top: '52%', height: '6%' },    // [3] 时间轴（视觉第二行）
          { left: '6%', right: '6%', top: '66%', height: '12%' },   // [1] 成交量（视觉第三行）
          { left: '6%', right: '6%', top: '82%', height: '8%' },   // [2] MACD（视觉第四行）
        ],
        // X 轴：4 个分类轴，分别对应 4 个 grid
        // [0] 主图 X 轴：隐藏标签，axisPointer 标签显示时间
        // [1] 时间轴 X 轴：显示日期标签，自适应密度（根据缩放后可见数据点数）
        // [2] 成交量 X 轴：隐藏标签，axisPointer 标签显示成交额
        // [3] MACD X 轴：隐藏标签，axisPointer 标签隐藏
        xAxis: [
          {
            type: 'category', data: dates, gridIndex: 0, axisLabel: { show: false },
            axisLine: { lineStyle: { color: colors.axisLineColor } }, splitLine: { show: false },
            axisPointer: { label: { backgroundColor: '#777' } },
          },
          {
            type: 'category', data: dates, gridIndex: 1,
            axisLabel: {
              color: colors.textColor, fontSize: 11,
              formatter: timeAxisFormatter,
              interval: ((index: number) => {
                // 使用预计算的标签索引集合（O(1) 查找）
                // labelIndicesRef 由 recomputeLabelIndices() 在数据/缩放变化时更新
                return labelIndicesRef.current.has(index);
              }) as (index: number) => boolean,
            },
            axisTick: { show: true, alignWithLabel: true, lineStyle: { color: colors.axisLineColor }, length: 8 },
            axisLine: { lineStyle: { color: colors.axisLineColor } },
            splitLine: { show: false },
          },
          {
            type: 'category', data: dates, gridIndex: 2, axisLabel: { show: false },
            axisLine: { lineStyle: { color: colors.axisLineColor } }, splitLine: { show: false },
            axisPointer: {
              label: {
                backgroundColor: '#777',
                formatter: (params: { value: string }) => {
                  const idx = params.value ? dates.indexOf(params.value) : -1;
                  if (idx < 0 || idx >= data.length) return params.value;
                  const amt = formatAmount(data[idx].amount);
                  return `${amt.value} ${amt.unit}`;
                },
              },
            },
          },
          {
            type: 'category', data: dates, gridIndex: 3, axisLabel: { show: false },
            axisLine: { lineStyle: { color: colors.axisLineColor } }, splitLine: { show: false },
            axisPointer: { label: { show: false } },
          },
        ],
        // Y 轴：4 个，按 gridIndex 顺序排列
        // [0] 主图 Y 轴（gridIndex:0）：价格刻度，虚线分割
        // [1] 时间轴 Y 轴（gridIndex:1）：完全隐藏
        // [2] 成交量 Y 轴（gridIndex:2）：显示刻度标签，单位自动转换为万/亿
        // [3] MACD Y 轴（gridIndex:3）：数值刻度，无分割线
        yAxis: [
          { scale: true, gridIndex: 0, splitArea: { show: false }, axisLine: { show: false }, axisTick: { show: false }, splitLine: { lineStyle: { color: colors.splitLineColor } }, axisLabel: { color: colors.textColor, fontSize: 11 } },
          // [1] 时间轴 Y 轴（隐藏）
          { gridIndex: 1, show: false },
          // [2] 成交量 Y 轴：显示刻度，单位自动转换为万/亿
          { 
            scale: true, gridIndex: 2, splitNumber: 2, 
            axisLabel: { 
              show: true, 
              color: colors.textColor, 
              fontSize: 10,
              formatter: (v: number) => {
                if (v === 0) return '0';
                const vInWan = v / 10000;
                if (vInWan >= 10000) {
                  return `${(vInWan / 10000).toFixed(1)}亿`;
                }
                return `${vInWan.toFixed(0)}万`;
              },
            },
            axisLine: { show: false }, 
            axisTick: { show: false }, 
            splitLine: { show: false },
          },
          { scale: true, gridIndex: 3, splitNumber: 2, axisLabel: { color: colors.textColor, fontSize: 10 }, axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: false } },  // [3] MACD Y 轴
        ],
        // dataZoom：缩放控制器，联动所有 4 个 X 轴
        // [0] inside：鼠标滚轮/触摸板双指缩放
        // [1] slider：底部滑块条，可拖拽平移，橙色填充区域
        dataZoom: [
          { type: 'inside', xAxisIndex: [0, 1, 2, 3], start: dzStart, end: 100 },
          {
            type: 'slider', xAxisIndex: [0, 1, 2, 3],
            top: '92%', height: 28, start: dzStart, end: 100,  // [4] 滑块，紧跟在时间轴下面
            textStyle: { color: colors.textColor, fontSize: 11 },
            borderColor: colors.axisLineColor,
            fillerColor: 'rgba(0, 212, 255, 0.15)',
            handleStyle: { color: '#00d4ff', borderWidth: 2, width: 10, height: 26 },
            moveHandleSize: 8, showDetail: false,
          },
        ],
        // Series：9 个系列，分别绑定到不同的 grid / xAxis / yAxis
        // [0] 蜡烛图（candlestick）：K 线主图，红涨绿跌，分钟线带午休分割线
        // [1-4] MA 均线（line）：MA5/MA10/MA30/MA60，绑定主图 grid
        // [5] 成交量柱（bar）：绑定成交量 grid，红涨绿跌，分钟线带午休分割线
        // [6-7] DIF/DEA 线（line）：绑定 MACD grid
        // [8] MACD 柱（bar）：绑定 MACD grid，红涨绿跌，分钟线带午休分割线
        series: [
          // [0] K 线蜡烛图
          {
            name: 'kline',
            type: 'candlestick',
            data: klineData,
            itemStyle: { color: colors.upColor, color0: colors.downColor, borderColor: colors.upColor, borderColor0: colors.downColor },
            xAxisIndex: 0, yAxisIndex: 0,
            // 分钟线添加交易时段分割线
            markLine: isMinuteLine
              ? {
                  silent: true,
                  symbol: 'none',
                  lineStyle: { type: 'dashed', width: 1, color: '#ccc' },
                  data: [
                    // 11:30 午休分界线（仅在找到有效索引时添加）
                    ...(midday1130Index !== -1
                      ? [
                          {
                            xAxis: midday1130Index,
                            lineStyle: { color: '#ccc', type: 'dashed', width: 1 },
                            label: { show: true, position: 'end', formatter: '11:30', color: colors.textColor, fontSize: 10 },
                          },
                        ]
                      : []),
                    // 13:00 午休分界线（仅在找到有效索引时添加）
                    ...(midday1300Index !== -1
                      ? [
                          {
                            xAxis: midday1300Index,
                            lineStyle: { color: '#ccc', type: 'dashed', width: 1 },
                            label: { show: true, position: 'start', formatter: '13:00', color: colors.textColor, fontSize: 10 },
                          },
                        ]
                      : []),
                  ],
                }
              : undefined,
          },
          { name: labels.ma5, type: 'line', data: ma5, smooth: true, showSymbol: false, lineStyle: { width: 1.5, color: colors.ma5Color }, xAxisIndex: 0, yAxisIndex: 0 },
          { name: labels.ma10, type: 'line', data: ma10, smooth: true, showSymbol: false, lineStyle: { width: 1.5, color: colors.ma10Color }, xAxisIndex: 0, yAxisIndex: 0 },
          { name: labels.ma30, type: 'line', data: ma30, smooth: true, showSymbol: false, lineStyle: { width: 1.5, color: colors.ma30Color }, xAxisIndex: 0, yAxisIndex: 0 },
          { name: labels.ma60, type: 'line', data: ma60, smooth: true, showSymbol: false, lineStyle: { width: 1.5, color: colors.ma60Color }, xAxisIndex: 0, yAxisIndex: 0 },
          {
            name: labels.volume, type: 'bar',
            data: volumes.map((v, i) => ({ value: v, itemStyle: { color: volumeColors[i] } })),
            xAxisIndex: 2, yAxisIndex: 2,
            // 分钟线添加交易时段分割线
            markLine: isMinuteLine
              ? {
                  silent: true,
                  symbol: 'none',
                  lineStyle: { type: 'dashed', width: 1, color: '#ccc' },
                  data: [
                    // 11:30 午休分界线（仅在找到有效索引时添加）
                    ...(midday1130Index !== -1
                      ? [
                          {
                            xAxis: midday1130Index,
                            lineStyle: { color: '#ccc', type: 'dashed', width: 1 },
                            label: { show: false },
                          },
                        ]
                      : []),
                    // 13:00 午休分界线（仅在找到有效索引时添加）
                    ...(midday1300Index !== -1
                      ? [
                          {
                            xAxis: midday1300Index,
                            lineStyle: { color: '#ccc', type: 'dashed', width: 1 },
                            label: { show: false },
                          },
                        ]
                      : []),
                  ],
                }
              : undefined,
          },
          { name: labels.dif, type: 'line', data: dif, smooth: true, showSymbol: false, lineStyle: { width: 1, color: colors.difColor }, xAxisIndex: 3, yAxisIndex: 3 },
          { name: labels.dea, type: 'line', data: dea, smooth: true, showSymbol: false, lineStyle: { width: 1, color: colors.deaColor }, xAxisIndex: 3, yAxisIndex: 3 },
          {
            name: labels.macd, type: 'bar',
            data: macd.map((v, i) => ({ value: v, itemStyle: { color: macdColors[i] } })),
            xAxisIndex: 3, yAxisIndex: 3,
            // 分钟线添加交易时段分割线
            markLine: isMinuteLine
              ? {
                  silent: true,
                  symbol: 'none',
                  lineStyle: { type: 'dashed', width: 1, color: '#ccc' },
                  data: [
                    // 11:30 午休分界线（仅在找到有效索引时添加）
                    ...(midday1130Index !== -1
                      ? [
                          {
                            xAxis: midday1130Index,
                            lineStyle: { color: '#ccc', type: 'dashed', width: 1 },
                            label: { show: false },
                          },
                        ]
                      : []),
                    // 13:00 午休分界线（仅在找到有效索引时添加）
                    ...(midday1300Index !== -1
                      ? [
                          {
                            xAxis: midday1300Index,
                            lineStyle: { color: '#ccc', type: 'dashed', width: 1 },
                            label: { show: false },
                          },
                        ]
                      : []),
                  ],
                }
              : undefined,
          },
        ],
      };
      chart.setOption(option, true);

      // 非分时模式：监听 dataZoom 事件
      // 防止 setOption 触发的 dataZoom 事件导致无限循环
      let isProgrammaticZoom = false;
      const handleDataZoom = (params: echarts.ECElementEvent) => {
        if (isProgrammaticZoom) return;

        // 兼容 batch 形式（inside+slider 联动）和单组件形式的 dataZoom 事件
        const batch = params.batch && params.batch[0];
        const start = batch ? (batch.start ?? 0) : (params.start ?? 0);
        const end = batch ? (batch.end ?? 100) : (params.end ?? 100);

        // 更新可见范围 refs（interval 函数据此选取标签）
        const count = Math.round(data.length * (end - start) / 100);
        visibleCountRef.current = Math.max(1, count);
        visibleStartRef.current = Math.round(data.length * start / 100);

        // 重新计算标签索引并强制重渲染
        // 注：ECharts 缩放时不会自动重新调用 interval 回调，需要手动触发
        recomputeLabelIndices();

        // 强制重渲染：通过 setOption({}) 触发 ECharts 重新评估 interval 函数
        // isProgrammaticZoom 防止 setOption 触发的 dataZoom 事件导致无限循环
        isProgrammaticZoom = true;
        chart.setOption({});
        isProgrammaticZoom = false;

        // 当拖动到左边界 5% 以内时，触发分页加载
        if (start <= 5 && onDataZoomBoundary) {
          onDataZoomBoundary();
        }
      };
      chart.on('dataZoom', handleDataZoom);

      const handleResize = () => chart.resize();
      window.addEventListener('resize', handleResize);

      return () => {
        chart.off('dataZoom', handleDataZoom);
        window.removeEventListener('resize', handleResize);
      };
    }

    // 分时模式：只需监听 resize
    const handleResize = () => chart.resize();
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [
    data,
    period,
    getThemeColorsLocal,
    t,
    language,
    windowWidth,
    isSmallScreen,
    prevClose,
    showAllData,
    onDataZoomBoundary,
    recomputeLabelIndices,
    stockCode,
    visibleBars,
  ]);

  /** 图表容器：ECharts 渲染目标，圆角卡片样式 */
  return (
    <div
      ref={chartRef}
      style={{ width: '100%', height }}
      className="rounded-lg border border-subtle bg-card"
    />
  );
};

export default KLineChart;
