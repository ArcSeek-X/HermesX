/**
 * @file constants/dataSource.ts
 * @description 数据源唯一真源：Key 集合、文案键映射与统一取名（输出格式随输入）。
 * 对外 API：DataSourceKey / DATA_SOURCE_KEYS / resolveDataSourceLabel。
 * 文案在三语 `dataSource.*`，视觉属性在展示组件，本文件都不维护。
 */
import type { UiTextKey, UiTextParams } from '@/i18n/uiText';

/** 数据源标识，与后端回传的 `source` 字段逐字对应（小写） */
export type DataSourceKey = 'eastmoney' | 'tencent' | 'sina' | 'xueqiu' | 'stocksdk' | 'stockdb';

/** Key → 文案键；新增数据源只加这一行 + 三语各补一条文案 */
const LABEL_KEYS = {
  eastmoney: 'dataSource.eastmoney',
  tencent: 'dataSource.tencent',
  sina: 'dataSource.sina',
  xueqiu: 'dataSource.xueqiu',
  stocksdk: 'dataSource.stocksdk',
  stockdb: 'dataSource.stockdb',
} satisfies Record<DataSourceKey, UiTextKey>;

export const DATA_SOURCE_KEYS = Object.keys(LABEL_KEYS) as DataSourceKey[];

type DataSourceTranslator = (key: UiTextKey, params?: UiTextParams) => string;
type DataSourceValue = string | null | undefined;
type DataSourceInput = DataSourceValue | ReadonlyArray<DataSourceValue> | null;
type DataSourceLabels<T> = T extends ReadonlyArray<DataSourceValue> ? string[] : string;

/** 拆分 / 去空 / 去重 / 小写 / 保序；数组元素内的逗号同样拆开 */
function toDataSourceKeys(source: DataSourceInput): string[] {
  const keys = new Set<string>();
  for (const item of Array.isArray(source) ? source : [source]) {
    for (const part of String(item ?? '').split(/[,，]/)) {
      const key = part.trim().toLowerCase();
      if (key) keys.add(key);
    }
  }
  return [...keys];
}

/** 取名：已登记走 i18n，未登记回显原值，空值占位；输出格式随入参 */
export function resolveDataSourceLabel<T extends DataSourceInput>(
  source: T,
  t: DataSourceTranslator,
  fallback = '—',
): DataSourceLabels<T> {
  const labels = [...toDataSourceKeys(source)].map((key) => {
    const labelKey = LABEL_KEYS[key as DataSourceKey];
    return labelKey ? t(labelKey) : key;
  });
  if (Array.isArray(source)) return labels as DataSourceLabels<T>;
  const joined = labels.join(String(source ?? '').includes('，') ? '，' : ',');
  return (joined || fallback) as DataSourceLabels<T>;
}
