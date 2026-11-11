import apiClient from './index';
import { toCamelCase } from './utils';
import type { KLinePoint } from './kline';
import type { StockQuoteCore } from '../types/stock';

/**
 * 股票工具类 API。
 * 提供实时行情、当日分时、批量行情与分时、截图/文件识别股票代码等能力，
 * 服务于自选股列表与个股 K 线页的最近搜索卡片。
 */

/** 单只股票当日分时明细（KLinePoint 形态，date 为 'YYYY-MM-DD HH:mm:ss'） */
export interface StockTimeline {
  stockCode: string;
  stockName: string | null;
  /** 昨收价：分时图基准线（上游取空时为 null，前端退化为首末点比较） */
  prevClose: number | null;
  points: KLinePoint[];
}

/** 批量分时中的单只股票；points 已由后端等距下采样 */
export interface BatchTimelineItem {
  code: string;
  name: string | null;
  prevClose: number | null;
  points: KLinePoint[];
}

/** 单条被识别出的股票项（含识别置信度） */
export type ExtractItem = {
  /** 股票代码 */
  code?: string | null;
  /** 股票名称 */
  name?: string | null;
  /** 识别置信度（如 high/medium/low 或数值字符串） */
  confidence: string;
};

/** 从图片/文本中识别股票的响应 */
export type ExtractFromImageResponse = {
  /** 识别出的股票代码列表 */
  codes: string[];
  /** 逐条识别明细 */
  items?: ExtractItem[];
  /** 图像 OCR 原始文本（调试用） */
  rawText?: string;
};

/**
 * 单只股票实时行情，字段名与 `StockQuoteCore` 规范完全一致。
 * 后端已按规范 camelCase 输出，前端不再做二次命名适配。
 */
export type StockQuote = StockQuoteCore & {
  /** 行情快照时间（ISO 8601），数据源未提供时为 null */
  updateTime?: string | null;
};

/** 批量行情/分时的请求体代码上限，与后端契约保持一致 */
const BATCH_MAX_CODES = 10;

export const stocksApi = {
  /**
   * 上传截图，调用视觉模型识别其中的股票代码。
   * 显式把 Content-Type 设为 undefined 让浏览器自动填充 multipart 边界；
   * Vision 接口较慢，超时放宽到 60s。
   */
  async extractFromImage(file: File): Promise<ExtractFromImageResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const headers: { [key: string]: string | undefined } = { 'Content-Type': undefined };
    const response = await apiClient.post(
      '/api/v1/stocks/extract-from-image',
      formData,
      {
        headers,
        timeout: 60000, // Vision API can be slow; 60s
      },
    );

    const data = response.data as { codes?: string[]; items?: ExtractItem[]; raw_text?: string };
    return {
      codes: data.codes ?? [],
      items: data.items,
      rawText: data.raw_text,
    };
  },

  /**
   * 解析导入内容：支持上传文件或粘贴文本，二选一。
   * 后端从中解析出股票代码/名称列表返回。
   */
  async parseImport(file?: File, text?: string): Promise<ExtractFromImageResponse> {
    if (file) {
      const formData = new FormData();
      formData.append('file', file);
      const headers: { [key: string]: string | undefined } = { 'Content-Type': undefined };
      const response = await apiClient.post('/api/v1/stocks/parse-import', formData, { headers });
      const data = response.data as { codes?: string[]; items?: ExtractItem[] };
      return { codes: data.codes ?? [], items: data.items };
    }
    if (text) {
      const response = await apiClient.post('/api/v1/stocks/parse-import', { text });
      const data = response.data as { codes?: string[]; items?: ExtractItem[] };
      return { codes: data.codes ?? [], items: data.items };
    }
    throw new Error('请提供文件或粘贴文本');
  },

  /**
   * 获取单只股票实时行情（自选股列表展示用）。
   * 失败 / 上游取空时返回 null，由调用方降级为占位渲染。
   */
  async getQuote(stockCode: string): Promise<StockQuote | null> {
    try {
      const { data } = await apiClient.get<StockQuote>(
        `/api/v1/stocks/${encodeURIComponent(stockCode)}/quote`,
      );
      return data;
    } catch {
      return null;
    }
  },

  /**
   * 获取单只股票当日分时明细（自选股列表分时缩略图数据源）。
   * 失败 / 上游取空时返回 null，由调用方降级为占位渲染（不阻断列表）。
   */
  async getTimeline(stockCode: string): Promise<StockTimeline | null> {
    try {
      const { data } = await apiClient.get<Record<string, unknown>>(
        `/api/v1/stocks/${encodeURIComponent(stockCode)}/timeline`,
      );
      const timeline = toCamelCase<StockTimeline>(data);
      return { ...timeline, points: timeline.points ?? [] };
    } catch {
      return null;
    }
  },

  /**
   * 批量获取实时行情（最近搜索卡片列表用）。
   * 一次请求替代逐卡请求；单只拉取失败的股票由后端跳过，调用方按代码降级占位。
   */
  async batchQuote(codes: string[]): Promise<StockQuote[]> {
    const uniqueCodes = [...new Set(codes.filter(Boolean))].slice(0, BATCH_MAX_CODES);
    if (uniqueCodes.length === 0) return [];
    try {
      const { data } = await apiClient.post<{ items?: StockQuote[] }>(
        '/api/v1/stocks/batch-quote',
        { codes: uniqueCodes },
      );
      return data.items ?? [];
    } catch {
      return [];
    }
  },

  /**
   * 批量获取当日分时（最近搜索卡片走势图用）。
   * 后端复用分时缓存并下采样到缩略图点数；失败返回空数组。
   */
  async batchTimeline(codes: string[]): Promise<BatchTimelineItem[]> {
    const uniqueCodes = [...new Set(codes.filter(Boolean))].slice(0, BATCH_MAX_CODES);
    if (uniqueCodes.length === 0) return [];
    try {
      const { data } = await apiClient.post<{ items?: BatchTimelineItem[] }>(
        '/api/v1/stocks/batch-timeline',
        { codes: uniqueCodes },
      );
      return data.items ?? [];
    } catch {
      return [];
    }
  },
};
