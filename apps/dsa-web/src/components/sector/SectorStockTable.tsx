/**
 * 顶部 - 板块个股详情表格组件
 *
 * 展示某个板块下所有个股的详细行情数据，包括：
 * 代码、名称、最新价、涨跌幅、涨跌额、成交量、成交额、振幅、换手率
 *
 * 功能：
 * - 支持返回按钮回到板块总览
 * - 加载中显示 spinner
 * - 空数据显示「暂无数据」
 * - 涨跌相关字段使用全局股票颜色工具类（stock-up / stock-down / stock-flat）
 *
 * 数据来源：父组件通过 props 传入 sectorName 和 stocks
 */
import type React from 'react';
import { Card } from '../common';
import { useUiLanguage } from '../../contexts/UiLanguageContext';
import type { StockItem } from '../../api/sectorData';

/** 组件 Props 类型 */
type SectorStockTableProps = {
  /** 板块名称 */
  sectorName: string;
  /** 个股列表 */
  stocks: StockItem[];
  /** 是否正在加载 */
  loading: boolean;
  /** 返回板块总览回调 */
  onBack: () => void;
};

/**
 * 格式化数值（带单位）
 * 大于等于 1 亿显示为「X.XX亿」，大于等于 1 万显示为「X.XX万」，否则保留原始小数
 * 用于成交量、成交额等字段的显示
 */
function formatNumber(value: number | undefined | null, decimals = 2): string {
  if (value == null || Number.isNaN(value)) return '--';
  if (value === 0) return '0';
  if (Math.abs(value) >= 1e8) return `${(value / 1e8).toFixed(decimals)}亿`;
  if (Math.abs(value) >= 1e4) return `${(value / 1e4).toFixed(decimals)}万`;
  return value.toFixed(decimals);
}

/** 格式化百分比，带正负号前缀（如 +2.35%、-1.20%） */
function formatPercent(value: number | undefined | null): string {
  if (value == null || Number.isNaN(value)) return '--';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}%`;
}

/** 安全地格式化数值，保留指定小数位，null/NaN 返回 '--' */
function safeNumber(value: number | undefined | null, decimals = 2): string {
  if (value == null || Number.isNaN(value)) return '--';
  return value.toFixed(decimals);
}

/**
 * 根据涨跌值返回对应的全局颜色工具类名
 * 正值 → stock-up（红），负值 → stock-down（绿），零或空 → stock-flat（灰）
 */
function getKChangeColor(value: number | undefined | null): string {
  if (value == null || Number.isNaN(value)) return 'stock-flat';
  if (value > 0) return 'stock-up';
  if (value < 0) return 'stock-down';
  return 'stock-flat';
}

/** 板块个股表格主组件 */
export const SectorStockTable: React.FC<SectorStockTableProps> = ({
  sectorName,
  stocks,
  loading,
  onBack,
}) => {
  const { t } = useUiLanguage();

  return (
    <Card title={sectorName} className="space-y-4">
      {/* 顶部：返回按钮 + 个股数量 */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={onBack}
          className="text-sm text-secondary-text hover:text-foreground transition-colors"
        >
          ← 返回板块总览
        </button>
        <span className="text-xs text-muted-text">
          {t('common.itemsCount', { count: stocks.length })}
        </span>
      </div>

      {/* 内容区域：加载中 / 空数据 / 表格 */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan/20 border-t-cyan" />
        </div>
      ) : stocks.length === 0 ? (
        <div className="py-12 text-center text-muted-text">
          暂无数据
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            {/* 表头：代码、名称、最新价、涨跌幅、涨跌额、成交量、成交额、振幅、换手率 */}
            <thead>
              <tr className="border-b border-subtle text-xs text-muted-text">
                <th className="px-3 py-2 text-left font-medium">代码</th>
                <th className="px-3 py-2 text-left font-medium">名称</th>
                <th className="px-3 py-2 text-right font-medium">最新价</th>
                <th className="px-3 py-2 text-right font-medium">涨跌幅</th>
                <th className="px-3 py-2 text-right font-medium">涨跌额</th>
                <th className="px-3 py-2 text-right font-medium">成交量</th>
                <th className="px-3 py-2 text-right font-medium">成交额</th>
                <th className="px-3 py-2 text-right font-medium">振幅</th>
                <th className="px-3 py-2 text-right font-medium">换手率</th>
              </tr>
            </thead>
            {/* 表格主体：逐行渲染个股数据，涨跌相关字段使用全局颜色 */}
            <tbody>
              {stocks.map((stock) => (
                <tr
                  key={stock.code}
                  className="border-b border-subtle/50 hover:bg-elevated/50 transition-colors"
                >
                  <td className="px-3 py-2 font-mono text-xs">{stock.code}</td>
                  <td className="px-3 py-2 font-medium">{stock.name}</td>
                  {/* 最新价：根据涨跌幅着色 */}
                  <td className={`px-3 py-2 text-right font-mono ${getKChangeColor(stock.changePercent)}`}>
                    {safeNumber(stock.price)}
                  </td>
                  {/* 涨跌幅：加粗显示，根据涨跌着色 */}
                  <td className={`px-3 py-2 text-right font-mono font-medium ${getKChangeColor(stock.changePercent)}`}>
                    {formatPercent(stock.changePercent)}
                  </td>
                  {/* 涨跌额：带正负号，根据涨跌额着色 */}
                  <td className={`px-3 py-2 text-right font-mono ${getKChangeColor(stock.changeAmount)}`}>
                    {stock.changeAmount != null && stock.changeAmount > 0 ? '+' : ''}{safeNumber(stock.changeAmount)}
                  </td>
                  {/* 成交量：格式化为万/亿 */}
                  <td className="px-3 py-2 text-right font-mono text-xs">
                    {formatNumber(stock.volume, 0)}
                  </td>
                  {/* 成交额：格式化为万/亿 */}
                  <td className="px-3 py-2 text-right font-mono text-xs">
                    {formatNumber(stock.turnover)}
                  </td>
                  {/* 振幅：根据振幅值着色 */}
                  <td className={`px-3 py-2 text-right font-mono text-xs ${getKChangeColor(stock.amplitude)}`}>
                    {safeNumber(stock.amplitude)}%
                  </td>
                  {/* 换手率 */}
                  <td className="px-3 py-2 text-right font-mono text-xs">
                    {safeNumber(stock.turnoverRate)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
};
