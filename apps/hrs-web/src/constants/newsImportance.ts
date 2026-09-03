/**
 * 重要度统一业务量纲（快讯与消息日历共用）。
 *
 * 设计原则：数据源只是数据提供方，重要度的业务定义归本项目。上游量纲
 * （快讯 score 1~3、日历 importance 1~4、无字段的降级源）在服务层归一化
 * 入口统一为 0~4，前端据此做色阶与筛选，避免两套语义漂移。
 *
 * 完整设计见 docs/Live-calendar.md §5.7。
 */

/** 重要级，统一业务量纲（与后端 §5.7.2 一一对应） */
export type ImportanceLevel = 0 | 1 | 2 | 3 | 4;

/** 重要级枚举 */
export const IMPORTANCE = {
  /** 无：数据源未提供重要度（**不是**「最低等级」） */
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

/**
 * 色阶映射（快讯重要竖线 / 日历格子色点共用）。
 * 值全取 tailwind.config 语义令牌，随主题（浅/深色）联动。
 * `0` 返回 null 表示不渲染任何重要度标记。
 */
export const IMPORTANCE_COLORS: Record<ImportanceLevel, string | null> = {
  0: null,
  1: 'text-secondary-text',
  2: 'text-cyan/70',
  3: 'text-cyan',
  4: 'text-warning font-semibold',
};

/** 「重要」判定阈值，与后端 `wscn_live_news_important_score` / 日历阈值默认值对齐 */
export const IMPORTANT_THRESHOLD: ImportanceLevel = 3;

/** 是否为重要级 */
export function isImportant(level: number | null | undefined): boolean {
  return typeof level === 'number' && level >= IMPORTANT_THRESHOLD;
}
