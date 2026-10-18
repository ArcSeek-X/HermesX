/**
 * @file Emotion/BoardlistPage/BoardlistPage.tsx
 * BoardlistPage —— 涨跌榜页面
 * =====================================================================
 * 【功能介绍】
 * 「情绪」一级菜单下的涨跌榜页面，布局参考 /market/index：
 * 顶部标题 + 「涨停榜单 / 跌停榜单」两个 TAB。
 * - 涨停榜单：以表格展示 代码 / 名称 / 现价 / 涨幅 / 涨停时间 / 连板 /
 *   封单额 / 成交额 / 换手率 / 所属行业，数据来自 /api/v1/emotion/limit-up-board。
 * - 跌停榜单：内容区待后续开发（数据源已确认可行，复用 akshare 跌停股池）。
 *
 * 【状态 / 数据流】
 * - 当前激活 TAB 通过 useCachedState 持久化到 localStorage，刷新后保持。
 * - 涨停榜单挂载/切回时拉取，页面被路由缓存隐藏（isPageActive=false）时暂停加载。
 * =====================================================================
 * @author Lensgcx (GaoCangxiong)
 * @date 2026-10-16
 */
import type React from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { TabNav } from '@components';
import { Table, type TableColumnDef } from '@components/basic/Table';
import { AppPage } from '@components/layout/AppPage';
import { PageHeader } from '@components/layout/PageLayout/PageHeader';
import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import { useKeepAliveContext } from 'keepalive-for-react';
import { useCachedState } from '../../../hooks/useCachedState';
import { formatAmount, formatPercent, getChangeColorClass } from '../../../utils/format';
import { fetchLimitUpBoard } from '../../../api/emotionData';
import type { StockLimitUpQuote } from '../../../types/stock';

/** 涨停榜单表格行类型：领域数据 StockLimitUpQuote + UI 行 key id（= code，后端不返回，见 stock_type.md §7.1） */
type BoardRow = StockLimitUpQuote & { id: string };

/** 涨跌榜 TAB：涨停榜单 / 跌停榜单 */
type BoardTab = 'limit-up' | 'limit-down';

/** 涨跌榜 TAB 配置（顺序即展示顺序），label 经 i18n 映射，labelKey 指向 emotion.board.* */
const BOARD_TABS: { key: BoardTab; labelKey: 'emotion.board.limitUp' | 'emotion.board.limitDown' }[] = [
  { key: 'limit-up', labelKey: 'emotion.board.limitUp' },
  { key: 'limit-down', labelKey: 'emotion.board.limitDown' },
];

/** 连板数 → 展示文案：1=首板，>=2=N板，缺失=-- */
const renderBoards = (n: number | null): string => {
  if (n == null || n <= 0) return '--';
  return n === 1 ? '首板' : `${n}板`;
};

/**
 * 涨停时间格式化：源数据可能为 HHMMSS（akshare）或 HH:MM:SS（stock-sdk）。
 * 统一裁剪为 HH:MM，缺失返回 --。
 */
const formatBoardTime = (raw: string): string => {
  if (!raw) return '--';
  const digits = raw.replace(/\D/g, '');
  if (digits.length >= 5) return `${digits.slice(0, 2)}:${digits.slice(2, 4)}`;
  if (raw.includes(':')) return raw.slice(0, 5);
  return raw;
};

/**
 * 涨跌榜主页面组件。
 * 负责：标题渲染、涨停/跌停 TAB 切换、涨停榜单表格（含排序）。
 */
const BoardlistPage: React.FC = () => {
  const { t } = useUiLanguage();
  /** 页面活动态（路由缓存）：隐藏时暂停加载，切回即刷新 */
  const { active: isPageActive } = useKeepAliveContext();

  /** 当前激活的涨跌榜 TAB（localStorage 持久化用户偏好） */
  const [boardTab, setBoardTab] = useCachedState<BoardTab>(
    'emotion.boardTab',
    'limit-up',
    { storage: 'local' }
  );

  const [items, setItems] = useState<BoardRow[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchLimitUpBoard();
      setItems(res.items.map((it) => ({ ...it, id: it.code })));
    } catch (err) {
      console.error('Failed to load limit-up board', err);
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  // 仅当展示涨停榜单且页面处于活动态时拉取；路由缓存隐藏时暂停。
  useEffect(() => {
    if (!isPageActive || boardTab !== 'limit-up') return undefined;
    void load();
    return undefined;
  }, [boardTab, isPageActive, load]);

  const [sortDescriptor, setSortDescriptor] = useState<{ column: string; direction: 'ascending' | 'descending' }>(
    { column: 'consecutiveBoards', direction: 'descending' }
  );

  const sortedRows = useMemo(() => {
    if (!sortDescriptor?.column) return items;
    const { column, direction } = sortDescriptor;
    const dir = direction === 'descending' ? -1 : 1;
    return [...items].sort((a, b) => {
      const av = (a as unknown as Record<string, unknown>)[column];
      const bv = (b as unknown as Record<string, unknown>)[column];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * dir;
      return String(av).localeCompare(String(bv)) * dir;
    });
  }, [items, sortDescriptor]);

  const columns: TableColumnDef<BoardRow>[] = [
    { key: 'code', title: t('emotion.board.col.code'), minWidth: 90, defaultWidth: 100, isRowHeader: true },
    { key: 'name', title: t('emotion.board.col.name'), minWidth: 110, defaultWidth: 120 },
    {
      key: 'price',
      title: t('emotion.board.col.price'),
      minWidth: 90,
      defaultWidth: 100,
      allowsSorting: true,
      render: (r) => (r.price == null ? '--' : r.price.toFixed(2)),
    },
    {
      key: 'changePct',
      title: t('emotion.board.col.changePercent'),
      minWidth: 100,
      defaultWidth: 110,
      allowsSorting: true,
      render: (r) => <span className={getChangeColorClass(r.changePct)}>{formatPercent(r.changePct)}</span>,
    },
    {
      key: 'firstLimitTime',
      title: t('emotion.board.col.limitTime'),
      minWidth: 100,
      defaultWidth: 110,
      allowsSorting: true,
      render: (r) => formatBoardTime(r.firstLimitTime),
    },
    {
      key: 'consecutiveBoards',
      title: t('emotion.board.col.boards'),
      minWidth: 80,
      defaultWidth: 90,
      allowsSorting: true,
      render: (r) => renderBoards(r.consecutiveBoards),
    },
    {
      key: 'sealAmount',
      title: t('emotion.board.col.sealAmount'),
      minWidth: 110,
      defaultWidth: 120,
      allowsSorting: true,
      render: (r) => (r.sealAmount == null ? '--' : formatAmount(r.sealAmount)),
    },
    {
      key: 'amount',
      title: t('emotion.board.col.amount'),
      minWidth: 110,
      defaultWidth: 120,
      allowsSorting: true,
      render: (r) => (r.amount == null ? '--' : formatAmount(r.amount)),
    },
    {
      key: 'turnoverRate',
      title: t('emotion.board.col.turnoverRate'),
      minWidth: 100,
      defaultWidth: 110,
      allowsSorting: true,
      render: (r) => (r.turnoverRate == null ? '--' : `${r.turnoverRate.toFixed(2)}%`),
    },
    { key: 'industry', title: t('emotion.board.col.industry'), minWidth: 110, defaultWidth: 120 },
  ];

  return (
    <AppPage>
      <div className="flex h-full flex-col gap-3">
        <PageHeader title={t('layout.nav.boardlist.title')} description={t('layout.nav.boardlist.description')} />
        <TabNav<BoardTab>
          ariaLabel={t('emotion.board.switch')}
          variant="secondary"
          items={BOARD_TABS.map(({ key, labelKey }) => ({ value: key, label: t(labelKey) }))}
          value={boardTab}
          onChange={setBoardTab}
        />
        {boardTab === 'limit-up' ? (
          <Table<BoardRow>
            columns={columns}
            rows={sortedRows}
            isLoading={loading}
            sortDescriptor={sortDescriptor}
            onSortChange={(d) => setSortDescriptor({ column: String(d.column), direction: d.direction })}
            height="calc(100vh - 260px)"
          />
        ) : (
          <div className="flex flex-1 items-center justify-center text-sm text-muted-text">
            {t('emotion.board.limitDownComing')}
          </div>
        )}
      </div>
    </AppPage>
  );
};

export default BoardlistPage;
