/**
 * @file sortFilter.ts
 * @description 通用排序工具：提供与业务数据结构无关的纯排序方法。
 *   不依赖任何业务类型 / 接口，由调用方通过回调注入取值逻辑。
 * @module utils
 */

/**
 * 按「顺序权重」升序排序，并列时按兜底键升序（稳定）。
 * 常用于「用户自定义顺序」：getOrder 返回条目在列表中的顺序值（如 sortOrder），
 * getFallbackKey 用于同级兜底（如 id / code），保证结果稳定可复现。
 *
 * @param items `T[]` 待排序的数组（不会被原地修改，返回新数组）
 * @param getOrder `(item: T) => number` 取值回调：返回每条目的顺序权重，按该值升序排列
 * @param getFallbackKey `(item: T) => number | string`（可选）取值回调：当两条目顺序权重相等时，
 *   按该返回值升序兜底，用于消除并列、保证排序结果稳定可复现（如传条目 id）
 * @returns `T[]` 排序后的新数组
 */
export function sortByOrder<T>(
    items: T[],
    getOrder: (item: T) => number,
    getFallbackKey?: (item: T) => number | string,
): T[] {
    const list = [...items];
    return list.sort((a, b) => {
        const diff = getOrder(a) - getOrder(b);
        if (diff !== 0) return diff;
        if (getFallbackKey) return getFallbackKey(a) > getFallbackKey(b) ? 1 : -1;
        return 0;
    });
}

/**
 * 按「数值」降序排序；缺失值（null / undefined / NaN）的条目排到末尾。
 * 常用于行情指标（涨幅 / 成交额 / 换手率 / 市值等）排序。
 *
 * @param items `T[]` 待排序的数组（不会被原地修改，返回新数组）
 * @param getValue `(item: T) => number | null | undefined` 取值回调：返回每条目用于比较的数值；
 *   返回 null / undefined / NaN 视为缺失，该条目排到末尾
 * @returns `T[]` 排序后的新数组（有效值按降序，缺失值统一置于末尾）
 */
export function sortByFieldDesc<T>(
    items: T[],
    getValue: (item: T) => number | null | undefined,
): T[] {
    const list = [...items];
    return list.sort((a, b) => {
        const av = getValue(a);
        const bv = getValue(b);
        const aValid = av != null && !Number.isNaN(av);
        const bValid = bv != null && !Number.isNaN(bv);
        // 两者都有效：降序
        if (aValid && bValid) return (bv as number) - (av as number);
        // 仅一方有效：有效方在前
        if (aValid) return -1;
        if (bValid) return 1;
        // 都无效：保持原相对顺序
        return 0;
    });
}
