/**
 * 投资组合页（编排层）
 *
 * 左侧为账户视图（账户切换 / 新建 / 删除，见 PortfolioAccountViewPanel），
 * 右侧为持仓总览 / 持仓表格 / 集中度 / 事件记录四个页签。
 *
 * 本页持有账户范围与成本口径的单一数据源，负责快照与风险的加载、汇率刷新，
 * 以及页面级提示；各面板自身的下游请求（决策信号、事件记录、集中度派生、
 * 分析提交）由面板自管。
 */

import type React from 'react';
import { useCallback, useEffect, useRef, useState } from 'react';

import { toCnOrEn } from '@utils/uiLanguage';
import { buildFxRefreshFeedback, getFxRefreshFeedbackVariant } from '@utils/portfolioFormat';

import { portfolioApi } from '../../../api/portfolio';
import { getParsedApiError, type ParsedApiError } from '../../../api/error';

import { HrsButton, InlineAlert, InlineToast, TabNav, showToast } from '@components';
import { PageHeader } from '@components/layout/PageLayout/PageHeader';

import { useUiLanguage } from '../../../contexts/UiLanguageContext';
import { formatUiText } from '../../../i18n/uiText';
import { PORTFOLIO_TEXT } from '../../../locales/featureText';
import { usePreference } from '../../../hooks/usePreference';

import type {
  PortfolioCostMethod,
  PortfolioRiskResponse,
  PortfolioSnapshotResponse,
} from '../../../types/portfolio';

import {
  CsvImportModal,
  ManualEntryModal,
  PortfolioAccountViewPanel,
  PortfolioEventsPanel,
  PortfolioFocusPage,
  PortfolioOverviewPanel,
  PortfolioTablePanel,
} from './components';
import { useAccountView } from '../../../hooks';
import type { EntryModalTarget, PortfolioPageLanguage, PortfolioPanel } from './types';

/** 数据质量限制标签的中英文映射 */
const PORTFOLIO_LIMITATION_LABELS: Record<string, Record<PortfolioPageLanguage, string>> = {
  realtime_quote_best_effort: {
    zh: '实时行情为尽力获取',
    en: 'Realtime quotes are best-effort',
  },
  fx_and_cost_basis_partial: {
    zh: '汇率与成本基础为部分口径',
    en: 'FX and cost basis are partial',
  },
  sector_and_risk_metrics_limited: {
    zh: '行业与风险指标覆盖有限',
    en: 'Sector and risk metrics are limited',
  },
};

/** 汇率刷新竞态守卫：视图标识 + 请求序列号，视图变化时序列号递增使在途请求失效 */
interface FxRefreshScope {
  viewKey: string;
  requestId: number;
}

/** 快照 / 风险查询范围 */
interface PortfolioCoreQuery {
  /** 账户 ID，undefined 表示全部账户汇总 */
  accountId?: number;
  costMethod: PortfolioCostMethod;
}

/** 右侧主区页签 */
const PORTFOLIO_PANEL_TABS = [
  { value: 'overview' as PortfolioPanel, label: '持仓总览' },
  { value: 'positions' as PortfolioPanel, label: '持仓表格' },
  { value: 'concentration' as PortfolioPanel, label: '集中度' },
  { value: 'events' as PortfolioPanel, label: '事件记录' },
];

/** 格式化数据质量限制标签为本地化文本，未知标签原样返回 */
function formatPortfolioLimitation(limitation: string, language: PortfolioPageLanguage): string {
  return PORTFOLIO_LIMITATION_LABELS[limitation]?.[language] ?? limitation;
}

const PortfolioPage: React.FC = () => {
  const { language } = useUiLanguage();
  const text = PORTFOLIO_TEXT[language];

  useEffect(() => {
    document.title = text.documentTitle;
  }, [text.documentTitle]);

  /** 右侧主区当前页签 */
  const [activePortfolioTab, setActivePortfolioTab] = useState<PortfolioPanel>('overview');
  /** 当前打开的录入弹窗，null 表示全部关闭 */
  const [entryModalTarget, setEntryModalTarget] = useState<EntryModalTarget | null>(null);
  /** 成本口径：FIFO / 加权平均（持久化） */
  const [costMethod, setCostMethod] = usePreference<PortfolioCostMethod>('portfolio-cost-method', 'fifo');

  // —— 快照与风险 ——
  const [snapshot, setSnapshot] = useState<PortfolioSnapshotResponse | null>(null);
  const [risk, setRisk] = useState<PortfolioRiskResponse | null>(null);
  const [isLoadingSnapshot, setIsLoadingSnapshot] = useState(false);
  const [isRefreshingFx, setIsRefreshingFx] = useState(false);
  const [riskDegradedMessage, setRiskDegradedMessage] = useState<string | null>(null);

  // —— 页面级提示 ——
  const [pageError, setPageError] = useState<ParsedApiError | null>(null);
  const [writeGuardMessage, setWriteGuardMessage] = useState<string | null>(null);
  const [analysisTaskMessage, setAnalysisTaskMessage] = useState<string | null>(null);

  /** 整页刷新自增键：变化时触发对应面板重新查询 */
  const [eventsRefreshTick, setEventsRefreshTick] = useState(0);
  const [signalsRefreshTick, setSignalsRefreshTick] = useState(0);

  /** 统一错误回调：转发给页面全局错误提示 */
  const handleApiError = useCallback((error: unknown) => {
    setPageError(getParsedApiError(error));
  }, []);

  // 账户视图：账户列表、选中范围、新建 / 删除与各账户持仓条数
  const accountView = useAccountView({ snapshot, onError: handleApiError });
  const {
    accounts,
    selectedAccount,
    queryAccountId,
    writableAccount,
    writeBlocked,
    reloadAccounts,
  } = accountView;
  const hasAccounts = accounts.length > 0;

  /** 当前视图标识：账户范围 + 成本口径 */
  const fxRefreshScopeKey = `${selectedAccount === 'all' ? 'all' : `account:${selectedAccount}`}:cost:${costMethod}`;
  /** 汇率刷新竞态守卫，始终指向当前视图的最新序列号 */
  const fxRefreshScopeRef = useRef<FxRefreshScope>({ viewKey: fxRefreshScopeKey, requestId: 0 });

  /** 判断指定刷新上下文是否仍然有效 */
  const isFxRefreshScopeCurrent = (scope: FxRefreshScope) => (
    fxRefreshScopeRef.current.viewKey === scope.viewKey
    && fxRefreshScopeRef.current.requestId === scope.requestId
  );

  /**
   * 按指定范围加载快照与风险：两者分别请求，风险失败时降级为仅展示快照。
   * 每步校验刷新上下文，避免视图切换后旧请求覆盖新状态。
   */
  const loadSnapshotAndRiskInScope = useCallback(async (
    scope: FxRefreshScope,
    query: PortfolioCoreQuery,
  ): Promise<{ ok: boolean; snapshot?: PortfolioSnapshotResponse }> => {
    if (!isFxRefreshScopeCurrent(scope)) return { ok: false };

    setIsLoadingSnapshot(true);
    setRiskDegradedMessage(null);

    try {
      const snapshotData = await portfolioApi.getSnapshot({
        accountId: query.accountId,
        costMethod: query.costMethod,
        includeRealtime: false,
      });
      if (!isFxRefreshScopeCurrent(scope)) return { ok: false };
      const loadedSnapshot = snapshotData;
      setSnapshot(snapshotData);
      setPageError(null);

      try {
        const riskData = await portfolioApi.getRisk({
          accountId: query.accountId,
          costMethod: query.costMethod,
          includeRealtime: false,
        });
        if (!isFxRefreshScopeCurrent(scope)) return { ok: false };
        setRisk(riskData);
        setRiskDegradedMessage(null);
      } catch (riskErr) {
        if (!isFxRefreshScopeCurrent(scope)) return { ok: false };
        setRisk(null);
        setRiskDegradedMessage(getParsedApiError(riskErr).message || '风险数据获取失败，已降级为仅展示快照数据。');
      }
      return { ok: true, snapshot: loadedSnapshot };
    } catch (err) {
      if (!isFxRefreshScopeCurrent(scope)) return { ok: false };
      setSnapshot(null);
      setRisk(null);
      setPageError(getParsedApiError(err));
      return { ok: false };
    } finally {
      // 上下文已过期时由更新的请求负责收尾，避免提前解除加载态
      if (isFxRefreshScopeCurrent(scope)) {
        setIsLoadingSnapshot(false);
      }
    }
  }, []);

  /** 加载当前账户范围与成本口径下的快照 / 风险 */
  const loadSnapshotAndRisk = useCallback(async () => {
    await loadSnapshotAndRiskInScope(
      { viewKey: fxRefreshScopeKey, requestId: fxRefreshScopeRef.current.requestId },
      { accountId: queryAccountId, costMethod },
    );
  }, [fxRefreshScopeKey, queryAccountId, costMethod, loadSnapshotAndRiskInScope]);

  // 视图变化：递增汇率刷新序列号，使在途汇率刷新结果失效
  useEffect(() => {
    fxRefreshScopeRef.current = {
      viewKey: fxRefreshScopeKey,
      requestId: fxRefreshScopeRef.current.requestId + 1,
    };
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsRefreshingFx(false);
  }, [fxRefreshScopeKey]);

  // 账户范围 / 成本口径变化：重新加载快照与风险
  useEffect(() => {
    void loadSnapshotAndRisk();
  }, [loadSnapshotAndRisk]);

  // 写入限制解除时清除提示
  useEffect(() => {
    if (writeBlocked) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setWriteGuardMessage(null);
  }, [writeBlocked]);

  /** 刷新汇率：刷新后按同一上下文重载快照 / 风险，期间视图变化则丢弃结果 */
  const refreshFxRates = useCallback(async () => {
    if (!hasAccounts || isLoadingSnapshot || isRefreshingFx) return;

    const scope: FxRefreshScope = {
      viewKey: fxRefreshScopeKey,
      requestId: fxRefreshScopeRef.current.requestId + 1,
    };
    fxRefreshScopeRef.current = scope;

    try {
      setIsRefreshingFx(true);
      const result = await portfolioApi.refreshFx({ accountId: queryAccountId });
      if (!isFxRefreshScopeCurrent(scope)) return;
      const reloaded = await loadSnapshotAndRiskInScope(scope, { accountId: queryAccountId, costMethod });
      if (!reloaded.ok) return;
      const feedback = buildFxRefreshFeedback(result);
      const toastVariant = getFxRefreshFeedbackVariant(feedback.tone);
      // 右上角 Toast：标题为刷新结果，描述含最新汇率状态 + 反馈文案；手动关闭（duration:0），不自动消失
      showToast({
        title: text.fxRefreshResult,
        description: `${text.fxStatus}：${reloaded.snapshot?.fxStale ? text.stale : text.latest} - ${feedback.text}`,
        variant: toastVariant === 'info' ? 'primary' : toastVariant,
        placement: 'top',
        duration: 5000,
      });
    } catch (err) {
      if (!isFxRefreshScopeCurrent(scope)) return;
      setPageError(getParsedApiError(err));
    } finally {
      if (isFxRefreshScopeCurrent(scope)) {
        setIsRefreshingFx(false);
      }
    }
  }, [hasAccounts, isLoadingSnapshot, isRefreshingFx, fxRefreshScopeKey, queryAccountId, costMethod, loadSnapshotAndRiskInScope, text]);

  /** 刷新全部：账户列表 + 快照 / 风险，并触发事件与决策信号重新查询 */
  const refreshAllData = useCallback(async () => {
    await Promise.all([reloadAccounts(), loadSnapshotAndRisk()]);
    setEventsRefreshTick((current) => current + 1);
    setSignalsRefreshTick((current) => current + 1);
  }, [reloadAccounts, loadSnapshotAndRisk]);

  /** 快照为部分口径时，把限制标签拼接为本地化提示 */
  const snapshotQualityMessage = snapshot?.dataQuality === 'partial' && snapshot.limitations?.length
    ? snapshot.limitations
      .map((limitation) => formatPortfolioLimitation(limitation, toCnOrEn(language)))
      .join(language === 'en' ? '; ' : '；')
    : null;

  return (
    // 高度链（与自选股页一致）：本页未走 AppPage，根节点是 Main 的直接子节点，
    // min-h-full 即可解析为 Main 的内容高度；往下 flex 列 + grid flex-1 min-h-0 +
    // items-stretch，使持仓表格贴底填充剩余高度并随窗口变高而变高。
    // 内容超高时容器随内容长高、由 Main 滚动，不影响长页面。
    <div className="flex min-h-full flex-col gap-4 p-4 md:p-6">
      <PageHeader
        title={text.title}
        description={text.description}
        rightSlot={(
          <div className="flex items-center gap-2">
            <HrsButton
              variant="primary"
              onClick={() => void refreshFxRates()}
              isDisabled={!hasAccounts || isLoadingSnapshot || isRefreshingFx}
            >
              {isRefreshingFx ? text.refreshing : text.refreshFx}
            </HrsButton>
            <HrsButton
              variant="secondary"
              onClick={() => void refreshAllData()}
              isDisabled={isLoadingSnapshot || isRefreshingFx}
            >
              {isLoadingSnapshot ? text.refreshing : text.refreshAll}
            </HrsButton>
          </div>
        )}
      />

      {/* 全局提示区：账户作用域、错误 / 风险降级 / 写入拦截 / 分析任务、快照口径 */}
      {!hasAccounts ? (
        <InlineAlert variant="warning" title={text.noAccountsTitle} message={text.noAccountsMsg} />
      ) : writeBlocked ? (
        <InlineAlert variant="warning" message={text.writeBlocked} />
      ) : (
        <InlineAlert variant="success" message={formatUiText(text.accountLocked, { name: writableAccount?.name ?? '' })} />
      )}
      {pageError ? <InlineToast variant="danger" content={pageError} onClose={() => setPageError(null)} /> : null}
      {riskDegradedMessage ? (
        <InlineAlert variant="warning" title={text.riskDegraded} message={riskDegradedMessage} />
      ) : null}
      {writeGuardMessage ? (
        <InlineAlert variant="warning" title={text.operationHint} message={writeGuardMessage} />
      ) : null}
      {analysisTaskMessage ? (
        <InlineAlert variant="success" title={text.analysisTask} message={analysisTaskMessage} />
      ) : null}
      {snapshotQualityMessage ? (
        <InlineAlert variant="warning" title={text.snapshotPartialTitle} message={snapshotQualityMessage} />
      ) : null}

      <div className="grid grid-cols-1 lg:grid-cols-[240px_minmax(0,1fr)] gap-4 items-stretch flex-1 min-h-0">
        <PortfolioAccountViewPanel
          accountView={accountView}
          costMethod={costMethod}
          onCostMethodChange={(m) => setCostMethod(m)}
        />

        {/* 右栏 flex 列：TabNav 与各非填充面板 shrink-0 保持自然高度，持仓表格面板 flex-1 贴底填充 */}
        <section className="flex h-full min-h-0 flex-col space-y-3">
          <TabNav
            items={PORTFOLIO_PANEL_TABS}
            value={activePortfolioTab}
            onChange={setActivePortfolioTab}
            variant="secondary"
            size="sm"
            ariaLabel="持仓主区切换"
            className="shrink-0"
            rightSlot={(
              <div className="flex flex-wrap items-center gap-2">
                <HrsButton
                  variant="secondary"
                  isDisabled={writeBlocked}
                  onClick={() => setEntryModalTarget('manual')}
                >
                  手工录入
                </HrsButton>
                <HrsButton
                  variant="secondary"
                  isDisabled={writeBlocked}
                  onClick={() => setEntryModalTarget('csv')}
                >
                  券商 CSV 导入
                </HrsButton>
              </div>
            )}
          />

          {activePortfolioTab === 'overview' ? (
            <div className="shrink-0">
              <PortfolioOverviewPanel
                snapshot={snapshot}
                risk={risk}
              />
            </div>
          ) : null}

          {activePortfolioTab === 'positions' ? (
            <PortfolioTablePanel
              snapshot={snapshot}
              queryAccountId={queryAccountId}
              accountsLength={accounts.length}
              signalsRefreshTick={signalsRefreshTick}
              onError={handleApiError}
              onAnalysisMessage={setAnalysisTaskMessage}
            />
          ) : null}

          {activePortfolioTab === 'concentration' ? (
            <div className="shrink-0">
              <PortfolioFocusPage risk={risk} />
            </div>
          ) : null}

          {activePortfolioTab === 'events' ? (
            <div className="shrink-0">
              <PortfolioEventsPanel
                queryAccountId={queryAccountId}
                writeBlocked={writeBlocked}
                writableAccountId={writableAccount?.id}
                refreshTick={eventsRefreshTick}
                onMutated={() => void loadSnapshotAndRisk()}
                onError={handleApiError}
              />
            </div>
          ) : null}
        </section>
      </div>

      <ManualEntryModal
        isOpen={entryModalTarget === 'manual'}
        onClose={() => setEntryModalTarget(null)}
        writableAccountId={writableAccount?.id}
        accountBaseCurrency={writableAccount?.baseCurrency}
        onSuccess={() => void loadSnapshotAndRisk()}
        onError={handleApiError}
        onWriteWarning={setWriteGuardMessage}
      />

      <CsvImportModal
        isOpen={entryModalTarget === 'csv'}
        onClose={() => setEntryModalTarget(null)}
        writableAccountId={writableAccount?.id}
        writeBlocked={writeBlocked}
        onSuccess={() => void loadSnapshotAndRisk()}
        onError={handleApiError}
        onWriteWarning={setWriteGuardMessage}
      />
    </div>
  );
};

export default PortfolioPage;
