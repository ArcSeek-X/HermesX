/**
 * @file StockScreeningPage.tsx
 * @description AlphaSift 选股页面，提供基于 AlphaSift 适配层的智能选股功能。
 *              支持多策略选股、热点题材浏览、候选股票详情查看，并通过 HRS 数据
 *              增强候选股票的行情、基本面和新闻上下文。
 * @module pages
 *
 * 核心功能：
 * - 开启/检测 AlphaSift 适配层状态
 * - 选择市场、策略和返回数量，提交异步选股任务并轮询结果
 * - 浏览热点题材云图，查看发酵时间线和概念股
 * - 展示候选股票列表，支持展开查看因子评分、LLM 判断、风险标签等详情
 * - 选股任务状态持久化到 sessionStorage，刷新页面后自动恢复轮询
 */
import type React from 'react';
import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  Bookmark,
  Building2,
  CheckCircle2,
  ChevronDown,
  CircleAlert,
  Clock3,
  Droplet,
  Factory,
  Flame,
  Gem,
  Landmark,
  Pickaxe,
  Plane,
  Play,
  RefreshCw,
  Search,
  Shield,
  SlidersHorizontal,
  Stethoscope,
  Trees,
  Utensils,
  Wrench,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  alphasiftApi,
  type AlphaSiftCandidate,
  type AlphaSiftHotspotDetail,
  type AlphaSiftHotspot,
  type AlphaSiftHotspotsResponse,
  type AlphaSiftScreenResponse,
  type AlphaSiftScreenTaskStatus,
  type AlphaSiftStrategy,
} from '../api/alphasift';
import { formatParsedApiError, getParsedApiError, toApiErrorMessage, type ParsedApiError } from '../api/error';
import { AppPage, Button, InlineAlert } from '../components';
import { usePreference } from '../hooks/usePreference';

// ============ 常量与类型定义 ============

/** 可选市场列表（当前仅支持 A 股） */
const MARKETS = [{ id: 'cn', label: 'A 股' }];
/** sessionStorage 中持久化选股任务的键名，用于刷新页面后恢复轮询 */
const SCREEN_TASK_STORAGE_KEY = 'hrs.alphasift.activeScreenTask.v1';
/** 选股任务状态轮询间隔：2 秒 */
const SCREEN_TASK_POLL_INTERVAL_MS = 2000;

/** 持久化到 sessionStorage 的选股任务信息 */
type PersistedScreenTask = {
  taskId: string;
  market: string;
  strategy: string;
  maxResults: number;
};

/**
 * 从 sessionStorage 读取持久化的选股任务
 * 用于页面刷新后恢复正在进行的选股任务轮询
 * @returns 持久化的任务信息；无数据或解析失败时返回 null
 */
const readPersistedScreenTask = (): PersistedScreenTask | null => {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    const raw = window.sessionStorage.getItem(SCREEN_TASK_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as Partial<PersistedScreenTask>;
    if (typeof parsed.taskId !== 'string' || !parsed.taskId.trim()) {
      return null;
    }
    const restoredMaxResults = Number(parsed.maxResults);
    return {
      taskId: parsed.taskId,
      market: typeof parsed.market === 'string' && parsed.market.trim() ? parsed.market : 'cn',
      strategy: typeof parsed.strategy === 'string' && parsed.strategy.trim() ? parsed.strategy : 'dual_low',
      maxResults: Number.isFinite(restoredMaxResults) ? Math.min(100, Math.max(1, restoredMaxResults)) : 3,
    };
  } catch {
    return null;
  }
};

/**
 * 将选股任务信息持久化到 sessionStorage
 * @param task - 需要持久化的任务信息
 */
const persistScreenTask = (task: PersistedScreenTask) => {
  try {
    window.sessionStorage.setItem(SCREEN_TASK_STORAGE_KEY, JSON.stringify(task));
  } catch {
    // Session storage is best-effort; polling still works while the page stays mounted.
  }
};

/** 从 sessionStorage 中清除持久化的选股任务（任务完成或失败后调用） */
const clearPersistedScreenTask = () => {
  try {
    window.sessionStorage.removeItem(SCREEN_TASK_STORAGE_KEY);
  } catch {
    // Ignore storage cleanup failures.
  }
};

/** 判断选股任务错误是否不可恢复（如任务已被清理），不可恢复时需停止轮询 */
const isUnrecoverableScreenTaskError = (error: ParsedApiError) =>
  error.title === '选股任务不可恢复';

/**
 * 格式化可恢复的选股任务轮询错误信息
 * 超时、网络中断等临时性错误不会终止轮询，仅展示提示文案
 * @param error - 解析后的 API 错误
 * @returns 面向用户的错误提示文本
 */
const formatRecoverableScreenTaskPollingError = (error: ParsedApiError) => {
  if (error.category === 'upstream_timeout') {
    return '选股任务仍在后台运行，状态轮询暂时超时，将自动重试。';
  }
  if (error.category === 'upstream_network' || error.category === 'local_connection_failed') {
    return '选股任务仍在后台运行，暂时无法连接本地服务获取状态，将自动重试。';
  }
  return formatParsedApiError(error) || '暂时无法获取选股任务状态，稍后将自动重试。';
};

/** 格式化候选股票评分，保留两位小数；无效值返回 "-" */
const formatScore = (score: AlphaSiftCandidate['score']) => {
  if (score == null || Number.isNaN(Number(score))) {
    return '-';
  }
  return Number(score).toFixed(2);
};

/** 格式化数值，保留指定位小数；无效值返回 "-" */
const formatNumber = (value: unknown, digits = 2) => {
  if (value == null || value === '' || Number.isNaN(Number(value))) {
    return '-';
  }
  return Number(value).toFixed(digits);
};

/** 格式化成交额，亿元以上显示"亿"，万元以上显示"万"；无效值返回 "-" */
const formatAmount = (value: unknown) => {
  if (value == null || value === '' || Number.isNaN(Number(value))) {
    return '-';
  }
  const amount = Number(value);
  if (Math.abs(amount) >= 100_000_000) {
    return `${(amount / 100_000_000).toFixed(2)} 亿`;
  }
  if (Math.abs(amount) >= 10_000) {
    return `${(amount / 10_000).toFixed(2)} 万`;
  }
  return amount.toFixed(2);
};

/** 将小数格式化为百分比字符串（如 0.85 -> "85%"）；无效值返回 "-" */
const formatPercent = (value: unknown) => {
  if (value == null || value === '' || Number.isNaN(Number(value))) {
    return '-';
  }
  return `${(Number(value) * 100).toFixed(0)}%`;
};

/**
 * 获取候选股票的入选理由文本
 * 优先使用 reason 字段，其次从 postAnalysisSummaries 中取首个非空摘要
 * @param item - 候选股票数据
 * @returns 入选理由文本；均无数据时返回默认提示
 */
const getCandidateReason = (item: AlphaSiftCandidate) => {
  if (item.reason) {
    return item.reason;
  }
  const summaries = item.postAnalysisSummaries || {};
  const summary = Object.values(summaries).find((value) => typeof value === 'string' && value.trim());
  if (typeof summary === 'string') {
    return summary;
  }
  return 'AlphaSift 返回候选，但没有给出文字摘要。请查看下方因子、风险和原始字段。';
};

/**
 * 从候选股票原始数据中提取操作信号
 * 依次尝试 action、signal、recommendation 字段；无有效值时返回"观察"
 * @param item - 候选股票数据
 * @returns 操作信号文本
 */
const getSignal = (item: AlphaSiftCandidate) => {
  const rawSignal = item.raw.action ?? item.raw.signal ?? item.raw.recommendation;
  return typeof rawSignal === 'string' && rawSignal.trim() ? rawSignal : '观察';
};

/**
 * 从候选股票中提取因子评分条目，按分值降序排列，最多取前 6 个
 * @param item - 候选股票数据
 * @returns [因子名, 分值] 数组
 */
const getFactorEntries = (item: AlphaSiftCandidate) =>
  Object.entries(item.factorScores || {})
    .filter(([, value]) => typeof value === 'number')
    .sort((a, b) => Number(b[1]) - Number(a[1]))
    .slice(0, 6);

/** 将字符串数组转为修剪后的非空消息列表 */
const toMessageList = (values: string[] | undefined) =>
  Array.isArray(values) ? values.map((value) => String(value).trim()).filter(Boolean) : [];

/** 已知数据快照来源集合，用于识别数据源降级消息 */
const KNOWN_SNAPSHOT_SOURCES = new Set(['tushare', 'efinance', 'akshare_em', 'em_datacenter', 'baostock']);
/** 诊断消息截断最大长度 */
const MAX_MESSAGE_DETAIL_LENGTH = 96;

/**
 * 截断过长的诊断消息文本
 * 先压缩空白字符，超过最大长度时截断并添加省略号
 * @param value - 原始文本
 * @param maxLength - 最大长度，默认 96
 * @returns 截断后的文本
 */
const truncateMessageDetail = (value: string, maxLength = MAX_MESSAGE_DETAIL_LENGTH) => {
  const text = value.replace(/\s+/g, ' ').trim();
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength - 1)}…`;
};

/**
 * 将 AlphaSift 诊断明细归纳为简短的中文摘要
 * 识别交易日历、限流、403、超时、网络中断、API Key 缺失等常见错误模式
 * @param detail - 原始诊断明细文本
 * @returns 简短的中文摘要（已去除 URL）
 */
const summarizeAlphaSiftDiagnostic = (detail: string) => {
  if (/trade_cal returned no open trading days/i.test(detail)) {
    return '交易日历暂无可用开市日';
  }
  if (/too many requests|rate limit|http\s*429/i.test(detail)) {
    return '请求过于频繁';
  }
  if (/403 forbidden|forbidden|access denied/i.test(detail)) {
    return '访问被拒绝';
  }
  if (/timeout|timed out/i.test(detail)) {
    return '请求超时';
  }
  if (/RemoteDisconnected|Connection aborted|ProtocolError|ConnectionPool|Max retries exceeded|ProxyError|NameResolutionError/i.test(detail)) {
    return '网络连接中断';
  }
  if (/missing .*api key|GEMINI_API_KEY|GOOGLE_API_KEY|gemini_api_key/i.test(detail)) {
    return '缺少可用 LLM API Key';
  }
  if (/returned no data|empty/i.test(detail)) {
    return '未返回可用数据';
  }

  const withoutUrl = detail
    .replace(/https?:\/\/\S+/gi, 'URL')
    .replace(/\bwith url:\s*\S+/gi, 'with url: URL')
    .replace(/\burl:\s*\S+/gi, 'url: URL');
  return truncateMessageDetail(withoutUrl);
};

/**
 * 解析 "source: detail" 格式的数据源诊断消息
 * @param value - 原始消息字符串
 * @returns 解析后的 { source, detail }；格式不匹配时返回 null
 */
const parseSourceDiagnostic = (value: string) => {
  const match = value.match(/^([a-zA-Z0-9_-]+)\s*[:：]\s*(.+)$/);
  if (!match) {
    return null;
  }
  return {
    source: match[1],
    detail: match[2],
  };
};

/** 将选股消息标准化为小写键，用于去重判断 */
const normalizeScreenMessageKey = (value: string) => {
  const formatted = formatScreenMessage(value);
  return formatted ? formatted.trim().toLowerCase() : value.trim().toLowerCase();
};

/**
 * 格式化选股过程中的提示消息
 * 识别 LLM 重排失败、数据源降级等已知模式并转为中文提示；
 * 其余消息截断后返回；无意义的上下文应用消息返回空字符串
 * @param value - 原始消息字符串
 * @returns 格式化后的中文提示；无意义消息返回空字符串
 */
const formatScreenMessage = (value: string) => {
  if (/^HRS provider context applied \d+ of \d+ candidates/i.test(value)) {
    return '';
  }
  if (/^LLM ranking failed/i.test(value)) {
    return `LLM 重排失败：${summarizeAlphaSiftDiagnostic(value)}，已回退到本地因子评分。`;
  }

  const snapshotFallback = value.match(/^Snapshot source fallback:\s*(.+)$/i);
  if (snapshotFallback) {
    const parsed = parseSourceDiagnostic(snapshotFallback[1]);
    if (parsed) {
      return `数据源降级：${parsed.source}（${summarizeAlphaSiftDiagnostic(parsed.detail)}）`;
    }
    return `数据源降级：${summarizeAlphaSiftDiagnostic(snapshotFallback[1])}`;
  }

  const parsed = parseSourceDiagnostic(value);
  if (parsed && KNOWN_SNAPSHOT_SOURCES.has(parsed.source.toLowerCase())) {
    return `数据源降级：${parsed.source}（${summarizeAlphaSiftDiagnostic(parsed.detail)}）`;
  }
  return truncateMessageDetail(value);
};

/**
 * 从选股响应中提取去重后的提示消息列表
 * 合并 warnings、sourceErrors、llmParseErrors，按标准化键去重
 * @param meta - 选股响应元数据
 * @returns 去重后的中文提示消息数组
 */
const getScreenMessages = (meta: AlphaSiftScreenResponse | null) => {
  if (!meta) {
    return [];
  }
  const messages: string[] = [];
  const seen = new Set<string>();
  [...toMessageList(meta.warnings), ...toMessageList(meta.sourceErrors), ...toMessageList(meta.llmParseErrors)].forEach(
    (value) => {
      const key = normalizeScreenMessageKey(value);
      if (seen.has(key)) {
        return;
      }
      const message = formatScreenMessage(value);
      if (!message) {
        return;
      }
      seen.add(key);
      messages.push(message);
    },
  );
  return messages;
};

/** 判断选股任务状态是否处于运行中（pending 或 processing） */
const isRunningScreenTask = (status: string | undefined | null) => status === 'pending' || status === 'processing';

/**
 * 格式化选股任务失败信息
 * @param value - 失败原因文本
 * @returns 面向用户的失败提示
 */
const formatScreenTaskFailure = (value: string | null | undefined) => {
  const text = String(value || '').trim();
  if (!text) {
    return '选股任务失败，请稍后重试。';
  }
  return `选股任务失败：${summarizeAlphaSiftDiagnostic(text)}`;
};

/** 后端返回的无缓存热点提示文案，用于前端识别并转为中文 */
const ALPHASIFT_HOTSPOT_NO_CACHE_HINT = 'No cached AlphaSift hotspot snapshot. Click refresh to fetch live hotspots.';
/** 东方财富热点不可用的错误码 */
const ALPHASIFT_HOTSPOT_UNAVAILABLE_CODE = 'eastmoney_hotspot_unavailable';

/**
 * 格式化热点题材为空时的提示文案
 * 识别无缓存、数据源不可用等场景，给出对应的中文提示
 * @param result - 热点题材响应数据
 * @returns 面向用户的空数据提示文案
 */
const formatHotspotEmptyMessage = (result: AlphaSiftHotspotsResponse) => {
  const message = String(result.message || '').trim();
  const sourceErrors = result.sourceErrors || [];
  if (message && sourceErrors.includes(ALPHASIFT_HOTSPOT_UNAVAILABLE_CODE)) {
    return message;
  }
  if (message === ALPHASIFT_HOTSPOT_NO_CACHE_HINT) {
    return '暂无缓存热点题材，展开后可点击刷新拉取实时数据。';
  }
  const sourceError = sourceErrors[0];
  if (sourceError) {
    return `热点题材暂未返回数据：${summarizeAlphaSiftDiagnostic(sourceError)}`;
  }
  return '热点题材暂未返回数据';
};

/** 选股提示消息展示组件：单条直接渲染，多条以列表形式展示 */
const ScreenAlertMessage: React.FC<{ messages: string[] }> = ({ messages }) => {
  if (messages.length <= 1) {
    return <span>{messages[0]}</span>;
  }
  return (
    <ul className="list-disc space-y-1 pl-4">
      {messages.map((message) => (
        <li key={message}>{message}</li>
      ))}
    </ul>
  );
};

/** 判断候选股票是否包含 LLM 判断信息（论文、板块、主题、置信度、关注项、催化剂任一存在即可） */
const hasLlmInsight = (item: AlphaSiftCandidate) =>
  Boolean(
    item.llmThesis ||
      item.llmSector ||
      item.llmTheme ||
      item.llmConfidence != null ||
      item.llmWatchItems?.length ||
      item.llmCatalysts?.length,
  );

/**
 * 格式化热点题材发酵路线节点的时间标签
 * 依次取 publishedAt、date、time；支持日期和完整时间戳的本地化格式
 * @param item - 发酵路线节点
 * @returns 格式化后的时间标签；无时间时返回来源名
 */
const getRouteTimeLabel = (item: AlphaSiftHotspotDetail['route'][number]) => {
  const rawTime = item.publishedAt || item.date || item.time || '';
  if (!rawTime) {
    return item.source || '待确认';
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(rawTime)) {
    return rawTime;
  }
  const parsed = new Date(rawTime);
  if (!Number.isNaN(parsed.getTime())) {
    return parsed.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  }
  return rawTime;
};

/** 获取热点题材的发酵路线节点列表，优先 route，回退 timeline */
const getHotspotRouteItems = (detail: AlphaSiftHotspotDetail) => {
  const route = detail.route || [];
  if (route.length > 0) {
    return route;
  }
  return detail.timeline || [];
};

/** 格式化热点指标数值；无效值返回"观察中" */
const formatHotspotMetric = (value: unknown, digits = 1) => {
  const formatted = formatNumber(value, digits);
  return formatted === '-' ? '观察中' : formatted;
};

/** 获取热点题材的龙头股文本，最多取前 2 个；无数据时返回"观察中" */
const getHotspotLeadersText = (item: AlphaSiftHotspot) => {
  const leaders = (item.leaders || []).map((value) => String(value).trim()).filter(Boolean);
  if (leaders.length > 0) {
    return leaders.slice(0, 2).join('、');
  }
  return '观察中';
};

/** 获取热点题材的覆盖股票数文本；无效值返回"活跃股观察中" */
const getHotspotSampleText = (item: AlphaSiftHotspot) => {
  if (item.sampleStockCount == null || Number.isNaN(Number(item.sampleStockCount))) {
    return '活跃股观察中';
  }
  return `覆盖 ${item.sampleStockCount} 股`;
};

/** 格式化个股涨跌幅文本；无效值返回"行情待取" */
const formatStockChangeText = (value: unknown) => {
  const formatted = formatNumber(value);
  return formatted === '-' ? '行情待取' : `${formatted}%`;
};

/** 格式化热点题材更新时间戳为中文本地时间；无值时返回"待刷新" */
const formatHotspotUpdatedAt = (value: string | null) => {
  if (!value) {
    return '待刷新';
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
};

/**
 * 根据热度分和涨跌幅判断热点题材的强度等级
 * @param item - 热点题材数据
 * @param index - 排名索引（第 1 名自动为强势领先）
 * @returns 包含标签和样式类名的强度信息
 */
const getHotspotStrength = (item: AlphaSiftHotspot, index: number) => {
  const heat = Number(item.heatScore ?? 0);
  const changePct = Number(item.changePct ?? 0);
  if (index === 0 || heat >= 90 || changePct >= 8) {
    return { label: '强势领先', className: 'bg-stock-up-10 stock-up' };
  }
  if (heat >= 80 || changePct >= 5) {
    return { label: '强势', className: 'bg-blue-500/10 text-blue-500' };
  }
  return { label: '较强', className: 'bg-cyan/10 text-cyan' };
};

/**
 * 热点题材图标匹配规则：按题材名称关键词匹配对应的行业图标和配色
 * 匹配优先级从上到下，首个匹配的规则生效
 */
const HOTSPOT_ICON_RULES: Array<{
  pattern: RegExp;
  icon: React.ComponentType<{ className?: string }>;
  className: string;
}> = [
  { pattern: /金|银|铜|铝|铅|锌|钼|钴|镍|贵金属|矿|有色/, icon: Pickaxe, className: 'bg-orange-500/10 text-orange-500' },
  { pattern: /黄金|珠宝/, icon: Gem, className: 'bg-amber-500/10 text-amber-500' },
  { pattern: /油|气|能源|煤/, icon: Droplet, className: 'bg-yellow-700/10 text-yellow-700' },
  { pattern: /金融|券商|银行|保险|资本/, icon: Landmark, className: 'bg-orange-500/10 text-orange-500' },
  { pattern: /航空|机场|航天|运输/, icon: Plane, className: 'bg-blue-500/10 text-blue-500' },
  { pattern: /林业|农业|种植/, icon: Trees, className: 'bg-emerald-500/10 text-emerald-500' },
  { pattern: /医疗|诊断|卫生|医药/, icon: Stethoscope, className: 'bg-teal-500/10 text-teal-500' },
  { pattern: /食品|餐饮|酒/, icon: Utensils, className: 'bg-violet-500/10 text-violet-500' },
  { pattern: /工业|制造|修理|机械|设备/, icon: Wrench, className: 'bg-blue-500/10 text-blue-500' },
  { pattern: /租赁|地产|建筑/, icon: Building2, className: 'bg-emerald-500/10 text-emerald-500' },
  { pattern: /电|芯片|算力|AI|机器人/, icon: Factory, className: 'bg-indigo-500/10 text-indigo-500' },
  { pattern: /保险|安全/, icon: Shield, className: 'bg-blue-500/10 text-blue-500' },
];

/**
 * 根据热点题材名称获取对应的图标和配色
 * @param topic - 题材名称
 * @returns 匹配到的图标规则；无匹配时返回默认的 Activity 图标
 */
const getHotspotIcon = (topic: string) => {
  const match = HOTSPOT_ICON_RULES.find((rule) => rule.pattern.test(topic));
  return match || { icon: Activity, className: 'bg-cyan/10 text-cyan' };
};

/**
 * 迷你趋势线组件：根据评分生成 SVG 折线图
 * 评分越高折线上升幅度越大，选中状态使用橙色高亮
 * @param score - 评分值（0-100）
 * @param selected - 是否选中状态
 */
const MiniSparkline: React.FC<{ score?: number | null; selected?: boolean }> = ({ score, selected }) => {
  const normalizedScore = Number.isFinite(Number(score)) ? Math.max(0, Math.min(100, Number(score))) : 65;
  const lift = Math.max(0, Math.min(16, normalizedScore / 7));
  const path = `M2 35 C12 ${32 - lift / 4}, 16 ${34 - lift / 2}, 24 ${28 - lift / 3} S38 ${29 - lift}, 46 ${23 - lift / 2} S62 ${24 - lift}, 72 ${16 - lift / 3} S86 ${15 - lift}, 94 ${7}`;
  return (
    <svg className="h-8 w-20" viewBox="0 0 96 40" aria-hidden="true">
      <path d={`${path} L94 40 L2 40 Z`} fill={selected ? 'rgba(249,115,22,0.14)' : 'rgba(59,130,246,0.12)'} />
      <path d={path} fill="none" stroke={selected ? '#f97316' : '#3b82f6'} strokeLinecap="round" strokeWidth="2" />
    </svg>
  );
};

// ============ 主页面 ============

/**
 * AlphaSift 选股主页面组件
 *
 * 职责：
 * - 检测并开启 AlphaSift 适配层
 * - 选择市场、策略和返回数量，提交异步选股任务并轮询状态
 * - 浏览热点题材云图，查看发酵时间线和概念股详情
 * - 展示候选股票列表，支持展开查看因子评分、LLM 判断、风险标签等
 *
 * 数据流：
 * 1. 页面挂载时检测 AlphaSift 状态，可用时加载策略列表和热点题材
 * 2. 用户提交选股任务后，持久化 taskId 到 sessionStorage 并开始轮询
 * 3. 轮询到 completed 时展示候选结果，failed 时展示错误并清理任务
 * 4. 页面刷新后从 sessionStorage 恢复 taskId，继续轮询未完成的任务
 * 5. 用户可展开/折叠热点题材区域，选择题材查看详情和概念股
 */
const StockScreeningPage: React.FC = () => {
  const navigate = useNavigate();
  // 从 sessionStorage 恢复的持久化选股任务（仅初始化时读取一次）
  const [restoredTask] = useState<PersistedScreenTask | null>(() => readPersistedScreenTask());
  // AlphaSift 是否已开启
  const [enabled, setEnabled] = useState(false);
  // AlphaSift 适配层是否可用（依赖已安装且服务正常）
  const [available, setAvailable] = useState(false);
  // L4 缓存：市场/策略/数量偏好（localStorage 永久保存）
  const [market, setMarket] = usePreference<string>('screening-market', restoredTask?.market || 'cn');
  const [strategy, setStrategy] = usePreference<string>('screening-strategy', restoredTask?.strategy || 'dual_low');
  // 从后端加载的可用策略列表
  const [strategies, setStrategies] = useState<AlphaSiftStrategy[]>([]);
  const [maxResults, setMaxResults] = usePreference<number>('screening-max-results', restoredTask?.maxResults || 3);
  // 选股候选结果列表
  const [candidates, setCandidates] = useState<AlphaSiftCandidate[]>([]);
  // 热点题材列表
  const [hotspots, setHotspots] = useState<AlphaSiftHotspot[]>([]);
  // 热点题材缓存更新时间
  const [hotspotsUpdatedAt, setHotspotsUpdatedAt] = useState<string | null>(null);
  // 热点题材区域是否展开
  const [hotspotsExpanded, setHotspotsExpanded] = useState(false);
  // 当前选中的热点题材主题
  const [selectedHotspotTopic, setSelectedHotspotTopic] = useState<string | null>(null);
  // 选中热点题材的 ref，用于回调中获取最新值（避免闭包陈旧）
  const selectedHotspotTopicRef = useRef<string | null>(null);
  // 热点详情请求 ID 的 ref，用于取消过期的异步请求
  const hotspotDetailRequestIdRef = useRef(0);
  // 热点详情缓存（按 topic 存储，避免重复请求）
  const hotspotDetailsByTopicRef = useRef<Record<string, AlphaSiftHotspotDetail>>({});
  // 当前选中的热点题材详情数据
  const [hotspotDetail, setHotspotDetail] = useState<AlphaSiftHotspotDetail | null>(null);
  // 热点详情加载态
  const [loadingHotspotDetail, setLoadingHotspotDetail] = useState(false);
  // 热点详情加载错误信息
  const [hotspotDetailError, setHotspotDetailError] = useState('');
  // 热点题材列表加载态
  const [loadingHotspots, setLoadingHotspots] = useState(false);
  // 热点题材加载错误信息
  const [hotspotError, setHotspotError] = useState('');
  // 选股任务响应元数据（包含 runId、快照数、LLM 状态等）
  const [screenMeta, setScreenMeta] = useState<AlphaSiftScreenResponse | null>(null);
  // 当前展开详情的候选股票代码
  const [expandedCode, setExpandedCode] = useState<string | null>(null);
  // 选股任务整体加载态（提交中或轮询中）
  const [loading, setLoading] = useState(Boolean(restoredTask?.taskId));
  // 开启 AlphaSift 的加载态
  const [enabling, setEnabling] = useState(false);
  // 策略列表加载态
  const [loadingStrategies, setLoadingStrategies] = useState(false);
  // 选股任务调用错误信息
  const [error, setError] = useState('');
  // 策略列表加载错误信息
  const [strategyLoadError, setStrategyLoadError] = useState('');
  // 当前轮询的选股任务 ID
  const [activeTaskId, setActiveTaskId] = useState<string | null>(restoredTask?.taskId ?? null);
  // 选股任务进度百分比
  const [taskProgress, setTaskProgress] = useState(restoredTask?.taskId ? 10 : 0);
  // 选股任务状态提示文案
  const [taskMessage, setTaskMessage] = useState(restoredTask?.taskId ? '正在恢复选股任务状态...' : '');

  // ===== 派生值 =====
  // 当前选中的策略对象
  const selectedStrategy = useMemo(() => strategies.find((item) => item.id === strategy), [strategies, strategy]);
  // 策略显示名称（优先 name，其次 title，默认"自定义策略"）
  const selectedStrategyTitle = selectedStrategy?.name || selectedStrategy?.title || '自定义策略';
  // 策略标签（优先 category，其次 tag，默认"自定义"）
  const selectedStrategyTag = selectedStrategy?.category || selectedStrategy?.tag || selectedStrategy?.tags?.[0] || '自定义';
  // 策略完整显示文案（有策略对象时用标题，否则显示策略 ID）
  const displayedStrategy = selectedStrategy ? selectedStrategyTitle : `自定义策略 (${strategy})`;
  // 选股提示消息列表（从 screenMeta 中提取去重后的消息）
  const screenMessages = useMemo(() => getScreenMessages(screenMeta), [screenMeta]);
  // LLM 重排是否降级（未完成或未返回判断）
  const llmDegraded = screenMeta?.llmRanked === false;
  // 告警消息列表：LLM 降级时补充降级提示
  const alertMessages = llmDegraded
    ? screenMessages.length > 0
      ? screenMessages
      : ['LLM 重排未完成或未返回判断，当前候选来自 AlphaSift 本地因子评分。']
    : screenMessages;
  // 选股功能是否可用（已开启且适配层可用）
  const isScreeningEnabled = enabled && available;
  // 页面状态文案
  const statusText = isScreeningEnabled ? '选股已开启' : '选股未开启';

  // ===== 数据处理回调 =====

  /**
   * 应用选股结果到页面状态
   * 更新元数据、候选列表，并默认展开第一个候选的详情
   * @param result - 选股响应数据
   */
  const applyScreenResult = useCallback((result: AlphaSiftScreenResponse) => {
    const nextCandidates = result.candidates || [];
    setScreenMeta(result);
    setCandidates(nextCandidates);
    setExpandedCode(nextCandidates[0]?.code ?? null);
  }, []);

  /** 清空选股结果（切换策略/市场/数量时调用） */
  const clearScreeningResults = () => {
    setCandidates([]);
    setScreenMeta(null);
    setExpandedCode(null);
  };

  /**
   * 加载热点题材详情
   * 优先使用缓存；无缓存时发起 API 请求，并通过 requestId 机制取消过期响应
   * @param topic - 热点题材主题
   * @param options.refresh - 是否强制刷新（跳过缓存）
   */
  const loadHotspotDetail = useCallback(async (topic: string, options: { refresh?: boolean } = {}) => {
    if (!topic) {
      return;
    }
    const cachedDetail = !options.refresh ? hotspotDetailsByTopicRef.current[topic] : null;
    if (cachedDetail) {
      setHotspotDetail(cachedDetail);
      setHotspotDetailError('');
      setLoadingHotspotDetail(false);
      return;
    }
    const requestId = hotspotDetailRequestIdRef.current + 1;
    hotspotDetailRequestIdRef.current = requestId;
    const isCurrentRequest = () => hotspotDetailRequestIdRef.current === requestId;
    const canApplyRequest = () => isCurrentRequest() && selectedHotspotTopicRef.current === topic;
    setLoadingHotspotDetail(true);
    setHotspotDetail((currentDetail) => (currentDetail?.topic === topic ? currentDetail : null));
    setHotspotDetailError('');
    try {
      const detail = await alphasiftApi.getHotspotDetail({ topic, provider: 'akshare', refresh: options.refresh ?? false });
      if (!canApplyRequest()) {
        return;
      }
      hotspotDetailsByTopicRef.current = {
        ...hotspotDetailsByTopicRef.current,
        [topic]: detail,
      };
      setHotspotDetail(detail);
    } catch (err) {
      if (!canApplyRequest()) {
        return;
      }
      setHotspotDetail(null);
      setHotspotDetailError(toApiErrorMessage(err, '热点题材详情加载失败，请稍后重试。'));
    } finally {
      if (isCurrentRequest()) {
        setLoadingHotspotDetail(false);
      }
    }
  }, []);

  /**
   * 加载 AlphaSift 可用策略列表
   * 加载成功后若当前策略不在列表中，自动切换到首个策略
   */
  const loadStrategies = useCallback(async () => {
    setLoadingStrategies(true);
    try {
      setStrategyLoadError('');
      const result = await alphasiftApi.getStrategies();
      const loadedStrategies = result.strategies || [];
      setStrategies(loadedStrategies);
      if (loadedStrategies.length > 0) {
        setStrategy((currentStrategy) =>
          loadedStrategies.some((item) => item.id === currentStrategy) ? currentStrategy : loadedStrategies[0].id,
        );
      }
    } catch (err) {
      setStrategies([]);
      setStrategyLoadError(err instanceof Error ? err.message : 'AlphaSift 策略列表加载失败');
    } finally {
      setLoadingStrategies(false);
    }
  }, []);

  /**
   * 加载热点题材列表
   * 请求成功后合并详情缓存，保留当前选中的题材（若仍存在），否则清空选中
   * @param refresh - 是否强制刷新（拉取实时数据而非缓存）
   */
  const loadHotspots = useCallback(async (refresh = false) => {
    setLoadingHotspots(true);
    setHotspotError('');
    try {
      const result = await alphasiftApi.getHotspots({ provider: 'akshare', top: 12, refresh });
      const nextHotspots = result.hotspots || [];
      const nextDetails = result.details || {};
      hotspotDetailsByTopicRef.current = {
        ...hotspotDetailsByTopicRef.current,
        ...nextDetails,
      };
      const currentTopic = selectedHotspotTopicRef.current;
      const retainedTopic = Boolean(currentTopic && nextHotspots.some((item) => item.topic === currentTopic));
      const nextTopic = retainedTopic ? currentTopic : null;
      setHotspots(nextHotspots);
      setHotspotsUpdatedAt(result.cachedAt || (nextHotspots.length > 0 ? new Date().toISOString() : null));
      setSelectedHotspotTopic(nextTopic);
      selectedHotspotTopicRef.current = nextTopic;
      if (nextTopic && nextDetails[nextTopic]) {
        setHotspotDetail(nextDetails[nextTopic]);
        setLoadingHotspotDetail(false);
      } else if (retainedTopic && refresh && nextTopic) {
        void loadHotspotDetail(nextTopic, { refresh: true });
      } else if (!retainedTopic) {
        setHotspotDetail(null);
      }
      setHotspotDetailError('');
      if (nextHotspots.length === 0) {
        setHotspotError(formatHotspotEmptyMessage(result));
      }
    } catch (err) {
      setHotspotError(toApiErrorMessage(err, '热点题材加载失败，请稍后重试。'));
    } finally {
      setLoadingHotspots(false);
    }
  }, [loadHotspotDetail]);

  /** 选中热点题材：更新选中状态，优先展示缓存的详情数据 */
  const handleHotspotSelect = useCallback((topic: string) => {
    selectedHotspotTopicRef.current = topic;
    setSelectedHotspotTopic(topic);
    const cachedDetail = hotspotDetailsByTopicRef.current[topic];
    if (cachedDetail) {
      setHotspotDetail(cachedDetail);
      setHotspotDetailError('');
      setLoadingHotspotDetail(false);
    } else {
      setHotspotDetail((currentDetail) => (currentDetail?.topic === topic ? currentDetail : null));
    }
  }, []);

  /** 切换热点题材区域展开/折叠；折叠时清空选中状态和详情 */
  const toggleHotspotsExpanded = useCallback(() => {
    setHotspotsExpanded((expanded) => {
      const nextExpanded = !expanded;
      if (!nextExpanded) {
        selectedHotspotTopicRef.current = null;
        setSelectedHotspotTopic(null);
        setHotspotDetail(null);
        setHotspotDetailError('');
      }
      return nextExpanded;
    });
  }, []);

  /**
   * 点击热点题材中的概念股，跳转到首页进行个股分析
   * 通过路由 state 传递股票代码、名称和来源标记，首页接收后自动触发分析
   * @param stock - 概念股数据
   */
  const handleAnalyzeHotspotStock = useCallback((stock: AlphaSiftHotspotDetail['stocks'][number]) => {
    const stockCode = String(stock.code || '').trim();
    if (!stockCode) {
      return;
    }
    const stockName = String(stock.name || stockCode).trim();
    navigate('/', {
      state: {
        stockCode,
        stockName,
        autoAnalyze: true,
        selectionSource: 'alphasift_hotspot',
      },
    });
  }, [navigate]);

  // ===== 副作用 =====

  /** 同步 selectedHotspotTopic 状态到 ref，确保回调中能获取最新值 */
  useEffect(() => {
    selectedHotspotTopicRef.current = selectedHotspotTopic;
  }, [selectedHotspotTopic]);

  /** 选中热点题材变化时，自动加载对应的详情数据（优先使用缓存） */
  useEffect(() => {
    if (!selectedHotspotTopic) {
      return;
    }
    void loadHotspotDetail(selectedHotspotTopic);
  }, [loadHotspotDetail, selectedHotspotTopic]);

  /**
   * 页面挂载时检测 AlphaSift 状态
   * 可用且已开启时加载策略列表和热点题材；失败时标记为不可用
   */
  useEffect(() => {
    let active = true;
    alphasiftApi
      .getStatus()
      .then((status) => {
        if (!active) {
          return;
        }
        setEnabled(status.enabled);
        setAvailable(status.available);
        if (status.enabled && status.available) {
          void loadStrategies();
          void loadHotspots(false);
        }
      })
      .catch(() => {
        if (active) {
          setEnabled(false);
          setAvailable(false);
        }
      });
    return () => {
      active = false;
    };
  }, [loadHotspots, loadStrategies]);

  /**
   * 选股任务状态轮询
   * 当 activeTaskId 存在时，每 2 秒轮询任务状态：
   * - completed：展示候选结果并清理任务
   * - failed：展示错误信息并清理任务
   * - pending/processing：继续轮询
   * - 不可恢复错误：停止轮询并提示用户重新提交
   * - 可恢复错误（超时/网络）：继续轮询并展示临时提示
   * 组件卸载或 taskId 变化时清理定时器
   */
  useEffect(() => {
    if (!activeTaskId) {
      return undefined;
    }

    const pollingTaskId = activeTaskId;
    let active = true;
    let timer: ReturnType<typeof window.setTimeout> | undefined;

    function finishTask() {
      clearPersistedScreenTask();
      setActiveTaskId(null);
      setLoading(false);
    }

    function applyTaskStatus(task: AlphaSiftScreenTaskStatus) {
      const nextProgress = Number(task.progress ?? 0);
      setTaskProgress(Number.isFinite(nextProgress) ? nextProgress : 0);
      setTaskMessage(task.message || '');

      if (task.status === 'completed') {
        if (task.result) {
          applyScreenResult(task.result);
          setError('');
        } else {
          setError('选股任务已完成，但服务端未返回候选结果。');
          setCandidates([]);
          setScreenMeta(null);
        }
        finishTask();
        return;
      }

      if (task.status === 'failed') {
        setCandidates([]);
        setScreenMeta(null);
        setExpandedCode(null);
        setError(formatScreenTaskFailure(task.error || task.message));
        finishTask();
        return;
      }

      if (isRunningScreenTask(task.status)) {
        setLoading(true);
        timer = window.setTimeout(pollTask, SCREEN_TASK_POLL_INTERVAL_MS);
        return;
      }

      setError(`选股任务返回未知状态：${task.status || 'unknown'}`);
      finishTask();
    }

    async function pollTask() {
      try {
        const task = await alphasiftApi.getScreenTask(pollingTaskId);
        if (!active) {
          return;
        }
        applyTaskStatus(task);
      } catch (err) {
        if (!active) {
          return;
        }
        const parsedError = getParsedApiError(err);
        if (isUnrecoverableScreenTaskError(parsedError)) {
          setError(formatParsedApiError(parsedError) || '选股任务不可恢复，请重新提交。');
          setCandidates([]);
          setScreenMeta(null);
          finishTask();
          return;
        }
        setError(formatRecoverableScreenTaskPollingError(parsedError));
        setLoading(true);
        timer = window.setTimeout(pollTask, SCREEN_TASK_POLL_INTERVAL_MS);
      }
    }

    void pollTask();

    return () => {
      active = false;
      if (timer) {
        window.clearTimeout(timer);
      }
    };
  }, [activeTaskId, applyScreenResult]);

  // ===== 事件处理 =====

  /**
   * 开启 AlphaSift 适配层
   * 调用后端 enable 接口，成功后加载策略列表；
   * 失败时回退查询实际状态并展示错误
   */
  const handleEnable = async () => {
    setEnabling(true);
    setError('');
    try {
      await alphasiftApi.enable();
      setEnabled(true);
      setAvailable(true);
      await loadStrategies();
    } catch (err) {
      try {
        const status = await alphasiftApi.getStatus();
        setEnabled(status.enabled);
        setAvailable(status.available);
      } catch {
        setEnabled(false);
        setAvailable(false);
      }
      setError(err instanceof Error ? err.message : '开启 AlphaSift 失败');
    } finally {
      setEnabling(false);
    }
  };

  /** 切换策略：策略变化时清空已有选股结果 */
  const handleStrategyChange = (nextStrategy: string) => {
    if (nextStrategy !== strategy) {
      clearScreeningResults();
    }
    setStrategy(nextStrategy);
  };

  /** 切换市场：市场变化时清空已有选股结果 */
  const handleMarketChange = (nextMarket: string) => {
    if (nextMarket !== market) {
      clearScreeningResults();
    }
    setMarket(nextMarket);
  };

  /** 修改返回数量：数量变化时清空已有选股结果 */
  const handleMaxResultsChange = (nextMaxResults: number) => {
    if (nextMaxResults !== maxResults) {
      clearScreeningResults();
    }
    setMaxResults(nextMaxResults);
  };

  /**
   * 提交选股任务
   * 收集当前市场、策略和返回数量，调用后端 startScreen 接口创建异步选股任务；
   * 任务创建成功后将 taskId 持久化到 sessionStorage（用于刷新恢复），
   * 并设置 activeTaskId 触发状态轮询；失败时展示错误信息
   */
  const handleSubmit = async () => {
    setLoading(true);
    setError('');
    setScreenMeta(null);
    setTaskProgress(0);
    setTaskMessage('正在提交选股任务...');
    try {
      const task = await alphasiftApi.startScreen({ market, strategy, maxResults });
      persistScreenTask({
        taskId: task.taskId,
        market,
        strategy,
        maxResults,
      });
      setActiveTaskId(task.taskId);
      setTaskProgress(0);
      setTaskMessage(task.message || 'AlphaSift 选股任务已提交');
    } catch (err) {
      setCandidates([]);
      setLoading(false);
      setError(toApiErrorMessage(err, '选股任务提交失败，请稍后重试。'));
    }
  };

  return (
    <AppPage className="max-w-6xl space-y-6 pb-12 pt-6">
      {/* ===== 页面头部：状态指示（页面标题已由顶部 header 展示）===== */}
      <div className="inline-flex w-fit items-center gap-2 rounded-2xl border border-border/70 bg-card/80 px-4 py-2 text-sm shadow-soft-card">
        <span className={`h-2.5 w-2.5 rounded-full ${isScreeningEnabled ? 'bg-success' : 'bg-warning'}`} />
        <span className="font-medium text-secondary-text">{statusText}</span>
      </div>

      {!enabled ? (
        <InlineAlert
          variant="info"
          title="AlphaSift 未开启"
          message="点击后写入 ALPHASIFT_ENABLED=true；AlphaSift 已随后端依赖安装，若适配层缺失请先更新依赖或重建后端。"
          action={
            <Button size="sm" isLoading={enabling} loadingText="开启中..." onClick={() => void handleEnable()}>
              开启 AlphaSift
            </Button>
          }
        />
      ) : null}

      {enabled && !available ? (
        <InlineAlert
          variant="warning"
          title="AlphaSift 适配层不可用"
          message="适配层当前不可用，请先确认后端已安装依赖并重启服务，必要时执行 pip install -r requirements.txt 或使用设置页/服务端 /install 接口进行修复安装。"
        />
      ) : null}

      <InlineAlert
        variant="warning"
        title="实验功能与风险提示"
        message="AlphaSift 选股仍处于实验性质，结果仅用于研究和辅助判断，不构成投资建议；市场有风险，交易决策和损益由使用者自行承担。"
      />

      {loading ? (
        <InlineAlert
          variant="info"
          title="选股任务运行中"
          message={`${taskMessage || '正在执行 AlphaSift 选股'}。任务 ID：${activeTaskId ? activeTaskId.slice(0, 12) : '-'}`}
        />
      ) : null}

      {error ? <InlineAlert variant="danger" title="调用失败" message={error} /> : null}

      <section className="rounded-2xl border border-border/80 bg-card/95 p-4 shadow-soft-card">
        <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="flex items-start gap-3">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-orange-500/10 text-orange-500 shadow-[0_10px_30px_rgba(249,115,22,0.16)]">
              <Flame className="h-5 w-5" />
            </span>
            <div>
              <h2 className="text-lg font-bold tracking-normal text-foreground">热点题材</h2>
              <p className="mt-1 text-xs leading-5 text-secondary-text">
                来自 AlphaSift 最新 hotspot 能力；capital_heat、balanced_alpha 等策略会把 theme_heat 纳入评分。
              </p>
            </div>
          </div>
          <div className="flex flex-col items-start gap-2 lg:items-end">
            <div className="flex flex-wrap items-center gap-2">
              <Button
                size="sm"
                variant="secondary"
                disabled={!isScreeningEnabled}
                onClick={toggleHotspotsExpanded}
              >
                <Bookmark className="h-4 w-4" />
                {hotspotsExpanded ? '收起热点题材' : `展开热点题材${hotspots.length ? `（${hotspots.length}）` : ''}`}
                <ChevronDown className={`h-4 w-4 transition-transform ${hotspotsExpanded ? 'rotate-180' : ''}`} />
              </Button>
              {hotspotsExpanded ? (
              <Button
                size="sm"
                variant="secondary"
                isLoading={loadingHotspots}
                loadingText="刷新中..."
                disabled={!isScreeningEnabled || loadingHotspots}
                onClick={() => void loadHotspots(true)}
              >
                <RefreshCw className="h-4 w-4" />
                刷新热点题材
              </Button>
              ) : null}
            </div>
            <p className="text-xs text-secondary-text">更新时间：{formatHotspotUpdatedAt(hotspotsUpdatedAt)}</p>
          </div>
        </div>

        {hotspotError ? (
          <p className="mb-3 rounded-xl border border-warning/30 bg-warning/10 px-3 py-2 text-xs text-warning">
            {hotspotError}
          </p>
        ) : null}

        {!hotspotsExpanded ? (
          <div className="flex flex-col gap-2 rounded-xl border border-border/70 bg-surface/70 px-4 py-3 text-sm text-secondary-text sm:flex-row sm:items-center sm:justify-between">
            <span>
              {hotspots.length > 0
                ? `已缓存 ${hotspots.length} 个热点题材，展开后可查看热度、阶段和发酵路线。`
                : '热点题材默认折叠；展开后可读取缓存，点击刷新才拉取实时数据。'}
            </span>
            <span className="text-xs">实时详情会在选择具体题材后加载</span>
          </div>
        ) : hotspots.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border bg-surface/70 px-4 py-6 text-sm text-secondary-text">
            点击刷新后会拉取热点概念/行业排行、热度分、生命周期阶段和活跃龙头。
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
            {hotspots.map((item, index) => {
              const selected = selectedHotspotTopic === item.topic;
              const strength = getHotspotStrength(item, index);
              const iconMeta = getHotspotIcon(item.name || item.topic);
              const Icon = iconMeta.icon;
              return (
              <button
                key={`${item.topic}-${item.rank ?? ''}`}
                className={`group relative min-h-[116px] overflow-hidden rounded-xl border px-3 py-3 text-left transition-all ${
                  selected
                    ? 'border-orange-400 bg-gradient-to-br from-orange-500/10 via-card to-card shadow-[0_0_0_1px_rgba(249,115,22,0.16),0_18px_44px_rgba(249,115,22,0.14)]'
                    : 'border-border/80 bg-card hover:-translate-y-0.5 hover:border-orange-300/70 hover:shadow-soft-card'
                }`}
                type="button"
                onClick={() => handleHotspotSelect(item.topic)}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 items-start gap-3">
                    <span
                      className={`grid h-6 w-6 shrink-0 place-items-center rounded-full text-xs font-bold ${
                        index < 3 ? 'bg-orange-500 text-white shadow-[0_8px_24px_rgba(249,115,22,0.24)]' : 'bg-surface text-secondary-text'
                      }`}
                    >
                      {index + 1}
                    </span>
                    <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-full ${iconMeta.className}`}>
                      <Icon className="h-5 w-5" />
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-bold text-foreground">{item.name || item.topic}</p>
                      <span className={`mt-1 inline-flex rounded-md px-1.5 py-0.5 text-[11px] font-semibold ${strength.className}`}>
                        {strength.label}
                      </span>
                    </div>
                  </div>
                  <span className="shrink-0 text-2xl font-black leading-none text-orange-500">
                    {formatNumber(item.heatScore, 0)}
                  </span>
                </div>
                <div className="mt-4 grid max-w-[72%] gap-1 text-[11px] text-secondary-text">
                  <span>涨跌幅 <strong className="font-semibold text-foreground">{formatHotspotMetric(item.changePct)}%</strong></span>
                  <span>趋势 <strong className="font-semibold text-foreground">{formatHotspotMetric(item.trendScore)}</strong> · 持续 <strong className="font-semibold text-foreground">{formatHotspotMetric(item.persistenceScore)}</strong></span>
                  <span>{getHotspotSampleText(item)} · 龙头 {getHotspotLeadersText(item)}</span>
                </div>
                <div className="absolute bottom-3 right-3 opacity-95 transition-transform group-hover:scale-105">
                  <MiniSparkline score={item.heatScore} selected={selected} />
                </div>
              </button>
              );
            })}
          </div>
        )}

        {hotspotsExpanded && selectedHotspotTopic ? (
          <div className="mt-4 rounded-xl border border-border/80 bg-surface/80 p-4">
            <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h3 className="text-sm font-semibold text-foreground">
                  {hotspotDetail?.name || selectedHotspotTopic}
                </h3>
                <p className="mt-1 text-xs leading-5 text-secondary-text">
                  {loadingHotspotDetail ? '正在读取发酵路线与概念股...' : hotspotDetail?.summary || '点击题材查看发酵路线与概念股。'}
                </p>
                {hotspotDetail?.canonicalTopic && hotspotDetail.canonicalTopic !== selectedHotspotTopic ? (
                  <p className="mt-1 text-[11px] text-secondary-text">标准题材：{hotspotDetail.canonicalTopic}</p>
                ) : null}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {hotspotDetail?.qualityStatus ? (
                  <span className="w-fit rounded-full bg-warning/10 px-3 py-1 text-xs font-semibold text-warning">
                    质量 {hotspotDetail.qualityStatus}
                  </span>
                ) : null}
                {hotspotDetail?.fallbackUsed || hotspotDetail?.stale ? (
                  <span className="w-fit rounded-full bg-warning/10 px-3 py-1 text-xs font-semibold text-warning">
                    {hotspotDetail.staleAgeHours != null ? `缓存回退 ${formatNumber(hotspotDetail.staleAgeHours, 1)}h` : '缓存回退'}
                  </span>
                ) : null}
                {hotspotDetail?.stockCount != null ? (
                  <span className="w-fit rounded-full bg-orange-500/10 px-3 py-1 text-xs font-semibold text-orange-500">
                    概念股 {hotspotDetail.stockCount}
                  </span>
                ) : null}
              </div>
            </div>

            {hotspotDetailError ? (
              <p className="mb-3 rounded-xl border border-warning/30 bg-warning/10 px-3 py-2 text-xs text-warning">
                {hotspotDetailError}
              </p>
            ) : null}

            {hotspotDetail && ((hotspotDetail.missingFields || []).length > 0 || (hotspotDetail.sourceErrors || []).length > 0) ? (
              <details className="mb-3 rounded-xl border border-warning/30 bg-warning/10 px-3 py-2 text-xs text-warning">
                <summary className="cursor-pointer font-semibold">详情数据已降级，展开查看原因</summary>
                <div className="mt-2 space-y-1 leading-5">
                  {(hotspotDetail.missingFields || []).length > 0 ? (
                    <p>缺失字段：{(hotspotDetail.missingFields || []).join('、')}</p>
                  ) : null}
                  {(hotspotDetail.sourceErrors || []).slice(0, 4).map((message, index) => (
                    <p key={`${message}-${index}`}>{message}</p>
                  ))}
                </div>
              </details>
            ) : null}

            {hotspotDetail ? (
              <div className="grid gap-4 lg:grid-cols-[1fr_1.3fr]">
                <div>
                  <p className="mb-3 flex items-center gap-1.5 text-xs font-semibold text-secondary-text">
                    <Clock3 className="h-3.5 w-3.5 text-orange-500" />
                    发酵时间线
                  </p>
                  <div className="relative space-y-0 pl-4 before:absolute before:bottom-3 before:left-[5px] before:top-2 before:w-px before:bg-border">
                    {getHotspotRouteItems(hotspotDetail).map((item, index) => (
                      <div key={`${item.title}-${index}`} className="relative pb-4 last:pb-0">
                        <span className="absolute -left-4 top-1 h-2.5 w-2.5 rounded-full border border-orange-400 bg-card" />
                        <div className="rounded-lg border border-border/70 bg-card/80 p-3">
                          <p className="text-[11px] font-semibold text-orange-500">{getRouteTimeLabel(item)}</p>
                          <p className="mt-1 text-xs font-semibold text-foreground">{item.title}</p>
                          <p className="mt-1 text-xs leading-5 text-secondary-text">{item.description}</p>
                          {item.source ? <p className="mt-2 text-[11px] text-secondary-text">来源 {item.source}</p> : null}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="mb-2 text-xs font-semibold text-secondary-text">概念股</p>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {(hotspotDetail.stocks || []).slice(0, 10).map((stock) => (
                      <div key={`${stock.code || stock.name}`} className="rounded-lg border border-border/70 bg-card/80 p-3">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <p className="truncate text-xs font-semibold text-foreground">{stock.name || stock.code || '-'}</p>
                            <p className="mt-1 text-[11px] text-secondary-text">{stock.code || '-'}</p>
                          </div>
                          <div className="flex shrink-0 items-center gap-1">
                            <span className="rounded-full bg-cyan/10 px-2 py-1 text-[11px] font-semibold text-cyan">
                              {stock.role || '概念股'}
                            </span>
                            {stock.code ? (
                              <button
                                type="button"
                                aria-label={`分析 ${stock.name || stock.code}`}
                                className="inline-flex h-7 items-center gap-1 rounded-full border border-cyan/30 bg-cyan/10 px-2 text-[11px] font-semibold text-cyan transition-colors hover:border-cyan hover:bg-cyan/15 hover:text-foreground"
                                onClick={() => handleAnalyzeHotspotStock(stock)}
                              >
                                <Play className="h-3 w-3" />
                                分析
                              </button>
                            ) : null}
                          </div>
                        </div>
                        <p className="mt-2 text-[11px] text-secondary-text">
                          涨跌幅 {formatStockChangeText(stock.changePct)} · 热度 {formatNumber(stock.hotStockScore, 0)}
                        </p>
                        {stock.source || stock.sourceConfidence != null || stock.fallbackUsed ? (
                          <p className="mt-1 text-[11px] text-secondary-text">
                            来源 {stock.source || '-'}
                            {stock.sourceConfidence != null ? ` · 置信 ${formatPercent(stock.sourceConfidence)}` : ''}
                            {stock.fallbackUsed ? ' · 回退' : ''}
                          </p>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        ) : null}
      </section>

      <section className="rounded-2xl border border-cyan/35 bg-card/95 p-4 shadow-soft-card">
        <div className="mb-4 flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-foreground">选择策略</h2>
            <p className="mt-1 text-xs text-secondary-text">策略来自 AlphaSift；HRS 会对候选补充行情、基本面和新闻上下文。</p>
          </div>
          <span className="rounded-full border border-cyan/30 bg-cyan/10 px-3 py-1 text-xs font-semibold text-cyan">
            {selectedStrategyTag}
          </span>
        </div>

        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
          {loadingStrategies ? (
            <div className="rounded-xl border border-dashed border-border bg-surface/70 p-4 text-sm text-secondary-text">
              正在读取可用策略...
            </div>
          ) : strategies.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border bg-surface/70 p-4 text-sm text-secondary-text">
              {strategyLoadError || 'AlphaSift 策略列表暂未载入，可在下方手动输入策略参数。'}
            </div>
          ) : (
            strategies.map((item) => {
              const selected = item.id === strategy;
              return (
                <button
                  key={item.id}
                  className={`min-h-28 rounded-xl border p-4 text-left transition-all ${
                    selected
                      ? 'border-cyan bg-cyan/10 shadow-[0_0_0_1px_hsl(var(--primary)/0.15),0_16px_36px_hsl(var(--primary)/0.12)]'
                      : 'border-border/80 bg-surface/70 hover:border-cyan/45 hover:bg-hover/70'
                  }`}
                  type="button"
                  disabled={loading}
                  onClick={() => handleStrategyChange(item.id)}
                >
                  <span className="text-base font-semibold text-foreground">{item.name || item.title || item.id}</span>
                  <span className="mt-2 block text-sm leading-6 text-secondary-text">{item.description || item.id}</span>
                  <span className="mt-3 inline-flex text-xs font-semibold text-cyan">
                    {item.category || item.tag || item.tags?.[0] || item.id}
                  </span>
                </button>
              );
            })
          )}
        </div>
      </section>

      <section className="rounded-2xl border border-border bg-card/95 p-4 shadow-soft-card">
        <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-foreground">
          <SlidersHorizontal className="h-4 w-4 text-cyan" />
          参数设置
        </div>

        <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr_180px_auto] lg:items-end">
          <label className="space-y-2 text-xs font-medium text-secondary-text">
            市场
            <select
              className="h-11 w-full rounded-xl border border-border bg-surface px-3 text-sm text-foreground outline-none transition-colors focus:border-cyan"
              value={market}
              disabled={loading}
              onChange={(event) => handleMarketChange(event.target.value)}
            >
              {MARKETS.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>

          <label className="space-y-2 text-xs font-medium text-secondary-text">
            策略参数
            <input
              className="h-11 w-full rounded-xl border border-border bg-surface px-3 text-sm text-foreground outline-none transition-colors focus:border-cyan"
              value={strategy}
              disabled={loading}
              onChange={(event) => handleStrategyChange(event.target.value)}
            />
          </label>

          <label className="space-y-2 text-xs font-medium text-secondary-text">
            返回数量
            <input
              className="h-11 w-full rounded-xl border border-border bg-surface px-3 text-sm text-foreground outline-none transition-colors focus:border-cyan"
              type="number"
              min={1}
              max={100}
              value={maxResults}
              disabled={loading}
              onChange={(event) => handleMaxResultsChange(Number(event.target.value))}
            />
          </label>

          <Button
            className="h-11 min-w-40"
            isLoading={loading}
            loadingText="筛选中..."
            disabled={!isScreeningEnabled || loading}
            onClick={() => void handleSubmit()}
          >
            <Play className="h-4 w-4" />
            运行选股
          </Button>
        </div>
      </section>

      <section className="rounded-2xl border border-border bg-card/95 p-4 shadow-soft-card">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <span
              className={`grid h-7 w-7 place-items-center rounded-full ${
                candidates.length > 0 ? 'text-success' : isScreeningEnabled ? 'text-cyan' : 'text-warning'
              }`}
            >
              {candidates.length > 0 ? <CheckCircle2 className="h-5 w-5" /> : <CircleAlert className="h-5 w-5" />}
            </span>
            <div>
              <h2 className="text-sm font-semibold text-foreground">
                {loading ? '选股运行中' : candidates.length > 0 ? '选股完成' : isScreeningEnabled ? '等待运行' : '等待开启'}
              </h2>
              <p className="mt-1 text-xs text-secondary-text">
                {loading
                  ? `${taskMessage || '正在执行 AlphaSift 选股'} · ${taskProgress}%`
                  : `当前策略：${displayedStrategy} · ${MARKETS.find((item) => item.id === market)?.label}`}
              </p>
            </div>
          </div>
          <div className="grid gap-1 text-xs text-secondary-text sm:text-right">
            <span>任务：{activeTaskId ? activeTaskId.slice(0, 12) : '-'}</span>
            <span>Run ID：{screenMeta?.runId || '-'}</span>
            <span>
              快照 {screenMeta?.snapshotCount ?? '-'} · 过滤后 {screenMeta?.afterFilterCount ?? '-'} · 候选 {screenMeta?.candidateCount ?? candidates.length}
            </span>
            <span>
              LLM：{screenMeta?.llmRanked ? '已重排' : screenMeta ? '未重排' : '-'}
              {screenMeta?.llmCoverage != null ? ` · 覆盖 ${formatPercent(screenMeta.llmCoverage)}` : ''}
            </span>
            <span>
              HRS增强：{screenMeta?.hrsEnrichment?.enrichedCount ?? '-'} / {screenMeta?.hrsEnrichment?.requestedCount ?? '-'}
            </span>
          </div>
        </div>
      </section>

      {screenMeta && alertMessages.length > 0 ? (
        <InlineAlert
          variant={llmDegraded ? 'warning' : 'info'}
          title={llmDegraded ? 'LLM 已降级' : 'AlphaSift 提示'}
          message={<ScreenAlertMessage messages={alertMessages} />}
        />
      ) : null}

      <section className="rounded-2xl border border-border bg-card/95 p-4 shadow-soft-card">
        <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-base font-semibold text-foreground">选股结果</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-secondary-text">
              AlphaSift 返回候选后，HRS 会对前几名补充行情、基本面、新闻和辅助摘要。
            </p>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-2 text-xs text-secondary-text">
            <Search className="h-4 w-4 text-cyan" />
            {candidates.length} 条候选
          </div>
        </div>

        {candidates.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border bg-surface/70 px-5 py-10 text-center">
            <p className="text-sm font-medium text-foreground">暂无结果</p>
            <p className="mt-2 text-sm text-secondary-text">开启 AlphaSift 后点击“运行选股”生成候选列表。</p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-xl border border-border">
            <table className="w-full min-w-[860px] border-collapse text-sm">
              <thead className="bg-surface text-left text-xs text-secondary-text">
                <tr>
                  <th className="w-14 px-4 py-3 font-semibold">#</th>
                  <th className="px-4 py-3 font-semibold">代码</th>
                  <th className="px-4 py-3 font-semibold">名称</th>
                  <th className="px-4 py-3 font-semibold">行业</th>
                  <th className="px-4 py-3 font-semibold">价格</th>
                  <th className="px-4 py-3 font-semibold">涨跌幅</th>
                  <th className="px-4 py-3 font-semibold">评分</th>
                  <th className="px-4 py-3 font-semibold">LLM</th>
                  <th className="px-4 py-3 font-semibold">风险</th>
                  <th className="px-4 py-3 font-semibold">详情</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((item) => {
                  const expanded = expandedCode === item.code;
                  const factors = getFactorEntries(item);
                  const llmInsightAvailable = hasLlmInsight(item);
                  const llmFallbackText =
                    llmDegraded && !llmInsightAvailable
                      ? '本次 LLM 重排失败或未返回判断，当前展示的是本地因子评分结果。'
                      : '暂无 LLM 判断';
                  const hrsWarnings = item.hrsContext?.warnings || [];
                  const hrsNews = item.hrsNews || [];
                  return (
                    <Fragment key={`${item.rank}-${item.code}`}>
                      <tr className="border-t border-border align-top transition-colors hover:bg-hover/50">
                        <td className="px-4 py-3 text-secondary-text">{item.rank}</td>
                        <td className="px-4 py-3 font-mono font-semibold text-foreground">{item.code}</td>
                        <td className="px-4 py-3 font-semibold text-foreground">{item.name || '-'}</td>
                        <td className="px-4 py-3 text-secondary-text">{item.industry || '-'}</td>
                        <td className="px-4 py-3 text-secondary-text">{formatNumber(item.price)}</td>
                        <td className="px-4 py-3 text-secondary-text">{formatNumber(item.changePct)}%</td>
                        <td className="px-4 py-3 font-bold text-cyan">{formatScore(item.score)}</td>
                        <td className="px-4 py-3 text-secondary-text">{llmDegraded ? '未重排' : formatScore(item.llmScore)}</td>
                        <td className="px-4 py-3">
                          <span className="rounded-lg bg-success/10 px-2.5 py-1 text-xs font-semibold text-success">
                            {item.riskLevel || 'unknown'}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <button
                            className="text-sm font-semibold text-cyan transition-colors hover:text-foreground"
                            type="button"
                            onClick={() => setExpandedCode(expanded ? null : item.code)}
                          >
                            {expanded ? '收起' : '展开查看'}
                          </button>
                        </td>
                      </tr>
                      {expanded ? (
                        <tr className="border-t border-border bg-surface/45">
                          <td colSpan={10} className="px-4 py-4">
                            <div className="grid gap-4 lg:grid-cols-[1.1fr_1fr]">
                              <div className="space-y-3">
                                <div>
                                  <p className="text-xs font-semibold text-secondary-text">摘要</p>
                                  <p className="mt-1 text-sm leading-6 text-foreground">{getCandidateReason(item)}</p>
                                </div>
                                <div>
                                  <p className="text-xs font-semibold text-secondary-text">操作信号</p>
                                  <p className="mt-1 text-sm text-foreground">{getSignal(item)}</p>
                                </div>
                                {item.hrsAnalysisSummary ? (
                                  <div>
                                    <p className="text-xs font-semibold text-secondary-text">HRS 增强摘要</p>
                                    <p className="mt-1 text-sm leading-6 text-foreground">{item.hrsAnalysisSummary}</p>
                                  </div>
                                ) : null}
                                <div>
                                  <p className="text-xs font-semibold text-secondary-text">LLM 判断</p>
                                  <p className="mt-1 text-sm leading-6 text-foreground">
                                    {item.llmThesis || llmFallbackText}
                                  </p>
                                  {llmInsightAvailable ? (
                                    <p className="mt-1 text-xs text-secondary-text">
                                      板块 {item.llmSector || '-'} · 主题 {item.llmTheme || '-'} · 置信度 {formatPercent(item.llmConfidence)}
                                    </p>
                                  ) : (
                                    <p className="mt-1 text-xs text-secondary-text">LLM 元数据未返回</p>
                                  )}
                                </div>
                                <div>
                                  <p className="text-xs font-semibold text-secondary-text">风险标签</p>
                                  <p className="mt-1 text-sm text-foreground">
                                    {[...(item.riskFlags || []), ...(item.llmRisks || [])].length
                                      ? [...(item.riskFlags || []), ...(item.llmRisks || [])].join('，')
                                      : '无'}
                                  </p>
                                </div>
                              </div>
                              <div className="space-y-3">
                                <div>
                                  <p className="text-xs font-semibold text-secondary-text">主要因子</p>
                                  <div className="mt-2 grid grid-cols-2 gap-2">
                                    {factors.length > 0 ? (
                                      factors.map(([key, value]) => (
                                        <div key={key} className="rounded-lg border border-border bg-card px-3 py-2">
                                          <span className="block text-xs text-secondary-text">{key}</span>
                                          <span className="text-sm font-semibold text-foreground">{formatNumber(value)}</span>
                                        </div>
                                      ))
                                    ) : (
                                      <span className="text-sm text-secondary-text">无因子明细</span>
                                    )}
                                  </div>
                                </div>
                                <div>
                                  <p className="text-xs font-semibold text-secondary-text">成交额</p>
                                  <p className="mt-1 text-sm text-foreground">{formatAmount(item.amount)}</p>
                                </div>
                                <div>
                                  <p className="text-xs font-semibold text-secondary-text">LLM 关注项</p>
                                  <p className="mt-1 text-sm text-foreground">
                                    {item.llmWatchItems?.length ? item.llmWatchItems.join('，') : llmDegraded ? '未返回（LLM 已降级）' : '无'}
                                  </p>
                                </div>
                                <div>
                                  <p className="text-xs font-semibold text-secondary-text">催化因素</p>
                                  <p className="mt-1 text-sm text-foreground">
                                    {item.llmCatalysts?.length ? item.llmCatalysts.join('，') : llmDegraded ? '未返回（LLM 已降级）' : '无'}
                                  </p>
                                </div>
                                <div>
                                  <p className="text-xs font-semibold text-secondary-text">HRS 新闻</p>
                                  {hrsNews.length > 0 ? (
                                    <ul className="mt-1 space-y-1 text-sm text-foreground">
                                      {hrsNews.slice(0, 3).map((newsItem, newsIndex) => (
                                        <li key={`${item.code}-hrs-news-${newsIndex}`}>
                                          {newsItem.title || newsItem.snippet || '-'}
                                        </li>
                                      ))}
                                    </ul>
                                  ) : (
                                    <p className="mt-1 text-sm text-secondary-text">无</p>
                                  )}
                                </div>
                                {hrsWarnings.length > 0 ? (
                                  <div>
                                    <p className="text-xs font-semibold text-secondary-text">HRS 增强提示</p>
                                    <p className="mt-1 text-sm text-secondary-text">{hrsWarnings.join('，')}</p>
                                  </div>
                                ) : null}
                              </div>
                            </div>
                          </td>
                        </tr>
                      ) : null}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </AppPage>
  );
};

export default StockScreeningPage;
