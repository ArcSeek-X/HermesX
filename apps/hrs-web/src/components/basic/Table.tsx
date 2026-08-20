/**
 * Table.tsx
 * ------------------------------------------------------------
 * 文件作用：
 *   通用数据表格组件。基于 HeroUI Table 组件封装，提供数据驱动的表格渲染能力。
 *   支持列定义、行数据渲染、列排序、行选择（全选/单选）、空状态展示、
 *   操作列插槽、分页功能以及多种表格变体。
 *
 * 核心功能：
 *   1. 数据驱动：表头由 columns 数组定义，行数据由 rows 数组传入；
 *   2. 列排序：通过 column.allowsSorting 控制是否支持排序，
 *      排序状态变化通过 onSortChange 回调通知父组件；
 *   3. 行选择：支持单选/多选/全选，通过 selectionMode 控制，
 *      选中项通过 onSelectionChange 回调；
 *   4. 空状态：通过 renderEmptyState 自定义表格为空时的展示内容；
 *   5. 操作列：通过 column.render 插槽函数自定义单元格内容（如操作按钮）；
 *   6. 分页：通过 pagination 配置启用分页，使用独立 Pagination 组件显示页码导航和数据统计；
 *   7. 可配置：variant、className 等属性均支持外部配置。
 *
 * 使用示例：
 *   <Table
 *     columns={[
 *       { key: 'name', title: '名称', allowsSorting: true },
 *       { key: 'price', title: '价格' },
 *       { key: 'actions', title: '操作', render: (row) => <Button>编辑</Button> },
 *     ]}
 *     rows={[{ id: '1', name: '股票A', price: 100 }]}
 *     selectionMode="multiple"
 *     onSelectionChange={(keys) => console.log(keys)}
 *     pagination={{ total: 100, pageSize: 20, pages: 5, pageNum: 1, onPageChange: setPage }}
 *   />
 * ------------------------------------------------------------
 */

import { useCallback, useMemo } from 'react';
import {
  TableRoot,
  TableContent,
  TableHeader,
  TableColumn,
  TableBody,
  TableRow,
  TableCell,
  TableSortableColumnHeader,
  EmptyState,
} from '@heroui/react';
import { Inbox } from 'lucide-react';
import PaginationBar from './Pagination';
import type { Key, SortDescriptor, Selection } from '@heroui/react';
import { cn } from '../../utils/cn';

/**
 * 列宽度类型。
 * 支持数字（像素值）、百分比字符串、fr 单位字符串。
 */
type ColumnWidth = number | `${number}%` | `${number}fr`;

/**
 * 表格列定义接口。
 * 每一列通过 key 唯一标识，title 显示列名，
 * 可通过 allowsSorting 控制是否支持排序，
 * 可通过 render 插槽函数自定义单元格渲染内容。
 */
export interface TableColumnDef<T> {
  /** 列的唯一标识，对应行数据中的字段名 */
  key: string;
  /** 列标题，显示在表头 */
  title: string;
  /** 是否支持排序，默认 false */
  allowsSorting?: boolean;
  /** 列宽度，支持像素值、百分比（如 '16%'）或 fr 单位（如 '1fr'） */
  width?: ColumnWidth;
  /**
   * 自定义单元格渲染函数。
   * 传入行数据，返回要渲染的 React 节点。
   * 未提供时默认渲染 row[column.key] 的值。
   */
  render?: (row: T) => React.ReactNode;
}

/**
 * 排序描述符接口。
 * 描述当前排序的列和排序方向。
 * 从 @heroui/react 导入以保持类型一致性。
 */
export type { SortDescriptor } from '@heroui/react';

/**
 * 分页配置接口。
 * 传入后启用分页功能，渲染分页控件。
 * 采用受控模式：调用方管理页码状态，通过 onPageChange 接收翻页事件。
 */
export interface PaginationConfig {
  /** 总条数 */
  total: number;
  /** 每页显示的行数 */
  pageSize: number;
  /** 总页数 */
  pages: number;
  /** 当前页码（从 1 开始） */
  pageNum: number;
  /** 页码变化时的回调 */
  onPageChange: (pageNum: number) => void;
}

/**
 * 表格组件属性接口。
 * 泛型 T 表示行数据类型，必须包含 id 字段用于唯一标识每一行。
 */
export interface TableProps<T extends { id: string | number }> {
  /** 列定义数组，决定表格有哪些列、每列的标题、宽度、是否可排序等 */
  columns: TableColumnDef<T>[];
  /** 行数据数组，每行必须包含 id 字段作为唯一标识 */
  rows: T[];
  /**
   * 表格视觉变体，透传给 HeroUI Table 的 variant。
   * - 'primary': 主要样式（默认）
   * - 'secondary': 次要样式
   */
  variant?: 'primary' | 'secondary';
  /** 表格根容器的自定义类名 */
  className?: string;
  /**
   * 行选择模式：
   * - 'none': 不支持选择（默认）
   * - 'single': 单选
   * - 'multiple': 多选（含全选）
   */
  selectionMode?: 'none' | 'single' | 'multiple';
  /** 当前选中的行 key 集合（受控模式） */
  selectedKeys?: Iterable<Key>;
  /** 选中行变化时的回调，返回当前选中的 key 集合 */
  onSelectionChange?: (keys: Selection) => void;
  /** 排序变化时的回调，返回排序描述对象 */
  onSortChange?: (sortDescriptor: SortDescriptor) => void;
  /** 当前排序描述符（受控模式） */
  sortDescriptor?: SortDescriptor;
  /**
   * 自定义空状态渲染函数。
   * 当 rows 为空时调用，返回要展示的 React 节点。
   * 未提供时使用默认空状态文案。
   */
  renderEmptyState?: () => React.ReactNode;
  /** 表格加载状态，为 true 时显示加载指示器 */
  isLoading?: boolean;
  /** 表格最大高度，超出后表格内部滚动 */
  maxHeight?: string | number;
  /**
   * 分页配置。
   * 传入对象后启用分页功能，显示分页控件和统计信息。
   * 采用受控模式：调用方负责数据切片和页码管理。
   */
  pagination?: PaginationConfig;
}

/**
 * 通用数据表格组件。
 *
 * 负责将 columns 和 rows 数据转换为 HeroUI Table 的结构化渲染，
 * 并处理排序、选择、空状态等交互逻辑。
 */
export function Table<T extends { id: string | number }>({
  columns,
  rows,
  variant = 'primary',
  className = '',
  selectionMode = 'none',
  selectedKeys,
  onSelectionChange,
  onSortChange,
  sortDescriptor,
  renderEmptyState,
  isLoading = false,
  maxHeight,
  pagination,
}: TableProps<T>) {
  /**
   * 处理选择变化。
   * 直接传递 HeroUI 的 Selection 类型给回调。
   */
  const handleSelectionChange = useCallback(
    (selection: Selection) => {
      if (!onSelectionChange) return;
      onSelectionChange(selection);
    },
    [onSelectionChange],
  );

  /**
   * 渲染单元格内容。
   * 如果列定义了 render 函数则使用自定义渲染，否则直接显示字段值。
   */
  const renderCell = useCallback(
    (row: T, columnKey: string) => {
      // 查找对应列定义
      const colDef = columns.find((c) => c.key === columnKey);

      // 如果有自定义渲染函数，使用它
      if (colDef?.render) {
        return colDef.render(row);
      }

      // 否则直接显示字段值（通过索引访问）
      const value = (row as Record<string, unknown>)[columnKey];
      if (value == null) return '—';
      return String(value);
    },
    [columns],
  );

  /**
   * 默认空状态渲染。
   * 当表格处于加载中时显示“加载中…”提示，
   * 否则显示无数据的空状态（图标 + 文案）。
   */
  const defaultEmptyState = useMemo(() => {
    return () => {
      // 加载中：展示加载提示，避免与空数据状态混淆
      if (isLoading) {
        return (
          <div className="py-10 text-center text-sm text-muted">加载中…</div>
        );
      }

      return (
        <EmptyState className="flex h-full w-full flex-col items-center justify-center gap-4 text-center">
          <Inbox className="size-6 text-muted" />
          <span className="text-sm text-muted">暂无数据</span>
        </EmptyState>
      );
    };
  }, [isLoading]);






  /**
   * 实际渲染的行数据。
   * 受控模式下调用方已切片，直接渲染 rows。
   */
  const displayRows = rows;

  /**
   * 表格容器样式。
   * 当指定 maxHeight 时，在外层 div 设置最大高度并启用滚动。
   */
  const containerStyle = maxHeight
    ? {
      maxHeight: typeof maxHeight === 'number' ? `${maxHeight}px` : maxHeight,
      overflow: 'auto' as const,
    }
    : undefined;

  return (
    <div className="hrs-table flex flex-col w-full rounded-md" style={containerStyle}>
      {/* HeroUI Table 主体 */}
      <TableRoot variant={variant} className={cn('hrs-table__root', className)}>
        <TableContent
          aria-label="数据表格"
          selectionMode={selectionMode === 'none' ? undefined : selectionMode}
          selectedKeys={selectedKeys}
          onSelectionChange={handleSelectionChange}
          sortDescriptor={sortDescriptor}
          onSortChange={onSortChange}
        >
          {/* 表头 */}
          <TableHeader className="hrs-table__header">
            {columns.map((col) => (
              <TableColumn
                key={col.key}
                allowsSorting={col.allowsSorting}
                width={col.width}
              >
                {col.allowsSorting ? (
                  <TableSortableColumnHeader
                    sortDirection={
                      sortDescriptor?.column === col.key
                        ? sortDescriptor.direction
                        : undefined
                    }
                  >
                    {col.title}
                  </TableSortableColumnHeader>
                ) : (
                  col.title
                )}
              </TableColumn>
            ))}
          </TableHeader>

          {/* 表体 */}
          <TableBody
            className="hrs-table__body"
            items={displayRows}
            renderEmptyState={renderEmptyState ?? defaultEmptyState}
          >
            {/* 
              使用 render props 模式，根据行数据渲染每一行。
              HeroUI Table 要求通过 (item) => <TableRow> 的方式渲染。
            */}
            {(item) => (
              <TableRow key={String(item.id)} columns={columns} className="">
                {(col) => (
                  <TableCell className="border-b border-subtle">
                    {renderCell(item, col.key)}
                  </TableCell>
                )}
              </TableRow>
            )}
          </TableBody>
        </TableContent>
      </TableRoot>
      {/* 底部分页栏：加载完成（isLoading 消失）后才显示 */}
      {pagination && !isLoading && (
        <PaginationBar
          className="hrs-table__pagination"
          size="xs"
          total={pagination.total}
          pages={pagination.pages}
          pageNum={pagination.pageNum}
          onPageChange={pagination.onPageChange}
        />
      )}
    </div>
  );
}

export default Table;
