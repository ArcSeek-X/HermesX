/**
 * @file pages/Stock/StockMetricViewPage/components/StockMetricViewConditionEditor.tsx
 * @description 股票度量视图筛选条件编辑器（「显示域 + 编辑按钮 + 模态框表单」三段式）。
 * 显示域只读展示已保存条件；点「编辑条件」打开模态框，表单内可多次新增 / 移除条件（草稿态）；
 * 点「保存」才把整组草稿一次性提交给上层并回显到显示域，取消 / 关闭则丢弃草稿。
 * 纯受控组件：不持有业务条件、不直接发请求，变更一律通过回调上抛。
 * @author Lensgcx (GaoCangxiong)
 */

import { useState } from 'react';
import type React from 'react';
import { Pencil } from 'lucide-react';
import { Chip, HrsButton, HrsNumberField, HrsSelect, Modal } from '@components';
import { useUiLanguage } from '@/contexts/UiLanguageContext';
import type { UiTextKey } from '@/i18n/uiText';
import type {
  StockMetricViewFilterField,
  StockMetricViewFilterItem,
  StockMetricViewFilterOp,
} from '@/types/stockMetricView';
import {
  STOCK_METRIC_FILTERABLE_FIELDS,
  STOCK_METRIC_FILTER_OPS,
} from '@/hooks/useStockMetricView';

/** 筛选字段 → i18n 键（含未在下拉中出现的字段，保证映射完整） */
const FIELD_LABEL_KEY: Record<StockMetricViewFilterField, UiTextKey> = {
  market: 'stockMetricView.filterField.market',
  code: 'stockMetricView.filterField.code',
  price: 'stockMetricView.filterField.price',
  changePct: 'stockMetricView.filterField.changePct',
  totalMarketCap: 'stockMetricView.filterField.totalMarketCap',
  peRatioTTM: 'stockMetricView.filterField.peRatioTTM',
  dividendYieldPct: 'stockMetricView.filterField.dividendYieldPct',
  industry: 'stockMetricView.filterField.industry',
  epsGrowthTtmYoyPct: 'stockMetricView.filterField.epsGrowthTtmYoyPct',
  roePct: 'stockMetricView.filterField.roePct',
  pbRatio: 'stockMetricView.filterField.pbRatio',
  psRatioTTM: 'stockMetricView.filterField.psRatioTTM',
  revenueGrowthYoyPct: 'stockMetricView.filterField.revenueGrowthYoyPct',
};

/** 算子 → i18n 键 */
const OP_LABEL_KEY: Record<StockMetricViewFilterOp, UiTextKey> = {
  eq: 'stockMetricView.op.eq',
  neq: 'stockMetricView.op.neq',
  gt: 'stockMetricView.op.gt',
  gte: 'stockMetricView.op.gte',
  lt: 'stockMetricView.op.lt',
  lte: 'stockMetricView.op.lte',
  between: 'stockMetricView.op.between',
  in: 'stockMetricView.op.in',
};

/** 把表单里的数值归一为 API 形态 */
function buildValue(
  op: StockMetricViewFilterOp,
  single: number | null,
  min: number | null,
  max: number | null,
): StockMetricViewFilterItem['value'] {
  return op === 'between' ? [min ?? null, max ?? null] : (single ?? null);
}

/** 复制整组条件（value 可能是数组，需单独拷贝，避免草稿改写已保存条件） */
function cloneConditions(items: StockMetricViewFilterItem[]): StockMetricViewFilterItem[] {
  return items.map((item) => ({
    ...item,
    value: Array.isArray(item.value) ? [...item.value] : item.value,
  }));
}

/** 组件入参：条件由上层持有，本组件只负责编辑交互与草稿态 */
export interface StockMetricViewConditionEditorProps {
  /** 当前已保存的非市场条件（显示域数据源） */
  conditions: StockMetricViewFilterItem[];
  /** 保存整组条件（模态框点「保存」时触发，整体替换） */
  onSave: (items: StockMetricViewFilterItem[]) => void;
  /** 按序号删除一条已保存条件；不传则显示域不带快捷删除 */
  onRemove?: (index: number) => void;
  /** 是否加载中（禁用编辑入口） */
  isLoading?: boolean;
}

/**
 * 筛选条件编辑器：显示域 + 编辑按钮 + 条件编辑模态框。
 *
 * @param props - 组件属性
 * @param props.conditions - 已保存条件
 * @param props.onSave - 保存整组条件回调
 * @param props.onRemove - 单条快捷删除回调（可选）
 * @param props.isLoading - 加载态
 * @returns 显示域与条件编辑模态框
 */
export function StockMetricViewConditionEditor({
  conditions,
  onSave,
  onRemove,
  isLoading,
}: StockMetricViewConditionEditorProps): React.JSX.Element {
  const { t } = useUiLanguage();

  const [isOpen, setIsOpen] = useState(false);
  // 模态框内的整组条件草稿；保存前不触碰上层 conditions
  const [draftConditions, setDraftConditions] = useState<StockMetricViewFilterItem[]>([]);
  // 单条条件表单的草稿态
  const [draftField, setDraftField] = useState<StockMetricViewFilterField>('price');
  const [draftOp, setDraftOp] = useState<StockMetricViewFilterOp>('gte');
  const [draftSingle, setDraftSingle] = useState<number | null>(null);
  const [draftMin, setDraftMin] = useState<number | null>(null);
  const [draftMax, setDraftMax] = useState<number | null>(null);

  const isBetween = draftOp === 'between';
  // 区间下限大于上限为非法，禁用添加
  const invalidRange =
    isBetween && draftMin != null && draftMax != null && draftMin > draftMax;

  /** 把当前表单值组装成一条条件；无有效值 / 区间非法时返回 null */
  const buildDraftItem = (): StockMetricViewFilterItem | null => {
    if (invalidRange) return null;
    const value = buildValue(draftOp, draftSingle, draftMin, draftMax);
    if (value == null || (Array.isArray(value) && value.every((v) => v == null))) return null;
    return { field: draftField, op: draftOp, value };
  };

  /** 清空数值输入，字段与算子保留，便于连续新增同口径条件 */
  const clearValueDraft = (): void => {
    setDraftSingle(null);
    setDraftMin(null);
    setDraftMax(null);
  };

  /** 打开编辑器：以当前已保存条件为起点，并重置表单草稿 */
  const openEditor = (): void => {
    setDraftConditions(cloneConditions(conditions));
    setDraftField('price');
    setDraftOp('gte');
    clearValueDraft();
    setIsOpen(true);
  };

  /** 关闭编辑器：草稿不回写，下次打开会重新从 conditions 初始化 */
  const closeEditor = (): void => setIsOpen(false);

  /** 把当前表单追加为一条草稿条件 */
  const handleAddDraft = (): void => {
    const item = buildDraftItem();
    if (!item) return;
    setDraftConditions((prev) => [...prev, item]);
    clearValueDraft();
  };

  /** 保存整组草稿；表单里填了但没点「添加条件」的值也一并提交，避免误以为已保存 */
  const handleSave = (): void => {
    const pending = buildDraftItem();
    onSave(pending ? [...draftConditions, pending] : draftConditions);
    setIsOpen(false);
  };

  /** 把条件渲染为可读摘要 */
  const summarize = (item: StockMetricViewFilterItem): string => {
    const fieldLabel = t(FIELD_LABEL_KEY[item.field]);
    const opLabel = t(OP_LABEL_KEY[item.op]);
    if (Array.isArray(item.value)) {
      const [lo, hi] = item.value;
      return `${fieldLabel} ${opLabel} ${lo ?? '*'} ~ ${hi ?? '*'}`;
    }
    return `${fieldLabel} ${opLabel} ${item.value ?? '*'}`;
  };

  const currentItem = buildDraftItem();

  return (
    <div className="flex min-w-0 flex-1 items-start gap-2">
      {/* 显示域：只读回显已保存条件，保存后才更新 */}
      <div className="flex min-h-[38px] min-w-0 flex-1 flex-wrap items-center gap-2 rounded-md border border-subtle px-2 py-1.5">
        {conditions.length === 0 ? (
          <span className="text-xs text-muted-text">{t('stockMetricView.filter.empty')}</span>
        ) : (
          conditions.map((item, index) => (
            <Chip
              key={`${item.field}-${index}`}
              variant="secondary"
              color="accent"
              onClose={onRemove ? () => onRemove(index) : undefined}
            >
              {summarize(item)}
            </Chip>
          ))
        )}
      </div>

      <HrsButton variant="ghost" size="sm" onClick={openEditor} isDisabled={isLoading}>
        <Pencil className="h-3.5 w-3.5" />
        {t('stockMetricView.filter.edit')}
      </HrsButton>

      <Modal isOpen={isOpen} onClose={closeEditor} size="lg">
        <Modal.Header>
          <Modal.Heading>{t('stockMetricView.filter.edit')}</Modal.Heading>
        </Modal.Header>
        <Modal.Body>
          {/* 新增条件表单：字段 / 算子 / 数值区间 + 添加 */}
          <div className="flex flex-wrap items-end gap-2">
            <div className="flex w-[160px] flex-col gap-1">
              <span className="text-xs text-secondary-text">{t('stockMetricView.filter.field')}</span>
              <HrsSelect
                options={STOCK_METRIC_FILTERABLE_FIELDS.map((f) => ({
                  key: f,
                  label: t(FIELD_LABEL_KEY[f]),
                }))}
                value={draftField}
                onChange={(v) => {
                  if (typeof v === 'string') setDraftField(v as StockMetricViewFilterField);
                }}
              />
            </div>
            <div className="flex w-[130px] flex-col gap-1">
              <span className="text-xs text-secondary-text">{t('stockMetricView.filter.op')}</span>
              <HrsSelect
                options={STOCK_METRIC_FILTER_OPS.map((op) => ({ key: op, label: t(OP_LABEL_KEY[op]) }))}
                value={draftOp}
                onChange={(v) => {
                  if (typeof v === 'string') setDraftOp(v as StockMetricViewFilterOp);
                }}
              />
            </div>
            {isBetween ? (
              <>
                <div className="flex w-[120px] flex-col gap-1">
                  <span className="text-xs text-secondary-text">{t('stockMetricView.filter.min')}</span>
                  <HrsNumberField
                    value={draftMin ?? undefined}
                    onChange={(val) => setDraftMin(Number.isNaN(val) ? null : val)}
                  />
                </div>
                <div className="flex w-[120px] flex-col gap-1">
                  <span className="text-xs text-secondary-text">{t('stockMetricView.filter.max')}</span>
                  <HrsNumberField
                    value={draftMax ?? undefined}
                    onChange={(val) => setDraftMax(Number.isNaN(val) ? null : val)}
                  />
                </div>
              </>
            ) : (
              <div className="flex w-[140px] flex-col gap-1">
                <span className="text-xs text-secondary-text">{t('stockMetricView.filter.value')}</span>
                <HrsNumberField
                  value={draftSingle ?? undefined}
                  onChange={(val) => setDraftSingle(Number.isNaN(val) ? null : val)}
                />
              </div>
            )}
            <HrsButton
              variant="secondary"
              size="sm"
              onClick={handleAddDraft}
              isDisabled={invalidRange || !currentItem}
            >
              {t('stockMetricView.filter.add')}
            </HrsButton>
            {invalidRange && (
              <span className="text-xs text-danger">{t('stockMetricView.filter.invalidRange')}</span>
            )}
          </div>

          {/* 草稿条件列表：保存前仅在模态框内可增删，不影响显示域 */}
          {draftConditions.length > 0 && (
            <div className="mt-4 flex flex-col gap-2 border-t border-subtle pt-3">
              <span className="text-xs text-secondary-text">{t('stockMetricView.filter.pending')}</span>
              <div className="flex flex-wrap gap-2">
                {draftConditions.map((item, index) => (
                  <Chip
                    key={`${item.field}-${item.op}-${index}`}
                    variant="secondary"
                    color="accent"
                    onClose={() => setDraftConditions((prev) => prev.filter((_, i) => i !== index))}
                  >
                    {summarize(item)}
                  </Chip>
                ))}
              </div>
            </div>
          )}
        </Modal.Body>
        <Modal.Footer>
          <HrsButton variant="secondary" onClick={closeEditor}>
            {t('common.cancel')}
          </HrsButton>
          <HrsButton variant="primary" onClick={handleSave}>
            {t('stockMetricView.filter.save')}
          </HrsButton>
        </Modal.Footer>
      </Modal>
    </div>
  );
}
