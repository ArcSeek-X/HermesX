/**
 * 组合页面共享类型
 *
 * 供 PortfolioPage 主页面与四个面板组件（持仓总览 / 持仓表格 / 集中度 / 事件记录）复用，
 * 避免同一语义在页面与组件间重复声明、或组件反向依赖页面造成循环引用。
 *
 * 传参约定：
 * - 面板组件只接收「已按当前账户视图加载好的数据 + 回调」，不接收账户 ID 自行请求；
 *   账户范围、成本口径由主页面统一决定（queryAccountId / costMethod），保证单一数据源。
 */

import type {
  PortfolioCashDirection,
  PortfolioCorporateActionType,
  PortfolioSide,
} from '../../../types/portfolio';

/** 页面支持的语言（用于数据质量限制标签本地化） */
export type PortfolioPageLanguage = 'zh' | 'en';

/** 事件类型：交易 / 资金 / 公司行为 */
export type EventType = 'trade' | 'cash' | 'corporate';

/** 主区面板：持仓总览 / 持仓表格 / 集中度 / 事件记录 */
export type PortfolioPanel = 'overview' | 'positions' | 'concentration' | 'events';

/** 录入弹窗入口：手工录入 / CSV 导入（新建账户弹窗由账户视图面板自行管理） */
export type EntryModalTarget = 'manual' | 'csv';

/** 手工录入子表单：交易 / 资金流水 / 公司行为 */
export type ManualEntryTab = 'trade' | 'cash' | 'corporate';

/** 集中度展示维度：sector 为行业维度，position 为行业数据不可用时的个股降级维度 */
export type ConcentrationDimension = 'sector' | 'position';

/** 集中度饼图切片 */
export interface ConcentrationSlice {
  /** 切片名称（行业名或股票代码） */
  name: string;
  /** 权重百分比 */
  value: number;
}

/** 事件记录筛选条件 */
export interface PortfolioEventFilters {
  /** 事件类型 */
  eventType: EventType;
  /** 起始日期（YYYY-MM-DD），空表示不限 */
  dateFrom: string;
  /** 截止日期（YYYY-MM-DD），空表示不限 */
  dateTo: string;
  /** 股票代码，空表示不限 */
  symbol: string;
  /** 买卖方向，空表示不限 */
  side: '' | PortfolioSide;
  /** 资金方向，空表示不限 */
  direction: '' | PortfolioCashDirection;
  /** 公司行为类型，空表示不限 */
  actionType: '' | PortfolioCorporateActionType;
}

/** 待确认删除的事件记录 */
export interface PendingEventDelete {
  /** 事件类型，决定调用哪个删除接口 */
  eventType: EventType;
  /** 事件记录 ID */
  eventId: number;
  /** 删除确认弹窗展示的文案 */
  confirmMessage: string;
}
