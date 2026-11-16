/**
 * @file stockColor.ts
 * @description 全局图表配色常量：股票涨跌色、K 线均线与 MACD 指标色，以及随主题切换的适配色。
 * 供 K 线图（KLineView/KLineChart/StockInfoHeader）、板块图表与股票卡片等组件统一引用。
 * @author Lensgcx (GaoCangxiong)
 */

// 股票涨跌颜色（A 股习惯：红涨绿跌）
/** 上涨颜色（红色） */
export const STOCK_UP_COLOR = '#ef5350';

/** 下跌颜色（绿色） */
export const STOCK_DOWN_COLOR = '#26a69a';

/** 平盘颜色（灰色） */
export const STOCK_FLAT_COLOR = '#999999';

// K 线技术指标颜色
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

// 主题适配颜色
/**
 * 主题适配后的图表配色集合：涨跌与指标色取全局常量，文字/轴线/分割线色随浅/深主题切换。
 */
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

/**
 * 读取当前主题下的图表配色。
 * @returns 涨跌/指标色取全局常量，文字/轴线/分割线色依据 document 是否含 dark 类切换
 */
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
