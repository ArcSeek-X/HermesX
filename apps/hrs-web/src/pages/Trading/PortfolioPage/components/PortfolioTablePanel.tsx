/**
 * 持仓表格面板
 *
 * 展示持仓明细表格；手工录入与券商 CSV 导入两个写入入口上移至主页面 TabNav 右侧插槽
 * （任何页签下均可见，全部账户视图下禁用）。
 *
 * 持仓行与决策信号均由本面板通过 usePortfolioSignals 基于已加载好的快照/风险派生，
 * 主页面不自行请求持仓相关的下游数据。
 */

import type React from 'react';
import { useMemo, useState } from 'react';
import { AnimCard, HrsButton, InlineAlert } from '@components';
import { EmptyState } from '@components/basic/EmptyState';
import { Table } from '@components/basic/Table';
import type { TableColumnDef } from '@components/basic/Table';
import { PortfolioSignalSummary } from '@components/decision-signals/DecisionSignalDisplay';
import { useUiLanguage } from '../../../../contexts/UiLanguageContext';
import { PORTFOLIO_TEXT } from '../../../../locales/featureText';
import {
  formatPositionMoney,
  formatPositionPrice,
  formatSignedPct,
  getPositionPriceLabel,
  hasPositionPrice,
} from '@utils/portfolioFormat';
import type { DecisionSignalItem } from '../../../../types/decisionSignals';
import type { PortfolioSnapshotResponse } from '../../../../types/portfolio';
import type { FlatPosition } from '../../../../types/portfolio';
import { usePortfolioSignals } from '../../../../hooks';

/**
 * 持仓表格字号：统一使用 XS（text-xs = 12px）。
 * 表头（th）无独立字号，随表格根容器继承；单元格（td）显式声明，避免受容器样式影响。
 */
const TABLE_TEXT_CLASS = 'text-xs';

/** 持仓表格面板属性 */
interface PortfolioTablePanelProps {
  /** 当前视图的持仓快照 */
  snapshot: PortfolioSnapshotResponse | null;
  /** 当前查询账户 ID，'all' 时为 undefined（只读汇总） */
  queryAccountId?: number;
  /** 账户列表长度，用于判定快照是否覆盖全部账户 */
  accountsLength: number;
  /** 整页刷新自增键：变化时强制重新查询决策信号 */
  signalsRefreshTick?: number;
  /** 统一错误回调，转发给主页面全局错误提示 */
  onError: (error: unknown) => void;
  /** 分析任务提交成功后的消息回调，用于主页面全局提示 */
  onAnalysisMessage: (message: string) => void;
}

/** 持仓表格每页行数 */
const POSITION_PAGE_SIZE = 10;

/**
 * 持仓表格卡片的最小高度（兜底，非主 sizing）。
 *
 * 表格主高度由 flex 链贴底填充（Table 的 fillHeight），本值只在下限兜底：页面顶部最多可同时出现
 * 账户提示 / 写入拦截 / 错误 / 风险降级 / 快照口径等多条 InlineAlert，全部出现时会挤占可用高度。
 * 低于此高度每页 10 行只剩三四行可见、翻页体验差，因此设地板：触顶时改为让页面随内容长高、
 * 由 Main 滚动，而不是把表格无限压扁。
 */
const POSITION_TABLE_MIN_HEIGHT = 320;

export const PortfolioTablePanel: React.FC<PortfolioTablePanelProps> = ({
  snapshot,
  queryAccountId,
  accountsLength,
  signalsRefreshTick,
  onError,
  onAnalysisMessage,
}) => {
  const { language, t } = useUiLanguage();
  const text = PORTFOLIO_TEXT[language];

  const {
    positionRows,
    signalByPositionKey,
    signalsLoading,
    signalsWarning,
    positionUnderAnalysis,
    handleAnalyzePosition,
  } = usePortfolioSignals({ snapshot, queryAccountId, accountsLength, signalsRefreshTick, onError, onAnalysisMessage });

  /**
   * 表格行类型：扁平持仓 + 行 id + 该行已解析的持仓信号 + 是否正在分析。
   * basic/Table 的单元格内容按 items（行）记忆化：列定义变化不会触发单元格重渲染，
   * 因此行级动态数据（信号、分析中状态）必须随行数据一起下发。
   */
  type PositionTableRow = FlatPosition & {
    id: string;
    signal?: DecisionSignalItem;
    analyzing: boolean;
  };

  /** 构造表格行：附加行 id，并把信号与分析状态随行下发 */
  const positionTableRows = useMemo<PositionTableRow[]>(
    () => positionRows.map((row, index) => {
      const key = `${row.accountId}-${row.symbol}-${row.market}`;
      return {
        ...row,
        // basic/Table 基于 react-aria 集合，要求行 key 唯一；
        // 重复持仓（同账户 + 同代码 + 同市场）需补序号区分，查询仍用业务 key
        id: `${key}#${index}`,
        signal: signalByPositionKey.get(key),
        analyzing: positionUnderAnalysis === key,
      };
    }),
    [positionRows, signalByPositionKey, positionUnderAnalysis],
  );

  /** 当前页码（1 起） */
  const [positionPageNum, setPositionPageNum] = useState(1);

  /** 持仓总条数与总页数 */
  const totalPositions = positionTableRows.length;
  const totalPages = Math.max(1, Math.ceil(totalPositions / POSITION_PAGE_SIZE));

  /**
   * 安全页码：限制在 [1, totalPages]。
   * 切换账户 / 刷新后持仓数变少时，避免用越界页码切片取到空页；
   * 不用 effect 回写，直接派生，规避 set-state-in-effect。
   */
  const safePageNum = Math.min(Math.max(1, positionPageNum), totalPages);

  /** 当前页要渲染的行：basic/Table 的分页为受控模式，切片由调用方负责 */
  const pageRows = useMemo(
    () => positionTableRows.slice(
      (safePageNum - 1) * POSITION_PAGE_SIZE,
      safePageNum * POSITION_PAGE_SIZE,
    ),
    [positionTableRows, safePageNum],
  );

  /**
   * 持仓表格列定义
   * 严格遵循 basic/Table 的 TableColumnDef：每列必须提供 key / title / minWidth / defaultWidth，
   * 自定义单元格通过 render 返回 React 节点，数字列右对齐通过 cellClassName 控制。
   */
  const positionTableColumns = useMemo<TableColumnDef<PositionTableRow>[]>(
    () => [
      {
        key: 'account',
        title: text.account,
        minWidth: 100,
        defaultWidth: '10%',
        isRowHeader: true,
        cellClassName: TABLE_TEXT_CLASS,
        render: (row) => <span className="text-foreground-soft">{row.accountName}</span>,
      },
      {
        key: 'symbol',
        title: text.code,
        minWidth: 80,
        defaultWidth: '8%',
        cellClassName: TABLE_TEXT_CLASS,
        render: (row) => <span className="font-mono text-foreground">{row.symbol}</span>,
      },
      {
        key: 'quantity',
        title: text.quantity,
        minWidth: 80,
        defaultWidth: '8%',
        cellClassName: `${TABLE_TEXT_CLASS} text-right`,
        render: (row) => row.quantity.toFixed(2),
      },
      {
        key: 'avgCost',
        title: text.avgCost,
        minWidth: 80,
        defaultWidth: '8%',
        cellClassName: `${TABLE_TEXT_CLASS} text-right`,
        render: (row) => row.avgCost.toFixed(4),
      },
      {
        key: 'lastPrice',
        title: text.lastPrice,
        // 该列含「价格 + 价格口径副文本（如 收盘价 · 2026-03-18）」两行，需最宽
        minWidth: 150,
        defaultWidth: '13%',
        cellClassName: `${TABLE_TEXT_CLASS} text-right`,
        render: (row) => (
          <div>
            <div>{formatPositionPrice(row)}</div>
            {/* 价格口径副文本比正文再小一档（xxs = 10px），保持层级 */}
            <div className={`text-xxs ${hasPositionPrice(row) ? 'text-foreground-soft' : 'text-warning'}`}>
              {getPositionPriceLabel(row)}
            </div>
          </div>
        ),
      },
      {
        key: 'marketValue',
        title: text.marketValue,
        minWidth: 110,
        defaultWidth: '11%',
        cellClassName: `${TABLE_TEXT_CLASS} text-right`,
        render: (row) => formatPositionMoney(row.marketValueBase, row),
      },
      {
        key: 'unrealizedPnl',
        title: text.unrealizedPnl,
        minWidth: 110,
        defaultWidth: '11%',
        cellClassName: `${TABLE_TEXT_CLASS} text-right`,
        render: (row) => (
          <span className={
            hasPositionPrice(row)
              ? row.unrealizedPnlBase >= 0 ? 'text-success' : 'text-danger'
              : 'text-secondary'
          }>
            {formatPositionMoney(row.unrealizedPnlBase, row)}
          </span>
        ),
      },
      {
        key: 'returnPct',
        title: text.returnPct,
        minWidth: 80,
        defaultWidth: '8%',
        cellClassName: `${TABLE_TEXT_CLASS} text-right`,
        render: (row) => (
          <span className={
            hasPositionPrice(row) && row.unrealizedPnlPct != null
              ? row.unrealizedPnlPct >= 0 ? 'text-success' : 'text-danger'
              : 'text-secondary'
          }>
            {formatSignedPct(row.unrealizedPnlPct)}
          </span>
        ),
      },
      {
        key: 'decisionSignals',
        title: t('decisionSignals.portfolioColumn'),
        // 决策信号列承载风险摘要文本，给足宽度避免频繁换行
        minWidth: 170,
        defaultWidth: '16%',
        cellClassName: `${TABLE_TEXT_CLASS} text-right align-top`,
        render: (row) => <PortfolioSignalSummary item={row.signal} loading={signalsLoading} />,
      },
      {
        key: 'action',
        title: text.action,
        minWidth: 80,
        defaultWidth: '7%',
        cellClassName: `${TABLE_TEXT_CLASS} text-right`,
        render: (row) => (
          <HrsButton
            variant="secondary"
            size="xs"
            onClick={() => handleAnalyzePosition(row)}
            isDisabled={row.analyzing}
          >
            {row.analyzing ? text.submitting : text.analyze}
          </HrsButton>
        ),
      },
    ],
    [text, t, signalsLoading, handleAnalyzePosition],
  );

  /**
   * 表格高度：不写死，交由 flex 链贴底填充（Table 的 fillHeight）。
   *
   * 原实现按「每页行数 × 估算行高 + 余量」算固定高度（10×44+64，上限 560），目的是让翻页时
   * 高度稳定、避免末页行数少导致表格塌陷；但该估算既不随窗口变高而变高，也与页面其它区域
   * （页头、提示条、TAB）的实际占位无关，窗口稍高就浪费空间、稍低就溢出。
   *
   * 改为结构性填充后高度由 flex 决定，与当前页实际行数天然无关，翻页稳定性反而更强：
   * 末页行数少也不会塌陷，分页栏不会上跳。
   */

  return (
    <div className="flex flex-1 min-h-0 flex-col gap-3">
      <AnimCard className="flex-1 min-h-0 flex-col p-4" style={{ minHeight: POSITION_TABLE_MIN_HEIGHT }}>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-foreground">{text.positionsTitle}</h2>
        </div>
        {signalsWarning ? (
          <InlineAlert
            variant="warning"
            title={t('decisionSignals.portfolioWarningTitle')}
            message={signalsWarning}
            className="mb-3 rounded-xl px-3 py-2 text-xs shadow-none"
          />
        ) : null}
        {positionRows.length === 0 ? (
          <EmptyState
            type="card"
            title={text.noPositionsTitle}
            description={text.noPositionsDescription}
            className="border-none bg-transparent px-4 py-8 shadow-none"
          />
        ) : (
          <Table<PositionTableRow>
            columns={positionTableColumns}
            rows={pageRows}
            fillHeight
            className={TABLE_TEXT_CLASS}
            pagination={{
              total: totalPositions,
              pageSize: POSITION_PAGE_SIZE,
              pages: totalPages,
              pageNum: safePageNum,
              onPageChange: setPositionPageNum,
            }}
          />
        )}
      </AnimCard>
    </div>
  );
};
