import axios from 'axios';

/**
 * 前端统一的 API 错误解析与分类模块（error.ts）。
 *
 * 职责定位：
 * 把底层 axios / fetch 抛出的「原始错误」规范化成结构统一的 ParsedApiError，
 * 让上层页面与组件无需关心错误到底来自网络层、HTTP 层还是后端业务体。
 *
 * 原始错误的来源大致有三类：
 *  1. 网络错误：本地服务都没连上（如 fetch failed / ECONNREFUSED）。
 *  2. HTTP 错误：连上了但状态码非 2xx（如 400 / 502 / 503）。
 *  3. 后端结构化错误体：HTTP 200 但业务失败，或 4xx/5xx 的 body 里带 detail。
 *
 * 本模块做两件事：
 *  A. 从各种杂乱的错误对象里「尽可能多地抽取可读文本」（payload / statusText / message / cause / code）。
 *  B. 基于抽取到的文本 + HTTP 状态码 + 后端 error_code，把错误「分类」到固定的 ApiErrorCategory，
 *     并给出中文 title / message，便于 UI 做差异化提示与降级处理。
 *
 * 对外主要出口：
 *  - parseApiError：纯解析，返回 ParsedApiError（不改动原 error 对象）。
 *  - getParsedApiError：无论传入什么，都尽量返回一个 ParsedApiError（容错入口）。
 *  - createApiError / attachParsedApiError：把 ParsedApiError「贴回」Error 对象，方便抛出与透传。
 *  - toApiErrorMessage：一行拿到可直接展示给用户的文案。
 *  - isXxx 系列：类型守卫，供调用方做分支判断。
 */

// 错误分类枚举：所有错误最终都会被归到其中一类。
// 调用方可以基于 category 做差异化 UI（如 llm_not_configured 引导去配置页，local_connection_failed 提示检查服务）。
// 'unknown' 是兜底分类，表示无法识别归类的错误。
export type ApiErrorCategory =
  | 'agent_disabled'             // Agent 模式未开启
  | 'missing_params'             // 请求缺少必要参数（如股票代码）
  | 'llm_not_configured'          // 系统未配置任何可用 LLM 模型
  | 'model_tool_incompatible'     // 当前模型不支持工具/函数调用
  | 'invalid_tool_call'           // 上游模型返回的工具调用结构不完整
  | 'portfolio_oversell'          // 卖出数量超过可用持仓
  | 'portfolio_busy'              // 持仓账本正在处理另一笔变更
  | 'upstream_llm_400'            // 上游模型接口（chat/completions 等）拒绝请求
  | 'upstream_timeout'            // 服务端访问外部依赖超时
  | 'upstream_network'            // 服务端访问外部依赖的网络/DNS/代理失败
  | 'local_connection_failed'     // 浏览器连不上本地 Web 服务
  | 'duplicate_item'              // 重复添加（自选股等）
  | 'http_error'                 // 其它有明确 HTTP 失败信息的请求错误
  | 'unknown';                   // 无法归类的兜底错误

// 规范化后的错误结构：UI 与页面统一消费这个结构，而不直接读原始 error。
export interface ParsedApiError {
  title: string;       // 给用户看的一句话标题（如「无法连接到本地服务」）
  message: string;     // 给用户看的详细说明，可操作指引
  rawMessage: string;  // 原始可读文本（未经中文润色，便于排查 / 日志）
  status?: number;     // HTTP 状态码（网络层错误时可能为空）
  category: ApiErrorCategory; // 错误分类，用于分支判断
}

// 兼容 axios 风格的错误载体：axios 把响应挂在 .response 上，错误码挂在 .code 上。
type ResponseLike = {
  status?: number;
  data?: unknown;
  statusText?: string;
};

// 任意「可能携带错误信息的对象」的通用形状。
// 用于从 axios 错误、普通 Error、甚至自定义对象里安全取值，避免直接访问属性报错。
type ErrorCarrier = {
  response?: ResponseLike;
  code?: string;
  message?: string;
  parsedError?: ParsedApiError;
  cause?: unknown;
};

// createParsedApiError 的入参：除 title/message 必填外，其余均可选（提供兜底）。
type CreateParsedApiErrorOptions = {
  title: string;
  message: string;
  rawMessage?: string;
  status?: number;
  category?: ApiErrorCategory;
};

/** 类型守卫：判断 value 是否为普通对象（非 null），用于安全地读取其字段。 */
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

/** 从多个候选值里取第一个非空字符串；全部为空时返回 null。用于「优先取最具体的消息」。 */
function pickString(...values: unknown[]): string | null {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) {
      return value.trim();
    }
  }
  return null;
}

/** 把任意值转成可读字符串：字符串直接 trim，数字/布尔转字符串，对象尝试 JSON.stringify，失败则退回 String。 */
function stringifyValue(value: unknown): string | null {
  if (value === null || value === undefined) {
    return null;
  }

  if (typeof value === 'string') {
    return value.trim() || null;
  }

  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }

  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

/** 从错误对象中安全取出 axios 的 response（HTTP 响应体）。取不到则返回 undefined。 */
function getResponse(error: unknown): ResponseLike | undefined {
  if (!isRecord(error)) {
    return undefined;
  }

  const response = (error as ErrorCarrier).response;
  return response && typeof response === 'object' ? response : undefined;
}

/** 取出错误对象的 code 字段（axios 错误码，如 'ECONNABORTED' / 'ERR_NETWORK'）。 */
function getErrorCode(error: unknown): string | undefined {
  return isRecord(error) && typeof (error as ErrorCarrier).code === 'string'
    ? (error as ErrorCarrier).code
    : undefined;
}

/** 取出错误对象的 message：兼容「字符串错误」「Error 实例」「带 message 字段的对象」三种形态。 */
function getErrorMessage(error: unknown): string | null {
  if (typeof error === 'string') {
    return error.trim() || null;
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message.trim();
  }

  if (isRecord(error) && typeof (error as ErrorCarrier).message === 'string') {
    const message = (error as ErrorCarrier).message?.trim();
    return message || null;
  }

  return null;
}

/** 取出错误对象的 cause（如 new Error(msg, { cause })）中的 message，用于拿到更深一层的错误原因。 */
function getCauseMessage(error: unknown): string | null {
  if (!isRecord(error)) {
    return null;
  }

  return getErrorMessage((error as ErrorCarrier).cause);
}

/** 把若干候选文本拼成一段小写匹配串（用 ' | ' 分隔），供后面的关键词匹配统一检索。 */
function buildMatchText(parts: Array<string | undefined | null>): string {
  return parts
    .filter((part): part is string => typeof part === 'string' && part.trim().length > 0)
    .join(' | ')
    .toLowerCase();
}

/** 判断 haystack 是否包含 needles 中的任意一个（均转小写比较，忽略大小写）。 */
function includesAny(haystack: string, needles: string[]): boolean {
  return needles.some((needle) => haystack.includes(needle.toLowerCase()));
}

/**
 * 解析 FastAPI 的 422 校验错误体：data 通常是数组，每项形如 { loc: [...], msg: '...' }。
 * 把每项格式化为「字段路径: 错误信息」，多条用 '; ' 连接后返回。
 */
function extractValidationDetail(detail: unknown): string | null {
  if (!Array.isArray(detail)) {
    return null;
  }

  const parts = detail
    .map((item) => {
      if (!isRecord(item)) {
        return stringifyValue(item);
      }

      const location = Array.isArray(item.loc)
        ? item.loc.map((segment) => String(segment)).join('.')
        : null;
      const message = pickString(item.msg, item.message, item.error);
      if (!location && !message) {
        return stringifyValue(item);
      }
      return [location, message].filter(Boolean).join(': ');
    })
    .filter((entry): entry is string => Boolean(entry));

  return parts.length > 0 ? parts.join('; ') : null;
}

/** 从响应体里取出后端错误码（error_code）：兼容 detail 嵌套或平铺两种情况。 */
function extractErrorCode(data: unknown): string | null {
  if (!isRecord(data)) {
    return null;
  }

  const detail = data.detail;
  if (isRecord(detail)) {
    return pickString(detail.error, detail.code, data.error, data.code);
  }

  return pickString(data.error, data.code);
}

/** 对 duplicate_item 的原始文案做中文润色：去掉句尾标点并补一句「请勿重复添加」。 */
function parsedDuplicateMessage(payloadText: string | null): string | null {
  if (!payloadText) return null;
  // 后端 duplicate_item 的消息形如「分类下已存在股票 603019.SH」「目标分类下已存在该股票」
  // 统一收敛为精简提示，去掉多余标点
  return payloadText.replace(/[。.]$/, '') + '，请勿重复添加。';
}

/**
 * 从后端响应体（response.data）里抽取「给用户看的可读错误文案」。
 * 兼容多种后端返回形态：
 *  - 纯字符串（如后端直接返回一段文本）
 *  - 数组（FastAPI 422 校验错误）
 *  - 对象，且 detail 为对象（{ message / error / detail: [...] }）
 *  - 对象，且 detail 为字符串或平铺的 message/error/title 等字段
 * 抽取优先级：具体字段 > 校验细节 > 兜底 JSON 化。
 */
export function extractErrorPayloadText(data: unknown): string | null {
  if (typeof data === 'string') {
    return data.trim() || null;
  }

  if (Array.isArray(data)) {
    return extractValidationDetail(data) ?? stringifyValue(data);
  }

  if (!isRecord(data)) {
    return stringifyValue(data);
  }

  const detail = data.detail;
  if (isRecord(detail)) {
    return (
      pickString(detail.message, detail.error)
      ?? extractValidationDetail(detail.detail)
      ?? stringifyValue(detail)
    );
  }

  return (
    pickString(
      detail,
      data.message,
      data.error,
      data.title,
      data.reason,
      data.description,
      data.msg,
    )
    ?? extractValidationDetail(detail)
    ?? stringifyValue(data)
  );
}

/** 构造一个 ParsedApiError：对可选字段做兜底（rawMessage 缺省回退到 message，category 缺省为 'unknown'）。 */
export function createParsedApiError(options: CreateParsedApiErrorOptions): ParsedApiError {
  return {
    title: options.title,
    message: options.message,
    rawMessage: options.rawMessage?.trim() || options.message,
    status: options.status,
    category: options.category ?? 'unknown',
  };
}

/** 类型守卫：判断某个值是否已经是合法的 ParsedApiError（供 getParsedApiError 复用，避免重复解析）。 */
export function isParsedApiError(value: unknown): value is ParsedApiError {
  return isRecord(value)
    && typeof value.title === 'string'
    && typeof value.message === 'string'
    && typeof value.rawMessage === 'string'
    && typeof value.category === 'string';
}

/** 类型守卫：判断某个 Error 是否携带 parsedError（即已被封装为 API 请求错误）。 */
export function isApiRequestError(
  value: unknown,
): value is Error & ErrorCarrier & { parsedError: ParsedApiError } {
  return value instanceof Error
    && isRecord(value)
    && isParsedApiError((value as ErrorCarrier).parsedError);
}

/** 把 ParsedApiError 拼成一行展示文案：无标题则只取 message；标题与说明相同则只取标题；否则「标题：说明」。 */
export function formatParsedApiError(parsed: ParsedApiError): string {
  if (!parsed.title.trim()) {
    return parsed.message;
  }
  if (parsed.title === parsed.message) {
    return parsed.title;
  }
  return `${parsed.title}：${parsed.message}`;
}

/**
 * 容错入口：无论传入什么（ParsedApiError / 带 parsedError 的 Error / 原始 axios 错误 / 字符串），
 * 都尽量返回一个 ParsedApiError，绝不直接抛异常。页面拿不准错误类型时统一走这个。
 */
export function getParsedApiError(error: unknown): ParsedApiError {
  if (isParsedApiError(error)) {
    return error;
  }
  if (isRecord(error) && isParsedApiError((error as ErrorCarrier).parsedError)) {
    return (error as ErrorCarrier).parsedError as ParsedApiError;
  }
  return parseApiError(error);
}

/**
 * 把一个 ParsedApiError「包成可抛出的 Error 对象」并返回。
 * 同时把 response / code / status / category / rawMessage 等附在 Error 上，方便在 catch 链里继续透传与读取。
 */
export function createApiError(
  parsed: ParsedApiError,
  extra: { response?: ResponseLike; code?: string; cause?: unknown } = {},
): Error & ErrorCarrier & { status?: number; category: ApiErrorCategory; rawMessage: string } {
  const apiError = new Error(formatParsedApiError(parsed)) as Error & ErrorCarrier & {
    status?: number;
    category: ApiErrorCategory;
    rawMessage: string;
  };
  apiError.name = 'ApiRequestError';
  apiError.parsedError = parsed;
  apiError.response = extra.response;
  apiError.code = extra.code;
  apiError.status = parsed.status;
  apiError.category = parsed.category;
  apiError.rawMessage = parsed.rawMessage;
  if (extra.cause !== undefined) {
    apiError.cause = extra.cause;
  }
  return apiError;
}

/**
 * 就地把一个 ParsedApiError「贴回」传入的错误对象（mutate）：
 *  - 给对象挂 parsedError 字段；
 *  - 若是 Error 实例，改写 name 与 message 为格式化后的文案。
 * 适合在已经要抛出的 error 上补充结构化信息，避免丢失原始对象。
 */
export function attachParsedApiError(error: unknown): ParsedApiError {
  const parsed = parseApiError(error);
  if (isRecord(error)) {
    const carrier = error as ErrorCarrier;
    carrier.parsedError = parsed;
  }
  if (error instanceof Error) {
    error.name = 'ApiRequestError';
    error.message = formatParsedApiError(parsed);
  }
  return parsed;
}

/** 便捷判断：错误是否归类为「本地服务连接失败」。供调用方决定要不要提示检查本地服务。 */
export function isLocalConnectionFailure(error: unknown): boolean {
  return parseApiError(error).category === 'local_connection_failed';
}

/**
 * 核心解析函数：把一个原始错误规范化成 ParsedApiError，并按顺序做分类匹配。
 *
 * 处理流程：
 *  1. 从 error 里抽取 response / status / payloadText / errorCode / errorMessage / causeMessage / code。
 *  2. 用 pickString 选出「最具体的原始文本」rawMessage（payload > statusText > errorMessage > cause > code）。
 *  3. 把所有文本拼成小写 matchText，向下逐个 if 分支匹配关键词 / errorCode / status，
 *     命中即返回对应 category 的中文 title/message。
 *  4. 都没命中时，若拿到 payload 或 status，归为通用 'http_error'；否则兜底 'unknown'。
 *
 * 注意：分类分支有先后顺序，越具体的错误（如 alphasift_*、portfolio_*）越靠前，
 * 通用网络/HTTP 错误放后面，避免被提前误匹配。
 */
export function parseApiError(error: unknown): ParsedApiError {
  const response = getResponse(error);
  const status = response?.status;
  const payloadText = extractErrorPayloadText(response?.data);
  const errorCode = extractErrorCode(response?.data);
  const errorMessage = getErrorMessage(error);
  const causeMessage = getCauseMessage(error);
  const code = getErrorCode(error);
  const rawMessage = pickString(payloadText, response?.statusText, errorMessage, causeMessage, code)
    ?? '请求未成功完成，请稍后重试。';
  const matchText = buildMatchText([rawMessage, errorMessage, causeMessage, code, errorCode, response?.statusText]);

  console.log(1111111111111)
    console.log(response)

  if (includesAny(matchText, ['agent mode is not enabled', 'agent_mode'])) {
    return createParsedApiError({
      title: 'Agent 模式未开启',
      message: '当前功能依赖 Agent 模式，请先开启后再重试。',
      rawMessage,
      status,
      category: 'agent_disabled',
    });
  }

  const hasStockCodeField = includesAny(matchText, ['stock_code', 'stock_codes']);
  const hasMissingParamText = includesAny(matchText, ['必须提供 stock_code 或 stock_codes', 'missing', 'required']);
  if (hasStockCodeField && hasMissingParamText) {
    return createParsedApiError({
      title: '请求缺少必要参数',
      message: '请先补充股票代码或必要输入后再试。',
      rawMessage,
      status,
      category: 'missing_params',
    });
  }

  if (errorCode === 'portfolio_oversell' || includesAny(matchText, ['oversell detected'])) {
    return createParsedApiError({
      title: '卖出数量超过可用持仓',
      message: '卖出数量超过当前可用持仓，请删除或修正对应卖出流水后重试。',
      rawMessage,
      status,
      category: 'portfolio_oversell',
    });
  }

  if (errorCode === 'portfolio_busy' || includesAny(matchText, ['portfolio ledger is busy'])) {
    return createParsedApiError({
      title: '持仓账本正忙',
      message: '持仓账本正在处理另一笔变更，请稍后重试。',
      rawMessage,
      status,
      category: 'portfolio_busy',
    });
  }

  if (errorCode === 'alphasift_install_failed') {
    return createParsedApiError({
      title: 'AlphaSift 修复安装失败',
      message: 'HRS 已尝试修复安装 AlphaSift，但 pip 安装未成功。请检查 ALPHASIFT_INSTALL_SPEC、网络代理或后端 Python 环境。',
      rawMessage,
      status,
      category: 'http_error',
    });
  }

  if (errorCode === 'alphasift_install_spec_missing') {
    return createParsedApiError({
      title: 'AlphaSift 安装来源未配置',
      message: '请先确认后端依赖已安装；如需使用修复安装入口，请配置受信任的 ALPHASIFT_INSTALL_SPEC。',
      rawMessage,
      status,
      category: 'http_error',
    });
  }

  if (errorCode === 'alphasift_install_spec_not_allowed') {
    return createParsedApiError({
      title: 'AlphaSift 安装来源受限',
      message: '修复安装仅允许使用受信任的 AlphaSift GitHub 来源；如需本地路径或 wheel，请先手动安装到当前 Python 环境。',
      rawMessage,
      status,
      category: 'http_error',
    });
  }

  if (errorCode === 'alphasift_unavailable' || includesAny(matchText, ['cannot import alphasift', 'alphasift.screen'])) {
    return createParsedApiError({
      title: 'AlphaSift 未就绪',
      message: rawMessage,
      rawMessage,
      status,
      category: 'http_error',
    });
  }

  if (errorCode === 'alphasift_adapter_unavailable') {
    return createParsedApiError({
      title: 'AlphaSift 适配层不可用',
      message: '当前 AlphaSift 版本缺少 HRS 稳定适配层。请重新安装或升级 AlphaSift 后再试。',
      category: 'http_error',
      rawMessage,
      status,
    });
  }

  console.log(22222222222)
  if (errorCode === 'alphasift_screen_task_not_found') {
    return createParsedApiError({
      title: '选股任务不可恢复',
      message: '服务端没有找到这次选股任务，可能后端已重启或任务记录已清理，请重新运行选股。',
      rawMessage,
      status,
      category: 'http_error',
    });
  }

  if (errorCode === 'alphasift_screen_failed') {
    return createParsedApiError({
      title: 'AlphaSift 选股失败',
      message: 'AlphaSift 运行时访问外部行情、快照或模型服务失败，请稍后重试，或检查网络与代理设置。',
      rawMessage,
      status,
      category: 'upstream_network',
    });
  }

  const noConfiguredLlm = (
    includesAny(matchText, ['all llm models failed']) && includesAny(matchText, ['last error: none'])
  ) || includesAny(matchText, [
    'no llm configured',
    'no effective primary model configured',
    'litellm_model not configured',
    'ai analysis will be unavailable',
  ]);
  if (noConfiguredLlm) {
    return createParsedApiError({
      title: '系统没有配置可用的 LLM 模型',
      message: '请先在系统设置中配置主模型、可用渠道或相关 API Key 后再重试。',
      rawMessage,
      status,
      category: 'llm_not_configured',
    });
  }

  if (includesAny(matchText, [
    'tool call',
    'function call',
    'does not support tools',
    'tools is not supported',
    'reasoning',
  ])) {
    return createParsedApiError({
      title: '当前模型不兼容工具调用',
      message: '当前模型不适合 Agent / 工具调用场景，请更换支持工具调用的模型后重试。',
      rawMessage,
      status,
      category: 'model_tool_incompatible',
    });
  }
console.log(33333333333)
  if (includesAny(matchText, [
    'thought_signature',
    'missing function',
    'missing tool',
    'invalid tool call',
    'invalid function call',
  ])) {
    return createParsedApiError({
      title: '上游模型返回的数据结构不完整',
      message: '上游模型返回的工具调用结构不符合要求，请更换模型或关闭相关推理模式后重试。',
      rawMessage,
      status,
      category: 'invalid_tool_call',
    });
  }

  if (includesAny(matchText, ['timeout', 'timed out', 'read timeout', 'connect timeout']) || code === 'ECONNABORTED') {
    return createParsedApiError({
      title: '连接上游服务超时',
      message: '服务端访问外部依赖时超时，请稍后重试，或检查当前网络与代理设置。',
      rawMessage,
      status,
      category: 'upstream_timeout',
    });
  }

  if (
    status === 502
    || status === 503
    || includesAny(matchText, [
      'dns',
      'enotfound',
      'name or service not known',
      'temporary failure in name resolution',
      'proxy',
      'tunnel',
      '502',
      '503',
    ])
  ) {
    return createParsedApiError({
      title: '服务端无法访问外部依赖',
      message: '页面已连接到本地服务，但本地服务访问外部模型或数据接口失败，请检查代理、DNS 或出网配置。',
      rawMessage,
      status,
      category: 'upstream_network',
    });
  }
console.log(4444444444)
  const hasLlmProviderHint = includesAny(matchText, [
    'chat/completions',
    'generativelanguage',
    'openai',
    'gemini',
  ]);
  if (status === 400 && hasLlmProviderHint) {
    return createParsedApiError({
      title: '上游模型接口拒绝了当前请求',
      message: '本地服务正常，但上游模型接口拒绝了请求，请检查模型名称、参数格式或工具调用兼容性。',
      rawMessage,
      status,
      category: 'upstream_llm_400',
    });
  }

  const localConnectionFailed = !response && (
    includesAny(matchText, ['fetch failed', 'failed to fetch', 'network error', 'connection refused', 'econnrefused'])
    || code === 'ERR_NETWORK'
    || code === 'ECONNREFUSED'
  );
  if (localConnectionFailed) {
    return createParsedApiError({
      title: '无法连接到本地服务',
      message: '浏览器当前无法连接到本地 Web 服务，请检查服务是否启动、监听地址是否正确、端口是否开放。',
      rawMessage,
      status,
      category: 'local_connection_failed',
    });
  }

  if (errorCode === 'duplicate_item' || includesAny(matchText, ['已存在', 'duplicate_item'])) {
    return createParsedApiError({
      title: '已存在',
      message: parsedDuplicateMessage(payloadText) ?? '该分组下已存在此股票，请勿重复添加。',
      rawMessage,
      status,
      category: 'duplicate_item',
    });
  }
console.log(555555555)
console.log(payloadText)
console.log(status)

  if (payloadText || status) {
    return createParsedApiError({
      title: '请求失败',
      message: payloadText ?? `请求未成功完成（HTTP ${status}）。`,
      rawMessage,
      status,
      category: 'http_error',
    });
  }

console.log(6666666666)
console.log(rawMessage)
  return createParsedApiError({
    title: '请求失败',
    message: rawMessage,
    rawMessage,
    status,
    category: 'unknown',
  });
}

/** 一行拿到「可直接展示给用户」的错误文案；解析失败或空文案时返回 fallback。 */
export function toApiErrorMessage(error: unknown, fallback = '请求未成功完成，请稍后重试。'): string {
  const parsed = getParsedApiError(error);
  const message = formatParsedApiError(parsed);
  return message.trim() || fallback;
}

/** 类型守卫：判断错误是否为 axios 抛出的错误（用于需要进一步读取 axios 专属字段的场景）。 */
export function isAxiosApiError(error: unknown): boolean {
  return axios.isAxiosError(error);
}
