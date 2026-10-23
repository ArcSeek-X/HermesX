/**
 * 事件记录面板
 *
 * 自我管理交易 / 资金 / 公司行为三类流水的筛选、分页、抓取与删除；
 * 主页面仅传入当前账户范围（queryAccountId）与写入许可（writeBlocked / writableAccountId），
 * 并在删除后通过 onMutated 触发持仓核心数据刷新。删除等写入型操作在「全部账户只读视图」下禁用。
 */

import type React from 'react';
import { useEffect, useRef, useState } from 'react';
import { AnimCard, HrsButton, HrsInput, HrsSelect, ConfirmDialog } from '@components';
import { EmptyState } from '@components/basic/EmptyState';
import {
  formatCashDirectionLabel,
  formatCorporateActionLabel,
  formatSideLabel,
} from '@utils/portfolioFormat';
import { portfolioApi } from '../../../../api/portfolio';
import type {
  PortfolioCashDirection,
  PortfolioCashLedgerListItem,
  PortfolioCorporateActionListItem,
  PortfolioCorporateActionType,
  PortfolioSide,
  PortfolioTradeListItem,
} from '../../../../types/portfolio';
import type { EventType, PendingEventDelete, PortfolioEventFilters } from '../types';

/** 事件记录默认每页条数 */
const DEFAULT_PAGE_SIZE = 20;

/** 事件记录面板属性 */
interface PortfolioEventsPanelProps {
  /** 当前查询账户 ID，'all' 时为 undefined（只读汇总） */
  queryAccountId?: number;
  /** 是否处于全部账户只读视图：为 true 时禁用删除 */
  writeBlocked: boolean;
  /** 当前可写入账户 ID，删除前再次校验 */
  writableAccountId?: number;
  /** 整页刷新自增键：变化时重新抓取当前页事件 */
  refreshTick?: number;
  /** 删除成功后回调，用于主页面刷新持仓核心数据 */
  onMutated?: () => void;
  /** 统一错误回调，转发给主页面全局错误提示 */
  onError?: (error: unknown) => void;
}

export const PortfolioEventsPanel: React.FC<PortfolioEventsPanelProps> = ({
  queryAccountId,
  writeBlocked,
  writableAccountId,
  refreshTick = 0,
  onMutated,
  onError,
}) => {
  /** 当前筛选条件 */
  const [eventFilters, setEventFilters] = useState<PortfolioEventFilters>({
    eventType: 'trade',
    dateFrom: '',
    dateTo: '',
    symbol: '',
    side: '',
    direction: '',
    actionType: '',
  });
  /** 按字段局部更新筛选条件 */
  const updateEventFilters = (patch: Partial<PortfolioEventFilters>) => {
    setEventFilters((prev) => ({ ...prev, ...patch }));
  };
  const [eventPage, setEventPage] = useState(1);
  const [eventTotal, setEventTotal] = useState(0);
  const [eventLoading, setEventLoading] = useState(false);
  const [tradeEvents, setTradeEvents] = useState<PortfolioTradeListItem[]>([]);
  const [cashEvents, setCashEvents] = useState<PortfolioCashLedgerListItem[]>([]);
  const [corporateEvents, setCorporateEvents] = useState<PortfolioCorporateActionListItem[]>([]);
  /** 待确认删除的事件记录 */
  const [pendingDelete, setPendingDelete] = useState<PendingEventDelete | null>(null);
  const [eventDeleteLoading, setEventDeleteLoading] = useState(false);
  /** 事件查询令牌：每次发起查询递增，陈旧在途请求（如已删除账户）的结果与错误据此丢弃 */
  const eventsLoadTokenRef = useRef(0);

  const totalEventPages = Math.max(1, Math.ceil(eventTotal / DEFAULT_PAGE_SIZE));
  /** 当前事件类型下的事件条数，用于删除最后一条时回退页码 */
  const currentEventCount = eventFilters.eventType === 'trade'
    ? tradeEvents.length
    : eventFilters.eventType === 'cash'
      ? cashEvents.length
      : corporateEvents.length;

  /** 加载事件记录指定页，按事件类型调用对应 API，支持日期/代码/方向等筛选 */
  const loadEventsPage = async (page: number, token: number) => {
    setEventLoading(true);
    try {
      if (eventFilters.eventType === 'trade') {
        const response = await portfolioApi.listTrades({
          accountId: queryAccountId,
          dateFrom: eventFilters.dateFrom || undefined,
          dateTo: eventFilters.dateTo || undefined,
          symbol: eventFilters.symbol || undefined,
          side: eventFilters.side || undefined,
          page,
          pageSize: DEFAULT_PAGE_SIZE,
        });
        if (eventsLoadTokenRef.current !== token) return;
        setTradeEvents(response.items || []);
        setEventTotal(response.total || 0);
      } else if (eventFilters.eventType === 'cash') {
        const response = await portfolioApi.listCashLedger({
          accountId: queryAccountId,
          dateFrom: eventFilters.dateFrom || undefined,
          dateTo: eventFilters.dateTo || undefined,
          direction: eventFilters.direction || undefined,
          page,
          pageSize: DEFAULT_PAGE_SIZE,
        });
        if (eventsLoadTokenRef.current !== token) return;
        setCashEvents(response.items || []);
        setEventTotal(response.total || 0);
      } else {
        const response = await portfolioApi.listCorporateActions({
          accountId: queryAccountId,
          dateFrom: eventFilters.dateFrom || undefined,
          dateTo: eventFilters.dateTo || undefined,
          symbol: eventFilters.symbol || undefined,
          actionType: eventFilters.actionType || undefined,
          page,
          pageSize: DEFAULT_PAGE_SIZE,
        });
        if (eventsLoadTokenRef.current !== token) return;
        setCorporateEvents(response.items || []);
        setEventTotal(response.total || 0);
      }
    } catch (err) {
      if (eventsLoadTokenRef.current !== token) return;
      onError?.(err);
    } finally {
      if (eventsLoadTokenRef.current === token) setEventLoading(false);
    }
  };

  /** 加载事件记录（使用当前页码） */
  const loadEvents = async (token: number) => {
    await loadEventsPage(eventPage, token);
  };

  // 事件记录加载：挂载、页码、筛选条件、账户范围或整页刷新键变化时触发；
  // 每次触发递增令牌，陈旧在途请求（如已删除账户）的结果与错误会被丢弃，避免误报报错。
  useEffect(() => {
    const token = (eventsLoadTokenRef.current += 1);
    void loadEvents(token);
    // loadEvents 每次渲染重建，按数据依赖显式列出触发项
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventPage, eventFilters, queryAccountId, refreshTick]);

  // 筛选条件或账户范围变化时重置到第一页
  useEffect(() => {
    // 数据加载型副作用，按仓库约定关闭该规则
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setEventPage(1);
  }, [eventFilters, queryAccountId]);

  /** 打开删除确认：未锁定具体账户时拦截 */
  const requestDelete = (target: PendingEventDelete) => {
    if (!writableAccountId) return;
    setPendingDelete(target);
  };

  /** 确认删除事件记录：按类型调用对应 API，删除最后一页最后一条时回退到上一页 */
  const confirmDelete = async () => {
    if (!pendingDelete || eventDeleteLoading) return;
    if (!writableAccountId) {
      setPendingDelete(null);
      return;
    }
    const nextPage = currentEventCount === 1 && eventPage > 1 ? eventPage - 1 : eventPage;
    try {
      setEventDeleteLoading(true);
      if (pendingDelete.eventType === 'trade') {
        await portfolioApi.deleteTrade(pendingDelete.eventId);
      } else if (pendingDelete.eventType === 'cash') {
        await portfolioApi.deleteCashLedger(pendingDelete.eventId);
      } else {
        await portfolioApi.deleteCorporateAction(pendingDelete.eventId);
      }
      setPendingDelete(null);
      if (nextPage !== eventPage) {
        setEventPage(nextPage);
      }
      await loadEventsPage(nextPage, (eventsLoadTokenRef.current += 1));
      onMutated?.();
    } catch (err) {
      onError?.(err);
    } finally {
      setEventDeleteLoading(false);
    }
  };

  return (
    <AnimCard className="flex-col p-4">
      <h3 className="text-sm font-semibold text-foreground mb-3">事件记录</h3>
      <div className="space-y-2">
        <div className="grid grid-cols-2 gap-2">
          <HrsSelect
            value={eventFilters.eventType}
            onChange={(v) => updateEventFilters({ eventType: v as EventType })}
            options={[
              { key: 'trade', label: '交易流水' },
              { key: 'cash', label: '资金流水' },
              { key: 'corporate', label: '公司行为' },
            ]}
          />
          <HrsButton variant="secondary" onClick={() => void loadEvents(eventsLoadTokenRef.current += 1)} isDisabled={eventLoading}>
            {eventLoading ? '加载中...' : '刷新流水'}
          </HrsButton>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <HrsInput
            type="date"
            clearable={false}
            className="w-full"
            value={eventFilters.dateFrom}
            onChange={(e) => updateEventFilters({ dateFrom: e.target.value })}
          />
          <HrsInput
            type="date"
            clearable={false}
            className="w-full"
            value={eventFilters.dateTo}
            onChange={(e) => updateEventFilters({ dateTo: e.target.value })}
          />
        </div>

        {(eventFilters.eventType === 'trade' || eventFilters.eventType === 'corporate') ? (
          <HrsInput
            placeholder="按股票代码筛选"
            value={eventFilters.symbol}
            onChange={(e) => updateEventFilters({ symbol: e.target.value })}
          />
        ) : null}

        {eventFilters.eventType === 'trade' ? (
          <HrsSelect
            value={eventFilters.side}
            onChange={(v) => updateEventFilters({ side: v as '' | PortfolioSide })}
            options={[
              { key: '', label: '全部买卖方向' },
              { key: 'buy', label: '买入' },
              { key: 'sell', label: '卖出' },
            ]}
          />
        ) : null}

        {eventFilters.eventType === 'cash' ? (
          <HrsSelect
            value={eventFilters.direction}
            onChange={(v) => updateEventFilters({ direction: v as '' | PortfolioCashDirection })}
            options={[
              { key: '', label: '全部资金方向' },
              { key: 'in', label: '流入' },
              { key: 'out', label: '流出' },
            ]}
          />
        ) : null}

        {eventFilters.eventType === 'corporate' ? (
          <HrsSelect
            value={eventFilters.actionType}
            onChange={(v) => updateEventFilters({ actionType: v as '' | PortfolioCorporateActionType })}
            options={[
              { key: '', label: '全部公司行为' },
              { key: 'cash_dividend', label: '现金分红' },
              { key: 'split_adjustment', label: '拆并股调整' },
            ]}
          />
        ) : null}

        <div className="text-[11px] text-foreground-soft">
          {writeBlocked
            ? '删除修正仅在单账户视图可用。请先选择具体账户后再删除错误流水。'
            : '如有错误流水，可直接删除后重新录入。'}
        </div>

        <div className="max-h-64 overflow-auto rounded-lg border border-white/10 p-2">
          {eventFilters.eventType === 'trade' && tradeEvents.map((trade) => (
            <div key={`trade-${trade.id}`} className="flex items-start justify-between gap-3 border-b border-white/5 py-2 text-xs text-foreground-soft">
              <div className="min-w-0">
                {trade.tradeDate} {formatSideLabel(trade.side)} {trade.symbol} 数量={trade.quantity} 价格={trade.price}
              </div>
              <HrsButton
                variant="danger-soft"
                size="xs"
                isDisabled={writeBlocked}
                onClick={() => requestDelete({
                  eventType: 'trade',
                  eventId: trade.id,
                  confirmMessage: `确认删除 ${trade.tradeDate} 的${formatSideLabel(trade.side)}流水 ${trade.symbol}（数量 ${trade.quantity}，价格 ${trade.price}）吗？`,
                })}
              >
                删除
              </HrsButton>
            </div>
          ))}

          {eventFilters.eventType === 'cash' && cashEvents.map((cash) => (
            <div key={`cash-${cash.id}`} className="flex items-start justify-between gap-3 border-b border-white/5 py-2 text-xs text-secondary">
              <div className="min-w-0">
                {cash.eventDate} {formatCashDirectionLabel(cash.direction)} {cash.amount} {cash.currency}
              </div>
              <HrsButton
                variant="danger-soft"
                size="xs"
                isDisabled={writeBlocked}
                onClick={() => requestDelete({
                  eventType: 'cash',
                  eventId: cash.id,
                  confirmMessage: `确认删除 ${cash.eventDate} 的资金流水（${formatCashDirectionLabel(cash.direction)} ${cash.amount} ${cash.currency}）吗？`,
                })}
              >
                删除
              </HrsButton>
            </div>
          ))}

          {eventFilters.eventType === 'corporate' && corporateEvents.map((action) => (
            <div key={`corporate-${action.id}`} className="flex items-start justify-between gap-3 border-b border-white/5 py-2 text-xs text-secondary">
              <div className="min-w-0">
                {action.effectiveDate} {formatCorporateActionLabel(action.actionType)} {action.symbol}
              </div>
              <HrsButton
                variant="danger-soft"
                size="xs"
                isDisabled={writeBlocked}
                onClick={() => requestDelete({
                  eventType: 'corporate',
                  eventId: action.id,
                  confirmMessage: `确认删除 ${action.effectiveDate} 的公司行为 ${formatCorporateActionLabel(action.actionType)}（${action.symbol}）吗？`,
                })}
              >
                删除
              </HrsButton>
            </div>
          ))}

          {!eventLoading && currentEventCount === 0 ? (
            <EmptyState
              type="card"
              title="暂无流水"
              description="调整筛选条件或先录入一笔交易、资金流水或公司行为。"
              className="border-none bg-transparent px-3 py-6 shadow-none"
            />
          ) : null}
        </div>

        <div className="flex items-center justify-between text-xs text-secondary">
          <span>第 {eventPage} / {totalEventPages} 页</span>
          <div className="flex gap-2">
            <HrsButton variant="secondary" size="xs" isDisabled={eventPage <= 1}
              onClick={() => setEventPage(Math.max(1, eventPage - 1))}>
              上一页
            </HrsButton>
            <HrsButton variant="secondary" size="xs" isDisabled={eventPage >= totalEventPages}
              onClick={() => setEventPage(Math.min(totalEventPages, eventPage + 1))}>
              下一页
            </HrsButton>
          </div>
        </div>
      </div>

      <ConfirmDialog
        isOpen={Boolean(pendingDelete)}
        title="删除错误流水"
        message={pendingDelete?.confirmMessage || '确认删除这条流水吗？'}
        confirmText={eventDeleteLoading ? '删除中...' : '确认删除'}
        cancelText="取消"
        isDanger
        onConfirm={() => void confirmDelete()}
        onCancel={() => {
          if (!eventDeleteLoading) {
            setPendingDelete(null);
          }
        }}
      />
    </AnimCard>
  );
};
