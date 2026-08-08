/**
 * K 线周期选择器
 *
 * 单行按钮组，参考示例图排版：
 * 分时  日K  5日  周K  月K  年K  120分  60分  30分  15分  5分
 *
 * 激活态使用 cyan 高亮
 * 支持 i18n 多语言切换
 */

import type React from 'react';
import type { KLinePeriod } from '../../api/kline';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import { cn } from '../../utils/cn';

type PeriodSelectorProps = {
  period: KLinePeriod;
  onChange: (period: KLinePeriod) => void;
};

/** 周期配置（单行排列，顺序参考示例图） */
const PERIODS: { i18nKey: string; value: KLinePeriod }[] = [
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

export const PeriodSelector: React.FC<PeriodSelectorProps> = ({ period, onChange }) => {
  const { t } = useUiLanguage();

  return (
    <div className="flex w-full justify-end gap-2">
      {PERIODS.map((item) => (
        <button
          key={item.value}
          type="button"
          onClick={() => onChange(item.value)}
          style={{ fontSize: '14px', ...(period === item.value ? { fontWeight: 700 } : {}) }}
          className={cn(
            'min-w-0 px-3 py-2 rounded-md transition-colors text-center truncate',
            period === item.value
              ? 'bg-[var(--nav-active-bg)] text-[hsl(var(--primary))] border border-[var(--nav-active-border)]'
              : 'text-muted-text hover:text-foreground hover:bg-[var(--nav-hover-bg)] border border-transparent',
          )}
        >
          {t(item.i18nKey as any)}
        </button>
      ))}
    </div>
  );
};

export default PeriodSelector;
