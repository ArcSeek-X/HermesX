/**
 * 持仓总览面板
 *
 * 展示当前账户视图下的组合健康度概览：
 *   资产指标卡（总权益 / 总市值 / 总现金）+ 风险指标卡（回撤监控 / 止损预警 / 口径范围 / AI 风险信号）。
 * 汇率专项刷新入口已移至页面头部（PortfolioPage 顶部操作区），
 * 刷新结果以右上角 Toast 呈现，本组件不再内置汇率状态卡。
 *
 * 数据由主页面按账户范围与成本口径加载后传入，本组件不自行请求接口。
 */

import type React from 'react';
import { useMemo } from 'react';
import { AnimCard, KeyValueCard } from '@components';
import { formatNumber } from '@utils/amountFormat';
import { formatPct } from '@utils/portfolioFormat';
import { buildDecisionActionLabelMap, getDecisionActionLabel } from '@utils/decisionAction';
import { useUiLanguage } from '../../../../contexts/UiLanguageContext';
import { PORTFOLIO_TEXT } from '../../../../locales/featureText';
import type { DecisionSignalItem } from '../../../../types/decisionSignals';
import type { PortfolioRiskResponse, PortfolioSnapshotResponse } from '../../../../types/portfolio';

/** AI 风险信号卡片最多展示的预览条数 */
const AI_RISK_PREVIEW_LIMIT = 3;

/** 持仓总览面板属性 */
interface PortfolioOverviewPanelProps {
  /** 当前视图的持仓快照，null 表示尚未加载成功 */
  snapshot: PortfolioSnapshotResponse | null;
  /** 风险指标数据，null 表示风险模块降级 */
  risk: PortfolioRiskResponse | null;
}

export const PortfolioOverviewPanel: React.FC<PortfolioOverviewPanelProps> = ({
  snapshot,
  risk,
}) => {
  const { language, t } = useUiLanguage();
  const text = PORTFOLIO_TEXT[language];
  const decisionActionLabels = useMemo(() => buildDecisionActionLabelMap(t), [t]);
  /** 快照未落地时的兜底计价币种 */
  const quoteCurrency = snapshot?.currency || 'CNY';
  /** AI 风险信号预览项 */
  const aiRiskPreviewItems = (risk?.decisionSignalRisk?.items ?? []).slice(0, AI_RISK_PREVIEW_LIMIT);

  /** 将决策信号动作转换为可读标签，缺失时回退到「告警」 */
  const formatSignalRiskAction = (signal: Partial<DecisionSignalItem>): string => (
    getDecisionActionLabel(
      signal.action,
      signal.actionLabel,
      null,
      text.alert,
      decisionActionLabels,
    ) ?? text.alert
  );

  return (
    <div className="space-y-3">
      <section className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        <KeyValueCard
          label={text.totalEquity}
          value={formatNumber(snapshot?.totalEquity, { decimals: 2 })}
          preValue={quoteCurrency}
          ordinal={0}
        />

        <KeyValueCard
          label={text.totalMarketValue}
          value={formatNumber(snapshot?.totalMarketValue, { decimals: 2 })}
          preValue={quoteCurrency}
          ordinal={1}
        />

        <KeyValueCard
          label={text.totalCash}
          value={formatNumber(snapshot?.totalCash, { decimals: 2 })}
          preValue={quoteCurrency}
          ordinal={2}
        />

      </section>

      <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
        <AnimCard className="flex-col p-5" gradientBackground ordinal={4}>
          <h3 className="text-sm font-semibold text-foreground mb-2">{text.drawdownMonitor}</h3>
          <div className="text-xs text-foreground-soft space-y-1">
            <div>{text.maxDrawdown}: {formatPct(risk?.drawdown?.maxDrawdownPct)}</div>
            <div>{text.currentDrawdown}: {formatPct(risk?.drawdown?.currentDrawdownPct)}</div>
            <div>{text.alert}: {risk?.drawdown?.alert ? text.yes : text.no}</div>
          </div>
        </AnimCard>

        <AnimCard className="flex-col p-5" gradientBackground ordinal={5}>
          <h3 className="text-sm font-semibold text-foreground mb-2">{text.stopLossWarning}</h3>
          <div className="text-xs text-foreground-soft space-y-1">
            <div>{text.triggeredCount}: {risk?.stopLoss?.triggeredCount ?? 0}</div>
            <div>{text.nearCount}: {risk?.stopLoss?.nearCount ?? 0}</div>
            <div>{text.alert}: {risk?.stopLoss?.nearAlert ? text.yes : text.no}</div>
          </div>
        </AnimCard>

        <AnimCard className="flex-col p-5" gradientBackground ordinal={6}>
          <h3 className="text-sm font-semibold text-foreground mb-2">{text.scope}</h3>
          <div className="text-xs text-foreground-soft space-y-1">
            <div>{text.accountCount}: {snapshot?.accountCount ?? 0}</div>
            <div>{text.currency}: {snapshot?.currency || 'CNY'}</div>
            <div>{text.costMethodShort}: {(snapshot?.costMethod || 'fifo').toUpperCase()}</div>
          </div>
        </AnimCard>

        <AnimCard className="flex-col p-5" gradientBackground ordinal={7}>
          <h3 className="text-sm font-semibold text-foreground mb-2">{text.aiRiskSignals}</h3>
          <div className="text-xs text-foreground-soft space-y-1">
            {risk?.decisionSignalRisk?.available === false ? (
              <div className="text-warning">{text.aiRiskUnavailable}</div>
            ) : (
              <>
                <div>{text.aiRiskTotal}: {risk?.decisionSignalRisk?.total ?? 0}</div>
                <div>
                  {text.sellSignals}: {risk?.decisionSignalRisk?.actions?.sell ?? 0} · {text.reduceSignals}: {risk?.decisionSignalRisk?.actions?.reduce ?? 0} · {text.alertSignals}: {risk?.decisionSignalRisk?.actions?.alert ?? 0}
                </div>
                {aiRiskPreviewItems.length > 0 ? (
                  <div className="space-y-1 pt-1">
                    {aiRiskPreviewItems.map((signal) => (
                      <div
                        key={`${signal.accountId ?? 'all'}-${signal.market}-${signal.symbol}-${signal.signal.id ?? signal.signal.action}`}
                        className="truncate text-foreground"
                      >
                        {signal.symbol} · {formatSignalRiskAction(signal.signal)}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div>{text.noAiRiskSignals}</div>
                )}
              </>
            )}
          </div>
        </AnimCard>
      </section>
    </div>
  );
};
