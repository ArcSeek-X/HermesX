/**
 * @file Discover/ScannerPage/components/ScannerProgressSteps.tsx
 * @description 信号扫描分步面板：扫描过程中按步骤展示每步过滤出的股票列表
 *   （第一步·解析股票池 / 第二步·技术信号扫描）。步骤快照由后端全量下发，组件仅渲染。
 *   扫描页为「左栏配置 + 右栏增量结果」的非模态布局，本组件内联于右栏。
 */

import { Check, Loader2 } from 'lucide-react';
import { useUiLanguage } from '../../../../contexts/UiLanguageContext';
import type { ScannerStep } from '../../../../api/scanner';
import { toFullStockSymbol } from '@utils/stock/stockCode';

/** 分步面板 Props */
export type ScannerProgressStepsProps = {
  /** 各步骤快照：步骤状态 + 该步过滤出的股票 */
  scanSteps: ScannerStep[];
};

/** 每步渲染状态图标（完成=对勾 / 进行中=旋转指示）、步骤标题与数量，股票列表超高时内部滚动。 */
function ScannerProgressSteps({ scanSteps }: ScannerProgressStepsProps) {
  const { t } = useUiLanguage();

  // 后端只下发 key（pool / signal），标题走 i18n 与界面语言联动
  const resolveStepTitle = (stepKey: string): string =>
    stepKey === 'signal' ? t('scanner.running.stepSignal') : t('scanner.running.stepPool');

  return (
    <div className="space-y-2">
      {scanSteps.map((step) => (
        <div key={step.key} className="rounded-lg border border-subtle bg-subtle p-3">
          <div className="flex items-center justify-between text-xs font-medium">
            <span className="flex items-center gap-1.5">
              {step.status === 'done' ? (
                <Check className="h-3.5 w-3.5 text-primary" />
              ) : (
                <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-text" />
              )}
              {resolveStepTitle(step.key)}
            </span>
            <span className="text-muted-text">
              {step.status === 'done'
                ? t('scanner.running.stepCount', { count: step.total })
                : t('scanner.running.stepPending')}
            </span>
          </div>
          {step.stocks.length > 0 ? (
            <ul className="mt-2 max-h-32 overflow-y-auto rounded-md bg-card px-2.5 py-1.5 text-[11px] leading-6 text-secondary-text">
              {step.stocks.map((stock) => (
                <li key={stock.code} className="truncate">
                  {stock.name}（{toFullStockSymbol(stock.code)}）
                </li>
              ))}
            </ul>
          ) : (
            step.status === 'done' && (
              <p className="mt-2 text-[11px] text-muted-text">{t('scanner.running.stepEmpty')}</p>
            )
          )}
        </div>
      ))}
    </div>
  );
}

export default ScannerProgressSteps;
