/**
 * 全局颜色常量
 * 股票分析系统统一配色方案，所有前端组件应引用此处定义的颜色
 */

// ==========================================
// 股票涨跌颜色（红涨绿跌）
// ==========================================

/** 上涨颜色（红色） */
export const STOCK_UP_COLOR = '#ef5350';

/** 下跌颜色（绿色） */
export const STOCK_DOWN_COLOR = '#26a69a';

/** 平盘颜色（灰色） */
export const STOCK_FLAT_COLOR = '#999999';

// ==========================================
// K 线图技术指标颜色
// ==========================================

/** MA5 均线颜色（橙色） */
export const MA5_COLOR = '#FFB74D';

/** MA10 均线颜色（紫色） */
export const MA10_COLOR = '#AB47BC';

/** MA30 均线颜色（蓝色） */
export const MA30_COLOR = '#42A5F5';

/** MA60 均线颜色（绿色） */
export const MA60_COLOR = '#66BB6A';

/** DIF 线颜色（蓝色） */
export const DIF_COLOR = '#42A5F5';

/** DEA 线颜色（橙色） */
export const DEA_COLOR = '#FFB74D';

/** MACD 上涨柱颜色（红色） */
export const MACD_UP_COLOR = '#ef5350';

/** MACD 下跌柱颜色（绿色） */
export const MACD_DOWN_COLOR = '#26a69a';

// ==========================================
// 主题适配颜色
// ==========================================

export interface ThemeColors {
  /** 上涨颜色 */
  upColor: string;
  /** 下跌颜色 */
  downColor: string;
  /** MA5 颜色 */
  ma5Color: string;
  /** MA10 颜色 */
  ma10Color: string;
  /** MA30 颜色 */
  ma30Color: string;
  /** MA60 颜色 */
  ma60Color: string;
  /** DIF 颜色 */
  difColor: string;
  /** DEA 颜色 */
  deaColor: string;
  /** MACD 上涨颜色 */
  macdUpColor: string;
  /** MACD 下跌颜色 */
  macdDownColor: string;
  /** 文字颜色 */
  textColor: string;
  /** 轴线颜色 */
  axisLineColor: string;
  /** 分割线颜色 */
  splitLineColor: string;
}

/** 获取当前主题对应的图表颜色配置 */
export function getThemeColors(): ThemeColors {
  const isDark = document.documentElement.classList.contains('dark');
  return {
    upColor: STOCK_UP_COLOR,
    downColor: STOCK_DOWN_COLOR,
    ma5Color: MA5_COLOR,
    ma10Color: MA10_COLOR,
    ma30Color: MA30_COLOR,
    ma60Color: MA60_COLOR,
    difColor: DIF_COLOR,
    deaColor: DEA_COLOR,
    macdUpColor: MACD_UP_COLOR,
    macdDownColor: MACD_DOWN_COLOR,
    textColor: isDark ? '#e0e0e0' : '#333333',
    axisLineColor: isDark ? '#555555' : '#cccccc',
    splitLineColor: isDark ? '#333333' : '#eeeeee',
  };
}

/** 根据涨跌值获取颜色 */
export function getKChangeColor(change: number): string {
  if (change > 0) return STOCK_UP_COLOR;
  if (change < 0) return STOCK_DOWN_COLOR;
  return STOCK_FLAT_COLOR;
}
