/**
 * 集中度面板
 *
 * 展示行业（或行业数据不可用时回退个股）维度的集中度饼图，以及展示口径、
 * 板块集中度告警、Top1 权重三行说明。切片与展示维度由本组件基于风险指标自行派生。
 */

import type React from 'react';
import { useMemo } from 'react';
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';
import { Card } from '@components';
import { EmptyState } from '@components/basic/EmptyState';
import { useUiLanguage } from '../../../../contexts/UiLanguageContext';
import { PORTFOLIO_TEXT } from '../../../../locales/featureText';
import { formatPct } from '@utils/portfolioFormat';
import type { PortfolioRiskResponse } from '../../../../types/portfolio';
import type { ConcentrationDimension, ConcentrationSlice } from '../types';

/** 饼图配色（最多 6 个切片循环使用） */
const PIE_COLORS = ['#00d4ff', '#00ff88', '#ffaa00', '#ff7a45', '#7f8cff', '#ff4466'];

/** 集中度面板属性：仅需风险指标，切片与维度由本组件自行派生 */
interface PortfolioFocusPageProps {
  /** 风险指标数据，用于行业/持仓集中度、板块告警与 Top1 权重 */
  risk: PortfolioRiskResponse | null;
}

export const PortfolioFocusPage: React.FC<PortfolioFocusPageProps> = ({ risk }) => {
  const { language } = useUiLanguage();
  const text = PORTFOLIO_TEXT[language];

  /** 行业集中度饼图数据：取前 6 大行业及其权重百分比 */
  const sectorConcentrationSlices = useMemo<ConcentrationSlice[]>(() => {
    const sectors = risk?.sectorConcentration?.topSectors ?? [];
    return sectors
      .slice(0, 6)
      .map((item) => ({ name: item.sector, value: Number(item.weightPct ?? 0) }))
      .filter((item) => item.value > 0);
  }, [risk]);

  /** 持仓集中度回退饼图数据：行业数据不可用时，取前 6 大持仓权重 */
  const positionConcentrationSlices = useMemo<ConcentrationSlice[]>(() => {
    if (!risk?.concentration?.topPositions?.length) return [];
    return risk.concentration.topPositions
      .slice(0, 6)
      .map((item) => ({ name: item.symbol, value: Number(item.weightPct ?? 0) }))
      .filter((item) => item.value > 0);
  }, [risk]);

  /** 优先行业维度，不可用时回退到持仓维度 */
  const concentrationSlices = sectorConcentrationSlices.length > 0 ? sectorConcentrationSlices : positionConcentrationSlices;
  const concentrationDimension: ConcentrationDimension = sectorConcentrationSlices.length > 0 ? 'sector' : 'position';

  return (
    <Card padding="md">
      <h2 className="text-sm font-semibold text-foreground mb-3">
        {concentrationDimension === 'sector' ? text.sectorConcentration : text.positionConcentrationFallback}
      </h2>
      {concentrationSlices.length > 0 ? (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={concentrationSlices} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90}>
                {concentrationSlices.map((slice) => (
                  <Cell key={`cell-${slice.name}`} fill={PIE_COLORS[concentrationSlices.indexOf(slice) % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => `${Number(value).toFixed(2)}%`} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <EmptyState
          type="card"
          title={text.noConcentrationTitle}
          description={text.noConcentrationDescription}
          className="border-none bg-transparent px-4 py-10 shadow-none"
        />
      )}
      <div className="mt-3 text-xs text-foreground-soft space-y-1">
        <div>
          {text.displayScope}: {concentrationDimension === 'sector' ? text.sectorDimension : text.positionDimensionFallback}
        </div>
        <div>{text.sectorAlert}: {risk?.sectorConcentration?.alert ? text.yes : text.no}</div>
        <div>{text.topWeight}: {formatPct(risk?.sectorConcentration?.topWeightPct ?? risk?.concentration?.topWeightPct)}</div>
      </div>
    </Card>
  );
};
