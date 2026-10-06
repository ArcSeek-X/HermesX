/**
 * LiveCalendarFilterState.ts
 * ------------------------------------------------------------
 * 消息日历筛选的**状态契约与纯函数**，与 `LiveCalendarFilter.tsx`（纯组件）分离：
 * 两者同文件会触发 `react-refresh/only-export-components`，且 Page 只消费这里的
 * 类型与默认值时不应把组件一起拉进热更新边界。
 *
 * @author Lensgcx (GaoCangxiong)
 */

import { ALL_IMPORTANCE_LEVELS, type ImportanceLevel } from '../../../constants/newsImportance';

/** 事件类型三态：全部 / 财经大事件(FE) / 经济数据(FD) */
export type LiveCalendarTypeFilter = 'all' | 'FE' | 'FD';

/** 筛选条件的值 */
export interface LiveCalendarFilterValue {
    /** 重要度多选：0=无 / 1=普通 / 2=较重要 / 3=重要 / 4=非常重要 */
    importance: ImportanceLevel[];
    /** 事件类型三态 */
    calendarType: LiveCalendarTypeFilter;
    /** 国家 ID；空串表示全部 */
    countryId: string;
    /** 标题关键词（匹配 title / shortTitle） */
    keyword: string;
}

/**
 * 生成一份默认（无筛选）条件。
 *
 * 每次调用返回**新对象**：重置必须产生新引用，否则与「上一次生效值」同引用时
 * 消费方的引用比较会判定「无变化」而不回灌默认值（表现为点了重置但面板没变）。
 */
export function createDefaultLiveCalendarFilter(): LiveCalendarFilterValue {
    return {
        importance: [...ALL_IMPORTANCE_LEVELS],
        calendarType: 'all',
        countryId: '',
        keyword: '',
    };
}

/**
 * 默认（无筛选）条件的只读基准（重要度全选 / 类型全部 / 国家全部 / 关键词空）。
 * 仅供初始化等「只读」场景；重置请用 `createDefaultLiveCalendarFilter()` 取新对象。
 */
export const DEFAULT_LIVE_CALENDAR_FILTER: LiveCalendarFilterValue =
    createDefaultLiveCalendarFilter();

/** 生效中的筛选条件数量（供按钮角标与高亮态使用） */
export function countActiveFilters(value: LiveCalendarFilterValue): number {
    let count = 0;
    if (value.importance.length !== ALL_IMPORTANCE_LEVELS.length) count += 1;
    if (value.calendarType !== 'all') count += 1;
    if (value.countryId) count += 1;
    if (value.keyword.trim()) count += 1;
    return count;
}
