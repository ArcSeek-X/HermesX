/**
 * 消息日历（Live Calendar）类型定义。
 *
 * 数据来源为华尔街见闻财经日历，接口契约见 docs/Live-calendar.md §7。
 * 类型命名遵循 .conventions/frontend/TYPE_NAMING.md：
 * 描述数据契约的类型用 `Def` 后缀（可脱离组件独立存在、被组件解析渲染）。
 *
 * 字段为后端 snake_case 经 api 层归一化后的 camelCase。
 */

import type { ImportanceLevel } from '../constants/newsImportance';

/** 分类 Tab 取值（按展示顺序：全部 → 宏观 → 财报 → 新股 → 活动） */
export type CalendarTabValue = 'all' | 'macro' | 'earnings' | 'ipo' | 'activity';

/** 分类 Tab 数据契约 */
export interface CalendarTabDef {
  value: CalendarTabValue;
  label: string;
  order: number;
}

/** 国家字典数据契约 */
export interface CalendarCountryDef {
  countryId: string;
  countryName: string;
  currency: string;
  currencyName: string;
  flagUri: string;
}

/** 单条日历事件数据契约 */
export interface LiveCalendarEventDef {
  id: number;
  key: string;
  /** 事件时间，秒级 UTC */
  startAt: number;
  title: string;
  /** 精简标题，日历格子直接渲染 */
  shortTitle: string;
  summary: string;
  /** `FE` 财经大事件 / `FD` 经济数据指标 */
  calendarType: 'FE' | 'FD';
  /** 命中的分类（可多归属） */
  tabKeys: CalendarTabValue[];
  /** 重要级，统一业务量纲：0=无 / 1=普通 / 2=较重要 / 3=重要 / 4=非常重要 */
  importance: ImportanceLevel;
  country: string;
  countryId: string;
  flagUri: string;
  actual: string;
  forecast: string;
  previous: string;
  /** 全天事件（上游 public_date 为 0） */
  isAllDay: boolean;
  sourceUri: string;
}

/** 月度日历查询参数数据契约 */
export interface LiveCalendarQueryDef {
  year: number;
  month: number;
  tab?: CalendarTabValue;
  countryId?: string;
  importanceMin?: number;
  includeEconomicData?: boolean;
}
