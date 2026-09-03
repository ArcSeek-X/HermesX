/**
 * 板块资金流向折线图
 *
 * 职责：
 * - 接收板块资金流历史数据（SectorFundFlowResponse）
 * - 渲染 ECharts 多折线图（横轴=日期，纵轴=主力净流入/亿）
 * - 处理空数据态
 *
 * 数据来源：东方财富 push2his 日线资金流（klt=101）
 * 单位：亿（后端已完成 元→亿 转换，保留 2 位小数）
 */
import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import type { SectorFundFlowResponse } from '../../api/sectorData';
import { STOCK_UP_COLOR, STOCK_DOWN_COLOR, getThemeColors } from '../../constants/stockColor';

type SectorFundFlowChartProps = {
  data: SectorFundFlowResponse;
  height?: string;
};

/** 格式化金额（亿），保留 2 位小数，带正负号 */
function formatFlowValue(value: number | null): string {
  if (value == null || Number.isNaN(value)) return '--';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(2)}`;
}

/**
 * 板块资金流向折线图
 *
 * 横轴：日期；纵轴：主力净流入（亿）
 * 折线颜色由后端按 latest 绝对值分配色阶
 */
export function SectorFundFlowChart({ data, height = '500px' }: SectorFundFlowChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  // 初始化 / 销毁
  useEffect(() => {
    if (!chartRef.current) return;
    const chart = echarts.init(chartRef.current);
    chartInstance.current = chart;

    const handleResize = () => chart.resize();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.dispose();
      chartInstance.current = null;
    };
  }, []);

  // 数据更新
  useEffect(() => {
    const chart = chartInstance.current;
    if (!chart) return;

    const { dates, sectors } = data;
    if (!dates.length || !sectors.length) return;

    const colors = getThemeColors();

    const option: echarts.EChartsOption = {
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(20,20,30,0.9)',
        borderColor: '#333',
        textStyle: { color: '#eee', fontSize: 12 },
        formatter: (params: unknown) => {
          const items = params as Array<{
            seriesName: string;
            value: number | null;
            color: string;
            axisValueLabel: string;
          }>;
          if (!Array.isArray(items) || items.length === 0) return '';
          const date = items[0].axisValueLabel;
          let html = `<div style="font-weight:600;margin-bottom:6px;">${date}</div>`;
          // 按绝对值降序排列
          const sorted = [...items].sort(
            (a, b) => Math.abs(b.value ?? 0) - Math.abs(a.value ?? 0)
          );
          for (const item of sorted) {
            const val = item.value;
            const display = formatFlowValue(val);
            const color =
              val != null && val > 0 ? STOCK_UP_COLOR : val != null && val < 0 ? STOCK_DOWN_COLOR : '#888';
            html += `
              <div style="display:flex;justify-content:space-between;gap:16px;margin-bottom:2px;">
                <span style="display:flex;align-items:center;gap:4px;">
                  <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${item.color};"></span>
                  ${item.seriesName}
                </span>
                <span style="color:${color};font-weight:500;">${display} 亿</span>
              </div>`;
          }
          return html;
        },
      },
      legend: {
        data: sectors.map((s) => s.name),
        textStyle: { color: colors.textColor, fontSize: 11 },
        top: 0,
        type: 'scroll',
        pageTextStyle: { color: colors.textColor },
      },
      grid: { left: 60, right: 20, top: 40, bottom: 70 },
      xAxis: {
        type: 'category',
        data: dates,
        boundaryGap: false,
        axisLine: { lineStyle: { color: colors.axisLineColor } },
        axisLabel: { color: colors.textColor, fontSize: 11, interval: 3 },
      },
      yAxis: {
        type: 'value',
        name: '亿',
        nameTextStyle: { color: colors.textColor, fontSize: 11 },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { color: colors.splitLineColor, type: 'dashed' } },
        axisLabel: {
          color: colors.textColor,
          fontSize: 11,
          formatter: (v: number) => {
            if (Math.abs(v) < 0.005) return `{zero|${v.toFixed(2)}}`;
            if (v > 0) return `{up|${v.toFixed(2)}}`;
            return `{down|${v.toFixed(2)}}`;
          },
          rich: {
            up: { color: STOCK_UP_COLOR, fontWeight: 'bold', fontSize: 11 },
            down: { color: STOCK_DOWN_COLOR, fontWeight: 'bold', fontSize: 11 },
            zero: { color: '#999999', fontWeight: 'bold', fontSize: 11 },
          },
        },
      },
      dataZoom: [
        { type: 'inside', xAxisIndex: [0], start: 0, end: 100 },
        {
          type: 'slider',
          xAxisIndex: [0],
          bottom: 4,
          height: 24,
          start: 0,
          end: 100,
          textStyle: { color: colors.textColor, fontSize: 10 },
          borderColor: colors.axisLineColor,
          fillerColor: 'rgba(0, 212, 255, 0.15)',
          handleStyle: { color: '#00d4ff', borderWidth: 1 },
          moveHandleSize: 6,
          showDetail: false,
        },
      ],
      series: sectors.map((s) => ({
        name: s.name,
        type: 'line' as const,
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { width: 1.5, color: s.color },
        itemStyle: { color: s.color },
        data: s.series,
        emphasis: { focus: 'series' as const },
        connectNulls: false,
      })),
    };

    chart.setOption(option, true);
  }, [data]);

  if (!data.dates.length || !data.sectors.length) {
    return null;
  }

  return <div ref={chartRef} style={{ width: '100%', height }} />;
}
