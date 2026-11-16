/**
 * @file newsImportance.ts
 * @description 快讯与消息日历共用的重要度统一业务量纲（0~4）。上游各源的量纲在服务层归一化入口统一为 0~4，
 * 前端据此做筛选，避免多套语义漂移。供 LiveCalendar 系列组件、NewsCard 与 useLiveCalendar 使用。
 * 完整设计见 documents/product/行情资讯/Live-calendar.md §5.7。
 * @author Lensgcx (GaoCangxiong)
 */

/** 重要级，统一业务量纲（与后端 §5.7.2 一一对应） */
export type ImportanceLevel = 0 | 1 | 2 | 3 | 4;

/** 重要级枚举，语义与后端约定对齐 */
export const IMPORTANCE = {
  /** 无：数据源未提供重要度（不是「最低等级」） */
  NONE: 0,
  /** 普通 */
  NORMAL: 1,
  /** 较重要 */
  MINOR: 2,
  /** 重要 */
  IMPORTANT: 3,
  /** 非常重要 */
  CRITICAL: 4,
} as const;

/** 文案映射；`0`（无）不展示文案 */
export const IMPORTANCE_LABELS: Record<ImportanceLevel, string> = {
  0: '',
  1: '普通',
  2: '较重要',
  3: '重要',
  4: '非常重要',
};

/** 全部重要级（升序），供多选筛选判定「是否全选」 */
export const ALL_IMPORTANCE_LEVELS: ImportanceLevel[] = [
  IMPORTANCE.NONE,
  IMPORTANCE.NORMAL,
  IMPORTANCE.MINOR,
  IMPORTANCE.IMPORTANT,
  IMPORTANCE.CRITICAL,
];
