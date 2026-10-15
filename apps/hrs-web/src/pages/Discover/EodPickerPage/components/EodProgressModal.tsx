/**
 * @file Discover/EodPickerPage/components/EodProgressModal.tsx
 * @description 尾盘选股进度遮罩：模态头（标题）→ 进度区（旋转指示器 + 百分比进度条 + 阶段文案）
 *   → 分步结果区（每一步过滤出的股票列表）→ 模态脚（取消按钮）。
 *   分步快照由后端阶段性全量下发，组件仅负责渲染，不维护步骤状态机。
 */

import { Check, Loader2 } from 'lucide-react';
import { HrsButton, Modal } from '@components';
import { useUiLanguage } from '../../../../contexts/UiLanguageContext';
import type { EodPickerStep } from '../../../../api/eodPicker';
import { toFullStockSymbol } from '@utils/stock/stockCode';

/** 进度遮罩 Props */
export type EodProgressModalProps = {
  /** 是否打开（页面筛选任务轮询中为 true） */
  isOpen: boolean;
  /** 取消回调：页面层丢弃 taskId 回到开始屏（后端任务继续跑完） */
  onCancel: () => void;
  /** 任务进度百分比 0~100，驱动进度条宽度 */
  progressPercent: number;
  /** 后端阶段文案（如「分时强度计算 4/6」），为空时展示占位符 */
  stageMessage: string;
  /** 各筛选步骤快照：步骤状态 + 该步过滤出的股票 */
  filterSteps: EodPickerStep[];
};

/**
 * 进度遮罩：禁用遮罩点击关闭（避免误触中断轮询），关闭入口为标题 X 与底部取消按钮。
 * 每步渲染状态图标（完成=对勾 / 进行中=旋转指示）、步骤标题与数量，股票列表超高时内部滚动。
 * @param isOpen - 是否打开
 * @param onCancel - 取消回调
 * @param progressPercent - 进度百分比
 * @param stageMessage - 阶段文案
 * @param filterSteps - 分步筛选快照
 */
function EodProgressModal({
  isOpen,
  onCancel,
  progressPercent,
  stageMessage,
  filterSteps,
}: EodProgressModalProps) {
  const { t } = useUiLanguage();

  /** 步骤标题：后端只下发 key（basic / strength），标题走 i18n 与界面语言联动 */
  const resolveStepTitle = (stepKey: string): string =>
    stepKey === 'strength' ? t('eodPicker.running.stepStrength') : t('eodPicker.running.stepBasic');

  return (
    <Modal isOpen={isOpen} onClose={onCancel} size="md" variant="blur" isDismissable={false}>
      <Modal.Header>
        <Modal.Heading>{t('eodPicker.running.title')}</Modal.Heading>
      </Modal.Header>
      <Modal.Body>
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-primary/30 border-t-primary" />
          <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <div className="flex w-full items-center justify-between text-sm">
            <span className="text-secondary-text">{stageMessage || '...'}</span>
            <span className="font-medium">{progressPercent}%</span>
          </div>
        </div>

        {filterSteps.length > 0 && (
          <div className="mt-4 space-y-2">
            {filterSteps.map((step) => (
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
                      ? t('eodPicker.running.stepCount', { count: step.total })
                      : t('eodPicker.running.stepPending')}
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
                    <p className="mt-2 text-[11px] text-muted-text">{t('eodPicker.running.stepEmpty')}</p>
                  )
                )}
              </div>
            ))}
          </div>
        )}
      </Modal.Body>
      <Modal.Footer>
        <HrsButton variant="secondary" size="md" className="w-full" onClick={onCancel}>
          {t('eodPicker.running.cancel')}
        </HrsButton>
      </Modal.Footer>
    </Modal>
  );
}

export default EodProgressModal;
