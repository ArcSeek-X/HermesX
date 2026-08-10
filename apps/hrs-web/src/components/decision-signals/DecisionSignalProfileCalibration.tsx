/**
 * DecisionSignalProfileCalibration.tsx
 *
 * 作用简述：
 *   决策信号「画像校准（Profile Calibration）」可视化组件。
 *   用于展示不同投资策略画像（conservative / balanced / aggressive）在历史样本上的
 *   表现校准数据：命中率、平均收益、未命中率、无法评估率、最大不利偏移（MAE）等。
 *   支持两步下钻：
 *     1) 选择某一投资组合画像（profile）；
 *     2) 选择按「周期（horizon）」或「动作（action）」维度做二级拆解，查看子分桶指标。
 *   当样本量不足（sampleSufficient=false）时给出提示，而非展示不可靠指标。
 */

import type React from 'react';
import { useMemo, useState } from 'react';
import type { DecisionAction } from '../../types/analysis';
import type {
  DecisionProfile,
  DecisionSignalHorizon,
  DecisionSignalProfileCalibration as DecisionSignalProfileCalibrationData,
  DecisionSignalProfileCalibrationBucket,
} from '../../types/decisionSignals';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { buildDecisionActionLabelMap } from '../../utils/decisionAction';
import { getDecisionSignalHorizonLabel } from '../../utils/decisionSignalLabels';
import { getDecisionProfileLabel } from '../../utils/decisionSignalProfile';
import { cn } from '../../utils/cn';

// 二级拆解维度：按周期或按动作。
type BreakdownMode = 'horizon' | 'action';

// 可选画像列表（固定三种）。
const PROFILE_OPTIONS: DecisionProfile[] = ['conservative', 'balanced', 'aggressive'];
// 全部动作枚举值（用于类型守卫判断）。
const ACTION_VALUES: DecisionAction[] = ['buy', 'add', 'hold', 'reduce', 'sell', 'watch', 'avoid', 'alert'];
// 全部周期枚举值（用于类型守卫判断）。
const HORIZON_VALUES: DecisionSignalHorizon[] = ['intraday', '1d', '3d', '5d', '10d', 'swing', 'long'];

// 动作类型守卫：判断字符串是否为合法的 DecisionAction。
function isDecisionAction(value: string | undefined): value is DecisionAction {
  return !!value && ACTION_VALUES.includes(value as DecisionAction);
}

// 周期类型守卫：判断字符串是否为合法的 DecisionSignalHorizon。
function isDecisionSignalHorizon(value: string | undefined): value is DecisionSignalHorizon {
  return !!value && HORIZON_VALUES.includes(value as DecisionSignalHorizon);
}

// 数值格式化为百分比字符串；无效值返回空串（由调用方决定展示。
function formatPercent(value: number | null): string {
  if (value === null || Number.isNaN(value)) return '';
  const formatted = Number(value).toFixed(2).replace(/\.?0+$/, '');
  return `${formatted}%`;
}

// 组件属性：接收一份完整的画像校准数据。
type Props = {
  calibration: DecisionSignalProfileCalibrationData;
};

// 画像校准组件：渲染画像选择、整体指标与二级维度拆解。
export const DecisionSignalProfileCalibration: React.FC<Props> = ({ calibration }) => {
  const { t } = useUiLanguage();
  // 构建动作多语言标签映射（依赖 t 变化时重建）。
  const actionLabels = useMemo(() => buildDecisionActionLabelMap(t), [t]);
  // 当前选中的画像（默认 balanced）与拆解维度（默认按 horizon）。
  const [selectedProfile, setSelectedProfile] = useState<DecisionProfile>('balanced');
  const [breakdownMode, setBreakdownMode] = useState<BreakdownMode>('horizon');
  // 按画像聚合的分桶数据。
  const profileBuckets = calibration.breakdowns.decisionProfile;
  // 选中画像对应的整体分桶。
  const selectedProfileBucket = profileBuckets.find(
    (bucket) => bucket.dimensions.decisionProfile === selectedProfile,
  );
  // 未知画像分桶（用于提示说明）。
  const unknownProfileBucket = profileBuckets.find(
    (bucket) => bucket.dimensions.decisionProfile === 'unknown',
  );
  // 根据拆解维度选择对应的二级分桶数组（画像×周期 / 画像×动作）。
  const allChildBuckets = breakdownMode === 'horizon'
    ? calibration.breakdowns.decisionProfileHorizon
    : calibration.breakdowns.decisionProfileAction;
  // 仅保留当前选中画像下的子分桶。
  const childBuckets = allChildBuckets.filter(
    (bucket) => bucket.dimensions.decisionProfile === selectedProfile,
  );

  // 将单个分桶转换为一组指标行（命中率/平均收益/未命中率/无法评估率/MAE），并标注色调。
  const metricRows = (bucket: DecisionSignalProfileCalibrationBucket) => [
    {
      label: t('decisionSignals.profileCalibrationHitRate'),
      value: formatPercent(bucket.hitRatePct),
      tone: 'text-success',
    },
    {
      label: t('decisionSignals.profileCalibrationAverageReturn'),
      value: formatPercent(bucket.avgStockReturnPct),
      tone: 'text-foreground',
    },
    {
      label: t('decisionSignals.profileCalibrationMissRate'),
      value: formatPercent(bucket.missRatePct),
      tone: 'text-danger',
    },
    {
      label: t('decisionSignals.profileCalibrationUnableRate'),
      value: formatPercent(bucket.unableRatePct),
      tone: 'text-warning',
    },
    {
      label: t('decisionSignals.profileCalibrationMae'),
      value: formatPercent(bucket.maxAdverseExcursionPct),
      tone: 'text-warning',
    },
  ];

  // 为二级子分桶生成展示标签：按动作模式取动作标签，按周期模式取周期标签，未知则回退提示。
  const childLabel = (bucket: DecisionSignalProfileCalibrationBucket): string => {
    if (breakdownMode === 'action') {
      const action = bucket.dimensions.action;
      return isDecisionAction(action)
        ? actionLabels[action]
        : t('decisionSignals.profileCalibrationUnknownDimension');
    }
    const horizon = bucket.dimensions.horizon;
    return isDecisionSignalHorizon(horizon)
      ? getDecisionSignalHorizonLabel(horizon, t)
      : t('decisionSignals.profileCalibrationUnknownDimension');
  };

  return (
    // 校准总区块：顶部分隔线 + 标题区。
    <section className="mt-5 border-t border-border/60 pt-5" aria-labelledby="profile-calibration-title">
      {/* 标题 + 描述 + 最小样本量阈值说明 */}
      <div className="max-w-3xl">
        <h3 id="profile-calibration-title" className="text-base font-semibold text-foreground">
          {t('decisionSignals.profileCalibrationTitle')}
        </h3>
        <p className="mt-1 text-sm text-secondary-text">
          {t('decisionSignals.profileCalibrationDescription')}
        </p>
        <p className="mt-1 text-xs text-secondary-text">
          {t('decisionSignals.profileCalibrationThreshold', {
            count: calibration.minimumCompletedSampleSize,
          })}
        </p>
      </div>

      {/* 画像选择：三个可点按钮，选中态高亮，展示「已完成样本数」 */}
      <div className="mt-4 grid gap-2 sm:grid-cols-3">
        {PROFILE_OPTIONS.map((profile) => {
          const bucket = profileBuckets.find((item) => item.dimensions.decisionProfile === profile);
          const completed = bucket?.completed ?? 0;
          const selected = selectedProfile === profile;
          return (
            <button
              key={profile}
              type="button"
              aria-pressed={selected}
              onClick={() => setSelectedProfile(profile)}
              className={cn(
                'rounded-xl border px-3 py-3 text-left transition-colors',
                selected
                  ? 'border-primary/70 bg-primary/10 text-foreground'
                  : 'border-border/60 bg-elevated/30 text-secondary-text hover:border-primary/40 hover:text-foreground',
              )}
            >
              <span className="block text-sm font-medium">{getDecisionProfileLabel(profile, t)}</span>
              <span className="mt-1 block text-xs">
                {t('decisionSignals.profileCalibrationCompletedShort', { count: completed })}
              </span>
            </button>
          );
        })}
      </div>

      {/* 若存在「未知画像」样本，给出提示 */}
      {unknownProfileBucket && unknownProfileBucket.total > 0 ? (
        <p className="mt-3 text-xs text-secondary-text">
          {t('decisionSignals.profileCalibrationUnknownNotice', { count: unknownProfileBucket.total })}
        </p>
      ) : null}

      {/* 选中画像的整体指标卡片：样本量不足时提示，否则展示五项指标 */}
      <div className="mt-4 rounded-xl border border-border/60 bg-elevated/25 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h4 className="text-sm font-semibold text-foreground">
            {getDecisionProfileLabel(selectedProfile, t)}
          </h4>
          <p className="text-xs text-secondary-text">
            {t('decisionSignals.profileCalibrationSampleCounts', {
              completed: selectedProfileBucket?.completed ?? 0,
              total: selectedProfileBucket?.total ?? 0,
            })}
          </p>
        </div>
        {!selectedProfileBucket?.sampleSufficient ? (
          <p className="mt-3 rounded-lg border border-warning/30 bg-warning/10 px-3 py-2 text-sm text-warning">
            {t('decisionSignals.profileCalibrationInsufficient')}
          </p>
        ) : (
          <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
            {metricRows(selectedProfileBucket).map((metric) => (
              <div key={metric.label} className="rounded-lg border border-border/50 bg-background/30 px-3 py-2">
                <p className="text-xs text-secondary-text">{metric.label}</p>
                <p className={cn('mt-1 text-lg font-semibold', metric.tone)}>
                  {metric.value || t('decisionSignals.profileCalibrationUnavailable')}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* MAE（最大不利偏移）说明文字 */}
      <p className="mt-3 text-xs text-secondary-text">
        {t('decisionSignals.profileCalibrationMaeDescription')}
      </p>

      {/* 二级拆解维度切换：按周期 / 按动作 */}
      <div className="mt-5 flex flex-wrap gap-2" aria-label={t('decisionSignals.profileCalibrationBreakdownLabel')}>
        {(['horizon', 'action'] as BreakdownMode[]).map((mode) => (
          <button
            key={mode}
            type="button"
            aria-pressed={breakdownMode === mode}
            onClick={() => setBreakdownMode(mode)}
            className={cn(
              'rounded-lg border px-3 py-2 text-sm transition-colors',
              breakdownMode === mode
                ? 'border-primary/70 bg-primary/10 text-foreground'
                : 'border-border/60 text-secondary-text hover:border-primary/40 hover:text-foreground',
            )}
          >
            {mode === 'horizon'
              ? t('decisionSignals.profileCalibrationByHorizon')
              : t('decisionSignals.profileCalibrationByAction')}
          </button>
        ))}
      </div>

      {/* 二级子分桶列表：无样本时提示，否则按卡片网格展示各子维度指标 */}
      {childBuckets.length === 0 ? (
        <p className="mt-3 text-sm text-secondary-text">
          {t('decisionSignals.profileCalibrationNoBreakdownSamples')}
        </p>
      ) : (
        <div className="mt-3 grid gap-3 lg:grid-cols-2">
          {childBuckets.map((bucket) => {
            const label = childLabel(bucket);
            return (
              <article
                key={`${selectedProfile}-${breakdownMode}-${label}`}
                className="rounded-xl border border-border/60 bg-elevated/25 p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h5 className="text-sm font-semibold text-foreground">{label}</h5>
                  <p className="text-xs text-secondary-text">
                    {t('decisionSignals.profileCalibrationSampleCounts', {
                      completed: bucket.completed,
                      total: bucket.total,
                    })}
                  </p>
                </div>
                {!bucket.sampleSufficient ? (
                  <p className="mt-3 rounded-lg border border-warning/30 bg-warning/10 px-3 py-2 text-sm text-warning">
                    {t('decisionSignals.profileCalibrationInsufficient')}
                  </p>
                ) : (
                  <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
                    {metricRows(bucket).map((metric) => (
                      <div key={metric.label} className="rounded-lg border border-border/50 bg-background/30 px-3 py-2">
                        <p className="text-xs text-secondary-text">{metric.label}</p>
                        <p className={cn('mt-1 text-base font-semibold', metric.tone)}>
                          {metric.value || t('decisionSignals.profileCalibrationUnavailable')}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
};
