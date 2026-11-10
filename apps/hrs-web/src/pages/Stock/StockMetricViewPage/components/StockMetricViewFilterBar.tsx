/**
 * @file pages/Stock/StockMetricViewPage/components/StockMetricViewFilterBar.tsx
 * @description 股票度量视图查询条件区：市场单选、股票搜索、非市场条件的新增 / 编辑 / 回显，
 * 以及查询 / 重置按钮。状态与请求统一由 useStockMetricView 持有，本组件纯受控，通过 metricViewModel 回调上抛。
 */

import type React from 'react';
import { StockSearch } from '@components/StockSearch/StockSearch';
import { CountryMarketSelect, type CountryMarketOptionDef } from '@components';
import { HrsButton } from '@components/basic/HrsButton/HrsButton';
import { useUiLanguage } from '@/contexts/UiLanguageContext';
import type { StockSelectionMeta } from '@/types/stock';
import type { StockMetricViewSupportedMarket } from '@/types/stockMetricView';
import type { UseStockMetricViewResult } from '@/hooks/useStockMetricView';
import { StockMetricViewConditionEditor } from './StockMetricViewConditionEditor';

/** 组件入参：透传整个度量视图模型，状态与回调由 Hook 持有 */
export interface StockMetricViewFilterBarProps {
  metricViewModel: UseStockMetricViewResult;
}

/** 市场国旗：内联 SVG data URI（自包含，避免外链在受限网络下加载失败）。仅 CN / HK / US 三个市场。 */
const MARKET_FLAG_SVGS: Record<string, string> = {
  cn: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 30 20'><rect width='30' height='20' fill='#DE2910'/><path d='M5,2 L5.7,4.03 L7.85,4.07 L6.14,5.37 L6.76,7.43 L5,6.2 L3.24,7.43 L3.86,5.37 L2.15,4.07 L4.3,4.03 Z' fill='#FFDE00'/></svg>",
  hk: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 30 20'><rect width='30' height='20' fill='#DE2910'/><g fill='#fff'><circle cx='15' cy='10' r='2.2'/><g transform='translate(15,10)'><ellipse rx='1.6' ry='4' cx='0' cy='-4'/><ellipse rx='1.6' ry='4' cx='0' cy='-4' transform='rotate(72)'/><ellipse rx='1.6' ry='4' cx='0' cy='-4' transform='rotate(144)'/><ellipse rx='1.6' ry='4' cx='0' cy='-4' transform='rotate(216)'/><ellipse rx='1.6' ry='4' cx='0' cy='-4' transform='rotate(288)'/></g></g></svg>",
  us: "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 30 20'><rect width='30' height='20' fill='#fff'/><rect y='1.54' width='30' height='1.54' fill='#B22234'/><rect y='4.62' width='30' height='1.54' fill='#B22234'/><rect y='7.69' width='30' height='1.54' fill='#B22234'/><rect y='10.77' width='30' height='1.54' fill='#B22234'/><rect y='13.85' width='30' height='1.54' fill='#B22234'/><rect y='16.92' width='30' height='1.54' fill='#B22234'/><rect width='13' height='10.77' fill='#3C3B6E'/></svg>",
};

/** 由市场 ID 生成内联 SVG 国旗 data URI（无对应则空串，组件将不渲染国旗） */
const marketFlagUri = (id: string): string =>
  MARKET_FLAG_SVGS[id] ? `data:image/svg+xml,${encodeURIComponent(MARKET_FLAG_SVGS[id])}` : '';

/** 市场可选项：复用 CountryMarketSelect 数据契约；countryMarketName 直接展示市场代码 */
const MARKET_OPTIONS: CountryMarketOptionDef[] = [
  { countryMarketId: 'cn', countryMarketName: 'CN', currency: 'CNY', currencyName: '人民币', flagUri: marketFlagUri('cn') },
  { countryMarketId: 'hk', countryMarketName: 'HK', currency: 'HKD', currencyName: '港元', flagUri: marketFlagUri('hk') },
  { countryMarketId: 'us', countryMarketName: 'US', currency: 'USD', currencyName: '美元', flagUri: marketFlagUri('us') },
];

/** 把 StockSearch 回传的市场标签收窄为受支持市场；未知值返回 undefined（不切市场） */
function normalizeMarketTag(tag?: string): StockMetricViewSupportedMarket | undefined {
  const lowered = tag?.toLowerCase();
  return lowered === 'cn' || lowered === 'hk' || lowered === 'us' ? lowered : undefined;
}

/** 查询条件区组件 */
export function StockMetricViewFilterBar({
  metricViewModel,
}: StockMetricViewFilterBarProps): React.JSX.Element {
  const { t } = useUiLanguage();
  const {
    conditions,
    selectedMarket,
    setMarketFilter,
    setConditions,
    applyFilters,
    selectStock,
    removeFilter,
    resetFilters,
    isLoading,
  } = metricViewModel;

  // 已选股票代码：从 conditions 的 code 条件派生；重置 / 删除后搜索框同步清空
  const selectedCode = String(conditions.find((item) => item.field === 'code')?.value ?? '');

  /** 下拉选中 / 回车提交：优先用展示代码（不带市场后缀，与后端行 code 一致） */
  const handleStockSubmit = (
    code: string,
    _name?: string,
    _source?: 'manual' | 'autocomplete',
    metadata?: StockSelectionMeta,
  ): void => {
    if (!code) return;
    selectStock(metadata?.displayCode ?? code.split('.')[0], normalizeMarketTag(metadata?.marketTag));
  };

  return (
    <div className="flex w-full items-center justify-between gap-3 p-4 flex-wrap">
      {/* 左组：市场 + 股票 + 条件显示域 / 编辑，占满剩余宽度 */}
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <div className="flex shrink-0 flex-col gap-1">
          <span className="text-xs text-secondary-text">{t('stockMetricView.filter.market')}</span>
          <CountryMarketSelect
            options={MARKET_OPTIONS}
            multiple={false}
            groupBy="flattening"
            value={selectedMarket ? [selectedMarket] : []}
            onChange={(next) => {
              const market = next[0];
              if (market === 'cn' || market === 'hk' || market === 'us') {
                setMarketFilter(market);
              }
            }}
            placeholder={t('stockMetricView.filter.market')}
            className="w-32"
          />
        </div>

        <div className="flex w-[240px] shrink-0 flex-col gap-1">
          <span className="text-xs text-secondary-text">{t('stockMetricView.filter.stock')}</span>
          <StockSearch
            value={selectedCode}
            onChange={() => {}}
            onSubmit={handleStockSubmit}
            onClear={() => selectStock(null)}
            disabled={isLoading}
            ariaLabel={t('stockMetricView.filter.stock')}
          />
        </div>

        {/* 条件显示域 + 编辑按钮 + 模态框表单（保存后才回显） */}
        <StockMetricViewConditionEditor
          conditions={conditions}
          onSave={setConditions}
          onRemove={removeFilter}
          isLoading={isLoading}
        />
      </div>

      {/* 右组：操作按钮贴最右 */}
      <div className="ml-auto flex shrink-0 items-center gap-2">
        <HrsButton variant="primary" size="sm" onClick={applyFilters} isLoading={isLoading}>
          {t('stockMetricView.filter.query')}
        </HrsButton>
        <HrsButton variant="ghost" size="sm" onClick={resetFilters} isDisabled={isLoading}>
          {t('stockMetricView.filter.reset')}
        </HrsButton>
      </div>
    </div>
  );
}
