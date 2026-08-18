import apiClient from './index';
import { toCamelCase } from './utils';

/**
 * 股票工具类 API。
 * 提供从截图/文件中识别股票代码、解析导入文本等辅助能力，服务于自选股录入。
 */

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
   * 后端返回 StockQuote，含现价/涨跌额/涨跌幅/成交额/换手率/总市值等。
   */
  async getQuote(stockCode: string): Promise<StockQuote | null> {
    try {
      const { data } = await apiClient.get<Record<string, unknown>>(
        `/api/v1/stocks/${encodeURIComponent(stockCode)}/quote`,
      );
      return toCamelCase<StockQuote>(data);
    } catch {
      return null;
    }
  },
};

/** 实时行情（与后端 StockQuote 对齐） */
export interface StockQuote {
  stockCode: string;
  stockName?: string | null;
  currentPrice: number;
  change?: number | null;
  changePercent?: number | null;
  open?: number | null;
  high?: number | null;
  low?: number | null;
  prevClose?: number | null;
  volume?: number | null;
  amount?: number | null;
  turnoverRate?: number | null;
  totalMv?: number | null;
  updateTime?: string | null;
}
