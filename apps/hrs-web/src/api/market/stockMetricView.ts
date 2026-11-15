/**
 * @file api/stockMetricView.ts
 * @description 股票度量视图 API 层：封装 /api/v1/stock-metric 的 query 与 exportCsv 两个端点。
 * 不含 UI 状态、不返回列定义、不缓存业务结果。
 * 后端响应契约本身已是 camelCase（见 api/v1/schemas/stock_metric.py），本层**不做键名转换**：
 * 再跑一次 camelcase-keys 会把 peRatioTTM / psRatioTTM 这类连续大写字段破坏成
 * peRatioTtm / psRatioTtm，导致表格按列 key 取值落空（市盈率整列显示「—」）。
 * 适配层只做两件事：把 industry: null 归一为 undefined、为每行补 id（Table 行键）。
 * @author Lensgcx (GaoCangxiong)
 */

import apiClient from '@/api';
import type {
  StockMetricViewExportDef,
  StockMetricViewQueryDef,
  StockMetricViewResultDef,
  StockMetricViewRow,
} from '@/types/stockMetricView';

/** 度量视图接口前缀（与后端 prefix=/stock-metric 一致，仅语言惯例变体） */
const STOCK_METRIC_BASE = '/api/v1/stock-metric';

/** 原样响应（适配前）：industry 可能为 null，list 元素无 id */
type RawStockMetricViewRow = Omit<StockMetricViewRow, 'id' | 'industry'> & {
  industry: string | null;
};

type RawStockMetricViewResult = Omit<StockMetricViewResultDef, 'list'> & {
  list: RawStockMetricViewRow[];
};

/**
 * 把后端原始响应适配为前端行类型。
 * - industry: null → undefined（与 StockIdentity.industry 语义一致，差异只在适配层消化）。
 * - 补 id = `${market}:${code}`（Table 泛型约束所需的行键，非后端字段）。
 * - 其余字段按 camelCase 原名透传，键名与列定义 / 类型真源逐字一致。
 */
function adaptStockMetricViewResult(raw: RawStockMetricViewResult): StockMetricViewResultDef {
  const list: StockMetricViewRow[] = (raw.list ?? []).map((row) => ({
    ...row,
    id: `${row.market}:${row.code}`,
    industry: row.industry ?? undefined,
  }));
  return { ...raw, list };
}

export const stockMetricViewApi = {
  /**
   * 全市场指标分页查询。
   * @param def 查询入参（filterList + sort + 分页），缺省字段由后端补默认
   * @returns 分页结果；无匹配时 list 为 []
   * @throws 透传 HTTP 错误（由 api 拦截器统一提示，调用方按需 catch 解析 message）
   */
  async query(def: StockMetricViewQueryDef): Promise<StockMetricViewResultDef> {
    const res = await apiClient.post(`${STOCK_METRIC_BASE}/query`, def);
    return adaptStockMetricViewResult(res.data as RawStockMetricViewResult);
  },

  /**
   * 按当前筛选条件导出 CSV（服务端生成，避免前端循环分页触发限流）。
   * @param def 导出入参（筛选 DSL + 本地化表头 + 可见列顺序）
   * @returns CSV Blob，调用方负责触发浏览器下载
   * @throws 透传 HTTP 错误（失败时后端返回 JSON 错误体，非半份 CSV）
   */
  async exportCsv(def: StockMetricViewExportDef): Promise<Blob> {
    const res = await apiClient.post(`${STOCK_METRIC_BASE}/export`, def, {
      responseType: 'blob',
    });
    return res.data as Blob;
  },
};
