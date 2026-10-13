import { DEFAULT_FILTERS, type EodPickerFilters } from './eodPicker';

/**
 * 尾盘选股法的本地持久化（照搬参考项目的 localStorage 思路，用本仓库 storage 工具）。
 * - filters：当前筛选条件（防抖保存）
 * 容错：任何解析失败都回退默认值，healFilters 兜底字段缺失。
 */

const FILTERS_KEY = 'hrs.eodPicker.filters';

function readJSON<T>(key: string, fallback: T): T {
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function writeJSON(key: string, value: unknown): void {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* 忽略写入失败（隐私模式 / 配额） */
  }
}

/** 兜底：保证 filters 拥有全部字段且类型正确 */
export function healFilters(input: Partial<EodPickerFilters> | null | undefined): EodPickerFilters {
  const base = DEFAULT_FILTERS;
  const v = (input ?? {}) as Partial<EodPickerFilters>;
  const num = (x: unknown, d: number): number => (typeof x === 'number' && !Number.isNaN(x) ? x : d);
  // 上限字段允许 null（不限制）：仅接受 number 或 null，其余回退默认
  const numOrNull = (x: unknown, d: number): number | null =>
    x === null ? null : typeof x === 'number' && !Number.isNaN(x) ? x : d;
  return {
    circMvMin: num(v.circMvMin, base.circMvMin),
    circMvMax: numOrNull(v.circMvMax, base.circMvMax),
    volumeRatioMin: num(v.volumeRatioMin, base.volumeRatioMin),
    changePctMin: num(v.changePctMin, base.changePctMin),
    changePctMax: numOrNull(v.changePctMax, base.changePctMax),
    turnoverRateMin: num(v.turnoverRateMin, base.turnoverRateMin),
    turnoverRateMax: numOrNull(v.turnoverRateMax, base.turnoverRateMax),
    excludeSt: typeof v.excludeSt === 'boolean' ? v.excludeSt : base.excludeSt,
    strengthMin: num(v.strengthMin, base.strengthMin),
    limit: num(v.limit, base.limit),
  };
}

export function loadFilters(): EodPickerFilters {
  return healFilters(readJSON<Partial<EodPickerFilters>>(FILTERS_KEY, DEFAULT_FILTERS));
}

let filtersSaveTimer: ReturnType<typeof setTimeout> | null = null;
export function saveFiltersDebounced(f: EodPickerFilters, delay = 500): void {
  if (filtersSaveTimer) clearTimeout(filtersSaveTimer);
  filtersSaveTimer = setTimeout(() => writeJSON(FILTERS_KEY, f), delay);
}


