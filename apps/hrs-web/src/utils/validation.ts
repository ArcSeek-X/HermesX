/**
 * 股票代码 / 查询文本校验工具
 *
 * 作用：在前端对用户输入的股票代码和自由文本查询做本地前置校验，覆盖 A 股、港股、
 * 美股、日股、韩股的常见代码格式。目标是把明显非法、不应发往后端的输入在本地就拦截掉，
 * 减少无效请求与误用。
 */

/** 校验结果结构：是否合法、错误提示、规范化后的文本 */
interface ValidationResult {
  valid: boolean;
  message?: string;
  normalized: string;
}

// 自由文本查询允许出现的字符：大写字母、数字、点、中日汉字（含扩展 A 区）及空白
const SUPPORTED_QUERY_CHARACTERS = /^[A-Z0-9.\u3400-\u9FFF\s]+$/;

// 支持的股票代码格式集合（统一大写后匹配）：
const STOCK_CODE_PATTERNS = [
  /^\d{6}$/, // A 股 6 位数字代码
  /^(SH|SZ|BJ)\d{6}$/, // 带交易所前缀的 A 股代码，如 SH600519
  /^\d{6}\.(SH|SZ|SS|BJ)$/, // 带交易所后缀的 A 股代码，如 600519.SH
  /^\d{5}$/, // 无前缀的港股代码
  /^HK\d{1,5}$/, // 带 HK 前缀的港股代码，如 HK00700
  /^\d{1,5}\.HK$/, // 带 .HK 后缀的港股代码，如 00700.HK
  /^\d{4,5}\.T$/, // 日本 Yahoo 后缀格式，如 7203.T
  /^\d{6}\.(KS|KQ)$/, // 韩国 Yahoo 后缀格式，如 005930.KS 或 035720.KQ
  /^[A-Z]{1,5}(?:\.(?:US|[A-Z]))?$/, // 常见美股代码格式，如 AAPL 或 AAPL.US
];

/**
 * 判断输入是否看起来像一个股票代码（仅做格式匹配，不做业务兜底）。
 *
 * @param value - 用户输入
 * @returns 匹配任一支持格式返回 true
 */
export const looksLikeStockCode = (value: string): boolean => {
  const normalized = value.trim().toUpperCase();
  return STOCK_CODE_PATTERNS.some((regex) => regex.test(normalized));
};

/**
 * 校验常见的 A 股、港股、美股、日股、韩股股票代码格式。
 *
 * @param value - 用户输入的股票代码
 * @returns 校验结果，包含规范化字符串与错误提示（若非法）
 */
export const validateStockCode = (value: string): ValidationResult => {
  const normalized = value.trim().toUpperCase();

  if (!normalized) {
    return { valid: false, message: '请输入股票代码', normalized };
  }

  const valid = looksLikeStockCode(normalized);

  return {
    valid,
    message: valid ? undefined : '股票代码格式不正确',
    normalized,
  };
};

/**
 * 在请求后端之前，拒绝明显非法的自由文本查询。
 * 规则：空文本视为合法（交由后端处理）；像股票代码的视为合法；
 * 含非法字符（如特殊符号）视为非法；同时包含字母与数字（疑似乱拼）也视为非法。
 *
 * @param value - 用户输入的查询文本
 * @returns true 表示应被拒绝
 */
export const isObviouslyInvalidStockQuery = (value: string): boolean => {
  const normalized = value.trim().toUpperCase();

  if (!normalized || looksLikeStockCode(normalized)) {
    return false;
  }

  if (!SUPPORTED_QUERY_CHARACTERS.test(normalized)) {
    return true;
  }

  const hasLetters = /[A-Z]/.test(normalized);
  const hasDigits = /\d/.test(normalized);

  return hasLetters && hasDigits;
};
