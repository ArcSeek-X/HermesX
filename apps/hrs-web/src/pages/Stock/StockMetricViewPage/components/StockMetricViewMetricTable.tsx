/**
 * @file pages/Stock/StockMetricViewPage/components/StockMetricViewMetricTable.tsx
 * @description 股票度量视图结果表格：AnimCard 包裹 Table，承接排序 / 受控分页 / 空态；
 * 列定义由页面组装后传入，行数据 / 分页 / 排序状态与翻页 / 排序回调均取自 metricViewModel。
 */

import { useCallback, useMemo } from 'react';
import type React from 'react';
import { Table } from '@components/basic/Table/Table';
import type { SortDescriptor, TableColumnDef, PaginationDef } from '@components/basic/Table/Table';
import { EmptyState } from '@components/basic/EmptyState';
import { useUiLanguage } from '@/contexts/UiLanguageContext';
import type { StockMetricViewRow } from '@/types/stockMetricView';
import type { UseStockMetricViewResult } from '@/hooks/useStockMetricView';
import { createStockMetricViewRowNumberColumn } from './stockMetricViewColumns';

/** 组件入参：列定义由页面组装，其余模型状态与回调取自 metricViewModel */
export interface StockMetricViewMetricTableProps {
  /** 当前市场可见的业务列定义（不含序号列） */
  columns: TableColumnDef<StockMetricViewRow>[];
  /** 股票度量视图模型（含行数据、分页、排序状态与翻页 / 排序回调） */
  metricViewModel: UseStockMetricViewResult;
  /** 空态标题 */
  emptyTitle: string;
  /** 空态描述 */
  emptyDescription?: string;
}

/** 股票度量视图结果表格 */
export function StockMetricViewMetricTable({
  columns,
  metricViewModel,
  emptyTitle,
  emptyDescription,
}: StockMetricViewMetricTableProps): React.JSX.Element {
  const { t } = useUiLanguage();
  const {
    list: rows,
    isLoading,
    total,
    pages,
    pageNum,
    pageSize,
    sortDescriptor: metricSort,
    setPageNum,
    setSortDescriptor,
  } = metricViewModel;

  // 首列序号：跨页连续，按行 id 建映射供列渲染器取值
  const rowNumberById = useMemo(
    () => new Map(rows.map((row, index) => [row.id, (pageNum - 1) * pageSize + index + 1])),
    [rows, pageNum, pageSize],
  );
  const tableColumns = useMemo(
    () => [createStockMetricViewRowNumberColumn(t, rowNumberById), ...columns],
    [columns, rowNumberById, t],
  );

  // 受控分页：字段名与 PaginationDef 一致
  const pagination = useMemo<PaginationDef>(
    () => ({ total, pageSize, pages, pageNum, onPageChange: setPageNum }),
    [total, pageSize, pages, pageNum, setPageNum],
  );

  // 领域排序 → Table 的 SortDescriptor
  const tableSortDescriptor = useMemo<SortDescriptor>(
    () => ({ column: metricSort.field, direction: metricSort.order === 'desc' ? 'descending' : 'ascending' }),
    [metricSort],
  );

  /** Table 的 SortDescriptor 反向翻译为度量视图领域排序（field + order） */
  const handleSortChange = useCallback(
    (descriptor: SortDescriptor): void => {
      setSortDescriptor({
        field: String(descriptor.column),
        order: descriptor.direction === 'descending' ? 'desc' : 'asc',
      });
    },
    [setSortDescriptor],
  );

  const renderEmptyState = useCallback(
    () => <EmptyState title={emptyTitle} description={emptyDescription} variant="muted" type="text" />,
    [emptyTitle, emptyDescription],
  );

  return (
    <Table<StockMetricViewRow>
      columns={tableColumns}
      rows={rows}
      isLoading={isLoading}
      sortDescriptor={tableSortDescriptor}
      onSortChange={handleSortChange}
      pagination={pagination}
      fillHeight
      // 紧凑密度：后代选择器覆盖 HeroUI 默认列头 / 单元格内边距，仅当前页面生效
      wrapperClassName="[&_th]:whitespace-nowrap [&_td]:py-2.5 [&_td]:text-xs"
      renderEmptyState={renderEmptyState}
    />
  );
}
