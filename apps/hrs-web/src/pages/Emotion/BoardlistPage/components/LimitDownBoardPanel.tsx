/**
 * @file LimitDownBoardPanel.tsx
 * @description 跌停榜单面板（页面级组件）：KPI 指标卡 + 可排序明细表。
 *   页面被路由缓存隐藏时暂停拉取，切回即刷新。
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useKeepAliveContext } from 'keepalive-for-react';
import { Table } from '@components/basic/Table';
import type { SortDescriptor } from '@components/basic/Table';
import { useUiLanguage } from '../../../../contexts/UiLanguageContext';
import { fetchLimitDownBoard } from '../../../../api/limitPoolData';
import { normalizeStockCode } from '@utils/stock/stockCode';
import { buildLimitBoardColumns, sortBoardRows, type LimitBoardRow } from './boardColumns';
import { summarizeLimitBoard } from './boardMetrics';
import { LimitBoardIndexCards } from './LimitBoardIndexCards';

/** 默认排序：连板数降序 */
const DEFAULT_SORT: SortDescriptor = { column: 'consecutiveBoards', direction: 'descending' };

/** 跌停榜单面板：指标卡 + 可排序明细表 */
export function LimitDownBoardPanel() {
  const { t } = useUiLanguage();
  const navigate = useNavigate();
  /** 页面活动态（路由缓存）：隐藏时暂停拉取，切回即刷新 */
  const { active: isPanelActive } = useKeepAliveContext();

  const [boardRows, setBoardRows] = useState<LimitBoardRow[]>([]);
  // 初始即加载态：挂载首帧展示「加载中」，避免空数据态一闪而过
  const [isBoardLoading, setIsBoardLoading] = useState(true);
  const [sortDescriptor, setSortDescriptor] = useState<SortDescriptor>(DEFAULT_SORT);

  /** 点击代码 / 名称列跳转个股 K 线页：统一 ?stockCode= 直达，见 jump2Kline.md */
  const openStockKline = useCallback(
    (row: LimitBoardRow) => {
      const pureCode = normalizeStockCode(row.code);
      navigate(`/stock/kline?stockCode=${encodeURIComponent(pureCode)}`);
    },
    [navigate],
  );

  // 面板可见时拉取跌停榜；路由缓存隐藏时暂停，切回重跑即刷新。
  // isStale 守卫避免隐藏 / 卸载后的迟滞响应写入 state。
  useEffect(() => {
    if (!isPanelActive) return undefined;
    let isStale = false;
    void (async () => {
      setIsBoardLoading(true);
      try {
        const response = await fetchLimitDownBoard();
        if (isStale) return;
        setBoardRows(response.items.map((item) => ({ ...item, id: item.code })));
      } catch (err) {
        if (isStale) return;
        console.error('Failed to load limit-down board', err);
        setBoardRows([]);
      } finally {
        if (!isStale) setIsBoardLoading(false);
      }
    })();
    return () => {
      isStale = true;
    };
  }, [isPanelActive]);

  const boardColumns = useMemo(
    () =>
      buildLimitBoardColumns(t, {
        sealTimeColumnTitle: t('emotion.board.col.limitDownTime'),
        boardType: 'limit-down',
        onOpenStockKline: openStockKline,
      }),
    [t, openStockKline],
  );
  const boardSummary = useMemo(() => summarizeLimitBoard(boardRows), [boardRows]);
  const sortedBoardRows = useMemo(() => sortBoardRows(boardRows, sortDescriptor), [boardRows, sortDescriptor]);

  return (
    <div className="flex flex-1 min-h-0 flex-col gap-3">
      <LimitBoardIndexCards boardType="limit-down" boardSummary={boardSummary} isBoardLoading={isBoardLoading} />
      <Table<LimitBoardRow>
        columns={boardColumns}
        rows={sortedBoardRows}
        isLoading={isBoardLoading}
        sortDescriptor={sortDescriptor}
        onSortChange={setSortDescriptor}
        fillHeight
      />
    </div>
  );
}
