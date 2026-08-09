/**
 * 决策信号时间解析工具
 *
 * 作用：把后端返回的决策信号时间字符串（可能带或不带时区偏移）安全地解析为 JavaScript Date。
 * 对缺失时区偏移的纯本地时间字符串，自动补上 UTC 标识（Z）以保证各环境解析一致，
 * 避免时区歧义；解析失败返回 null 而非抛错。供时间线排序、展示等场景复用。
 */

// 时区偏移标识：Z 或 +/-HH:MM / +/-HHMM
const TIMEZONE_OFFSET_PATTERN = /(?:Z|[+-]\d{2}:?\d{2})$/i;
// 无时区偏移的日期时间格式：2026-08-09T10:00:00 或带毫秒
const DATE_TIME_WITHOUT_TIMEZONE_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?$/;

/**
 * 解析决策信号时间字符串。
 * 当字符串缺少时区偏移时，补上 Z（UTC）再解析，保证跨环境一致。
 *
 * @param value - 时间字符串（可为 null/undefined）
 * @returns 成功的 Date 对象；空值或非法值返回 null
 */
export function parseDecisionSignalDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const trimmedValue = value.trim();
  if (!trimmedValue) return null;
  const normalizedValue = DATE_TIME_WITHOUT_TIMEZONE_PATTERN.test(trimmedValue) && !TIMEZONE_OFFSET_PATTERN.test(trimmedValue)
    ? `${trimmedValue}Z`
    : trimmedValue;
  const date = new Date(normalizedValue);
  return Number.isNaN(date.getTime()) ? null : date;
}
