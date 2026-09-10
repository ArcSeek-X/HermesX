/**
 * @fileoverview 组件文档页：Table（通用数据表格）
 * 路由地址 /docs/component/table，菜单名「表格」。
 * 用于演示 Table 的数据驱动渲染、列排序、行选择、操作列插槽、空态与分页。
 * @module pages
 */

import React, { useMemo, useState } from 'react';
import type { Selection, SortDescriptor } from '@heroui/react';
import { AppPage, HrsButton } from '../../../components';
import { Table, type TableColumnDef, type PaginationDef } from '../../../components/basic/Table';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';

/** 行数据类型：泛型 T 必须包含 id 字段作为唯一标识 */
interface StockRow {
  id: string;
  name: string;
  code: string;
  price: number;
  change: number;
}

/** 基础行数据（示例一 / 二 / 三 / 四共用） */
const STOCK_ROWS: StockRow[] = [
  { id: '1', name: '贵州茅台', code: '600519', price: 1425.32, change: 1.23 },
  { id: '2', name: '宁德时代', code: '300750', price: 189.45, change: -0.87 },
  { id: '3', name: '腾讯控股', code: '00700', price: 412.6, change: 2.15 },
  { id: '4', name: '苹果', code: 'AAPL', price: 227.8, change: -1.02 },
  { id: '5', name: '英伟达', code: 'NVDA', price: 138.9, change: 3.4 },
];

/** 分页演示数据（示例六）：20 条模拟数据 */
const PAGED_ROWS: StockRow[] = Array.from({ length: 20 }, (_, i) => ({
  id: String(i + 1),
  name: `示例股票 ${i + 1}`,
  code: `0000${i + 1}`.slice(-5),
  price: Number((10 + i * 3.7).toFixed(2)),
  change: Number(((i % 7) - 3).toFixed(2)),
}));

const PAGE_SIZE = 5;

/**
 * 表格组件文档演示页。
 *
 * Table 基于 HeroUI Table 封装：表头由 columns 数组定义（minWidth / defaultWidth 必填），
 * 行数据由 rows 数组传入（每条必须含 id），支持列排序、行选择、render 插槽、空态与受控分页。
 */
export const DocsTablePage: React.FC = () => {
  const { t } = useUiLanguage();

  // 示例二：排序（受控 sortDescriptor，前端本地排序演示）
  const [sortDescriptor, setSortDescriptor] = useState<SortDescriptor>({ column: 'price', direction: 'ascending' });
  // 示例三：行选择（多选受控）
  const [selectedIds, setSelectedIds] = useState<string[]>(['1']);
  // 示例六：分页（受控页码）
  const [pageNum, setPageNum] = useState(1);

  /** 列定义：名称 / 代码 / 最新价（可排序）/ 涨跌幅（可排序 + render 插槽）/ 操作（render 插槽） */
  const columns: TableColumnDef<StockRow>[] = [
    { key: 'name', title: '名称', minWidth: 120, defaultWidth: 120 },
    { key: 'code', title: '代码', minWidth: 90, defaultWidth: 90 },
    { key: 'price', title: '最新价', minWidth: 90, defaultWidth: 90, allowsSorting: true },
    {
      key: 'change',
      title: '涨跌幅',
      minWidth: 90,
      defaultWidth: 90,
      allowsSorting: true,
      render: (row) => (
        <span className={row.change >= 0 ? 'text-success' : 'text-danger'}>
          {row.change >= 0 ? '+' : ''}{row.change.toFixed(2)}%
        </span>
      ),
    },
    {
      key: 'actions',
      title: '操作',
      minWidth: 120,
      defaultWidth: 120,
      render: (row) => (
        <HrsButton variant="ghost" size="xs" onClick={() => setEditedName(row.name)}>
          编辑
        </HrsButton>
      ),
    },
  ];

  /** 示例二：按 sortDescriptor 本地排序后的行数据 */
  const sortedRows = useMemo(() => {
    const { column, direction } = sortDescriptor;
    if (!column) return STOCK_ROWS;
    const dir = direction === 'ascending' ? 1 : -1;
    return [...STOCK_ROWS].sort((a, b) => {
      const av = (a as unknown as Record<string, unknown>)[String(column)];
      const bv = (b as unknown as Record<string, unknown>)[String(column)];
      if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * dir;
      return String(av ?? '').localeCompare(String(bv ?? '')) * dir;
    });
  }, [sortDescriptor]);

  /** 示例三：选择变化（Selection 为 'all' 或 Set<Key>，统一转换为 id 数组） */
  const handleSelectionChange = (keys: Selection) => {
    if (keys === 'all') {
      setSelectedIds(STOCK_ROWS.map((r) => r.id));
      return;
    }
    setSelectedIds(Array.from(keys).map(String));
  };

  /** 示例四：操作列点击的「编辑」回显 */
  const [editedName, setEditedName] = useState<string | null>(null);

  /** 示例六：当前页数据切片（受控分页：调用方负责切片与页码管理） */
  const pageRows = useMemo(
    () => PAGED_ROWS.slice((pageNum - 1) * PAGE_SIZE, pageNum * PAGE_SIZE),
    [pageNum],
  );
  const pagination: PaginationDef = {
    total: PAGED_ROWS.length,
    pageSize: PAGE_SIZE,
    pages: Math.ceil(PAGED_ROWS.length / PAGE_SIZE),
    pageNum,
    onPageChange: setPageNum,
  };

  return (
    <AppPage>
      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-1">
          <h1 className="text-lg font-semibold text-primary-text">{t('layout.nav.development.docsTable.title')}</h1>
          <p className="text-xs text-muted">
            基于 HeroUI Table 封装的通用数据表格（Table）。表头由 columns 数组定义（minWidth / defaultWidth 必填）、
            行数据由 rows 数组传入（每条必须含 id），支持列排序、行选择、render 插槽、空态与受控分页。
          </p>
        </header>

        {/* 1. 基础数据驱动表格 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例一：基础数据驱动表格</h2>
          <p className="text-xs text-muted">
            columns + rows 数据驱动渲染；未定义 render 的列直接显示字段值，操作列通过 render 插槽渲染 HrsButton。
          </p>
          <Table columns={columns} rows={STOCK_ROWS} />
        </section>

        {/* 2. 列排序 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例二：列排序（allowsSorting）</h2>
          <p className="text-xs text-muted">
            column.allowsSorting 启用排序（表头出现排序按钮）；sortDescriptor / onSortChange 受控，点击「最新价 / 涨跌幅」表头切换排序。
          </p>
          <Table
            columns={columns}
            rows={sortedRows}
            sortDescriptor={sortDescriptor}
            onSortChange={(d) => setSortDescriptor(d)}
          />
        </section>

        {/* 3. 行选择 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例三：行选择（selectionMode）</h2>
          <p className="text-xs text-muted">
            selectionMode 支持 single / multiple（含全选）；selectedKeys / onSelectionChange 受控。
          </p>
          <span className="text-xs text-secondary-text">已选中：{selectedIds.length > 0 ? selectedIds.join(' / ') : '无'}</span>
          <Table
            columns={columns}
            rows={STOCK_ROWS}
            selectionMode="multiple"
            selectedKeys={new Set(selectedIds)}
            onSelectionChange={handleSelectionChange}
          />
        </section>

        {/* 4. 操作列 + 编辑回显 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例四：操作列 render 插槽</h2>
          <p className="text-xs text-muted">
            点击「编辑」按钮回显该行数据（render 插槽接收整行对象，可渲染任意 React 节点）。
          </p>
          {editedName && <span className="text-xs text-secondary-text">上次点击「编辑」的行：{editedName}</span>}
          <Table columns={columns} rows={STOCK_ROWS} selectionMode="single" />
        </section>

        {/* 5. 空态与加载态 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例五：空态（renderEmptyState）与加载态（isLoading）</h2>
          <p className="text-xs text-muted">
            rows 为空时展示空态（未传 renderEmptyState 时使用默认「暂无数据」）；isLoading 时展示加载提示。
          </p>
          <div className="flex flex-col gap-4">
            <Table
              columns={columns}
              rows={[]}
              renderEmptyState={() => (
                <div className="py-10 text-center text-sm text-muted">自定义空态：暂无符合条件的股票</div>
              )}
            />
            <Table columns={columns} rows={[]} isLoading />
          </div>
        </section>

        {/* 6. 分页 */}
        <section className="flex flex-col gap-3 rounded-lg border border-border/70 bg-card/75 p-6">
          <h2 className="text-sm font-medium text-primary-text">示例六：分页（pagination）</h2>
          <p className="text-xs text-muted">
            传入 pagination 配置启用分页（受控模式）：调用方管理页码与数据切片，组件渲染分页控件与统计信息。
          </p>
          <Table columns={columns} rows={pageRows} pagination={pagination} />
        </section>
      </div>
    </AppPage>
  );
};

export default DocsTablePage;
