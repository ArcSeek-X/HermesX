/** Table 组件演示页：数据驱动、排序、选择、操作列、空态、分页与树形数据。 */

import React, { useMemo, useState } from 'react';
import type { Selection, SortDescriptor } from '@heroui/react';
import { HrsButton } from '@components';
import { AppPage } from '@components/layout/AppPage';
import { Table, type TableColumnDef, type PaginationDef } from '@components/basic/Table/Table';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import { DocsSection } from '../DocsSection';

interface StockQuoteRow {
  id: string;
  name: string;
  code: string;
  price: number;
  change: number;
}

const STOCK_QUOTE_ROWS: StockQuoteRow[] = [
  { id: '1', name: '贵州茅台', code: '600519', price: 1425.32, change: 1.23 },
  { id: '2', name: '宁德时代', code: '300750', price: 189.45, change: -0.87 },
  { id: '3', name: '腾讯控股', code: '00700', price: 412.6, change: 2.15 },
  { id: '4', name: '苹果', code: 'AAPL', price: 227.8, change: -1.02 },
  { id: '5', name: '英伟达', code: 'NVDA', price: 138.9, change: 3.4 },
];

const STOCK_PAGE_SIZE = 5;
const PAGINATED_STOCK_ROWS: StockQuoteRow[] = Array.from({ length: 20 }, (_, index) => ({
  id: String(index + 1),
  name: `示例股票 ${index + 1}`,
  code: `0000${index + 1}`.slice(-5),
  price: Number((10 + index * 3.7).toFixed(2)),
  change: Number(((index % 7) - 3).toFixed(2)),
}));

/** 组织单元：children 递归表示层级，key 作为行标识字段 */
interface OrgUnitRow {
  key: string;
  name: string;
  leader: string;
  phone?: string;
  email?: string;
  memberCount: number;
  order: number;
  status: '正常' | '停用';
  children?: OrgUnitRow[];
}

const ORG_UNIT_ROWS: OrgUnitRow[] = [
  {
    key: 'root',
    name: '云原科技集团',
    leader: '周明远',
    email: 'hq@example.com',
    memberCount: 0,
    order: 1,
    status: '正常',
    children: [
      {
        key: 'rd',
        name: '研发中心',
        leader: '陈思远',
        email: 'rd@example.com',
        memberCount: 0,
        order: 1,
        status: '正常',
        children: [
          {
            key: 'arch',
            name: '平台架构部',
            leader: '李维',
            email: 'archi@example.com',
            memberCount: 2,
            order: 1,
            status: '正常',
            children: [
              { key: 'test', name: '测试', leader: '周明远', memberCount: 0, order: 10, status: '正常' },
              { key: 'app-dev', name: '应用开发部', leader: '吴敏', email: 'app@example.com', memberCount: 1, order: 2, status: '正常' },
              { key: 'qa', name: '测试质量部', leader: '韩雪', email: 'qa@example.com', memberCount: 0, order: 3, status: '正常' },
            ],
          },
        ],
      },
      { key: 'product', name: '产品中心', leader: '赵晴', email: 'pm@example.com', memberCount: 0, order: 2, status: '正常' },
      { key: 'hr', name: '职能中心', leader: '钱伟', email: 'hr@example.com', memberCount: 0, order: 3, status: '正常' },
    ],
  },
  {
    key: 'star',
    name: '星澜网络集团',
    leader: '林嘉禾',
    email: 'star-hq@example.com',
    memberCount: 0,
    order: 2,
    status: '正常',
    children: [
      {
        key: 'star-tech',
        name: '技术中心',
        leader: '何睿',
        email: 'star-tech@example.com',
        memberCount: 0,
        order: 1,
        status: '正常',
        children: [
          { key: 'star-front', name: '前端研发部', leader: '苏晴', email: 'star-front@example.com', memberCount: 3, order: 1, status: '正常' },
          { key: 'star-back', name: '后端研发部', leader: '郑凯', email: 'star-back@example.com', memberCount: 4, order: 2, status: '正常' },
        ],
      },
      { key: 'star-market', name: '市场中心', leader: '叶琳', email: 'star-market@example.com', memberCount: 0, order: 2, status: '正常' },
    ],
  },
  {
    key: 'yuan',
    name: '远见智能集团',
    leader: '沈立群',
    email: 'yuan-hq@example.com',
    memberCount: 0,
    order: 3,
    status: '正常',
    children: [
      { key: 'yuan-ai', name: 'AI 研究院', leader: '唐越', email: 'yuan-ai@example.com', memberCount: 6, order: 1, status: '正常' },
      { key: 'yuan-data', name: '数据平台部', leader: '冯媛', email: 'yuan-data@example.com', memberCount: 5, order: 2, status: '正常' },
      {
        key: 'yuan-ops',
        name: '运营中心',
        leader: '许航',
        email: 'yuan-ops@example.com',
        memberCount: 0,
        order: 3,
        status: '停用',
        children: [
          { key: 'yuan-cs', name: '客户服务部', leader: '蒋宁', email: 'yuan-cs@example.com', memberCount: 2, order: 1, status: '正常' },
        ],
      },
    ],
  },
];

/** 组织单元列：defaultWidth 混用 px 数字与百分比字符串演示宽度分配 */
const ORG_UNIT_COLUMNS: TableColumnDef<OrgUnitRow>[] = [
  { key: 'name', title: '部门名称', minWidth: 220, defaultWidth: '28%', align: 'left', fixed: true },
  { key: 'leader', title: '负责人', minWidth: 100, defaultWidth: 100, align: 'center' },
  { key: 'phone', title: '联系电话', minWidth: 120, defaultWidth: 120, align: 'center' },
  { key: 'email', title: '邮箱', minWidth: 170, defaultWidth: '18%', align: 'center' },
  { key: 'memberCount', title: '人数', minWidth: 70, defaultWidth: 70, align: 'center' },
  { key: 'order', title: '排序', minWidth: 70, defaultWidth: 70, align: 'center' },
  {
    key: 'status',
    title: '状态',
    minWidth: 90,
    defaultWidth: 90,
    align: 'center',
    render: (row) => (
      <span className="inline-flex items-center gap-1.5">
        <span className="size-1.5 rounded-full bg-success" />
        {row.status}
      </span>
    ),
  },
  {
    key: 'actions',
    title: '操作',
    minWidth: 150,
    defaultWidth: 150,
    align: 'center',
    render: () => (
      <span className="flex items-center gap-1 text-muted">
        <HrsButton variant="ghost" size="xs">+</HrsButton>
        <HrsButton variant="ghost" size="xs">编辑</HrsButton>
        <HrsButton variant="ghost" size="xs">删除</HrsButton>
      </span>
    ),
  },
];

export const DocsTablePage: React.FC = () => {
  const { t } = useUiLanguage();

  const [stockSortDescriptor, setStockSortDescriptor] = useState<SortDescriptor>({ column: 'price', direction: 'ascending' });
  const [selectedStockIds, setSelectedStockIds] = useState<string[]>(['1']);
  const [stockPageNum, setStockPageNum] = useState(1);
  const [editedStockName, setEditedStockName] = useState<string | null>(null);

  const stockColumns: TableColumnDef<StockQuoteRow>[] = [
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
        <HrsButton variant="ghost" size="xs" onClick={() => setEditedStockName(row.name)}>
          编辑
        </HrsButton>
      ),
    },
  ];

  const sortedStockRows = useMemo(() => {
    const { column, direction } = stockSortDescriptor;
    if (!column) return STOCK_QUOTE_ROWS;
    const sortDirection = direction === 'ascending' ? 1 : -1;
    return [...STOCK_QUOTE_ROWS].sort((a, b) => {
      const left = (a as unknown as Record<string, unknown>)[String(column)];
      const right = (b as unknown as Record<string, unknown>)[String(column)];
      if (typeof left === 'number' && typeof right === 'number') return (left - right) * sortDirection;
      return String(left ?? '').localeCompare(String(right ?? '')) * sortDirection;
    });
  }, [stockSortDescriptor]);

  const handleStockSelectionChange = (keys: Selection) => {
    if (keys === 'all') {
      setSelectedStockIds(STOCK_QUOTE_ROWS.map((row) => row.id));
      return;
    }
    setSelectedStockIds(Array.from(keys).map(String));
  };

  const pagedStockRows = useMemo(
    () => PAGINATED_STOCK_ROWS.slice((stockPageNum - 1) * STOCK_PAGE_SIZE, stockPageNum * STOCK_PAGE_SIZE),
    [stockPageNum],
  );
  const stockPagination: PaginationDef = {
    total: PAGINATED_STOCK_ROWS.length,
    pageSize: STOCK_PAGE_SIZE,
    pages: Math.ceil(PAGINATED_STOCK_ROWS.length / STOCK_PAGE_SIZE),
    pageNum: stockPageNum,
    onPageChange: setStockPageNum,
  };

  return (
    <AppPage>
      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-1">
          <h1 className="text-lg font-semibold text-foreground">{t('layout.nav.development.docsTable.title')}</h1>
          <p className="text-xs text-muted">
            基于 HeroUI Table 封装的通用数据表格（Table）。表头由 columns 数组定义（minWidth / defaultWidth 必填）、
            行数据由 rows 数组传入（默认每条含 id，可通过 rowKey 指定其他标识字段），支持列排序、行选择、render 插槽、空态、受控分页与树形数据。
          </p>
        </header>

        {/* 示例一：columns + rows 数据驱动渲染，render 插槽渲染操作列 */}
        <DocsSection title="示例一：基础数据驱动表格" description="columns + rows 数据驱动渲染；未定义 render 的列直接显示字段值，操作列通过 render 插槽渲染 HrsButton。">
          <Table columns={stockColumns} rows={STOCK_QUOTE_ROWS} />
        </DocsSection>

        {/* 示例二：allowsSorting 启用列排序，sortDescriptor / onSortChange 受控 */}
        <DocsSection title="示例二：列排序（allowsSorting）" description="column.allowsSorting 启用排序（表头出现排序按钮）；sortDescriptor / onSortChange 受控，点击「最新价 / 涨跌幅」表头切换排序。">
          <Table
            columns={stockColumns}
            rows={sortedStockRows}
            sortDescriptor={stockSortDescriptor}
            onSortChange={setStockSortDescriptor}
          />
        </DocsSection>

        {/* 示例三：selectionMode 行选择，selectedKeys / onSelectionChange 受控 */}
        <DocsSection title="示例三：行选择（selectionMode）" description="selectionMode 支持 single / multiple（含全选）；selectedKeys / onSelectionChange 受控。">
          <span className="text-xs text-secondary-text">已选中：{selectedStockIds.length > 0 ? selectedStockIds.join(' / ') : '无'}</span>
          <Table
            columns={stockColumns}
            rows={STOCK_QUOTE_ROWS}
            selectionMode="multiple"
            selectedKeys={new Set(selectedStockIds)}
            onSelectionChange={handleStockSelectionChange}
          />
        </DocsSection>

        {/* 示例四：操作列 render 插槽接收整行对象，点击按钮回显该行 */}
        <DocsSection title="示例四：操作列 render 插槽" description="点击「编辑」按钮回显该行数据（render 插槽接收整行对象，可渲染任意 React 节点）。">
          {editedStockName && <span className="text-xs text-secondary-text">上次点击「编辑」的行：{editedStockName}</span>}
          <Table columns={stockColumns} rows={STOCK_QUOTE_ROWS} selectionMode="single" />
        </DocsSection>

        {/* 示例五：renderEmptyState 自定义空态，isLoading 加载态 */}
        <DocsSection title="示例五：空态（renderEmptyState）与加载态（isLoading）" description="rows 为空时展示空态（未传 renderEmptyState 时使用默认「暂无数据」）；isLoading 时展示加载提示。">
          <div className="flex flex-col gap-4">
            <Table
              columns={stockColumns}
              rows={[]}
              renderEmptyState={() => (
                <div className="py-10 text-center text-sm text-muted">自定义空态：暂无符合条件的股票</div>
              )}
            />
            <Table columns={stockColumns} rows={[]} isLoading />
          </div>
        </DocsSection>

        {/* 示例六：pagination 受控分页，调用方管理页码与数据切片 */}
        <DocsSection title="示例六：分页（pagination）" description="传入 pagination 配置启用分页（受控模式）：调用方管理页码与数据切片，组件渲染分页控件与统计信息。">
          <Table columns={stockColumns} rows={pagedStockRows} pagination={stockPagination} />
        </DocsSection>

        {/* 示例七：treeColumnKey 树形数据，默认展开首行；defaultExpandedKeys 可覆盖默认 */}
        <DocsSection
          title="示例七：树形数据（treeColumnKey）"
          description="以组织管理为例：配置 treeColumnKey 后，children 递归渲染为子行；未传展开配置时默认只展开首行，行 key 集合变化后按新首行重新默认展开。defaultExpandedKeys 指定初始展开的行（非受控，无需外部 state），expandedKeys 则完全由外部受控，传入任一配置都不再注入默认展开；展开/折叠状态由组件内部管理。列定义的 minWidth 为最小像素宽，defaultWidth 支持数字 px 或 '18%' 这类百分比字符串。未配置 treeColumnKey 的表格仍按平铺渲染。"
        >
          <Table
            columns={ORG_UNIT_COLUMNS}
            rows={ORG_UNIT_ROWS}
            rowKey="key"
            treeColumnKey="name"
            defaultExpandedKeys={new Set(['root', 'rd'])}
          />
        </DocsSection>
      </div>
    </AppPage>
  );
};

export default DocsTablePage;
