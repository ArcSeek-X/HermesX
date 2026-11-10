/**
 * @file pages/Stock/StockMetricViewPage/components/stockMetricViewColumns.tsx
 * @description 股票度量视图的列定义（前端唯一真源）：业务列逐列显式声明，单元格渲染抽为命名函数。
 * 列顺序、列宽、值格式化、对齐方式、固定列、按市场可见性、导出列顺序全部由本文件派生。
 * @author Lensgcx (GaoCangxiong)
 */

import type React from 'react';
import { Chip } from '@components';
import type { TableColumnDef } from '@components/basic/Table/Table';
import type { UiTextKey } from '@/i18n/uiText';
import type {
  StockMetricViewRow,
  StockMetricViewSupportedMarket,
} from '@/types/stockMetricView';
import { getChangeColorClass } from '@utils/format';
import { normalizeStockCode } from '@utils/stock/stockCode';

/** UI 文案函数签名（与 UiLanguageContext.t 一致） */
type StockMetricViewTranslate = (key: UiTextKey, params?: Record<string, string | number>) => string;

/** 数值列格式化类别：决定单元格呈现形态与是否带原币单位 */
type StockMetricViewValueFormat = 'decimal' | 'currency' | 'pct' | 'money' | 'compact' | 'rating';

/** 无值占位：null / 空串统一显示 —，与 0 语义分离 */
const STOCK_METRIC_VIEW_EMPTY_TEXT = '—';

/** 市场展示真源：国旗、本地化名称、原币代码（金额不折算，按原币展示） */
const STOCK_METRIC_VIEW_MARKET: Record<
  StockMetricViewSupportedMarket,
  { flag: string; labelKey: UiTextKey; currency: string }
> = {
  cn: { flag: '🇨🇳', labelKey: 'stockMetricView.market.cn', currency: 'CNY' },
  hk: { flag: '🇭🇰', labelKey: 'stockMetricView.market.hk', currency: 'HKD' },
  us: { flag: '🇺🇸', labelKey: 'stockMetricView.market.us', currency: 'USD' },
};

const ALL_STOCK_METRIC_VIEW_MARKETS: StockMetricViewSupportedMarket[] = ['cn', 'hk', 'us'];
const CN_STOCK_METRIC_VIEW_MARKETS: StockMetricViewSupportedMarket[] = ['cn'];

/**
 * 列定义辅助字段：markets 只供 buildStockMetricViewColumns 按所选市场裁剪，
 * 不进入 Table 的渲染契约（Table 仅消费 TableColumnDef 声明的字段）。
 */
interface StockMetricViewColumnDef extends TableColumnDef<StockMetricViewRow> {
  /** 有数据的市场；某市场不在其中则整列对该市场隐藏 */
  markets: StockMetricViewSupportedMarket[];
}

/**
 * 生成个股 K 线页直达路径（统一跳转协议 `?stockCode=`，见 jump2Kline.md §2）。
 * 代码归一化复用 utils/stock/stockCode 的 normalizeStockCode（项目统一真源，§2.2 推荐复用），
 * 可覆盖 SH/SZ/BJ 前缀、.SH/.SZ/.HK 后缀等写法，不再用 split('.')[0] 自行裁剪；
 * 归一后再编码，跳转方与链接 href 共用此真源。
 */
export function buildStockKlinePath(code: string): string {
  return `/stock/kline?stockCode=${encodeURIComponent(normalizeStockCode(code))}`;
}

/** 固定两位小数 + 千分位 */
function formatStockMetricDecimal(value: number): string {
  return value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/** 大数紧凑展示：>=1亿 用亿、>=1万 用万，否则千分位 */
function formatStockMetricCompactNumber(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1e8) return `${(value / 1e8).toFixed(2)}亿`;
  if (abs >= 1e4) return `${(value / 1e4).toFixed(2)}万`;
  return formatStockMetricDecimal(value);
}

/**
 * 按列格式化类别生成数值文本；null 一律渲染 —（不渲染 0、不估算）。
 * 原币单位由 renderStockMetricNumberCell 以小字号单独渲染，不拼进本函数的返回值。
 * 口径与 utils/format.ts 的 formatPercent / formatAmount / formatPricePoint 不同：本页百分比不带正号、
 * 空值用 — 而非 --、金额按万 / 亿自适应、小额保留千分位并带原币后缀，故不复用通用函数，
 * 仅共用涨跌色 getChangeColorClass。
 */
function formatStockMetricValue(value: number | null, format: StockMetricViewValueFormat): string {
  if (value == null) return STOCK_METRIC_VIEW_EMPTY_TEXT;
  switch (format) {
    case 'pct':
      return `${value.toFixed(2)}%`;
    case 'decimal':
      return formatStockMetricDecimal(value);
    case 'currency':
      return formatStockMetricDecimal(value);
    case 'money':
      return formatStockMetricCompactNumber(value);
    case 'compact':
      return formatStockMetricCompactNumber(value);
    case 'rating':
      return `${value} / 5`;
    default:
      return String(value);
  }
}

/** 市场原币代码：原币计价列共用，市场缺失时留空而不臆造币种 */
function getStockMetricViewCurrency(market: StockMetricViewSupportedMarket): string {
  return STOCK_METRIC_VIEW_MARKET[market]?.currency ?? '';
}

/** 原币单位字号：比单元格数值小一号，避免与数值抢视觉层级 */
const STOCK_METRIC_VIEW_CURRENCY_CLASS = 'text-[10px]';

/** 需要附原币单位的格式化类别：股价 / 每股收益 / 总市值按原币计价 */
function stockMetricViewNeedsCurrency(format: StockMetricViewValueFormat): boolean {
  return format === 'currency' || format === 'money';
}

/** 渲染：数值单元格按格式化类别展示，原币单位用小一号字；null 只显示 — 且不附带单位 */
function renderStockMetricNumberCell(
  value: number | null,
  format: StockMetricViewValueFormat,
  market: StockMetricViewSupportedMarket,
): React.ReactNode {
  const formatted = formatStockMetricValue(value, format);
  if (value == null || !stockMetricViewNeedsCurrency(format)) return formatted;
  const currency = getStockMetricViewCurrency(market);
  if (!currency) return formatted;
  return (
    <>
      {formatted}{' '}
      <span className={STOCK_METRIC_VIEW_CURRENCY_CLASS}>{currency}</span>
    </>
  );
}

/** 渲染：涨跌幅按全站规范着色（A 股红涨绿跌）；0 / 空值由 getChangeColorClass 统一置灰 */
function renderStockMetricChangePctCell(value: number | null): React.ReactNode {
  return <span className={getChangeColorClass(value)}>{formatStockMetricValue(value, 'pct')}</span>;
}

/** 渲染：所属板块 Chip，无值显示 — */
function renderStockMetricIndustryCell(industry: string | null | undefined): React.ReactNode {
  return industry == null || industry === ''
    ? STOCK_METRIC_VIEW_EMPTY_TEXT
    : <Chip size="xs" variant="primary" color="default" className="whitespace-nowrap">{industry}</Chip>;
}

/** 市场单元格：仅展示放大的国旗，市场名保留在 title / aria-label 中 */
function renderStockMetricMarketCell(
  market: StockMetricViewSupportedMarket,
  t: StockMetricViewTranslate,
): React.ReactNode {
  const display = STOCK_METRIC_VIEW_MARKET[market];
  if (!display) return STOCK_METRIC_VIEW_EMPTY_TEXT;
  const label = t(display.labelKey);
  return (
    <span className="inline-flex items-center justify-center" title={label} aria-label={label}>
      <span className="text-xl leading-none" aria-hidden="true">{display.flag}</span>
    </span>
  );
}

/** 代码 / 名称两列、cn / hk / us 三市场共用的标识样式：加粗 + 主题色 */
const STOCK_METRIC_VIEW_IDENTITY_CLASS = 'font-semibold text-primary';

/**
 * 代码 / 名称共用的 K 线跳转单元格：一期仅 A 股可跳转，其他市场渲染纯文本。
 * 是否可跳转不改变视觉层级，两列三市场一律使用同一套加粗主题色样式。
 */
function renderStockMetricKlineCell(
  row: StockMetricViewRow,
  label: React.ReactNode,
  t: StockMetricViewTranslate,
  onOpenKline: (row: StockMetricViewRow) => void,
): React.ReactNode {
  if (row.market !== 'cn') {
    return <span className={STOCK_METRIC_VIEW_IDENTITY_CLASS} title={t('stockMetricView.klineOnlyCn')}>{label}</span>;
  }
  return (
    <a
      href={buildStockKlinePath(row.code)}
      title={t('stockMetricView.openKline')}
      className={`cursor-pointer hover:underline ${STOCK_METRIC_VIEW_IDENTITY_CLASS}`}
      onClick={(event) => {
        event.preventDefault();
        onOpenKline(row);
      }}
    >
      {label}
    </a>
  );
}

/** 列构建入参：语言函数、当前所选市场（单选）、代码 / 名称列点击回调 */
export interface StockMetricViewColumnOptions {
  t: StockMetricViewTranslate;
  selectedMarket: StockMetricViewSupportedMarket;
  onOpenKline: (row: StockMetricViewRow) => void;
}

/**
 * 构建当前市场可见的业务列（序号列由表格组件另行置于首位）。
 * 单一真源同时服务表格渲染与 CSV 导出的列顺序 / 本地化表头（AC-7）。
 * 列定义逐项写全，暂不做工厂化收敛；单元格渲染统一引用上方命名函数。
 */
export function buildStockMetricViewColumns({
  t,
  selectedMarket,
  onOpenKline,
}: StockMetricViewColumnOptions): TableColumnDef<StockMetricViewRow>[] {
  /**
   * 一期固定 13 个业务列 + 首列市场标识。epsGrowthTtmYoyPct / analystRating 为 cn
   * 季频离线因子，hk / us 选择时整列隐藏（见下方 markets 裁剪）。
   * 序号、涨跌幅、量比、市盈率、股息率按「内容刚好显示」取紧凑宽度：列头与单元格
   * 默认 px-4（左右合计 32px），其余空间容纳中文列头与典型数值，不再预留额外留白。
   * 前 4 列（序号、市场、代码、名称）设为左侧固定列，横向滚动时保持股票标识可见；
   * 固定列须连续，序号列在 StockMetricViewMetricTable 中预置，此处固定其后 3 列。
   */
  const columns: StockMetricViewColumnDef[] = [
    {
      key: 'market',
      title: t('stockMetricView.column.market'),
      minWidth: 64,
      defaultWidth: 72,
      allowsSorting: true,
      isRowHeader: false,
      align: 'center',
      fixed: true,
      cellClassName: 'whitespace-nowrap',
      markets: ALL_STOCK_METRIC_VIEW_MARKETS,
      render: (row) => renderStockMetricMarketCell(row.market, t),
    },
    {
      key: 'code',
      title: t('stockMetricView.column.code'),
      minWidth: 100,
      defaultWidth: 110,
      allowsSorting: true,
      isRowHeader: true,
      align: 'left',
      fixed: true,
      cellClassName: 'whitespace-nowrap',
      markets: ALL_STOCK_METRIC_VIEW_MARKETS,
      render: (row) => renderStockMetricKlineCell(row, row.code, t, onOpenKline),
    },
    {
      key: 'name',
      title: t('stockMetricView.column.name'),
      minWidth: 150,
      defaultWidth: 170,
      allowsSorting: true,
      isRowHeader: false,
      align: 'left',
      fixed: true,
      cellClassName: 'whitespace-nowrap',
      markets: ALL_STOCK_METRIC_VIEW_MARKETS,
      render: (row) => renderStockMetricKlineCell(row, row.name || row.code, t, onOpenKline),
    },
    {
      key: 'price',
      title: t('stockMetricView.column.price'),
      minWidth: 140,
      defaultWidth: 150,
      allowsSorting: true,
      isRowHeader: false,
      align: 'right',
      cellClassName: 'whitespace-nowrap',
      markets: ALL_STOCK_METRIC_VIEW_MARKETS,
      render: (row) => renderStockMetricNumberCell(row.price, 'currency', row.market),
    },
    {
      key: 'changePct',
      title: t('stockMetricView.column.changePct'),
      minWidth: 88,
      defaultWidth: 92,
      allowsSorting: true,
      isRowHeader: false,
      align: 'right',
      cellClassName: 'whitespace-nowrap',
      markets: ALL_STOCK_METRIC_VIEW_MARKETS,
      render: (row) => renderStockMetricChangePctCell(row.changePct),
    },
    {
      key: 'volume',
      title: t('stockMetricView.column.volume'),
      minWidth: 120,
      defaultWidth: 130,
      allowsSorting: true,
      isRowHeader: false,
      align: 'right',
      cellClassName: 'whitespace-nowrap',
      markets: ALL_STOCK_METRIC_VIEW_MARKETS,
      render: (row) => renderStockMetricNumberCell(row.volume, 'compact', row.market),
    },
    {
      key: 'relativeVolume',
      title: t('stockMetricView.column.relativeVolume'),
      minWidth: 96,
      defaultWidth: 100,
      allowsSorting: true,
      isRowHeader: false,
      align: 'right',
      cellClassName: 'whitespace-nowrap',
      markets: ALL_STOCK_METRIC_VIEW_MARKETS,
      render: (row) => renderStockMetricNumberCell(row.relativeVolume, 'compact', row.market),
    },
    {
      key: 'totalMarketCap',
      title: t('stockMetricView.column.totalMarketCap'),
      minWidth: 190,
      defaultWidth: 200,
      allowsSorting: true,
      isRowHeader: false,
      align: 'right',
      cellClassName: 'whitespace-nowrap',
      markets: ALL_STOCK_METRIC_VIEW_MARKETS,
      render: (row) => renderStockMetricNumberCell(row.totalMarketCap, 'money', row.market),
    },
    {
      key: 'peRatioTTM',
      title: t('stockMetricView.column.peRatioTTM'),
      minWidth: 104,
      defaultWidth: 108,
      allowsSorting: true,
      isRowHeader: false,
      align: 'right',
      cellClassName: 'whitespace-nowrap',
      markets: ALL_STOCK_METRIC_VIEW_MARKETS,
      render: (row) => renderStockMetricNumberCell(row.peRatioTTM, 'decimal', row.market),
    },
    {
      key: 'epsDiluted',
      title: t('stockMetricView.column.epsDiluted'),
      minWidth: 150,
      defaultWidth: 160,
      allowsSorting: true,
      isRowHeader: false,
      align: 'right',
      cellClassName: 'whitespace-nowrap',
      markets: ALL_STOCK_METRIC_VIEW_MARKETS,
      render: (row) => renderStockMetricNumberCell(row.epsDiluted, 'currency', row.market),
    },
    {
      key: 'epsGrowthTtmYoyPct',
      title: t('stockMetricView.column.epsGrowthTtmYoyPct'),
      minWidth: 170,
      defaultWidth: 180,
      allowsSorting: true,
      isRowHeader: false,
      align: 'right',
      cellClassName: 'whitespace-nowrap',
      markets: CN_STOCK_METRIC_VIEW_MARKETS,
      render: (row) => renderStockMetricNumberCell(row.epsGrowthTtmYoyPct, 'pct', row.market),
    },
    {
      key: 'dividendYieldPct',
      title: t('stockMetricView.column.dividendYieldPct'),
      minWidth: 76,
      defaultWidth: 80,
      allowsSorting: true,
      isRowHeader: false,
      align: 'right',
      cellClassName: 'whitespace-nowrap',
      markets: ALL_STOCK_METRIC_VIEW_MARKETS,
      render: (row) => renderStockMetricNumberCell(row.dividendYieldPct, 'pct', row.market),
    },
    {
      key: 'industry',
      title: t('stockMetricView.column.industry'),
      minWidth: 140,
      defaultWidth: 150,
      allowsSorting: true,
      isRowHeader: false,
      align: 'center',
      cellClassName: 'whitespace-nowrap',
      markets: ALL_STOCK_METRIC_VIEW_MARKETS,
      render: (row) => renderStockMetricIndustryCell(row.industry),
    },
    {
      key: 'analystRating',
      title: t('stockMetricView.column.analystRating'),
      minWidth: 130,
      defaultWidth: 140,
      allowsSorting: true,
      isRowHeader: false,
      align: 'center',
      cellClassName: 'whitespace-nowrap',
      markets: CN_STOCK_METRIC_VIEW_MARKETS,
      render: (row) => renderStockMetricNumberCell(row.analystRating, 'rating', row.market),
    },
  ];

  return columns.filter((column) => column.markets.includes(selectedMarket));
}

/** 序号列：行号由表格组件按 (pageNum-1)*pageSize 计算后按行 id 注入 */
export function createStockMetricViewRowNumberColumn(
  t: StockMetricViewTranslate,
  rowNumberById: Map<string, number>,
): TableColumnDef<StockMetricViewRow> {
  return {
    key: 'rowNumber',
    title: t('stockMetricView.column.rowNumber'),
    minWidth: 56,
    defaultWidth: 60,
    allowsSorting: false,
    isRowHeader: false,
    align: 'center',
    fixed: 'left',
    cellClassName: 'whitespace-nowrap text-secondary-text',
    render: (row: StockMetricViewRow) => rowNumberById.get(row.id) ?? STOCK_METRIC_VIEW_EMPTY_TEXT,
  };
}
