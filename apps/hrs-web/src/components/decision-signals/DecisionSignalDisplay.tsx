/**
 * DecisionSignalDisplay.tsx
 *
 * 作用简述：
 *   决策信号（Decision Signal）的「展示层」组件集合，负责把一份结构化信号数据
 *   （DecisionSignalItem 及其关联的结果 / 反馈）渲染成多种可读 UI：
 *     - DecisionSignalCard：信号卡片（列表项 / 可选中，含操作按钮）。
 *     - DecisionSignalDetails：信号详情（含价格计划、结果、反馈、证据 JSON 等）。
 *     - SignalMetric / SignalTextBlock：可复用的小指标 / 文本块原子组件。
 *     - PortfolioSignalSummary：组合视角的信号一句话摘要。
 *   组件统一依赖各类 decisionSignal* 工具（标签映射、时间解析、画像 / 动作解析）
 *   做本地化与格式化，并通过多语言文案 t() 输出中文 / 英文界面。
 */

import type React from 'react';
import { PanelRightOpen } from 'lucide-react';
import { Badge, Card, JsonViewer } from '../';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import type { UiLanguage, UiTextKey } from '../../i18n/uiText';
import type {
  DecisionSignalFeedbackItem,
  DecisionSignalFeedbackValue,
  DecisionSignalItem,
  DecisionSignalOutcomeItem,
  DecisionSignalOutcomeValue,
  DecisionSignalStatus,
} from '../../types/decisionSignals';
import {
  buildDecisionActionLabelMap,
  getDecisionActionLabel,
  getDecisionActionTone,
  type DecisionActionTone,
} from '../../utils/decisionAction';
import { cn } from '../../utils/cn';
import { parseDecisionSignalDate } from '../../utils/decisionSignalTime';
import { getDecisionSignalProfileLabel } from '../../utils/decisionSignalProfile';
import {
  getDecisionSignalHorizonLabel,
  getDecisionSignalMarketLabel,
  getDecisionSignalMarketPhaseLabel,
  getDecisionSignalPlanQualityLabel,
} from '../../utils/decisionSignalLabels';

// Badge 视觉变体类型（与 common/Badge 组件对齐）。
type BadgeVariant = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'history';

// 信号状态 -> 多语言文案 key 的映射（用于状态 Badge 文本）。
const STATUS_LABEL_KEYS: Record<DecisionSignalStatus, UiTextKey> = {
  active: 'decisionSignals.active',
  expired: 'decisionSignals.expired',
  invalidated: 'decisionSignals.invalidated',
  closed: 'decisionSignals.closed',
  archived: 'decisionSignals.archived',
};

// 信号状态 -> Badge 颜色的映射。
const STATUS_VARIANTS: Record<DecisionSignalStatus, BadgeVariant> = {
  active: 'success',
  expired: 'warning',
  invalidated: 'danger',
  closed: 'default',
  archived: 'history',
};

// 动作语气 -> Badge 颜色的映射（来自 getDecisionActionTone）。
const ACTION_VARIANTS: Record<DecisionActionTone, BadgeVariant> = {
  success: 'success',
  warning: 'warning',
  danger: 'danger',
  default: 'default',
};

// 结果值 -> Badge 颜色的映射。
const OUTCOME_VARIANTS: Record<DecisionSignalOutcomeValue, BadgeVariant> = {
  hit: 'success',
  miss: 'danger',
  neutral: 'warning',
};

// 语言 -> Intl 区域标识的映射。
const LOCALE_BY_LANGUAGE: Record<UiLanguage, string> = {
  zh: 'zh-CN',
  en: 'en-US',
};

// 将信号时间字段格式化为「月/日 时:分」字符串；无效时间返回占位 '-'。
function formatDateTime(value: string | null | undefined, language: UiLanguage): string {
  const date = parseDecisionSignalDate(value);
  if (!date) return '-';
  return new Intl.DateTimeFormat(LOCALE_BY_LANGUAGE[language], {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

// 将数值格式化为两位小数并去掉末尾多余的零；无效值返回 '-'。
function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '-';
  return Number(value).toFixed(2).replace(/\.?0+$/, '');
}

// 在 formatNumber 基础上追加百分号。
function formatPercent(value: number | null | undefined): string {
  const number = formatNumber(value);
  return number === '-' ? number : `${number}%`;
}

// 置信度格式化：若原始值落在 [0,1] 视为比例，乘以 100 转百分比；否则原样加百分号。
function formatConfidence(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '-';
  const normalized = Math.abs(value) <= 1 ? value * 100 : value;
  return `${formatNumber(normalized)}%`;
}

// 入场区间格式化：高低都有时若相等只显示一个，否则显示「低 - 高」；缺省则返回 '-'。
function formatEntryRange(item: DecisionSignalItem): string {
  const hasLow = item.entryLow !== null && item.entryLow !== undefined;
  const hasHigh = item.entryHigh !== null && item.entryHigh !== undefined;
  if (hasLow && hasHigh) {
    return item.entryLow === item.entryHigh
      ? formatNumber(item.entryLow)
      : `${formatNumber(item.entryLow)} - ${formatNumber(item.entryHigh)}`;
  }
  if (hasLow) return formatNumber(item.entryLow);
  if (hasHigh) return formatNumber(item.entryHigh);
  return '-';
}

// 将「类 JSON」值规范为可显示字符串：字符串去空格、基础类型转字符串、对象 JSON 序列化；空值返回 null。
function formatJsonish(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === 'string') return value.trim() || null;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

// 将值转换为 JsonViewer 可接受的数组 / 对象；非数组非对象返回 null。
function asJsonViewerData(value: unknown): Record<string, unknown> | unknown[] | null {
  if (Array.isArray(value)) return value;
  if (value && typeof value === 'object') return value as Record<string, unknown>;
  return null;
}

// 获取动作标签：复用 decisionAction 工具，回退到默认「动作」文案。
function getActionLabel(item: DecisionSignalItem, t: (key: UiTextKey) => string): string {
  return getDecisionActionLabel(
    item.action,
    item.actionLabel,
    null,
    t('decisionSignals.action'),
    buildDecisionActionLabelMap(t),
  ) ?? t('decisionSignals.action');
}

// 获取动作对应的 Badge 变体（依据动作语气）。
function getActionVariant(item: DecisionSignalItem): BadgeVariant {
  return ACTION_VARIANTS[getDecisionActionTone(item.action, item.actionLabel, null)];
}

// 获取结果标签：无效值返回 '-'，否则拼出对应多语言 key。
function getOutcomeLabel(value: DecisionSignalOutcomeValue | null | undefined, t: (key: UiTextKey) => string): string {
  if (!value) return '-';
  const key = `decisionSignals.outcome.${value}` as UiTextKey;
  return t(key);
}

// 获取反馈标签：无效值回退到「无反馈」文案，否则拼出对应 key。
function getFeedbackLabel(value: DecisionSignalFeedbackValue | null | undefined, t: (key: UiTextKey) => string): string {
  if (!value) return t('decisionSignals.feedbackNone');
  const key = `decisionSignals.feedback.${value}` as UiTextKey;
  return t(key);
}

// 判断字符串是否为有效展示值（非占位 '-'）。
function hasDisplayValue(value: string): boolean {
  return value !== '-';
}

// 小指标文字色调类型。
type SignalMetricTone = 'default' | 'success' | 'warning' | 'danger';

// 指标色调 -> 文字颜色类。
const metricToneClass: Record<SignalMetricTone, string> = {
  default: 'text-foreground',
  success: 'text-success',
  warning: 'text-warning',
  danger: 'text-danger',
};

// 单条指标（标签 + 数值）的展示属性。
type SignalMetricProps = {
  label: string;
  value: string;
  tone?: SignalMetricTone;
};

// 单条指标原子组件：小标签 + 数值，数值按色调着色。
const SignalMetric: React.FC<SignalMetricProps> = ({ label, value, tone = 'default' }) => (
  <div className="min-w-0 rounded-xl border border-border/60 bg-elevated/45 px-3 py-2">
    <p className="truncate text-[11px] text-muted-text">{label}</p>
    <p className={cn('mt-1 truncate text-sm font-semibold tabular-nums', metricToneClass[tone])}>{value}</p>
  </div>
);

// 文本块色调类型（普通 / 警告 / 危险 / 信息）。
type SignalTextTone = 'default' | 'warning' | 'danger' | 'info';

// 文本块色调 -> 边框 / 背景 / 文字颜色类。
const textToneClass: Record<SignalTextTone, string> = {
  default: 'border-border/55 bg-elevated/35 text-secondary-text',
  warning: 'border-warning/25 bg-warning/10 text-warning',
  danger: 'border-danger/25 bg-danger/10 text-danger',
  info: 'border-cyan/25 bg-cyan/10 text-cyan',
};

// 文本块（带标签的整段说明文字）展示属性。
type SignalTextBlockProps = {
  label: string;
  value?: string | null;
  tone?: SignalTextTone;
  clamp?: boolean;
};

// 文本块原子组件：空值不渲染；clamp 为真时最多两行省略，否则按原样换行。
const SignalTextBlock: React.FC<SignalTextBlockProps> = ({ label, value, tone = 'default', clamp = true }) => {
  const normalized = value?.trim();
  if (!normalized) return null;
  return (
    <div className={cn('rounded-xl border px-3 py-2.5', textToneClass[tone])}>
      <p className="text-[11px] font-medium text-current/80">{label}</p>
      <p className={cn('mt-1 text-sm leading-5 text-current', clamp ? 'line-clamp-2' : 'whitespace-pre-wrap')}>
        {normalized}
      </p>
    </div>
  );
};

// 信号卡片组件属性：数据项、可选选中回调（传入即视为可交互）、是否选中。
type DecisionSignalCardProps = {
  item: DecisionSignalItem;
  onSelect?: (item: DecisionSignalItem) => void;
  selected?: boolean;
};

// 信号卡片：列表项或详情入口，展示动作 / 状态 / 画像 / 代码、标题、关键指标、价格计划与多段说明。
export const DecisionSignalCard: React.FC<DecisionSignalCardProps> = ({ item, onSelect, selected = false }) => {
  const { language, t } = useUiLanguage();
  const actionLabel = getActionLabel(item, t);
  const profileLabel = getDecisionSignalProfileLabel(item, t);
  const interactive = Boolean(onSelect);
  const entryRange = formatEntryRange(item);
  // 价格计划三段：入场区间、止损（危险色）、目标价（成功色）；过滤掉无值的项。
  const pricePlanItems = [
    { label: t('decisionSignals.entryRange'), value: entryRange, tone: 'default' as const },
    { label: t('decisionSignals.stopLoss'), value: formatNumber(item.stopLoss), tone: 'danger' as const },
    { label: t('decisionSignals.targetPrice'), value: formatNumber(item.targetPrice), tone: 'success' as const },
  ].filter((entry) => hasDisplayValue(entry.value));
  // 外层卡片样式：可交互时加 hover 高亮；选中时青色描边与浅青底。
  const className = cn(
    'block w-full rounded-2xl border bg-card/75 p-4 text-left',
    interactive ? 'transition-colors hover:border-cyan/40 hover:bg-hover/70' : '',
    selected ? 'border-cyan/50 bg-cyan/10' : 'border-border/70',
  );
  const content = (
    <>
      {/* 头部：左上为动作 / 状态 / 画像 Badge + 股票代码，右上为市场与创建时间 */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={getActionVariant(item)}>{actionLabel}</Badge>
            <Badge variant={STATUS_VARIANTS[item.status]}>{t(STATUS_LABEL_KEYS[item.status])}</Badge>
            <Badge variant="info">{t('decisionSignals.profile')}: {profileLabel}</Badge>
            <span className="font-mono text-sm text-secondary-text">{item.stockCode}</span>
          </div>
          <h3 className="mt-2 text-base font-semibold text-foreground">
            {item.stockName || item.stockCode}
          </h3>
        </div>
        <div className="text-right text-xs text-secondary-text">
          <div>{getDecisionSignalMarketLabel(item.market, t)}</div>
          <div className="mt-1">{formatDateTime(item.createdAt, language)}</div>
        </div>
      </div>

      {/* 关键三项指标：评分、置信度、周期 */}
      <div className="mt-4 grid grid-cols-3 gap-2">
        <SignalMetric label={t('decisionSignals.score')} value={formatNumber(item.score)} />
        <SignalMetric label={t('decisionSignals.confidence')} value={formatConfidence(item.confidence)} />
        <SignalMetric label={t('decisionSignals.horizon')} value={getDecisionSignalHorizonLabel(item.horizon, t)} />
      </div>

      {/* 价格计划区：入场区间 / 止损 / 目标价，仅在有值时渲染 */}
      {pricePlanItems.length > 0 ? (
        <div className="mt-3 rounded-xl border border-border/60 bg-elevated/35 px-3 py-2.5">
          <div className="grid gap-2 sm:grid-cols-3">
            {pricePlanItems.map((entry) => (
              <div key={entry.label} className="min-w-0">
                <p className="truncate text-[11px] text-muted-text">{entry.label}</p>
                <p className={cn('mt-1 truncate text-sm font-semibold tabular-nums', metricToneClass[entry.tone])}>
                  {entry.value}
                </p>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* 多段说明文本：理由、催化、关注条件、风险、失效条件（按色调区分） */}
      <div className="mt-3 grid gap-2">
        <SignalTextBlock label={t('decisionSignals.reason')} value={item.reason} />
        <SignalTextBlock label={t('decisionSignals.catalystSummary')} value={item.catalystSummary} tone="info" />
        <SignalTextBlock label={t('decisionSignals.watchConditions')} value={item.watchConditions} />
        <SignalTextBlock label={t('decisionSignals.riskSummary')} value={item.riskSummary} tone="warning" />
        <SignalTextBlock label={t('decisionSignals.invalidation')} value={item.invalidation} tone="danger" />
      </div>

      {/* 底部元信息：计划质量、市场阶段、到期时间、来源报告号 */}
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-text">
        <span>{t('decisionSignals.planQuality')}: {getDecisionSignalPlanQualityLabel(item.planQuality, t)}</span>
        <span>{t('decisionSignals.marketPhase')}: {getDecisionSignalMarketPhaseLabel(item.marketPhase, t)}</span>
        <span>{t('decisionSignals.expiresAt')}: {formatDateTime(item.expiresAt, language)}</span>
        {item.sourceReportId ? <span>{t('decisionSignals.sourceReport')}: #{item.sourceReportId}</span> : null}
      </div>
    </>
  );

  // 非交互卡片：直接渲染内容区。
  if (!interactive) {
    return <div className={className}>{content}</div>;
  }

  // 交互卡片：在内容区下方追加「查看详情」按钮，点击触发选中回调。
  return (
    <div className={className}>
      {content}
      <div className="mt-4 flex justify-end">
        <button
          type="button"
          onClick={() => onSelect?.(item)}
          className="btn-secondary inline-flex items-center gap-1.5 !px-3 !py-1.5 !text-xs"
          aria-label={t('decisionSignals.viewDetailsFor', { stock: item.stockName || item.stockCode })}
        >
          <PanelRightOpen className="h-3.5 w-3.5" />
          {t('common.details')}
        </button>
      </div>
    </div>
  );
};

type DetailRowProps = {
  label: string;
  value?: React.ReactNode;
};

const DetailRow: React.FC<DetailRowProps> = ({ label, value }) => (
  <div className="rounded-xl border border-border/60 bg-elevated/40 px-3 py-2">
    <p className="text-xs text-secondary-text">{label}</p>
    <div className="mt-1 text-sm text-foreground">{value || '-'}</div>
  </div>
);

type DecisionSignalDetailsProps = {
  item: DecisionSignalItem;
  actions?: React.ReactNode;
  outcomes?: DecisionSignalOutcomeItem[];
  outcomesLoading?: boolean;
  outcomesError?: string | null;
  feedback?: DecisionSignalFeedbackItem | null;
  feedbackLoading?: boolean;
  feedbackSaving?: boolean;
  feedbackError?: string | null;
  onFeedbackSubmit?: (value: DecisionSignalFeedbackValue) => void;
};

export const DecisionSignalDetails: React.FC<DecisionSignalDetailsProps> = ({
  item,
  actions,
  outcomes = [],
  outcomesLoading = false,
  outcomesError = null,
  feedback = null,
  feedbackLoading = false,
  feedbackSaving = false,
  feedbackError = null,
  onFeedbackSubmit,
}) => {
  const { language, t } = useUiLanguage();
  const actionLabel = getActionLabel(item, t);
  const profileLabel = getDecisionSignalProfileLabel(item, t);
  const entryRange = formatEntryRange(item);
  // 将证据 / 数据质量 / 元数据转换为 JsonViewer 可渲染结构（无则 null）。
  const evidenceData = asJsonViewerData(item.evidence);
  const qualityData = asJsonViewerData(item.dataQualitySummary);
  const metadataData = asJsonViewerData(item.metadata);

  return (
    // 详情总容器：纵向分区块（space-y-5）。
    <div className="space-y-5">
      {/* 头部：动作 / 状态 / 画像 Badge + 股票名与代码市场；右侧可选操作区 */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={getActionVariant(item)} size="md">{actionLabel}</Badge>
            <Badge variant={STATUS_VARIANTS[item.status]} size="md">{t(STATUS_LABEL_KEYS[item.status])}</Badge>
            <Badge variant="info" size="md">{t('decisionSignals.profile')}: {profileLabel}</Badge>
          </div>
          <h3 className="mt-3 text-xl font-semibold text-foreground">{item.stockName || item.stockCode}</h3>
          <p className="mt-1 font-mono text-sm text-secondary-text">{item.stockCode} · {getDecisionSignalMarketLabel(item.market, t)}</p>
        </div>
        {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
      </div>

      {/* 关键属性网格：评分 / 置信度 / 周期 / 画像 / 计划质量 / 市场阶段 / 来源 / 创建 / 到期 */}
      <div className="grid gap-3 sm:grid-cols-2">
        <DetailRow label={t('decisionSignals.score')} value={formatNumber(item.score)} />
        <DetailRow label={t('decisionSignals.confidence')} value={formatConfidence(item.confidence)} />
        <DetailRow label={t('decisionSignals.horizon')} value={getDecisionSignalHorizonLabel(item.horizon, t)} />
        <DetailRow label={t('decisionSignals.profile')} value={profileLabel} />
        <DetailRow label={t('decisionSignals.planQuality')} value={getDecisionSignalPlanQualityLabel(item.planQuality, t)} />
        <DetailRow label={t('decisionSignals.marketPhase')} value={getDecisionSignalMarketPhaseLabel(item.marketPhase, t)} />
        <DetailRow label={t('decisionSignals.sourceReport')} value={item.sourceReportId ? `#${item.sourceReportId}` : '-'} />
        <DetailRow label={t('decisionSignals.createdAt')} value={formatDateTime(item.createdAt, language)} />
        <DetailRow label={t('decisionSignals.expiresAt')} value={formatDateTime(item.expiresAt, language)} />
      </div>

      {/* 价格计划卡片：入场区间 / 止损 / 目标价 */}
      <Card title={t('decisionSignals.pricePlan')} padding="sm" className="rounded-xl">
        <div className="grid gap-3 sm:grid-cols-3">
          <DetailRow label={t('decisionSignals.entryRange')} value={entryRange} />
          <DetailRow label={t('decisionSignals.stopLoss')} value={formatNumber(item.stopLoss)} />
          <DetailRow label={t('decisionSignals.targetPrice')} value={formatNumber(item.targetPrice)} />
        </div>
      </Card>

      {/* 叙述类内容卡片：理由 / 催化 / 关注条件 / 风险 / 失效（不截断，原样换行） */}
      <Card padding="sm" className="rounded-xl">
        <div className="grid gap-3">
          <SignalTextBlock label={t('decisionSignals.reason')} value={formatJsonish(item.reason)} clamp={false} />
          <SignalTextBlock label={t('decisionSignals.catalystSummary')} value={formatJsonish(item.catalystSummary)} tone="info" clamp={false} />
          <SignalTextBlock label={t('decisionSignals.watchConditions')} value={formatJsonish(item.watchConditions)} clamp={false} />
          <SignalTextBlock label={t('decisionSignals.riskSummary')} value={formatJsonish(item.riskSummary)} tone="warning" clamp={false} />
          <SignalTextBlock label={t('decisionSignals.invalidation')} value={formatJsonish(item.invalidation)} tone="danger" clamp={false} />
        </div>
      </Card>

      {/* 结果评估卡片：按加载 / 错误 / 空 / 列表四种状态渲染，每条含周期、结果 Badge、收益率等 */}
      <Card title={t('decisionSignals.outcomes')} padding="sm" className="rounded-xl">
        {outcomesLoading ? (
          <p className="text-sm text-secondary-text">{t('common.loading')}...</p>
        ) : outcomesError ? (
          <p className="text-sm text-danger">{outcomesError}</p>
        ) : outcomes.length === 0 ? (
          <p className="text-sm text-secondary-text">{t('decisionSignals.noOutcomes')}</p>
        ) : (
          <div className="grid gap-3">
            {outcomes.map((outcome) => (
              <div key={outcome.id} className="rounded-xl border border-border/60 bg-elevated/40 px-3 py-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium text-foreground">{getDecisionSignalHorizonLabel(outcome.horizon, t)}</span>
                    {outcome.outcome ? (
                      <Badge variant={OUTCOME_VARIANTS[outcome.outcome]}>
                        {getOutcomeLabel(outcome.outcome, t)}
                      </Badge>
                    ) : (
                      <Badge variant="warning">{t('decisionSignals.outcome.unable')}</Badge>
                    )}
                  </div>
                  <span className="text-xs text-secondary-text">{outcome.engineVersion}</span>
                </div>
                <div className="mt-3 grid gap-2 sm:grid-cols-3">
                  <DetailRow label={t('decisionSignals.returnPct')} value={formatPercent(outcome.stockReturnPct)} />
                  <DetailRow label={t('decisionSignals.directionExpected')} value={outcome.directionExpected || '-'} />
                  <DetailRow label={t('decisionSignals.unableReason')} value={outcome.unableReason || '-'} />
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* 反馈卡片：展示当前反馈值 / 原因码 / 错误，并提供「有用 / 没用」两个提交按钮 */}
      <Card title={t('decisionSignals.feedbackTitle')} padding="sm" className="rounded-xl">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm text-foreground">
              {feedbackLoading ? `${t('common.loading')}...` : getFeedbackLabel(feedback?.feedbackValue, t)}
            </p>
            {feedback?.reasonCode ? (
              <p className="mt-1 text-xs text-secondary-text">{feedback.reasonCode}</p>
            ) : null}
            {feedbackError ? <p className="mt-2 text-sm text-danger">{feedbackError}</p> : null}
          </div>
          {onFeedbackSubmit ? (
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-secondary !px-3 !py-1.5 !text-xs"
                disabled={feedbackSaving}
                onClick={() => onFeedbackSubmit('useful')}
              >
                {t('decisionSignals.feedback.useful')}
              </button>
              <button
                type="button"
                className="btn-secondary !px-3 !py-1.5 !text-xs"
                disabled={feedbackSaving}
                onClick={() => onFeedbackSubmit('not_useful')}
              >
                {t('decisionSignals.feedback.not_useful')}
              </button>
            </div>
          ) : null}
        </div>
      </Card>

      {/* 原始数据卡片：仅当对应字段存在时才渲染 JSON 查看器（证据 / 数据质量 / 元数据） */}
      {evidenceData ? (
        <Card title={t('decisionSignals.evidence')} padding="sm" className="rounded-xl">
          <JsonViewer data={evidenceData} maxHeight="240px" />
        </Card>
      ) : null}
      {qualityData ? (
        <Card title={t('decisionSignals.dataQuality')} padding="sm" className="rounded-xl">
          <JsonViewer data={qualityData} maxHeight="240px" />
        </Card>
      ) : null}
      {metadataData ? (
        <Card title={t('decisionSignals.metadata')} padding="sm" className="rounded-xl">
          <JsonViewer data={metadataData} maxHeight="240px" />
        </Card>
      ) : null}
    </div>
  );
};

// 组合信号摘要组件属性：可选信号项（无则展示空态）、是否处于加载中。
type PortfolioSignalSummaryProps = {
  item?: DecisionSignalItem;
  loading?: boolean;
};

// 组合视角的信号一句话摘要：在持仓 / 组合列表中紧凑展示当前主信号（动作、周期、风险、关注条件）。
export const PortfolioSignalSummary: React.FC<PortfolioSignalSummaryProps> = ({ item, loading = false }) => {
  const { t } = useUiLanguage();
  // 加载中且尚无数据：展示加载文案。
  if (loading && !item) {
    return <span className="text-xs text-secondary-text">{t('decisionSignals.portfolioLoading')}</span>;
  }
  // 无信号数据：展示空态文案。
  if (!item) {
    return <span className="text-xs text-muted-text">{t('decisionSignals.portfolioEmpty')}</span>;
  }
  const actionLabel = getActionLabel(item, t);
  return (
    // 限制最小 / 最大宽度并左对齐，避免布局抖动。
    <div className="min-w-[11rem] max-w-[18rem] text-left">
      {/* 顶部：动作 Badge + 周期（仅在有周期时显示），整体靠右 */}
      <div className="flex flex-wrap items-center justify-end gap-1.5">
        <Badge variant={getActionVariant(item)}>{actionLabel}</Badge>
        {item.horizon ? <span className="text-[11px] text-secondary-text">{getDecisionSignalHorizonLabel(item.horizon, t)}</span> : null}
      </div>
      {/* 风险摘要（警告色，最多两行）与关注条件（次级文字，最多两行） */}
      {item.riskSummary ? <p className="mt-1 line-clamp-2 text-[11px] text-warning">{item.riskSummary}</p> : null}
      {item.watchConditions ? <p className="mt-1 line-clamp-2 text-[11px] text-secondary-text">{item.watchConditions}</p> : null}
    </div>
  );
};
