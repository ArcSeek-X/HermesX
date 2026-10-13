import { lazy, Suspense } from 'react';
import type { EChartsReactProps } from 'echarts-for-react';
import { Loading } from '@/components/common';

type LazyEChartProps = Omit<EChartsReactProps, 'echarts'>;

const ReactECharts = lazy(async () => {
  const [{ echarts }, coreModule] = await Promise.all([
    import('./echartsSetup'),
    import('echarts-for-react/lib/core'),
  ]);

  const EChartsReactCore = coreModule.default;
  const Component = (props: LazyEChartProps) => (
    <EChartsReactCore echarts={echarts} {...props} />
  );
  return { default: Component };
});

export function LazyEChart(props: LazyEChartProps) {
  return (
    <Suspense fallback={<Loading size="md" />}>
      <ReactECharts {...props} />
    </Suspense>
  );
}
