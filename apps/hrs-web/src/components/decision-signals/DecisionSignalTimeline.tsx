/**
 * DecisionSignalTimeline.tsx
 *
 * 作用简述：
 *   决策信号「时间轴散点图」组件（基于 recharts 的 ScatterChart）。
 *   把一批决策信号按「创建时间（X 轴）× 多空倾向排名（Y 轴）」映射到二维散点，
 *   每个点代表一条信号：点的位置由时间 + rank 决定，颜色由信号族（看多 / 防御 / 中性）
 *   决定，菱形表示 alert/watch 类特殊标记，外层环线由状态决定（实线/虚线、透明度区分）。
 *   支持悬浮 Tooltip 查看详情、点击点选中信号（onSelect），并提供加载 / 错误 / 空 / 截断
 *   等多种状态展示。
 */

import type React from 'react';
import { Activity } from 'lucide-react';
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip as ChartTooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { EmptyState, InlineAlert } from '../common';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import type { UiLanguage, UiTextKey } from '../../i18n/uiText';
import type { DecisionSignalItem, DecisionSignalStatus } from '../../types/decisionSignals';
import { buildDecisionActionLabelMap, getDecisionActionLabel } from '../../utils/decisionAction';
import { getDecisionSignalProfileLabel } from '../../utils/decisionSignalProfile';
import {
  getDecisionSignalHorizonLabel,
} from '../../utils/decisionSignalLabels';
import { parseDecisionSignalDate } from '../../utils/decisionSignalTime';
import { buildTimelineData, type TimelineDatum } from '../../utils/decisionSignalTimeline';

// Y 轴 rank（多空倾向排名）-> 标签映射，范围为 -3（强烈卖出）到 3（强烈买入）。
const RANK_LABELS: Record<number, string> = {
  [-3]: 'sell',
  [-2]: 'reduce',
  [-1]: 'avoid',
  0: 'watch / alert',
  1: 'hold',
  2: 'add',
  3: 'buy',
};

// 信号状态 -> 多语言文案 key 的映射（用于 Tooltip 中状态文本）。
const STATUS_LABEL_KEYS: Record<DecisionSignalStatus, UiTextKey> = {
  active: 'decisionSignals.active',
  expired: 'decisionSignals.expired',
  invalidated: 'decisionSignals.invalidated',
  closed: 'decisionSignals.closed',
  archived: 'decisionSignals.archived',
};

// 语言 -> Intl 区域标识的映射。
const LOCALE_BY_LANGUAGE: Record<UiLanguage, string> = {
  zh: 'zh-CN',
  en: 'en-US',
};

// 组件属性：信号列表、当前选中 id、加载/错误/截断状态、选中回调。
export type DecisionSignalTimelineProps = {
  items: DecisionSignalItem[];
  selectedId?: number | null;
  loading?: boolean;
  error?: string | null;
  truncated?: boolean;
  onSelect: (item: DecisionSignalItem) => void;
};

// 信号时间字段格式化为「月/日 时:分」；无效时间返回 '-'。
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

// 数值格式化为两位小数并去尾零；无效值返回 '-'。
function formatNumber(value: number | null | undefined): string {
  const number = finiteNumber(value);
  if (number === null) return '-';
  return number.toFixed(2).replace(/\.?0+$/, '');
}

// 将值规范为有限数值；null / undefined / NaN / Infinity 统一返回 null。
function finiteNumber(value: number | null | undefined): number | null {
  if (value === null || value === undefined || Number.isNaN(value) || !Number.isFinite(value)) return null;
  return value;
}

// 置信度格式化：比例值（|v|<=1）乘以 100；非比例值原样；无效返回 '-'。
function formatConfidence(value: number | null | undefined): string {
  const number = finiteNumber(value);
  if (number === null) return '-';
  return `${formatNumber(Math.abs(number) <= 1 ? number * 100 : number)}%`;
}

// 自定义散点图形的属性（recharts 注入 cx/cy 与当前数据点 payload）。
type TimelineShapeProps = {
  cx?: number;
  cy?: number;
  payload?: TimelineDatum;
};

// 从 recharts 点击事件中安全提取 TimelineDatum；兼容直接带 item 或包在 payload 中的两种结构。
function getTimelineDatumFromClick(value: unknown): TimelineDatum | null {
  if (!value || typeof value !== 'object') return null;
  const record = value as { item?: unknown; payload?: unknown };
  if (record.item && typeof record.item === 'object') return value as TimelineDatum;
  if (record.payload && typeof record.payload === 'object') return record.payload as TimelineDatum;
  return null;
}

// 单个散点的自定义绘制：状态环 + 主体（菱形或圆形）。
const TimelinePointShape: React.FC<TimelineShapeProps> = ({ cx = 0, cy = 0, payload }) => {
  if (!payload) return null;
  // 终态（terminal）点透明度更低，视觉上呈现「已结束」弱化效果。
  const opacity = payload.terminal ? 0.46 : 0.92;
  // 状态环：位于主体外圈，颜色由 payload.stroke、虚实由 statusDasharray（如虚线表示 expired/invalidated）。
  const statusRing = (
    <circle
      data-testid={`timeline-status-ring-${payload.item.id}`}
      cx={cx}
      cy={cy}
      r={payload.radius + 4}
      fill="none"
      stroke={payload.stroke}
      strokeDasharray={payload.statusDasharray}
      strokeWidth={1.5}
      opacity={payload.terminal ? 0.55 : 0.85}
    />
  );
  // 菱形（rotate 45 的正方形）用于 alert/watch 等特殊标记。
  if (payload.shape === 'diamond') {
    const size = payload.radius;
    return (
      <g>
        {statusRing}
        <rect
          data-testid={`timeline-point-${payload.item.id}`}
          x={cx - size}
          y={cy - size}
          width={size * 2}
          height={size * 2}
          rx={2}
          fill={payload.fill}
          opacity={opacity}
          stroke={payload.stroke}
          strokeWidth={payload.strokeWidth}
          transform={`rotate(45 ${cx} ${cy})`}
        />
      </g>
    );
  }
  // 默认圆形主体。
  return (
    <g>
      {statusRing}
      <circle
        data-testid={`timeline-point-${payload.item.id}`}
        cx={cx}
        cy={cy}
        r={payload.radius}
        fill={payload.fill}
        opacity={opacity}
        stroke={payload.stroke}
        strokeWidth={payload.strokeWidth}
      />
    </g>
  );
};

// 自定义 Tooltip 的属性（recharts 注入 active 与 payload 列表）。
type TimelineTooltipProps = {
  active?: boolean;
  payload?: Array<{ payload?: TimelineDatum }>;
};

// 悬浮提示：展示该信号的关键字段（股票、时间、动作、评分、置信度、周期、状态、来源、画像）。
export const TimelineTooltip: React.FC<TimelineTooltipProps> = ({ active, payload }) => {
  const { language, t } = useUiLanguage();
  const actionLabels = buildDecisionActionLabelMap(t);
  if (!active || !payload?.[0]?.payload) return null;
  const datum = payload[0].payload;
  const item = datum.item;
  const actionLabel = getDecisionActionLabel(
    item.action,
    item.actionLabel,
    null,
    t('decisionSignals.action'),
    actionLabels,
  ) ?? item.action;
  return (
    <div className="rounded-xl border border-border/70 bg-card/95 px-3 py-2 text-xs shadow-card">
      <div className="font-semibold text-foreground">{item.stockName || item.stockCode}</div>
      <div className="mt-2 grid gap-1 text-secondary-text">
        <span>{t('decisionSignals.createdAt')}: {formatDateTime(item.createdAt, language)}</span>
        <span>{t('decisionSignals.action')}: {actionLabel}</span>
        <span>{t('decisionSignals.score')}: {formatNumber(item.score)}</span>
        <span>{t('decisionSignals.confidence')}: {formatConfidence(item.confidence)}</span>
        <span>{t('decisionSignals.horizon')}: {getDecisionSignalHorizonLabel(item.horizon, t)}</span>
        <span>{t('decisionSignals.status')}: {t(STATUS_LABEL_KEYS[item.status])}</span>
        <span>{t('decisionSignals.sourceReport')}: {item.sourceReportId ? `#${item.sourceReportId}` : '-'}</span>
        <span>{t('decisionSignals.profile')}: {getDecisionSignalProfileLabel(item, t)}</span>
      </div>
    </div>
  );
};

// 时间轴散点图主组件：处理加载 / 错误 / 空 / 截断状态并渲染散点图与图例。
export const DecisionSignalTimeline: React.FC<DecisionSignalTimelineProps> = ({
  items,
  selectedId = null,
  loading = false,
  error = null,
  truncated = false,
  onSelect,
}) => {
  const { language, t } = useUiLanguage();
  // 将信号列表转换为散点数据（含 x=时间、rank=y、颜色、形状、状态环等）。
  const data = buildTimelineData(items);
  // 根据选中 id 找到对应数据点，得到其在序列中的序号（用于底部「已选第 N 条」提示）。
  const selectedDatum = selectedId === null ? null : data.find((datum) => datum.item.id === selectedId);
  const selectedIndex = selectedDatum?.index ?? null;

  // 加载态。
  if (loading) {
    return <p className="text-sm text-secondary-text">{t('common.loading')}...</p>;
  }

  // 错误态。
  if (error) {
    return <InlineAlert variant="danger" title={t('decisionSignals.timelineErrorTitle')} message={error} />;
  }

  // 空数据态：展示空状态占位。
  if (items.length === 0) {
    return (
      <EmptyState
        className="border-none bg-transparent py-6 shadow-none"
        title={t('decisionSignals.timelineEmptyTitle')}
        description={t('decisionSignals.timelineEmptyDescription')}
        icon={<Activity className="h-6 w-6" />}
      />
    );
  }

  return (
    // 总容器：纵向排列提示条、图表与图例。
    <div className="space-y-3">
      {/* 截断提示（数据被裁剪时给出 warning） */}
      {truncated ? (
        <InlineAlert
          variant="warning"
          title={t('decisionSignals.timelineTruncatedTitle')}
          message={t('decisionSignals.timelineTruncatedDescription')}
        />
      ) : null}
      {/* 固定高度图表区 */}
      <div className="h-[320px] min-h-[320px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 18, right: 18, bottom: 20, left: 4 }}>
            {/* 仅横向网格线，弱化视觉 */}
            <CartesianGrid stroke="rgba(148, 163, 184, 0.18)" vertical={false} />
            {/* X 轴：时间（数字类型，按数据最小/最大自适应），刻度格式化为日期时间 */}
            <XAxis
              dataKey="x"
              type="number"
              domain={['dataMin', 'dataMax']}
              tickFormatter={(value) => formatDateTime(new Date(Number(value)).toISOString(), language)}
              tick={{ fontSize: 11, fill: 'currentColor' }}
              stroke="rgba(148, 163, 184, 0.5)"
            />
            {/* Y 轴：rank（-3.5~3.5），固定刻度 -3..3，标签由 RANK_LABELS 映射 */}
            <YAxis
              dataKey="rank"
              type="number"
              domain={[-3.5, 3.5]}
              ticks={[-3, -2, -1, 0, 1, 2, 3]}
              tickFormatter={(value) => RANK_LABELS[Number(value)] ?? String(value)}
              tick={{ fontSize: 11, fill: 'currentColor' }}
              stroke="rgba(148, 163, 184, 0.5)"
              width={76}
            />
            {/* 自定义 Tooltip（悬浮即显示详情） */}
            <ChartTooltip
              cursor={{ stroke: 'rgba(148, 163, 184, 0.35)', strokeDasharray: '3 3' }}
              content={(props: unknown) => <TimelineTooltip {...(props as TimelineTooltipProps)} />}
            />
            {/* 散点：关闭动画，点击选中信号，使用自定义图形 */}
            <Scatter
              data={data}
              dataKey="rank"
              isAnimationActive={false}
              onClick={(value: unknown) => {
                const datum = getTimelineDatumFromClick(value);
                if (datum) onSelect(datum.item);
              }}
              shape={(props: unknown) => <TimelinePointShape {...(props as TimelineShapeProps)} />}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      {/* 图例：颜色族（看多/防御/中性）+ 菱形含义说明 + 当前选中项 */}
      <div className="flex flex-wrap gap-3 text-xs text-secondary-text">
        <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-[#16a34a]" />{t('decisionSignals.timelineFamilyBullish')}</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-[#dc2626]" />{t('decisionSignals.timelineFamilyDefensive')}</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-[#0891b2]" />{t('decisionSignals.timelineFamilyNeutral')}</span>
        <span>{t('decisionSignals.timelineAlertShape')}</span>
        {selectedIndex !== null ? <span>{t('decisionSignals.timelineSelected', { index: selectedIndex + 1 })}</span> : null}
      </div>
    </div>
  );
};
