import camelcaseKeys from 'camelcase-keys';

/**
 * 前端 API 层通用工具函数集合。
 * 主要职责：把后端以 snake_case 返回的响应数据统一转换为前端使用的 camelCase，
 * 避免每个接口调用点都手动做字段名映射。
 */

/**
 * 将 snake_case 对象键转换为 camelCase（支持嵌套对象与数组的深层转换）。
 * @param data API 响应数据 (snake_case)
 * @returns 转换后的 camelCase 对象
 */
export function toCamelCase<T>(data: unknown): T {
    if (data === null || data === undefined) {
        return data as T;
    }
    return camelcaseKeys(data as Record<string, unknown>, { deep: true }) as T;
}
