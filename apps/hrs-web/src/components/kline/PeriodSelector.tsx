/**
 * K 线周期选择器组件。
 * 以单行按钮组展示可切换的行情周期（分时 / 日 K / 周 K …），激活态高亮当前周期，文案走 i18n。
 *
 * @author Lensgcx (GaoCangxiong)
 */

import type React from 'react';
import type { KLinePeriod } from '../../api/kline';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { cn } from '../../utils/cn';

/** 周期选项：i18nKey 为展示文案键，value 为对应的 K 线周期标识 */
const KLINE_PERIOD_OPTIONS: { i18nKey: string; value: KLinePeriod }[] = [
  { i18nKey: 'kline.period.1m', value: '1m' },
  { i18nKey: 'kline.period.daily', value: 'daily' },
  { i18nKey: 'kline.period.5d', value: '5d' },
  { i18nKey: 'kline.period.weekly', value: 'weekly' },
  { i18nKey: 'kline.period.monthly', value: 'monthly' },
  { i18nKey: 'kline.period.yearly', value: 'yearly' },
  { i18nKey: 'kline.period.120m', value: '120m' },
  { i18nKey: 'kline.period.60m', value: '60m' },
  { i18nKey: 'kline.period.30m', value: '30m' },
  { i18nKey: 'kline.period.15m', value: '15m' },
  { i18nKey: 'kline.period.5m', value: '5m' },
];

export interface PeriodSelectorProps {
  /** 当前选中的周期，用于高亮激活态，必填 */
  period: KLinePeriod;
  /** 切换周期的回调，接收新选中的周期，必填 */
  onChange: (period: KLinePeriod) => void;
}

export const PeriodSelector: React.FC<PeriodSelectorProps> = ({ period, onChange }) => {
  const { t } = useUiLanguage();

  return (
    <div className="flex w-full justify-end gap-2">
      {KLINE_PERIOD_OPTIONS.map((option) => {
        const isActive = period === option.value;
        return (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            style={{ fontSize: '14px', ...(isActive ? { fontWeight: 700 } : {}) }}
            className={cn(
              'min-w-0 px-3 py-2 rounded-md transition-colors text-center truncate',
              isActive
                ? 'bg-[var(--nav-active-bg)] text-[hsl(var(--primary))] border border-[var(--nav-active-border)]'
                : 'text-muted-text hover:text-foreground hover:bg-[var(--nav-hover-bg)] border border-transparent',
            )}
          >
            {t(option.i18nKey as never)}
          </button>
        );
      })}
    </div>
  );
};

export default PeriodSelector;
