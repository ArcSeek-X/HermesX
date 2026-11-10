/**
 * @file Stock/StockMetricViewPage/StockMetricViewPage.tsx
 * @description 股票度量视图页面：组合查询条件区、口径 / 错误提示、结果表格与导出。
 * 业务状态由 useStockMetricView 统一管理，本文件只做编排与布局，不下沉请求逻辑。
 */

import type React from 'react';
import { useCallback, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { AppPage } from '@components/layout/AppPage';
import { PageHeader } from '@components/layout/PageLayout/PageHeader';
import { AnimCard } from '@components';
import { DataRefreshBar } from '@components';
import { showToast } from '@components';
import { HrsButton } from '@components';
import { useUiLanguage } from '@/contexts/UiLanguageContext';
import { useStockMetricView } from '@/hooks/useStockMetricView';
import type { StockMetricViewRow } from '@/types/stockMetricView';
import { StockMetricViewFilterBar } from './components/StockMetricViewFilterBar';
import { StockMetricViewMetricTable } from './components/StockMetricViewMetricTable';
import { buildStockKlinePath, buildStockMetricViewColumns } from './components/stockMetricViewColumns';

const StockMetricViewPage: React.FC = () => {
  const { t } = useUiLanguage();
  const navigate = useNavigate();
  const metricViewModel = useStockMetricView();
  const { exportCsv: exportStockMetricCsv } = metricViewModel;

  useEffect(() => {
    document.title = t('layout.nav.stockMetricView.title');
  }, [t]);

  /** 代码 / 名称列点击：按统一跳转协议直达个股 K 线页（jump2Kline.md §2） */
  const openStockKline = useCallback(
    (row: StockMetricViewRow) => navigate(buildStockKlinePath(row.code)),
    [navigate],
  );

  // 列定义随语言 / 所选市场重算，同时供表格渲染与 CSV 导出（列顺序单一真源）
  const visibleColumns = useMemo(
    () => buildStockMetricViewColumns({
      t,
      selectedMarket: metricViewModel.selectedMarket,
      onOpenKline: openStockKline,
    }),
    [t, metricViewModel.selectedMarket, openStockKline],
  );

  /** 导出列顺序 / 本地化表头直接取当前可见列，避免与表格列定义漂移（AC-7） */
  const exportMetricViewCsv = useCallback(() => {
    void exportStockMetricCsv(visibleColumns.map(({ key, title }) => ({ key, title })));
  }, [exportStockMetricCsv, visibleColumns]);

  // 错误提示：浮层 danger Toast，避免占用页面布局空间（校验 / 请求失败等）
  useEffect(() => {
    if (!metricViewModel.errorMessage) return;
    showToast.danger({
      title: t('stockMetricView.errorTitle'),
      description: metricViewModel.errorMessage,
      duration: 5000,
    });
  }, [metricViewModel.errorMessage, t]);

  // 口径提示：浮层 warning Toast，多条用「；」拼接；仅在口径集合变化时弹出
  const caliberWarning = metricViewModel.warnings.join('；');

  useEffect(() => {
    if (!caliberWarning) return;
    showToast.warning({
      title: t('stockMetricView.caliberTitle'),
      description: caliberWarning,
      duration: 5000,
    });
  }, [caliberWarning, t]);

  return (
    <AppPage fill className="h-full">
      {/* 顶部页头：标题 + 右侧操作区（因子快照日期、行情刷新、CSV 导出） */}
      <PageHeader
        title={t('layout.nav.stockMetricView.title')}
        description={t('layout.nav.stockMetricView.description')}
        rightSlot={
          <div className="flex items-center gap-2">
            {/* 因子口径快照日期：离线因子结算时点，无数据则不展示 */}
            {metricViewModel.asOfDate && (
              <span className="whitespace-nowrap text-xs text-muted-text">
                {t('stockMetricView.factorAsOf', { date: metricViewModel.asOfDate })}
              </span>
            )}
            {/* 行情刷新：手动点击刷新 + 倒计时结束自动刷新 */}
            <DataRefreshBar
              lastUpdate={metricViewModel.quoteUpdatedAt}
              loading={metricViewModel.isLoading}
              onRefresh={metricViewModel.refresh}
              onCountdownEnd={metricViewModel.refresh}
              refreshTitle={t('stockMetricView.refresh')}
            />
            {/* CSV 导出：列顺序与本地化表头取自当前可见列，避免与表格定义漂移 */}
            <HrsButton
              variant="secondary"
              onClick={exportMetricViewCsv}
              isLoading={metricViewModel.isExporting}
            >
              {t('stockMetricView.export')}
            </HrsButton>
          </div>
        }
      />

      {/* 错误 / 口径提示改为浮层 Toast（见下方 useEffect），不占用页面布局空间 */}

      {/* 查询条件区：市场单选、股票搜索、非市场条件编辑，封装于卡片内 */}
      <AnimCard variant="default">
        <StockMetricViewFilterBar metricViewModel={metricViewModel} />
      </AnimCard>

      {/* 结果表格：撑满页面剩余高度（一屏），表头吸顶、表体内部滚动；空态由 emptyTitle / emptyDescription 驱动 */}
      <StockMetricViewMetricTable
        columns={visibleColumns}
        metricViewModel={metricViewModel}
        emptyTitle={t('stockMetricView.emptyTitle')}
        emptyDescription={t('stockMetricView.emptyDescription')}
      />
    </AppPage>
  );
};

export default StockMetricViewPage;
