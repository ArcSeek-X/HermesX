/**
 * @file ChatPage.tsx
 * @description AI 对话页面（问股），提供智能问答交互功能。
 *              对应路由：/chat，是 Web 端核心交互页面之一。
 *
 * 主要功能：
 * - 多技能策略选择：用户可同时选择最多 3 个分析技能（如缠论、波浪理论等）
 * - 流式响应：通过 SSE 实时展示 AI 分析进度和结果
 * - 思考过程展示：可折叠查看 AI 的工具调用、推理步骤和耗时
 * - 历史会话管理：侧边栏展示历史对话列表，支持切换、删除、新建
 * - 追问上下文：从报告页跳转时自动携带股票上下文，支持连续追问
 * - 活跃股票上下文：根据用户消息自动解析当前分析的股票，支持自选股操作
 * - 上下文压缩开关：长会话场景下可启用 token 压缩以节省成本
 * - 消息导出：支持导出整段会话或单条消息为 Markdown 文件
 * - 通知渠道发送：可将会话内容发送到已配置的通知机器人/邮箱
 *
 * 核心依赖：
 * - useAgentChatStore：全局对话状态管理（消息列表、流式连接、会话切换等）
 * - agentApi：Agent 后端接口（技能列表、状态查询、会话删除、通知发送）
 * - systemConfigApi：系统配置接口（自选股管理、上下文压缩配置）
 * - useStockIndex：股票索引 Hook（用于从消息中匹配股票名称）
 * - useUiLanguage：UI 语言上下文（国际化文本）
 *
 * @module pages
 */
import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChevronDown, SlidersHorizontal } from 'lucide-react';
import { cn } from '../utils/cn';
import { agentApi } from '../api/agent';
import { systemConfigApi } from '../api/systemConfig';
import { ApiErrorAlert, Badge, Button, ConfirmDialog, EmptyState, InlineAlert, ScrollArea, Tooltip } from '../components/common';
import { createParsedApiError, getParsedApiError } from '../api/error';
import type { AgentStatusResponse, SkillInfo } from '../api/agent';
import { DashboardStateBlock } from '../components/dashboard';
import {
  useAgentChatStore,
  type Message,
  type ProgressStep,
} from '../stores/agentChatStore';
import { downloadSession, formatSessionAsMarkdown } from '../utils/chatExport';
import type { ChatFollowUpContext } from '../utils/chatFollowUp';
import {
  buildFollowUpPrompt,
  parseFollowUpRecordId,
  resolveChatFollowUpContext,
  sanitizeFollowUpStockCode,
  sanitizeFollowUpStockName,
} from '../utils/chatFollowUp';
import { isNearBottom } from '../utils/chatScroll';
import { getReportText } from '../utils/reportLanguage';
import { extractStockCodesFromMessage } from '../utils/chatStockCode';
import { findMatchingStockCode, includesStockCode, normalizeStockCode } from '../utils/stockCode';
import { useStockIndex } from '../hooks/useStockIndex';
import type { StockIndexItem } from '../types/stockIndex';
import { useUiLanguage } from '../contexts/UiLanguageContext';

// 当前活跃股票上下文类型，从追问上下文中提取股票代码和名称
type ActiveStockContext = Pick<ChatFollowUpContext, 'stock_code' | 'stock_name'>;

// 快捷问题列表：每个问题绑定一个分析技能和对应的股票上下文
const QUICK_QUESTIONS: Array<{
  label: string;
  skill: string;
  stockContext?: ActiveStockContext;
}> = [
  { label: '用缠论分析茅台', skill: 'chan_theory', stockContext: { stock_code: '600519', stock_name: '贵州茅台' } },
  { label: '波浪理论看宁德时代', skill: 'wave_theory', stockContext: { stock_code: '300750', stock_name: '宁德时代' } },
  { label: '分析比亚迪趋势', skill: 'bull_trend', stockContext: { stock_code: '002594', stock_name: '比亚迪' } },
  { label: '用箱体震荡分析 A 股中芯国际 688981', skill: 'box_oscillation', stockContext: { stock_code: '688981', stock_name: '中芯国际' } },
  { label: '分析腾讯 hk00700', skill: 'bull_trend', stockContext: { stock_code: 'HK00700', stock_name: '腾讯控股' } },
  { label: '用情绪周期分析东方财富', skill: 'emotion_cycle', stockContext: { stock_code: '300059', stock_name: '东方财富' } },
];

const MAX_SELECTED_SKILLS = 3; // 最多可选的分析技能数量
const CONTEXT_COMPRESSION_CONFIG_KEY = 'AGENT_CONTEXT_COMPRESSION_ENABLED'; // 上下文压缩配置项的 key
// 强比较信号：消息中包含明确的比较意图（如"比较""对比""vs"）
const STRONG_COMPARE_STOCK_MESSAGE_RE = /比较|对比|\bvs\b|和[^，。,.!?！？]{0,40}比/i;
// 弱比较信号：消息中出现差异、区别等词，需结合其他条件判断
const WEAK_COMPARE_STOCK_MESSAGE_RE = /差异(?!化)|区别|不同|相比|对照|比一比/;
// 选择类比较：消息中出现"哪个""二选一"等选择意图
const CHOICE_COMPARE_STOCK_MESSAGE_RE = /哪个|哪只|哪一个|谁更|更值得|更适合|怎么选|选哪|二选一/;
// 关联比较：消息中通过连词关联两只股票并提及差异/区别等
const LINKED_COMPARE_STOCK_MESSAGE_RE = /(?:和|与|跟|同)[^，。,.!?！？]{0,40}(?:差异(?!化)|区别|不同|相比|对照|比一比)/;
// 切换股票信号：消息中包含切换分析对象的意图（如"换成""改看"）
const SWITCH_STOCK_MESSAGE_RE = /换成|改看|分析|看看|研究|诊断/;

// 当前活跃股票解析结果：context 为股票上下文，useForCurrentSend 标记是否随本次请求发送
type ActiveStockResolution = {
  context: ActiveStockContext;
  useForCurrentSend: boolean;
};

/**
 * 根据用户消息中的股票名称，从股票索引中唯一匹配出对应的股票上下文。
 * 仅当消息中恰好匹配到一只股票时返回结果，避免歧义。
 * @param message - 用户输入的消息文本
 * @param index - 股票索引列表
 * @returns 唯一匹配的股票上下文，或 null
 */
const resolveUniqueStockNameContext = (
  message: string,
  index: StockIndexItem[],
): ActiveStockContext | null => {
  const normalizedMessage = message.trim().toLocaleLowerCase();
  if (!normalizedMessage) return null;

  // 遍历索引，通过中文名、英文名、别名收集所有匹配的股票
  const matches = new Map<string, ActiveStockContext>();
  for (const item of index) {
    if (!item.active) continue;
    // 中文名至少 2 个字，英文名至少 3 个字符，避免短词误匹配
    const terms = [item.nameZh, item.nameEn, ...(item.aliases || [])]
      .map((term) => term?.trim())
      .filter((term): term is string => Boolean(term))
      .filter((term) => /[\u3400-\u9fff]/.test(term) ? term.length >= 2 : term.length >= 3);
    if (!terms.some((term) => normalizedMessage.includes(term.toLocaleLowerCase()))) {
      continue;
    }
    const stockCode = normalizeStockCode(item.canonicalCode);
    matches.set(stockCode, { stock_code: stockCode, stock_name: item.nameZh || null });
  }

  // 仅当唯一匹配时返回，多匹配视为歧义
  return matches.size === 1 ? [...matches.values()][0] : null;
};

/**
 * 从消息对象中提取技能名称列表，兼容多种字段格式。
 * @param msg - 消息对象
 * @returns 技能名称数组
 */
const getMessageSkillNames = (msg: Message): string[] => {
  if (msg.skillNames?.length) return msg.skillNames;
  if (msg.skillName) return [msg.skillName];
  if (msg.skills?.length) return msg.skills;
  if (msg.skill) return [msg.skill];
  return [];
};

/** 将消息中的技能名称列表拼接为展示用标签字符串 */
const getMessageSkillLabel = (msg: Message): string => getMessageSkillNames(msg).join('、');

/**
 * 判断流水线阶段是否成功完成。
 * @param status - 阶段状态字符串
 * @returns 是否成功
 */
const isStageDoneSuccessful = (status?: string): boolean => {
  if (!status) return true;
  const normalized = status.trim().toLowerCase();
  return ['completed', 'success', 'succeeded', 'done'].includes(normalized);
};

/**
 * 获取阶段完成时的展示标签文本。
 * @param step - 进度步骤对象
 * @returns 展示用标签
 */
const getStageDoneLabel = (step: ProgressStep): string => {
  const stage = step.stage || 'stage';
  if (step.message) return step.message;
  if (isStageDoneSuccessful(step.status)) return `${stage} completed`;
  return `${stage} ${step.status || 'finished'}`;
};

/**
 * 获取因预算不足跳过流水线时的展示标签。
 * @param step - 进度步骤对象
 * @returns 展示用标签
 */
const getPipelineBudgetSkippedLabel = (step: ProgressStep): string => {
  if (step.message) return step.message;
  return `${step.stage || 'pipeline'} skipped: insufficient budget`;
};

/**
 * 判断用户消息是否为股票比较类消息。
 * 通过强信号、选择类信号、弱信号等综合判断是否涉及多只股票比较。
 * @param message - 用户消息文本
 * @param stockCodes - 从消息中提取的股票代码列表
 * @param currentStockCode - 当前活跃的股票代码
 * @returns 是否为比较类消息
 */
const isCompareStockMessage = (
  message: string,
  stockCodes: string[],
  currentStockCode?: string | null,
): boolean => {
  // 强比较信号直接判定为比较消息
  if (STRONG_COMPARE_STOCK_MESSAGE_RE.test(message)) {
    return true;
  }
  const current = currentStockCode ? normalizeStockCode(currentStockCode) : null;
  // 过滤掉当前已选股票，只看新增的股票代码
  const newStockCodes = current
    ? stockCodes.filter((code) => code !== current)
    : stockCodes;
  // 新增股票 >= 2 只，视为比较
  if (newStockCodes.length >= 2) {
    return true;
  }
  // 选择类信号 + 总股票 >= 2 只，视为比较
  if (CHOICE_COMPARE_STOCK_MESSAGE_RE.test(message) && stockCodes.length >= 2) {
    return true;
  }
  // 无弱比较信号则不是比较
  if (!WEAK_COMPARE_STOCK_MESSAGE_RE.test(message)) {
    return false;
  }
  // 弱信号 + 总股票 >= 2 只，视为比较
  if (stockCodes.length >= 2) {
    return true;
  }
  // 无当前股票上下文则不判定
  if (!currentStockCode) {
    return false;
  }
  // 有新股票且消息中通过连词关联比较意图
  const hasNewStock = stockCodes.some((code) => code !== current);
  return hasNewStock && LINKED_COMPARE_STOCK_MESSAGE_RE.test(message);
};

/**
 * 从用户消息中解析出新的活跃股票上下文。
 * 根据消息中提取的股票代码、是否为比较消息、是否为切换操作等，
 * 决定是否更新活跃股票上下文以及是否随当前请求发送。
 * @param message - 用户消息文本
 * @param currentContext - 当前的活跃股票上下文
 * @returns 解析结果，包含新上下文和是否随本次发送的标记
 */
const resolveActiveStockContextFromMessage = (
  message: string,
  currentContext: ActiveStockContext | null,
): ActiveStockResolution | null => {
  const stockCodes = extractStockCodesFromMessage(message);
  const stockCode = stockCodes[0] ?? null;
  if (!stockCode) {
    return null;
  }

  const isCompare = isCompareStockMessage(message, stockCodes, currentContext?.stock_code);
  const isSwitch = SWITCH_STOCK_MESSAGE_RE.test(message);
  const currentStockCode = currentContext?.stock_code
    ? normalizeStockCode(currentContext.stock_code)
    : null;
  const newStockCodes = currentStockCode
    ? stockCodes.filter((code) => code !== currentStockCode)
    : stockCodes;
  // Explicit switches can mention the old stock; use the single new code when present.
  // 显式切换时可能提及旧股票，取唯一新增代码作为目标
  const targetStockCode = isSwitch && newStockCodes.length === 1
    ? newStockCodes[0]
    : stockCode;
  const isDifferentStock = currentStockCode !== targetStockCode;

  // Compare messages and implicit follow-ups must not rewrite the active stock context.
  // 比较消息和隐式追问不得覆盖活跃股票上下文
  if (isCompare || (currentContext && !isSwitch)) {
    return null;
  }

  return {
    context: {
      stock_code: targetStockCode,
      stock_name: currentContext && !isDifferentStock
        ? currentContext.stock_name
        : null,
    },
    // Only explicit switches should affect the context sent with the current request.
    // 仅显式切换操作才影响随当前请求发送的上下文
    useForCurrentSend: isSwitch && isDifferentStock,
  };
};

/**
 * 从历史消息列表中恢复活跃股票上下文。
 * 遍历所有用户消息，逐步解析并更新上下文，最终返回恢复后的上下文。
 * @param messages - 历史消息列表
 * @returns 恢复后的活跃股票上下文，或 null
 */
const restoreActiveStockContextFromMessages = (messages: Message[]): ActiveStockContext | null => {
  let restoredContext: ActiveStockContext | null = null;
  for (const message of messages) {
    if (message.role !== 'user') {
      continue;
    }
    const resolution = resolveActiveStockContextFromMessage(message.content, restoredContext);
    if (resolution) {
      restoredContext = resolution.context;
    }
  }
  return restoredContext;
};

/**
 * AI 对话页面主组件。
 * 提供智能问答交互界面，支持技能策略选择、流式响应、思考过程展示、
 * 历史会话管理、追问上下文、自选股操作等功能。
 */
const ChatPage: React.FC = () => {
  const { t } = useUiLanguage();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [input, setInput] = useState(''); // 用户输入的消息文本
  const [skills, setSkills] = useState<SkillInfo[]>([]); // 可用的分析技能列表
  const [selectedSkillIds, setSelectedSkillIds] = useState<string[]>([]); // 当前选中的技能 ID 列表
  const [showSkillDesc, setShowSkillDesc] = useState<string | null>(null); // 当前展示描述的技能 ID
  const [mobileSkillPickerOpen, setMobileSkillPickerOpen] = useState(false); // 移动端技能选择器是否展开
  const [expandedThinking, setExpandedThinking] = useState<Set<string>>(new Set()); // 展开思考过程的消息 ID 集合
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null); // 待确认删除的会话 ID
  const [sidebarOpen, setSidebarOpen] = useState(false); // 移动端侧边栏是否打开
  const [sending, setSending] = useState(false); // 是否正在发送会话到通知渠道
  const [isFollowUpContextLoading, setIsFollowUpContextLoading] = useState(false); // 追问上下文是否正在加载
  const [sendToast, setSendToast] = useState<{ // 发送到通知渠道的反馈提示
    type: 'success' | 'error';
    message: string;
  } | null>(null);
  const [contextCompressionEnabled, setContextCompressionEnabled] = useState(false); // 上下文压缩是否启用
  const [contextCompressionLoaded, setContextCompressionLoaded] = useState(false); // 上下文压缩配置是否已加载
  const [contextCompressionSaving, setContextCompressionSaving] = useState(false); // 上下文压缩配置是否正在保存
  const [contextCompressionConfigVersion, setContextCompressionConfigVersion] = useState(''); // 上下文压缩配置版本号
  const [contextCompressionMaskToken, setContextCompressionMaskToken] = useState('******'); // 上下文压缩配置掩码 token
  const [contextCompressionError, setContextCompressionError] = useState<string | null>(null); // 上下文压缩配置错误信息
  const [copiedMessages, setCopiedMessages] = useState<Set<string>>(new Set()); // 已复制内容的消息 ID 集合
  const [showJumpToBottom, setShowJumpToBottom] = useState(false); // 是否显示"跳转到底部"按钮
  const [watchlistCodes, setWatchlistCodes] = useState<string[]>([]); // 自选股代码列表
  const [isWatchlistActioning, setIsWatchlistActioning] = useState(false); // 自选股操作是否进行中
  const [watchlistMessage, setWatchlistMessage] = useState<string | null>(null); // 自选股操作反馈消息
  const [activeStockCode, setActiveStockCode] = useState<string | null>(null); // 当前活跃股票代码
  const [activeStockContext, setActiveStockContext] = useState<ActiveStockContext | null>(null); // 当前活跃股票上下文
  const [agentStatus, setAgentStatus] = useState<AgentStatusResponse | null>(null); // Agent 后端状态
  const [agentStatusError, setAgentStatusError] = useState<string | null>(null); // Agent 状态获取错误
  const [agentStatusChecking, setAgentStatusChecking] = useState(true); // Agent 状态是否正在检查中
  const { index: stockIndex } = useStockIndex(
    agentStatus?.backend === 'codex_app_server',
  );
  const watchlistMessageTimerRef = useRef<number | null>(null); // 自选股消息自动消失的定时器
  const copyResetTimerRef = useRef<Partial<Record<string, number>>>({}); // 复制状态重置定时器映射
  const messagesViewportRef = useRef<HTMLDivElement>(null); // 消息列表视口引用
  const messagesEndRef = useRef<HTMLDivElement>(null); // 消息列表底部锚点引用
  const isMountedRef = useRef(true); // 组件是否已挂载（防止卸载后设置状态）
  const sendToastTimerRef = useRef<number | null>(null); // 发送反馈提示自动消失的定时器
  const followUpHydrationTokenRef = useRef(0); // 追问上下文水合令牌（防止竞态）
  const followUpContextRef = useRef<ChatFollowUpContext | null>(null); // 追问上下文引用
  const shouldStickToBottomRef = useRef(true); // 是否应保持滚动到底部
  const pendingScrollBehaviorRef = useRef<ScrollBehavior>('auto'); // 待执行的滚动行为
  const agentStatusRequestIdRef = useRef(0); // Agent 状态请求 ID（防止竞态）

  // Get localized text (default to Chinese)
  // 获取本地化文本（默认中文）
  const text = getReportText('zh');

  // Cleanup timers on unmount
  // 组件卸载时清理所有定时器
  useEffect(() => {
    const timers = copyResetTimerRef.current;
    return () => {
      if (sendToastTimerRef.current !== null) {
        window.clearTimeout(sendToastTimerRef.current);
      }
      Object.values(timers).forEach((timerId) => {
        if (timerId !== undefined) {
          window.clearTimeout(timerId);
        }
      });
    };
  }, []);

  // Set page title
  // 设置页面标题
  useEffect(() => {
    document.title = '问股 - DSA';
  }, []);

  // 标记组件已挂载，卸载时标记为 false
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  /**
   * 加载自选股列表。
   * 从系统配置接口获取当前用户的自选股代码列表。
   */
  const loadWatchlist = useCallback(async () => {
    try {
      const codes = await systemConfigApi.getWatchlist();
      if (isMountedRef.current) {
        setWatchlistCodes(codes);
      }
    } catch {
      // ignore error silently
    }
  }, []);

  // 组件挂载时加载自选股列表
  useEffect(() => {
    void loadWatchlist();
  }, [loadWatchlist]);

  /** 判断指定股票是否已在自选股列表中 */
  const stockInWatchlist = useCallback(
    (stockCode: string) => includesStockCode(watchlistCodes, stockCode),
    [watchlistCodes],
  );

  /**
   * 切换自选股状态：若已在自选则移除，否则添加。
   * @param stockCode - 股票代码
   */
  const handleToggleWatchlist = useCallback(
    async (stockCode: string) => {
      if (!stockCode || isWatchlistActioning) return;
      setIsWatchlistActioning(true);
      setWatchlistMessage(null);
      try {
        const existingStockCode = findMatchingStockCode(watchlistCodes, stockCode);
        if (existingStockCode) {
          const codes = await systemConfigApi.removeFromWatchlist(existingStockCode);
          if (isMountedRef.current) {
            setWatchlistCodes(codes);
            setWatchlistMessage(`已从自选中移除 ${stockCode}`);
          }
        } else {
          const codes = await systemConfigApi.addToWatchlist(stockCode);
          if (isMountedRef.current) {
            setWatchlistCodes(codes);
            setWatchlistMessage(`已加入自选 ${stockCode}`);
          }
        }
      } catch {
        if (isMountedRef.current) {
          setWatchlistMessage('操作失败，请重试');
        }
      } finally {
        if (isMountedRef.current) {
          setIsWatchlistActioning(false);
          if (watchlistMessageTimerRef.current !== null) {
            window.clearTimeout(watchlistMessageTimerRef.current);
          }
          watchlistMessageTimerRef.current = window.setTimeout(() => {
            if (isMountedRef.current) {
              setWatchlistMessage(null);
            }
          }, 3000);
        }
      }
    },
    [isWatchlistActioning, watchlistCodes],
  );

  // 从 agentChatStore 中解构出对话状态和操作方法
  const {
    messages,
    loading,
    progressSteps,
    sessionId,
    sessions,
    sessionsLoading,
    chatError,
    stopping,
    terminalStatus,
    stopError,
    loadSessions,
    loadInitialSession,
    switchSession,
    stopStream,
    startStream,
    clearCompletionBadge,
  } = useAgentChatStore();

  // 从历史消息中恢复活跃股票上下文（当无上下文且有消息时触发）
  useEffect(() => {
    if (activeStockContext || messages.length === 0) {
      return;
    }
    const restoredContext = restoreActiveStockContextFromMessages(messages);
    if (!restoredContext) {
      return;
    }
    setActiveStockContext(restoredContext);
    setActiveStockCode(restoredContext.stock_code);
  }, [activeStockContext, messages, sessionId]);

  /** 同步滚动状态：检测当前视口是否接近底部，更新 shouldStickToBottomRef 和"跳转到底部"按钮的显隐 */
  const syncScrollState = useCallback(() => {
    const viewport = messagesViewportRef.current;
    if (!viewport) return;
    const nearBottom = isNearBottom({
      scrollTop: viewport.scrollTop,
      clientHeight: viewport.clientHeight,
      scrollHeight: viewport.scrollHeight,
    });
    shouldStickToBottomRef.current = nearBottom;
    setShowJumpToBottom((prev) => (nearBottom ? false : prev));
  }, []);

  /** 将消息列表滚动到底部，behavior 控制滚动动画 */
  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'auto') => {
    messagesEndRef.current?.scrollIntoView({ behavior });
  }, []);

  /** 请求滚动到底部：设置标记并清除"跳转到底部"按钮，实际滚动由 useEffect 执行 */
  const requestScrollToBottom = useCallback((behavior: ScrollBehavior = 'auto') => {
    shouldStickToBottomRef.current = true;
    pendingScrollBehaviorRef.current = behavior;
    setShowJumpToBottom(false);
  }, []);

  /** 消息列表滚动事件处理：同步滚动状态 */
  const handleMessagesScroll = useCallback(() => {
    syncScrollState();
  }, [syncScrollState]);

  // 切换会话时重新检测滚动状态
  useEffect(() => {
    syncScrollState();
  }, [syncScrollState, sessionId]);

  // 消息或进度更新时自动滚动到底部（仅当用户已处于底部附近时）
  useEffect(() => {
    const behavior = pendingScrollBehaviorRef.current;
    const shouldAutoScroll = shouldStickToBottomRef.current;
    if (!shouldAutoScroll) {
      // 用户不在底部时，显示"跳转到底部"按钮
      if (messages.length > 0 || progressSteps.length > 0 || loading) {
        setShowJumpToBottom(true);
      }
      return;
    }

    // 使用 requestAnimationFrame 确保在 DOM 更新后执行滚动
    const frame = window.requestAnimationFrame(() => {
      scrollToBottom(behavior);
      // 加载中使用即时滚动，加载完成后切换为平滑滚动
      pendingScrollBehaviorRef.current = loading ? 'auto' : 'smooth';
    });

    return () => window.cancelAnimationFrame(frame);
  }, [messages, progressSteps, loading, sessionId, scrollToBottom]);

  // 加载完成后，后续滚动行为切换为平滑滚动
  useEffect(() => {
    if (!loading) {
      pendingScrollBehaviorRef.current = 'smooth';
    }
  }, [loading]);

  // 组件挂载时清除完成徽章状态
  useEffect(() => {
    clearCompletionBadge();
  }, [clearCompletionBadge]);

  // 组件挂载时加载初始会话（恢复上次会话或创建新会话）
  useEffect(() => {
    loadInitialSession();
  }, [loadInitialSession]);

  // 组件挂载时从后端加载可用的分析技能列表，并设置默认选中技能
  useEffect(() => {
    agentApi.getSkills()
      .then((res) => {
        setSkills(res.skills);
        const defaultId =
          res.default_skill_id ||
          res.skills[0]?.id ||
          '';
        setSelectedSkillIds(defaultId ? [defaultId] : []);
      })
      .catch((error) => {
        console.error('Failed to load chat skills:', error);
      });
  }, []);

  /**
   * 加载 Agent 后端状态。
   * 通过 requestId 防止竞态条件，确保只有最新请求的结果会更新状态。
   */
  const loadAgentStatus = useCallback(async () => {
    const requestId = agentStatusRequestIdRef.current + 1;
    agentStatusRequestIdRef.current = requestId;
    setAgentStatusChecking(true);
    try {
      const status = await agentApi.getStatus();
      if (!isMountedRef.current || agentStatusRequestIdRef.current !== requestId) return;
      setAgentStatus(status);
      setAgentStatusError(null);
    } catch (error: unknown) {
      if (!isMountedRef.current || agentStatusRequestIdRef.current !== requestId) return;
      setAgentStatus(null);
      setAgentStatusError(getParsedApiError(error).message);
    } finally {
      if (isMountedRef.current && agentStatusRequestIdRef.current === requestId) {
        setAgentStatusChecking(false);
      }
    }
  }, []);

  // 组件挂载时加载 Agent 后端状态
  useEffect(() => {
    void loadAgentStatus();
  }, [loadAgentStatus]);

  // 组件挂载时从系统配置加载上下文压缩开关的初始值
  useEffect(() => {
    let active = true;

    void systemConfigApi.getConfig(false)
      .then((config) => {
        if (!active) {
          return;
        }
        const enabledItem = config.items.find((item) => item.key === CONTEXT_COMPRESSION_CONFIG_KEY);
        setContextCompressionEnabled(String(enabledItem?.value ?? '').trim().toLowerCase() === 'true');
        setContextCompressionConfigVersion(config.configVersion);
        setContextCompressionMaskToken(config.maskToken || '******');
        setContextCompressionLoaded(true);
        setContextCompressionError(null);
      })
      .catch((error) => {
        if (!active) {
          return;
        }
        const parsed = getParsedApiError(error);
        setContextCompressionLoaded(false);
        setContextCompressionError(parsed.message || '无法读取上下文压缩配置');
        console.error('Failed to load context compression setting:', error);
      });

    return () => {
      active = false;
    };
  }, []);

  /**
   * 更新上下文压缩开关状态。
   * 乐观更新 UI，失败时回滚到之前的值，同时更新配置版本号。
   * @param nextEnabled - 目标启用状态
   */
  const updateContextCompressionEnabled = useCallback(
    async (nextEnabled: boolean) => {
      if (!contextCompressionLoaded || contextCompressionSaving) {
        return;
      }

      const previousEnabled = contextCompressionEnabled;
      setContextCompressionEnabled(nextEnabled);
      setContextCompressionSaving(true);
      setContextCompressionError(null);

      try {
        const result = await systemConfigApi.update({
          configVersion: contextCompressionConfigVersion,
          maskToken: contextCompressionMaskToken,
          reloadNow: true,
          items: [
            {
              key: CONTEXT_COMPRESSION_CONFIG_KEY,
              value: nextEnabled ? 'true' : 'false',
            },
          ],
        });
        setContextCompressionConfigVersion(result.configVersion || contextCompressionConfigVersion);
      } catch (error) {
        const parsed = getParsedApiError(error);
        setContextCompressionEnabled(previousEnabled);
        setContextCompressionError(parsed.message || '上下文压缩设置保存失败');
      } finally {
        setContextCompressionSaving(false);
      }
    },
    [
      contextCompressionConfigVersion,
      contextCompressionEnabled,
      contextCompressionLoaded,
      contextCompressionMaskToken,
      contextCompressionSaving,
    ],
  );

  // ===== 派生值与 Agent 可用性判断 =====
  const availableSkillIds = new Set(skills.map((skill) => skill.id)); // 后端可用技能 ID 集合
  const quickQuestions = QUICK_QUESTIONS.filter((question) => availableSkillIds.size === 0 || availableSkillIds.has(question.skill)); // 根据后端可用技能过滤快捷问题
  const selectedSkillIdSet = new Set(selectedSkillIds); // 已选技能 ID 集合（用于快速查找）
  const skillLimitReached = selectedSkillIds.length >= MAX_SELECTED_SKILLS; // 是否已达到技能选择上限
  const agentConfirmedUnavailable = Boolean(agentStatus && !agentStatus.available); // Agent 已确认不可用
  const agentAvailable = Boolean(agentStatus?.available) && !agentStatusChecking; // Agent 当前可用
  // 根据错误码选择对应的不可用提示文案
  const agentUnavailableMessage = agentStatus?.errorCode === 'agent_mode_disabled'
    ? t('chat.agentModeDisabled')
    : agentStatus?.errorCode === 'platform_unsupported'
      ? t('chat.agentPlatformUnsupported')
      : agentStatus?.backend === 'codex_app_server'
        ? t('chat.codexUnavailableMessage')
        : t('chat.defaultUnavailableMessage');
  // 构造 Agent 不可用时的结构化错误对象，供 ApiErrorAlert 展示
  const agentUnavailableError = agentConfirmedUnavailable
    ? createParsedApiError({
        title: t('chat.agentBackendUnavailableTitle'),
        message: agentUnavailableMessage,
        rawMessage: `${agentStatus?.errorCode || 'capability_unsupported'}: ${agentStatus?.message || ''}`,
        category: 'upstream_network',
      })
    : null;

  /** 根据技能 ID 列表获取对应的技能名称列表 */
  const getSkillNames = useCallback(
    (skillIds: string[]) => skillIds.map((id) => skills.find((s) => s.id === id)?.name || id),
    [skills],
  );

  /** 规范化技能 ID 列表：去空、去重、截断到最大数量 */
  const normalizeSelectedSkillIds = useCallback((skillIds: string[]) => {
    const normalized: string[] = [];
    for (const skillId of skillIds) {
      const cleaned = skillId.trim();
      if (cleaned && !normalized.includes(cleaned)) {
        normalized.push(cleaned);
      }
    }
    return normalized.slice(0, MAX_SELECTED_SKILLS);
  }, []);

  /** 切换技能选中状态：已选则取消，未选且未达上限则添加 */
  const toggleSkillSelection = useCallback((skillId: string) => {
    setSelectedSkillIds((prev) => {
      if (prev.includes(skillId)) {
        return prev.filter((id) => id !== skillId);
      }
      if (prev.length >= MAX_SELECTED_SKILLS) {
        return prev;
      }
      return [...prev, skillId];
    });
  }, []);

  /** 开启新对话：清空追问上下文、活跃股票上下文，并重置滚动状态 */
  const handleStartNewChat = useCallback(() => {
    followUpContextRef.current = null;
    setActiveStockContext(null);
    setActiveStockCode(null);
    requestScrollToBottom('auto');
    useAgentChatStore.getState().startNewChat();
    setSidebarOpen(false);
  }, [requestScrollToBottom]);

  /** 切换到指定会话：清空追问上下文和活跃股票上下文，重置滚动状态后切换会话 */
  const handleSwitchSession = useCallback((targetSessionId: string) => {
    if (targetSessionId === sessionId) {
      setSidebarOpen(false);
      return;
    }
    followUpContextRef.current = null;
    setActiveStockContext(null);
    setActiveStockCode(null);
    requestScrollToBottom('auto');
    switchSession(targetSessionId);
    setSidebarOpen(false);
  }, [requestScrollToBottom, sessionId, switchSession]);

  /** 确认删除会话：调用后端删除接口，刷新会话列表，若删除的是当前会话则开启新对话 */
  const confirmDelete = useCallback(() => {
    if (!deleteConfirmId) return;
    agentApi.deleteChatSession(deleteConfirmId)
      .then(() => {
        loadSessions();
        if (deleteConfirmId === sessionId) {
          handleStartNewChat();
        }
      })
      .catch((error) => {
        console.error('Failed to delete chat session:', error);
      });
    setDeleteConfirmId(null);
  }, [deleteConfirmId, sessionId, loadSessions, handleStartNewChat]);

  // Handle follow-up from report page: ?stock=600519&name=贵州茅台&recordId=xxx
  useEffect(() => {
    const stock = sanitizeFollowUpStockCode(searchParams.get('stock'));
    const name = sanitizeFollowUpStockName(searchParams.get('name'));
    const recordId = parseFollowUpRecordId(searchParams.get('recordId'));

    if (!stock) {
      setSearchParams({}, { replace: true });
      return;
    }

    const hydrationToken = ++followUpHydrationTokenRef.current;
    setInput(buildFollowUpPrompt(stock, name));
    setActiveStockCode(stock);
    setActiveStockContext({
      stock_code: stock,
      stock_name: name,
    });
    followUpContextRef.current = {
      stock_code: stock,
      stock_name: name,
    };
    if (recordId !== undefined) {
      setIsFollowUpContextLoading(true);
    }
    void resolveChatFollowUpContext({
      stockCode: stock,
      stockName: name,
      recordId,
    }).then((context) => {
      if (!isMountedRef.current || followUpHydrationTokenRef.current !== hydrationToken) {
        return;
      }
      followUpContextRef.current = context;
    }).finally(() => {
      if (isMountedRef.current && followUpHydrationTokenRef.current === hydrationToken) {
        setIsFollowUpContextLoading(false);
      }
    });
    setSearchParams({}, { replace: true });
  }, [searchParams, setSearchParams]);

  /**
   * 发送消息的核心处理函数。
   * 根据用户消息解析活跃股票上下文，确定要发送的技能和上下文，
   * 然后通过 startStream 发起流式请求。
   * @param overrideMessage - 覆盖输入框内容的消息文本（快捷问题场景）
   * @param overrideSkillIds - 覆盖当前选中的技能 ID 列表
   * @param overrideStockContext - 覆盖当前活跃的股票上下文
   */
  const handleSend = useCallback(
    async (
      overrideMessage?: string,
      overrideSkillIds?: string[],
      overrideStockContext?: ActiveStockContext,
    ) => {
      const msgText = (overrideMessage ?? input).trim();
      if (!msgText || loading || !agentAvailable || !agentStatus) return;
      if (overrideMessage !== undefined) {
        setInput(msgText);
      }
      const usedSkillIds = normalizeSelectedSkillIds(overrideSkillIds ?? selectedSkillIds);
      const usedSkillNames = usedSkillIds.length > 0 ? getSkillNames(usedSkillIds) : ['通用'];
      const codexStockContext = agentStatus?.backend === 'codex_app_server'
        ? overrideStockContext
        : undefined;

      let nextActiveStockContext = codexStockContext ?? activeStockContext;
      let useActiveContextForThisSend = Boolean(codexStockContext);
      const stockResolution = codexStockContext
        ? null
        : resolveActiveStockContextFromMessage(msgText, activeStockContext);
      if (stockResolution) {
        nextActiveStockContext = stockResolution.context;
        useActiveContextForThisSend = stockResolution.useForCurrentSend;
      } else if (
        agentStatus?.backend === 'codex_app_server'
        && !codexStockContext
        && (!nextActiveStockContext || SWITCH_STOCK_MESSAGE_RE.test(msgText))
      ) {
        const nameContext = resolveUniqueStockNameContext(msgText, stockIndex);
        if (nameContext) {
          nextActiveStockContext = nameContext;
          useActiveContextForThisSend = true;
        }
      }
      const contextForSend = useActiveContextForThisSend
        ? nextActiveStockContext
        : followUpContextRef.current ?? nextActiveStockContext ?? undefined;

      const payload = {
        message: msgText,
        session_id: sessionId,
        ...(usedSkillIds.length > 0 ? { skills: usedSkillIds } : {}),
        context: contextForSend ?? undefined,
      };
      await startStream(payload, {
        skillNames: usedSkillNames,
        skillName: usedSkillNames.join('、'),
        onAccepted: () => {
          followUpHydrationTokenRef.current += 1;
          followUpContextRef.current = null;
          setIsFollowUpContextLoading(false);
          if (nextActiveStockContext) {
            setActiveStockContext(nextActiveStockContext);
            setActiveStockCode(nextActiveStockContext.stock_code);
          }
          setInput('');
          setMobileSkillPickerOpen(false);
          requestScrollToBottom('smooth');
        },
      });
    },
    [activeStockContext, agentAvailable, agentStatus, getSkillNames, input, loading, normalizeSelectedSkillIds, requestScrollToBottom, selectedSkillIds, sessionId, startStream, stockIndex],
  );

  /** 键盘事件处理：Enter 发送消息，Shift+Enter 换行 */
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  /** 快捷问题点击处理：设置对应技能并发送预设问题 */
  const handleQuickQuestion = (q: (typeof QUICK_QUESTIONS)[0]) => {
    setSelectedSkillIds([q.skill]);
    handleSend(q.label, [q.skill], q.stockContext);
  };

  /** 显示发送反馈提示（成功/失败），在指定时间后自动消失 */
  const showSendFeedback = useCallback((nextToast: { type: 'success' | 'error'; message: string }, durationMs: number) => {
    if (sendToastTimerRef.current !== null) {
      window.clearTimeout(sendToastTimerRef.current);
    }
    setSendToast(nextToast);
    sendToastTimerRef.current = window.setTimeout(() => {
      setSendToast(null);
      sendToastTimerRef.current = null;
    }, durationMs);
  }, []);

  /** 切换指定消息的思考过程展开/折叠状态 */
  const toggleThinking = (msgId: string) => {
    setExpandedThinking((prev) => {
      const next = new Set(prev);
      if (next.has(msgId)) next.delete(msgId);
      else next.add(msgId);
      return next;
    });
  };

  /**
   * 复制消息内容到剪贴板。
   * 复制成功后标记该消息为"已复制"状态，2 秒后自动恢复。
   * @param msgId - 消息 ID
   * @param content - 要复制的文本内容
   */
  const copyMessageToClipboard = async (msgId: string, content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedMessages((prev) => new Set(prev).add(msgId));
      const existingTimer = copyResetTimerRef.current[msgId];
      if (existingTimer !== undefined) {
        window.clearTimeout(existingTimer);
      }
      copyResetTimerRef.current[msgId] = window.setTimeout(() => {
        setCopiedMessages((prev) => {
          const next = new Set(prev);
          next.delete(msgId);
          return next;
        });
        delete copyResetTimerRef.current[msgId];
      }, 2000);
    } catch (err) {
      console.error('Copy failed:', err);
    }
  };

  /** 将单条消息导出为 Markdown 文件并触发下载 */
  const downloadMessageAsMarkdown = useCallback((msg: Message) => {
    const skillLabel = getMessageSkillLabel(msg);
    const heading = msg.role === 'user' ? '# 用户消息' : `# AI 回复${skillLabel ? ` · ${skillLabel}` : ''}`;
    const content = [heading, '', msg.content].join('\n');
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${msg.role === 'user' ? 'user' : 'assistant'}-message-${msg.id}.md`;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  }, []);

  /** 根据进度步骤列表获取当前阶段的展示文本（如"正在思考""工具调用完成"等） */
  const getCurrentStage = (steps: ProgressStep[]): string => {
    if (steps.length === 0) return '正在连接...';
    const last = steps[steps.length - 1];
    if (last.type === 'thinking') return last.message || 'AI 正在思考...';
    if (last.type === 'tool_start')
      return `${last.display_name || last.tool}...`;
    if (last.type === 'tool_done')
      return `${last.display_name || last.tool} 完成`;
    if (last.type === 'stage_start')
      return last.message || `Starting ${last.stage || 'stage'}...`;
    if (last.type === 'stage_done')
      return getStageDoneLabel(last);
    if (last.type === 'pipeline_timeout')
      return last.message || `${last.stage || 'pipeline'} timed out`;
    if (last.type === 'pipeline_budget_skipped')
      return getPipelineBudgetSkippedLabel(last);
    if (last.type === 'generating')
      return last.message || '正在生成最终分析...';
    return '处理中...';
  };

  /** 渲染思考过程折叠头部：展示工具调用次数和总耗时，点击可展开/折叠详情 */
  const renderThinkingBlock = (msg: Message) => {
    if (!msg.thinkingSteps || msg.thinkingSteps.length === 0) return null;
    const isExpanded = expandedThinking.has(msg.id);
    const toolSteps = msg.thinkingSteps.filter((s) => s.type === 'tool_done');
    const totalDuration = toolSteps.reduce(
      (sum, s) => sum + (s.duration || 0),
      0,
    );
    const summary = `${toolSteps.length} 个工具调用 · ${totalDuration.toFixed(1)}s`;

    return (
      <button
        onClick={() => toggleThinking(msg.id)}
        className="flex items-center gap-2 text-xs text-muted-text hover:text-secondary-text transition-colors mb-2 w-full text-left"
      >
        <svg
          className={`w-3 h-3 transition-transform flex-shrink-0 ${isExpanded ? 'rotate-90' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 5l7 7-7 7"
          />
        </svg>
        <span className="flex items-center gap-1.5">
          <span className="opacity-60">思考过程</span>
          <span className="text-muted-text/50">·</span>
          <span className="opacity-50">{summary}</span>
        </span>
      </button>
    );
  };

  /**
   * 渲染思考过程详情列表。
   * 将 AI 的思考步骤（thinking、tool_start、tool_done、stage_start/done、generating 等）
   * 逐条渲染为带状态色点和图标的垂直列表，每条展示对应的阶段名称和耗时。
   * @param steps - 进度步骤数组
   * @returns JSX 元素
   */
  const renderThinkingDetails = (steps: ProgressStep[]) => (
    <div className="mb-3 pl-5 border-l border-border/40 space-y-1.5 animate-fade-in">
      {steps.map((step, idx) => {
        let statusClass = 'chat-progress-item-muted';
        let iconClass = 'chat-progress-dot-muted';
        let text = '';
        if (step.type === 'thinking') {
          text = step.message || `第 ${step.step} 步：思考`;
          statusClass = 'chat-progress-item-thinking';
          iconClass = 'chat-progress-dot-thinking';
        } else if (step.type === 'tool_start') {
          text = `${step.display_name || step.tool}...`;
          statusClass = 'chat-progress-item-tool';
          iconClass = 'chat-progress-dot-tool';
        } else if (step.type === 'tool_done') {
          text = `${step.display_name || step.tool} (${step.duration}s)`;
          statusClass = step.success ? 'chat-progress-item-success' : 'chat-progress-item-danger';
          iconClass = step.success ? 'chat-progress-dot-success' : 'chat-progress-dot-danger';
        } else if (step.type === 'stage_start') {
          text = step.message || `Starting ${step.stage || 'stage'}...`;
          statusClass = 'chat-progress-item-thinking';
          iconClass = 'chat-progress-dot-thinking';
        } else if (step.type === 'stage_done') {
          const isSuccess = isStageDoneSuccessful(step.status);
          text = getStageDoneLabel(step);
          statusClass = isSuccess ? 'chat-progress-item-success' : 'chat-progress-item-danger';
          iconClass = isSuccess ? 'chat-progress-dot-success' : 'chat-progress-dot-danger';
        } else if (step.type === 'pipeline_timeout') {
          text = step.message || `${step.stage || 'pipeline'} timed out`;
          statusClass = 'chat-progress-item-danger';
          iconClass = 'chat-progress-dot-danger';
        } else if (step.type === 'pipeline_budget_skipped') {
          text = getPipelineBudgetSkippedLabel(step);
          statusClass = 'chat-progress-item-muted';
          iconClass = 'chat-progress-dot-muted';
        } else if (step.type === 'generating') {
          text = step.message || '生成分析';
          statusClass = 'chat-progress-item-generating';
          iconClass = 'chat-progress-dot-generating';
        } else {
          text = step.message || step.type;
        }
        return (
          <div
            key={idx}
            className={cn('chat-progress-item', statusClass)}
          >
            <span className={cn('chat-progress-dot', iconClass)} />
            <span className="leading-relaxed">{text}</span>
          </div>
        );
      })}
    </div>
  );

  /**
   * 侧边栏内容：历史对话列表。
   * 包含标题栏（带"开启新对话"按钮）和可滚动的会话列表。
   * 每条会话显示标题、消息数量、最后活跃时间，并支持切换和删除操作。
   * 该内容在桌面端固定显示，在移动端以抽屉形式弹出。
   */
  const sidebarContent = (
    <>
      <div className="flex items-center justify-between border-b border-white/5 bg-white/2 p-3.5">
        <h2 className="text-sm font-semibold text-cyan uppercase tracking-[0.2em] flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          历史对话
        </h2>
        <button
          onClick={handleStartNewChat}
          className="rounded-lg p-1.5 text-muted-text transition-all hover:bg-white/10 hover:text-foreground"
          aria-label="开启新对话"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
        </button>
      </div>
      <ScrollArea testId="chat-session-list-scroll" viewportClassName="p-3">
        {sessionsLoading ? (
          <DashboardStateBlock
            loading
            compact
            title="加载对话中..."
            className="rounded-2xl border border-dashed border-border/50 bg-surface/30"
          />
        ) : sessions.length === 0 ? (
          <DashboardStateBlock
            compact
            title="暂无历史对话"
            description="开始提问后，这里会保留会话记录。"
            className="rounded-2xl border border-dashed border-border/50 bg-surface/30"
          />
        ) : (
          <div className="space-y-2">
            {sessions.map((s) => (
              <div key={s.session_id} className="session-item-row">
                <button
                  type="button"
                  onClick={() => handleSwitchSession(s.session_id)}
                  className={`session-item ${s.session_id === sessionId ? 'active' : ''}`}
                  aria-label={`切换到对话 ${s.title}`}
                  aria-current={s.session_id === sessionId ? 'page' : undefined}
                >
                  <div className="indicator" />
                  <div className="content">
                    <span className="title">{s.title}</span>
                    <div className="mt-0.5 flex items-center gap-2">
                      <span className="meta">
                        {s.message_count} 条对话
                      </span>
                      {s.last_active && (
                        <>
                          <span className="separator" />
                          <span className="meta">
                            {new Date(s.last_active).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </button>
                <button
                  type="button"
                  className="delete-btn"
                  onClick={() => {
                    setDeleteConfirmId(s.session_id);
                  }}
                  aria-label={`删除对话 ${s.title}`}
                >
                  <svg
                    className="w-3.5 h-3.5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}
      </ScrollArea>
    </>
  );

  // 当前选中技能的展示摘要文本（多个技能用顿号拼接，未选时显示"通用分析"）
  const selectedSkillSummary = selectedSkillIds.length > 0
    ? getSkillNames(selectedSkillIds).join('、')
    : '通用分析';

  return (
    // ===== 页面根容器：左侧边栏 + 右侧主聊天区域 =====
    <div
      data-testid="chat-workspace"
      className="flex h-[calc(100vh-5rem)] w-full min-w-0 gap-4 overflow-hidden sm:h-[calc(100vh-5.5rem)] lg:h-[calc(100vh-2rem)]"
    >
      {/* ===== 桌面端侧边栏：固定显示历史对话列表 ===== */}
      <div className="hidden h-full w-64 flex-shrink-0 flex-col overflow-hidden rounded-[1.25rem] border border-white/8 bg-card/82 shadow-soft-card md:flex">
        {sidebarContent}
      </div>

      {/* ===== 移动端侧边栏遮罩层：点击遮罩关闭，抽屉内为历史对话列表 ===== */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        >
          <div className="page-drawer-overlay absolute inset-0" />
          <div
            className="absolute left-0 top-0 bottom-0 w-72 flex flex-col glass-card overflow-hidden border-r border-white/10 bg-card/90 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            {sidebarContent}
          </div>
        </div>
      )}

      {/* ===== 删除会话确认弹窗 ===== */}
      <ConfirmDialog
        isOpen={Boolean(deleteConfirmId)}
        title="删除对话"
        message="删除后，该对话将不可恢复，确认删除吗？"
        confirmText="删除"
        cancelText="取消"
        isDanger
        onConfirm={confirmDelete}
        onCancel={() => setDeleteConfirmId(null)}
      />

      {/* ===== 主聊天区域：包含页头、消息列表、输入框 ===== */}
      <div className="flex h-full min-w-0 flex-1 flex-col overflow-hidden">
        {/* --- 页头区域：标题、后端标识、导出/发送按钮、介绍文案 --- */}
        <header className="mb-4 flex-shrink-0 space-y-3">
          <div className="flex items-start justify-between gap-4">
            <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
              <button
                onClick={() => setSidebarOpen(true)}
                className="md:hidden p-1.5 -ml-1 rounded-lg hover:bg-hover transition-colors text-secondary-text hover:text-foreground"
                aria-label="历史对话"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                </svg>
              </button>
              <svg
                className="w-6 h-6 text-cyan"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                />
              </svg>
              问股
              {agentStatus ? (
                <Badge
                  variant={agentStatus.backend === 'codex_app_server' ? 'warning' : 'history'}
                  size="sm"
                >
                  {t(agentStatus.backend === 'codex_app_server' ? 'chat.codexBackendBadge' : 'chat.defaultBackendBadge')}
                </Badge>
              ) : null}
            </h1>
            {messages.length > 0 && (
              <div className="flex flex-shrink-0 flex-wrap items-center justify-end gap-2">
                <Tooltip content="导出会话为 Markdown 文件">
                  <span className="inline-flex">
                    <Button
                      variant="action-primary"
                      size="sm"
                      onClick={() => downloadSession(messages)}
                      aria-label="导出会话为 Markdown 文件"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                        />
                      </svg>
                      导出会话
                    </Button>
                  </span>
                </Tooltip>
                <Tooltip content="发送到已配置的通知机器人/邮箱">
                  <span className="inline-flex">
                    <Button
                      variant="action-primary"
                      size="sm"
                      disabled={sending}
                      onClick={async () => {
                        if (sending) return;
                        setSending(true);
                        setSendToast(null);
                        try {
                          const content = formatSessionAsMarkdown(messages);
                          await agentApi.sendChat(content);
                          showSendFeedback({ type: 'success', message: '已发送到通知渠道' }, 3000);
                        } catch (err) {
                          const parsed = getParsedApiError(err);
                          showSendFeedback({
                            type: 'error',
                            message: parsed.message || '发送失败',
                          }, 5000);
                        } finally {
                          setSending(false);
                        }
                      }}
                      aria-label="发送到已配置的通知机器人/邮箱"
                    >
                      {sending ? (
                        <svg
                          className="w-4 h-4 animate-spin"
                          fill="none"
                          viewBox="0 0 24 24"
                        >
                          <circle
                            className="opacity-25"
                            cx="12"
                            cy="12"
                            r="10"
                            stroke="currentColor"
                            strokeWidth="4"
                          />
                          <path
                            className="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                          />
                        </svg>
                      ) : (
                        <svg
                          className="w-4 h-4"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                          />
                        </svg>
                      )}
                      发送
                    </Button>
                  </span>
                </Tooltip>
              </div>
            )}
          </div>
          <p className="text-secondary-text text-sm">
            {t(agentStatus?.backend === 'codex_app_server' ? 'chat.introCodex' : 'chat.introDefault')}
          </p>
          {agentStatus?.backend === 'codex_app_server' ? (
            <InlineAlert
              variant="warning"
              title={t('chat.codexLimitedTitle')}
              message={t('chat.codexLimitedMessage')}
              action={(
                <Button
                  variant="action-primary"
                  size="sm"
                  onClick={() => navigate('/settings?category=agent')}
                >
                  {t('chat.codexChangeBackend')}
                </Button>
              )}
              className="rounded-xl px-3 py-2 text-xs shadow-none"
            />
          ) : null}
          {sendToast ? (
            <InlineAlert
              variant={sendToast.type === 'success' ? 'success' : 'danger'}
              title={sendToast.type === 'success' ? '发送成功' : '发送失败'}
              message={sendToast.message}
              className="max-w-md rounded-xl px-3 py-2 text-xs shadow-none"
            />
          ) : null}
        </header>

        {/* --- 消息列表区域：空状态 / 消息气泡 / 加载中状态 --- */}
        <div className="relative z-10 flex min-h-0 flex-1 flex-col overflow-hidden border border-white/6 bg-card/78 glass-card">
          {/* Messages */}
          <ScrollArea
            className="relative z-10 flex-1"
            viewportRef={messagesViewportRef}
            onScroll={handleMessagesScroll}
            viewportClassName="space-y-6 p-4 md:p-6"
            testId="chat-message-scroll"
          >
            {messages.length === 0 && !loading ? (
              <div className="flex h-full items-center justify-center">
                <EmptyState
                  title="开始问股"
                  description={t(
                    agentStatus?.backend === 'codex_app_server'
                      ? 'chat.emptyDescriptionCodex'
                      : 'chat.emptyDescriptionDefault',
                  )}
                  className="max-w-2xl border-dashed bg-card/55"
                  icon={(
                    <svg
                      className="h-8 w-8"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={1.5}
                        d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                      />
                    </svg>
                  )}
                  action={(
                    <div className="flex max-w-lg flex-wrap justify-center gap-2">
                      {quickQuestions.map((q, i) => (
                        <button
                          key={i}
                          onClick={() => handleQuickQuestion(q)}
                          disabled={!agentAvailable}
                          className="quick-question-btn disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {q.label}
                        </button>
                      ))}
                    </div>
                  )}
                />
              </div>
            ) : (
              messages.map((msg) => {
                const skillLabel = getMessageSkillLabel(msg);
                return (
                <div
                  key={msg.id}
                  className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                >
                  <div
                    className={cn(
                      'flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[10px] font-bold shadow-sm transition-all',
                      msg.role === 'user' ? 'chat-avatar-user' : 'chat-avatar-ai'
                    )}
                  >
                    {msg.role === 'user' ? 'U' : 'AI'}
                  </div>
                  <div
                    className={cn(
                      'group/message min-w-0 w-fit max-w-[min(100%,48rem)] overflow-hidden px-5 py-3.5 transition-colors',
                      msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-ai'
                    )}
                  >
                    {msg.role === 'assistant' && (skillLabel || msg.backend) && (
                      <div className="mb-2 flex flex-wrap gap-2">
                        {skillLabel ? <Badge variant="info" className="chat-skill-badge shadow-none" aria-label={`技能 ${skillLabel}`}>
                          <svg
                            className="w-3 h-3"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M13 10V3L4 14h7v7l9-11h-7z"
                            />
                          </svg>
                          {skillLabel}
                        </Badge> : null}
                        {msg.backend ? (
                          <Badge variant={msg.backend === 'codex_app_server' ? 'warning' : 'history'} size="sm">
                            {t(msg.backend === 'codex_app_server' ? 'chat.codexBackendBadge' : 'chat.defaultBackendBadge')}
                          </Badge>
                        ) : null}
                      </div>
                    )}
                    {msg.role === 'assistant' && renderThinkingBlock(msg)}
                    {msg.role === 'assistant' &&
                      expandedThinking.has(msg.id) &&
                      msg.thinkingSteps &&
                      renderThinkingDetails(msg.thinkingSteps)}
                    {msg.role === 'assistant' ? (
                      <div className="relative">
                        <div className="chat-message-actions">
                          <button
                            type="button"
                            onClick={() => copyMessageToClipboard(msg.id, msg.content)}
                            className="chat-copy-btn"
                            aria-label={copiedMessages.has(msg.id) ? text.copied : text.copy}
                          >
                            {copiedMessages.has(msg.id) ? text.copied : text.copy}
                          </button>
                          <button
                            type="button"
                            onClick={() => downloadMessageAsMarkdown(msg)}
                            className="chat-copy-btn"
                            aria-label="导出此条消息为 Markdown"
                          >
                            导出
                          </button>
                        </div>
                        <div className="chat-prose pr-20 sm:pr-24">
                          <Markdown remarkPlugins={[remarkGfm]}>
                            {msg.content}
                          </Markdown>
                        </div>
                      </div>
                    ) : (
                      msg.content
                        .split('\n')
                        .map((line, i) => (
                          <p
                            key={i}
                            className="mb-1 last:mb-0 leading-relaxed"
                          >
                            {line || '\u00A0'}
                          </p>
                        ))
                    )}
                  </div>
                </div>
                );
              })
            )}

            {/* --- 加载中状态：显示 AI 头像和当前处理阶段（思考/工具调用/生成中） --- */}
            {loading && (
              <div className="flex gap-4">
                <div className="w-8 h-8 rounded-full bg-elevated text-foreground flex items-center justify-center flex-shrink-0 text-xs font-bold">
                  AI
                </div>
                <div className="min-w-[200px] max-w-[min(100%,48rem)] overflow-hidden rounded-2xl rounded-tl-sm border border-white/6 bg-card/72 px-5 py-4">
                  <div className="flex items-center gap-2.5 text-sm text-secondary-text">
                    <div className="relative w-4 h-4 flex-shrink-0">
                      <div className="absolute inset-0 rounded-full border-2 border-cyan/20" />
                      <div className="absolute inset-0 rounded-full border-2 border-cyan border-t-transparent animate-spin" />
                    </div>
                    <span className="text-secondary-text">
                      {getCurrentStage(progressSteps)}
                    </span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </ScrollArea>

          {/* --- "跳转到底部"浮动按钮：用户不在底部时出现，点击平滑滚动到最新消息 --- */}
          {showJumpToBottom && (
            <div className="pointer-events-none absolute bottom-[5.75rem] right-4 z-20 md:bottom-24 md:right-6">
              <button
                type="button"
                className="pointer-events-auto chat-copy-btn shadow-soft-card"
                onClick={() => {
                  requestScrollToBottom('smooth');
                  scrollToBottom('smooth');
                }}
                aria-label="查看最新消息"
              >
                <svg
                  className="h-3.5 w-3.5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 14l-7 7m0 0l-7-7m7 7V3"
                  />
                </svg>
                有新消息
              </button>
            </div>
          )}

          {/* --- 输入区域：错误提示、状态提示、上下文压缩开关、技能选择器、文本输入框 --- */}
          <div className="border-t border-white/6 bg-card/88 p-4 md:p-6 relative z-20">
            <div className="space-y-3">
              {/* --- 错误与状态提示：聊天错误、取消、超时、停止失败 --- */}
              {chatError ? <ApiErrorAlert error={chatError} /> : null}
              {terminalStatus === 'cancelled' ? (
                <div role="status" className="rounded-xl border border-slate-500/20 bg-slate-500/5 px-4 py-3 text-sm">
                  {t('chat.analysisStopped')}
                </div>
              ) : null}
              {terminalStatus === 'timeout' ? (
                <div role="status" className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-sm">
                  {t('chat.analysisTimedOut')}
                </div>
              ) : null}
              {stopError ? (
                <div role="alert" className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-sm">
                  {t('chat.stopRequestFailed')}
                </div>
              ) : null}
              {/* --- Agent 状态提示：不可用、状态获取失败、检查中、追问上下文加载中 --- */}
              {agentUnavailableError ? (
                <div className="space-y-2">
                  <ApiErrorAlert
                    error={agentUnavailableError}
                    actionLabel={t('chat.openAgentSettings')}
                    onAction={() => navigate('/settings?category=agent')}
                  />
                  <Button variant="secondary" size="sm" onClick={() => void loadAgentStatus()}>
                    {t('chat.recheckAgentStatus')}
                  </Button>
                </div>
              ) : null}
              {agentStatusError ? (
                <InlineAlert
                  variant="warning"
                  title={t('chat.statusUnavailableTitle')}
                  message={t('chat.statusUnavailableMessage')}
                  action={(
                    <Button variant="secondary" size="sm" onClick={() => void loadAgentStatus()}>
                      {t('chat.recheckAgentStatus')}
                    </Button>
                  )}
                  className="rounded-xl px-3 py-2 text-xs shadow-none"
                />
              ) : null}
              {agentStatusChecking ? (
                <InlineAlert
                  variant="info"
                  title={t('chat.statusCheckingTitle')}
                  message={t('chat.statusCheckingMessage')}
                  className="rounded-xl px-3 py-2 text-xs shadow-none"
                />
              ) : null}
              {isFollowUpContextLoading ? (
                <InlineAlert
                  variant="info"
                  title="追问上下文加载中"
                  message="正在加载历史分析上下文；现在可直接发送追问。"
                  className="rounded-xl px-3 py-2 text-xs shadow-none"
                />
              ) : null}
              {/* --- 上下文压缩开关：长会话场景下启用 token 压缩 --- */}
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/6 bg-surface/25 px-3 py-2">
                <label
                  className={cn(
                    'inline-flex items-center gap-2 text-sm',
                    contextCompressionLoaded && !contextCompressionSaving
                      ? 'cursor-pointer text-foreground'
                      : 'cursor-not-allowed text-muted-text',
                  )}
                >
                  <input
                    type="checkbox"
                    checked={contextCompressionEnabled}
                    disabled={!contextCompressionLoaded || contextCompressionSaving}
                    onChange={(event) => void updateContextCompressionEnabled(event.target.checked)}
                    className="chat-skill-checkbox"
                  />
                  <span className="font-medium">上下文压缩</span>
                  <span className="text-xs text-muted-text">节省长会话 token</span>
                </label>
                <span className="text-xs text-muted-text">
                  {contextCompressionSaving
                    ? '保存中...'
                    : contextCompressionEnabled
                      ? '已启用'
                      : '未启用'}
                </span>
              </div>
              {contextCompressionError ? (
                <InlineAlert
                  variant="danger"
                  title="上下文压缩设置未保存"
                  message={contextCompressionError}
                  className="rounded-xl px-3 py-2 text-xs shadow-none"
                />
              ) : null}
              {/* --- 技能策略选择器：桌面端平铺，移动端可折叠 --- */}
              {skills.length > 0 && (
                <div className="space-y-2">
                  <button
                    type="button"
                    className="home-surface-button flex h-10 w-full items-center justify-between gap-3 rounded-xl px-3 text-left text-sm text-foreground md:hidden"
                    aria-label={mobileSkillPickerOpen ? '收起策略选择' : '展开策略选择'}
                    aria-expanded={mobileSkillPickerOpen}
                    aria-controls="chat-skill-picker-panel"
                    onClick={() => setMobileSkillPickerOpen((open) => !open)}
                  >
                    <span className="flex min-w-0 items-center gap-2">
                      <SlidersHorizontal className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
                      <span className="flex-shrink-0 font-medium">策略</span>
                      <span className="truncate text-xs text-muted-text">{selectedSkillSummary}</span>
                    </span>
                    <ChevronDown
                      className={cn(
                        'h-4 w-4 flex-shrink-0 text-muted-text transition-transform',
                        mobileSkillPickerOpen ? 'rotate-180' : '',
                      )}
                      aria-hidden="true"
                    />
                  </button>
                  <div
                    id="chat-skill-picker-panel"
                    data-testid="chat-skill-picker-panel"
                    className={cn(
                      mobileSkillPickerOpen ? 'flex' : 'hidden',
                      'max-h-40 flex-wrap items-start gap-x-5 gap-y-2 overflow-y-auto rounded-xl border border-white/6 bg-surface/25 px-3 py-2 md:flex md:max-h-none md:overflow-visible md:border-0 md:bg-transparent md:p-0',
                    )}
                  >
                    <span className="text-xs text-muted-text font-medium uppercase tracking-wider flex-shrink-0 mt-1">
                      策略
                    </span>
                    <label className="flex items-center gap-1.5 text-sm cursor-pointer group mt-0.5">
                      <input
                        type="checkbox"
                        name="general-analysis"
                        value=""
                        checked={selectedSkillIds.length === 0}
                        onChange={() => setSelectedSkillIds([])}
                        className="chat-skill-checkbox"
                      />
                      <span
                        className={`transition-colors text-sm ${selectedSkillIds.length === 0 ? 'text-foreground font-medium' : 'text-secondary-text group-hover:text-foreground'}`}
                      >
                        通用分析
                      </span>
                    </label>
                    {skills.map((s) => {
                      const checked = selectedSkillIdSet.has(s.id);
                      const disabled = !checked && skillLimitReached;
                      return (
                        <label
                          key={s.id}
                          className={`flex items-center gap-1.5 cursor-pointer group relative mt-0.5 ${disabled ? 'opacity-60 cursor-not-allowed' : ''}`}
                          onMouseEnter={() => setShowSkillDesc(s.id)}
                          onMouseLeave={() => setShowSkillDesc(null)}
                        >
                          <input
                            type="checkbox"
                            name="skills"
                            value={s.id}
                            checked={checked}
                            disabled={disabled}
                            onChange={() => toggleSkillSelection(s.id)}
                            className="chat-skill-checkbox"
                          />
                          <span
                            className={`transition-colors text-sm ${checked ? 'text-foreground font-medium' : 'text-secondary-text group-hover:text-foreground'}`}
                          >
                            {s.name}
                          </span>
                          {showSkillDesc === s.id && s.description && (
                            <div className="skill-desc-tooltip">
                              <p className="skill-title">{s.name}</p>
                              <p>{s.description}</p>
                            </div>
                          )}
                        </label>
                      );
                    })}
                  </div>
                </div>
              )}

            {activeStockCode && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-text font-mono">{activeStockCode}</span>
                <Button
                  variant="secondary"
                  size="xsm"
                  isLoading={isWatchlistActioning}
                  onClick={() => void handleToggleWatchlist(activeStockCode)}
                  className="text-[11px]"
                >
                  {stockInWatchlist(activeStockCode) ? '从自选删除' : '加入自选'}
                </Button>
                {watchlistMessage && (
                  <span className="text-[11px] text-secondary-text animate-in fade-in">{watchlistMessage}</span>
                )}
              </div>
            )}

              <div className="flex items-end gap-3">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="例如：分析 600519 / 茅台现在适合买入吗？ (Enter 发送, Shift+Enter 换行)"
                  disabled={loading || !agentAvailable}
                  rows={1}
                  className="input-surface input-focus-glow flex-1 min-h-[44px] max-h-[200px] rounded-xl border bg-transparent px-4 py-2.5 text-sm transition-all focus:outline-none resize-none disabled:cursor-not-allowed disabled:opacity-60"
                  style={{ height: 'auto' }}
                  onInput={(e) => {
                    const t = e.target as HTMLTextAreaElement;
                    t.style.height = 'auto';
                    t.style.height = `${Math.min(t.scrollHeight, 200)}px`;
                  }}
                />
                {loading && agentStatus?.backend === 'codex_app_server' ? (
                  <Button
                    variant="danger-subtle"
                    onClick={stopStream}
                    disabled={stopping}
                    className="flex-shrink-0"
                  >
                    {stopping ? t('chat.stoppingAnalysis') : t('chat.stopAnalysis')}
                  </Button>
                ) : (
                  <Button
                    variant="primary"
                    onClick={() => handleSend()}
                    disabled={!input.trim() || loading || !agentAvailable}
                    isLoading={loading}
                    className="btn-primary flex-shrink-0"
                  >
                    发送
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
