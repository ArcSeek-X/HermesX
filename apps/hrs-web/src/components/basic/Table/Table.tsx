/**
 * 基于 HeroUI Table 的通用数据表格。
 *
 * 核心能力：
 * - 数据驱动：columns 定义列，rows 提供行数据，render 插槽自定义单元格；
 * - 排序与选择：allowsSorting + sortDescriptor/onSortChange，selectionMode + selectedKeys/onSelectionChange；
 * - 空态与分页：renderEmptyState 自定义空态，pagination 受控分页；
 * - 固定列与树形：fixed 配置固定列（细节见 fixedColumns.ts），treeColumnKey + children 递归子行。
 *
 * 使用示例：
 *   <Table
 *     columns={[
 *       { key: 'name', title: '名称', minWidth: 120, defaultWidth: 120, allowsSorting: true },
 *       { key: 'actions', title: '操作', minWidth: 90, defaultWidth: 90, render: (row) => <Button>编辑</Button> },
 *     ]}
 *     rows={[{ id: '1', name: '股票A' }]}
 *     selectionMode="multiple"
 *     onSelectionChange={(keys) => setSelected(keys)}
 *   />
 */

import { useCallback, useMemo, useRef } from 'react';
import type { ComponentProps, ReactElement } from 'react';
import { Table as HeroTable, EmptyState } from '@heroui/react';
import type { Key, SortDescriptor, Selection } from '@heroui/react';
import { HrsButton } from '../HrsButton/HrsButton';
import { ChevronRight, Inbox } from 'lucide-react';
import PaginationBar from '../Pagination';
import { cn } from '../../../utils/cn';
import styles from './Table.module.scss';
import { buildFixedColumnPropsByKey, useFixedColumnOffsets } from './fixedColumns';
import type { TableColumnFixedMode } from './fixedColumns';
export type { TableColumnFixedMode } from './fixedColumns';

export type { SortDescriptor } from '@heroui/react';

export interface TableColumnDef<T> {
  /** 列唯一标识，对应行数据字段名 */
  key: string;
  /** 列标题 */
  title: string;
  /** 是否可排序，默认 false */
  allowsSorting?: boolean;
  /** 最小宽度（px），HeroUI 要求必填 */
  minWidth: number;
  /** 默认宽度，支持 px 数字或 '15%' 等 CSS 长度；按各列相对比例分配 */
  defaultWidth: string | number;
  /** 行标题列，默认第一列（HeroUI 要求至少一列） */
  isRowHeader?: boolean;
  /** 自定义单元格渲染，未提供时显示 row[column.key] */
  render?: (row: T) => React.ReactNode;
  /** 单元格附加 className */
  cellClassName?: string;
  /** 整列对齐方式，默认 left */
  align?: TableColumnAlign;
  /** 固定列，true 等价 'left'；须从首列或末列起连续声明 */
  fixed?: TableColumnFixedMode;
}

export type TableColumnAlign = 'left' | 'right' | 'center';

const TABLE_ALIGN_TEXT_CLASS: Record<TableColumnAlign, string> = {
  left: 'text-left',
  right: 'text-right',
  center: 'text-center',
};

const TABLE_ALIGN_FLEX_CLASS: Record<TableColumnAlign, string> = {
  left: 'justify-start',
  right: 'justify-end',
  center: 'justify-center',
};

export interface PaginationDef {
  /** 数据总条数，用于展示总数统计 */
  total: number;
  /** 每页条数 */
  pageSize: number;
  /** 总页数 */
  pages: number;
  /** 当前页码，从 1 开始 */
  pageNum: number;
  /** 页码变化回调，返回新页码（从 1 开始） */
  onPageChange: (pageNum: number) => void;
}

export interface TableProps<T extends object> {
  /** 列定义数组：列标题、宽度、排序及单元格渲染方式 */
  columns: TableColumnDef<T>[];
  /** 行数据数组 */
  rows: T[];
  /** 行唯一标识字段，默认 'id'；字段值作为 React key 与行 class 后缀 */
  rowKey?: Extract<keyof T, string>;
  /** 表格视觉变体，默认 primary */
  variant?: 'primary' | 'secondary';
  /** 表格主体附加 className */
  className?: string;
  /** 外层容器附加 className（含表格与分页栏） */
  wrapperClassName?: string;
  /** 行选择模式：none 不显示选择列，single 单选，multiple 多选（含全选） */
  selectionMode?: 'none' | 'single' | 'multiple';
  /** 受控选中行 key 集合 */
  selectedKeys?: Iterable<Key>;
  /** 选中行变化回调，keys 为 'all' 表示全选 */
  onSelectionChange?: (keys: Selection) => void;
  /** 排序变化回调，返回新排序列与方向 */
  onSortChange?: (sortDescriptor: SortDescriptor) => void;
  /** 受控排序状态：column 为列 key，direction 为升序/降序 */
  sortDescriptor?: SortDescriptor;
  /** rows 为空时的自定义展示，未提供时用默认空态 */
  renderEmptyState?: () => React.ReactNode;
  /** 是否展示加载中空态提示，默认 false */
  isLoading?: boolean;
  /** 表格高度，超出后内部滚动；默认 320px */
  height?: string | number;
  /**
   * 撑满父容器剩余高度（需父级为 flex 列），此时忽略 height。
   * 用 calc(100vh - Npx) 会在窗口缩放、全屏或指标卡换行时失配。
   */
  fillHeight?: boolean;
  /** 传入后启用受控分页：调用方负责数据切片与页码管理 */
  pagination?: PaginationDef;
  /** 每行附加 className，用于按行标识追加自定义样式 */
  rowClassName?: string;
  /** 树形列 key；配置后 children 递归为子行，该列自动渲染展开按钮 */
  treeColumnKey?: string;
  /** 受控展开行 key 集合 */
  expandedKeys?: Iterable<Key>;
  /** 非受控初始展开行 key 集合 */
  defaultExpandedKeys?: Iterable<Key>;
  /** 展开/折叠变化回调，返回当前展开行 key 集合 */
  onExpandedChange?: (keys: Set<Key>) => void;
}

const SCROLL_CONTAINER_STYLE = { height: '100%', overflow: 'auto' as const };

export function Table<T extends object>({
  columns,
  rows,
  rowKey = 'id' as Extract<keyof T, string>,
  variant = 'primary',
  className = '',
  selectionMode = 'none',
  selectedKeys,
  onSelectionChange,
  onSortChange,
  sortDescriptor,
  renderEmptyState,
  isLoading = false,
  height = 320,
  fillHeight = false,
  pagination,
  rowClassName = '',
  wrapperClassName = '',
  treeColumnKey,
  expandedKeys,
  defaultExpandedKeys,
  onExpandedChange,
}: TableProps<T>) {
  const columnDefByField = useMemo(
    () => new Map(columns.map((column) => [column.key, column])),
    [columns],
  );

  // RAC 以行对象为 WeakMap key 缓存 Row；仅列变化时旧行会复用旧列数，
  // 导致 "Cell count must match column count"。用 dependencies 精确失效，不重挂载整表。
  const columnLayoutSignature = useMemo(
    () => columns.map((column) => column.key).join('|'),
    [columns],
  );

  // 平铺切树形或改行标识字段时行对象引用可能不变，需一并纳入依赖使缓存失效
  const rowCacheDependencies = useMemo(
    () => [columnLayoutSignature, treeColumnKey ?? '', rowKey],
    [columnLayoutSignature, treeColumnKey, rowKey],
  );

  const wrapperRef = useRef<HTMLDivElement>(null);
  useFixedColumnOffsets(wrapperRef, columns.length, columnLayoutSignature);
  const fixedPropsByField = useMemo(() => buildFixedColumnPropsByKey(columns), [columns]);

  const renderTableCell = useCallback(
    (row: T, fieldKey: string) => {
      const columnDef = columnDefByField.get(fieldKey);
      if (columnDef?.render) return columnDef.render(row);
      const value = (row as Record<string, unknown>)[fieldKey];
      return value == null ? '—' : String(value);
    },
    [columnDefByField],
  );

  const renderDefaultEmptyState = useCallback(() => {
    if (isLoading) {
      return <div className="py-10 text-center text-sm text-muted">加载中…</div>;
    }
    return (
      <EmptyState className="flex h-full w-full flex-col items-center justify-center gap-4 text-center">
        <Inbox className="size-6 text-muted" />
        <span className="text-sm text-muted">暂无数据</span>
      </EmptyState>
    );
  }, [isLoading]);

  const renderTableRow = (rowData: T): ReactElement => {
    const childTableRows = (rowData as { children?: T[] }).children;
    const rowIdentity = String(rowData[rowKey]);
    return (
      <HeroTable.Row
        key={rowIdentity}
        columns={columns}
        dependencies={rowCacheDependencies}
        className={cn(`hrs-table__row__${rowIdentity}`, rowClassName)}
      >
        {columns.map((columnDef) => {
          const align = columnDef.align ?? 'left';
          const fixedColumnProps = fixedPropsByField.get(columnDef.key);
          const isTreeColumnCell = treeColumnKey != null && columnDef.key === treeColumnKey;
          return (
            <HeroTable.Cell
              key={columnDef.key}
              className={cn(
                'border-b border-subtle',
                TABLE_ALIGN_TEXT_CLASS[align],
                columnDef.cellClassName,
                fixedColumnProps?.className,
              )}
              style={fixedColumnProps?.style}
            >
              {isTreeColumnCell
                ? (cellRenderProps) => (
                    <span className="flex items-center gap-1">
                      {cellRenderProps.hasChildItems && cellRenderProps.isTreeColumn && (
                        <HrsButton
                          slot="chevron"
                          variant="ghost"
                          size="xs"
                          aria-label={cellRenderProps.isExpanded ? '收起子行' : '展开子行'}
                          className="size-6 min-w-0 shrink-0 !px-0"
                        >
                          <ChevronRight
                            className={cn(
                              'size-4 transition-transform duration-150',
                              cellRenderProps.isExpanded && 'rotate-90',
                            )}
                          />
                        </HrsButton>
                      )}
                      {renderTableCell(rowData, columnDef.key)}
                    </span>
                  )
                : renderTableCell(rowData, columnDef.key)}
            </HeroTable.Cell>
          );
        })}
        {treeColumnKey != null && childTableRows && childTableRows.length > 0 && (
          <HeroTable.Collection items={childTableRows}>{renderTableRow}</HeroTable.Collection>
        )}
      </HeroTable.Row>
    );
  };

  const wrapperStyle = fillHeight
    ? undefined
    : { height: typeof height === 'number' ? `${height}px` : height };

  return (
    <div
      ref={wrapperRef}
      className={cn('hrs-table flex flex-col w-full', fillHeight && 'flex-1 min-h-0', wrapperClassName)}
      style={wrapperStyle}
    >
      <HeroTable variant={variant} className={cn('hrs-table__root flex-1 min-h-0 rounded-md bg-secondary', styles.root, className)}>
        <HeroTable.ScrollContainer className={styles.scrollOverride} style={SCROLL_CONTAINER_STYLE}>
          <HeroTable.ResizableContainer>
            <HeroTable.Content
              className="hrs-table__content rounded-md"
              aria-label="数据表格"
              selectionMode={selectionMode === 'none' ? undefined : selectionMode}
              selectedKeys={selectedKeys}
              onSelectionChange={onSelectionChange}
              sortDescriptor={sortDescriptor}
              onSortChange={onSortChange}
              treeColumn={treeColumnKey}
              expandedKeys={expandedKeys}
              defaultExpandedKeys={defaultExpandedKeys}
              onExpandedChange={onExpandedChange}
            >
              <HeroTable.Header className={cn('hrs-table__header bg-muted', styles.header)}>
                {columns.map((columnDef) => {
                  const align = columnDef.align ?? 'left';
                  const fixedColumnProps = fixedPropsByField.get(columnDef.key);
                  return (
                    <HeroTable.Column
                      key={columnDef.key}
                      id={columnDef.key}
                      allowsSorting={columnDef.allowsSorting}
                      minWidth={columnDef.minWidth as ComponentProps<typeof HeroTable.Column>['minWidth']}
                      defaultWidth={columnDef.defaultWidth as ComponentProps<typeof HeroTable.Column>['defaultWidth']}
                      isRowHeader={columnDef.isRowHeader ?? columnDef.key === columns[0]?.key}
                      className={cn(TABLE_ALIGN_TEXT_CLASS[align], fixedColumnProps?.className)}
                      style={fixedColumnProps?.style}
                    >
                      {columnDef.allowsSorting ? (
                        <HeroTable.SortableColumnHeader
                          className={cn('w-full', TABLE_ALIGN_FLEX_CLASS[align])}
                          sortDirection={
                            sortDescriptor?.column === columnDef.key
                              ? sortDescriptor.direction
                              : undefined
                          }
                        >
                          {columnDef.title}
                        </HeroTable.SortableColumnHeader>
                      ) : (
                        <span className={cn('block w-full', TABLE_ALIGN_TEXT_CLASS[align])}>
                          {columnDef.title}
                        </span>
                      )}
                    </HeroTable.Column>
                  );
                })}
              </HeroTable.Header>

              <HeroTable.Body
                className={cn('hrs-table__body', styles.body)}
                items={rows}
                dependencies={rowCacheDependencies}
                renderEmptyState={renderEmptyState ?? renderDefaultEmptyState}
              >
                {renderTableRow}
              </HeroTable.Body>
            </HeroTable.Content>
          </HeroTable.ResizableContainer>
        </HeroTable.ScrollContainer>
      </HeroTable>
      {/* 分页栏常驻：刷新时保留旧数据与分页控件，避免布局跳动 */}
      {pagination && (
        <PaginationBar
          className="hrs-table__pagination"
          size="xs"
          total={pagination.total}
          pageSize={pagination.pageSize}
          pages={pagination.pages}
          pageNum={pagination.pageNum}
          onPageChange={pagination.onPageChange}
        />
      )}
    </div>
  );
}

export default Table;
