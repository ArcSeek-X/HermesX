/**
 * @file boardColumns.tsx
 * @description 涨跌停榜单表格列定义与单元格格式化。涨停 / 跌停池字段同构，列定义通用，
 *   仅封板时间列表头按看板语义区分；代码 / 名称列点击跳转个股 K 线页（?stockCode= 协议，见 jump2Kline.md）。
 */

import type { TableColumnDef, SortDescriptor } from '@components/basic/Table';
import type { UiTextKey } from '../../../../i18n/uiText';
import type { LimitBoardQuote } from '../../../../types/stock';
import { formatAmount, formatPercent, getChangeColorClass, getBoardCountColor } from '../../../../utils/format';

/** 涨跌停榜单表格行：领域行情数据 + UI 行 key（= 代码，后端不返回） */
export type LimitBoardRow = LimitBoardQuote & { id: string };

/** 连板数 → 展示文案：1=首板，>=2=N 板，缺失/非法 -- */
export function formatBoardCount(boards: number | null): string {
  if (boards == null || boards <= 0) return '--';
  return boards === 1 ? '首板' : `${boards}板`;
}

/** 封板时间：HHMMSS（akshare）/ HH:MM:SS（stock-sdk）统一为 HH:MM，缺失 -- */
export function formatLimitTime(sealTime: string): string {
  if (!sealTime) return '--';
  const digits = sealTime.replace(/\D/g, '');
  if (digits.length >= 5) return `${digits.slice(0, 2)}:${digits.slice(2, 4)}`;
  return sealTime.includes(':') ? sealTime.slice(0, 5) : sealTime;
}

/** 代码 / 名称列点击单元格：跳转个股 K 线页；未传回调时退化为纯文本 */
function renderStockJumpCell(
  displayText: string,
  row: LimitBoardRow,
  jumpHint: string,
  onOpenStockKline?: (row: LimitBoardRow) => void,
) {
  if (!onOpenStockKline) return displayText;
  return (
    <div
      className="group cursor-pointer truncate"
      role="button"
      tabIndex={0}
      title={jumpHint}
      onClick={(e) => {
        e.stopPropagation();
        onOpenStockKline(row);
      }}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onOpenStockKline(row);
        }
      }}
    >
      <span className="group-hover:text-primary">{displayText}</span>
    </div>
  );
}

/** 涨跌停榜单列构建选项 */
export interface LimitBoardColumnsOptions {
  /** 封板时间列表头（涨停时间 / 跌停时间，由调用方按看板语义传入） */
  sealTimeColumnTitle: string;
  /** 榜单语义：决定连板数着色色系（涨停=红、跌停=绿） */
  boardType: 'limit-up' | 'limit-down';
  /** 点击代码 / 名称列跳转 K 线页回调 */
  onOpenStockKline?: (row: LimitBoardRow) => void;
}

/** 构建涨跌停榜单列定义：标题经 i18n 映射，代码 / 名称列点击跳转 K 线 */
export function buildLimitBoardColumns(
  t: (key: UiTextKey) => string,
  options: LimitBoardColumnsOptions,
): TableColumnDef<LimitBoardRow>[] {
  const { sealTimeColumnTitle, boardType, onOpenStockKline } = options;
  const jumpHint = t('emotion.board.openKline');
  return [
    {
      key: 'code',
      title: t('emotion.board.col.code'),
      minWidth: 90,
      defaultWidth: '8%',
      isRowHeader: true,
      render: (row) => renderStockJumpCell(row.code, row, jumpHint, onOpenStockKline),
    },
    {
      key: 'name',
      title: t('emotion.board.col.name'),
      minWidth: 110,
      defaultWidth: '11%',
      render: (row) => renderStockJumpCell(row.name, row, jumpHint, onOpenStockKline),
    },
    {
      key: 'price',
      title: t('emotion.board.col.price'),
      minWidth: 90,
      defaultWidth: '8%',
      allowsSorting: true,
      render: (row) => (row.price == null ? '--' : row.price.toFixed(2)),
    },
    {
      key: 'changePct',
      title: t('emotion.board.col.changePercent'),
      minWidth: 100,
      defaultWidth: '9%',
      allowsSorting: true,
      render: (row) => <span className={getChangeColorClass(row.changePct)}>{formatPercent(row.changePct)}</span>,
    },
    {
      key: 'firstLimitTime',
      title: sealTimeColumnTitle,
      minWidth: 100,
      defaultWidth: '9%',
      allowsSorting: true,
      render: (row) => formatLimitTime(row.firstLimitTime),
    },
    {
      key: 'consecutiveBoards',
      title: t('emotion.board.col.boards'),
      minWidth: 80,
      defaultWidth: '7%',
      allowsSorting: true,
      render: (row) => {
        const boards = row.consecutiveBoards;
        const text = formatBoardCount(boards);
        if (boards == null || boards <= 0) return text;
        return (
          <span className="font-semibold" style={{ color: getBoardCountColor(boards, boardType) }}>
            {text}
          </span>
        );
      },
    },
    {
      key: 'sealAmount',
      title: t('emotion.board.col.sealAmount'),
      minWidth: 110,
      defaultWidth: '10%',
      allowsSorting: true,
      render: (row) => formatAmount(row.sealAmount),
    },
    {
      key: 'amount',
      title: t('emotion.board.col.amount'),
      minWidth: 110,
      defaultWidth: '10%',
      allowsSorting: true,
      render: (row) => formatAmount(row.amount),
    },
    {
      key: 'turnoverRate',
      title: t('emotion.board.col.turnoverRate'),
      minWidth: 100,
      defaultWidth: '8%',
      allowsSorting: true,
      render: (row) => (row.turnoverRate == null ? '--' : `${row.turnoverRate.toFixed(2)}%`),
    },
    {
      key: 'industry',
      title: t('emotion.board.col.industry'),
      minWidth: 110,
      defaultWidth: '20%',
    },
  ];
}

/**
 * 按排序描述符排序榜单行：数值列按数值比较，其余按字符串比较，空值恒沉底。
 * 涨停 / 跌停面板共用同一排序规则。
 */
export function sortBoardRows(rows: LimitBoardRow[], sortDescriptor: SortDescriptor): LimitBoardRow[] {
  const { column, direction } = sortDescriptor;
  if (!column) return rows;
  const dir = direction === 'descending' ? -1 : 1;
  return [...rows].sort((a, b) => {
    const aValue = (a as unknown as Record<string, unknown>)[column];
    const bValue = (b as unknown as Record<string, unknown>)[column];
    if (aValue == null && bValue == null) return 0;
    if (aValue == null) return 1;
    if (bValue == null) return -1;
    if (typeof aValue === 'number' && typeof bValue === 'number') return (aValue - bValue) * dir;
    return String(aValue).localeCompare(String(bValue)) * dir;
  });
}
