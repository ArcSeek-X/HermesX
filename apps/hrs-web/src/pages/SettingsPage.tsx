/**
 * @file SettingsPage.tsx
 * @description 系统设置页，提供配置分类导航、LLM 通道编辑、调度器管理、AlphaSift 控制、
 *              配置备份导入/导出、桌面端更新检查、首次运行引导等功能
 * @module pages
 */
import type React from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { CheckCircle2, ChevronDown, CircleAlert, CircleDashed, Clock, Play, Plus, RefreshCw, Trash2 } from 'lucide-react';
import { useAuth, useSystemConfig } from '../hooks';
import { useUiLanguage } from '../contexts/UiLanguageContext';
import { createParsedApiError, getParsedApiError, type ParsedApiError } from '../api/error';
import { analysisApi } from '../api/analysis';
import { alphasiftApi, notifyAlphaSiftConfigChanged, notifySystemConfigChanged } from '../api/alphasift';
import { systemConfigApi } from '../api/systemConfig';
import { InlineTipCard, Button, ConfirmDialog, EmptyState } from '../components';
import {
  AgentBackendStatusPanel,
  AuthSettingsCard,
  ChangePasswordCard,
  GenerationBackendStatusPanel,
  IntelligentImport,
  LLMChannelEditor,
  NotificationTestPanel,
  SettingsCategoryNav,
  SettingsAlert,
  SettingsField,
  SettingsLoading,
  SettingsPanelErrorBoundary,
  SettingsSectionCard,
} from '../components/settings';
import { WEB_BUILD_INFO } from '../utils/constants';
import { parseStockListValue } from '../utils/stockList';
import { getCategoryDescription, getCategoryTitle } from '../utils/systemConfigI18n';
import type {
  ConfigValidationIssue,
  SchedulerStatusResponse,
  SetupStatusCheck,
  SetupStatusResponse,
  SystemConfigCategory,
  SystemConfigItem,
  SystemConfigUpdateItem,
} from '../types/systemConfig';
import type { UiLanguage, UiTextKey } from '../i18n/uiText';

/** 桌面端 Electron 注入的全局 window 对象类型，包含版本信息和更新相关 API */
type DesktopWindow = Window & {
  hrsDesktop?: {
    version?: unknown;
    getUpdateState?: () => Promise<RawDesktopUpdateState>;
    checkForUpdates?: () => Promise<RawDesktopUpdateState>;
    installDownloadedUpdate?: () => Promise<boolean>;
    openReleasePage?: (releaseUrl?: string) => Promise<boolean>;
    onUpdateStateChange?: (listener: (state: RawDesktopUpdateState) => void) => (() => void) | void;
  };
};

/** 桌面端更新状态（归一化后），包含更新状态、版本号、下载进度等信息 */
type DesktopUpdateState = {
  status?: string;
  updateMode?: string;
  currentVersion?: string;
  latestVersion?: string;
  releaseUrl?: string;
  checkedAt?: string;
  publishedAt?: string;
  message?: string;
  releaseName?: string;
  tagName?: string;
  downloadPercent?: number | null;
  downloadedBytes?: number | null;
  totalBytes?: number | null;
};

/** 桌面端原始更新状态（未归一化），字段类型为 unknown，需经过 normalizeDesktopUpdateState 转换 */
type RawDesktopUpdateState = {
  status?: unknown;
  updateMode?: unknown;
  currentVersion?: unknown;
  latestVersion?: unknown;
  releaseUrl?: unknown;
  checkedAt?: unknown;
  publishedAt?: unknown;
  message?: unknown;
  releaseName?: unknown;
  tagName?: unknown;
  downloadPercent?: unknown;
  downloadedBytes?: unknown;
  totalBytes?: unknown;
};

/** 桌面端更新通知信息：包含标题、消息、变体和可选的操作按钮 */
type DesktopUpdateNotice = {
  title: string;
  message: string;
  variant: 'error' | 'success' | 'warning';
  actionLabel?: string;
  actionKind?: 'release' | 'install';
};

/** LLM 通道编辑器涉及的运行时配置键集合，这些键的草稿值由通道编辑器统一管理 */
const LLM_CHANNEL_EDITOR_RUNTIME_KEYS = new Set([
  'LITELLM_MODEL',
  'LITELLM_FALLBACK_MODELS',
  'AGENT_LITELLM_MODEL',
  'VISION_MODEL',
  'LLM_TEMPERATURE',
]);
/** 生成后端状态面板需要展示的配置键集合，包含后端选择、超时、并发及各供应商密钥等 */
const GENERATION_BACKEND_STATUS_KEYS = new Set([
  'GENERATION_BACKEND',
  'GENERATION_FALLBACK_BACKEND',
  'GENERATION_BACKEND_TIMEOUT_SECONDS',
  'GENERATION_BACKEND_MAX_OUTPUT_BYTES',
  'GENERATION_BACKEND_MAX_CONCURRENCY',
  'LOCAL_CLI_BACKEND_MAX_CONCURRENCY',
  'OPENCODE_CLI_MODEL',
  'LITELLM_CONFIG',
  'LITELLM_MODEL',
  'LITELLM_FALLBACK_MODELS',
  'GEMINI_API_KEY',
  'GEMINI_API_KEYS',
  'GEMINI_MODEL',
  'GEMINI_MODEL_FALLBACK',
  'GEMINI_TEMPERATURE',
  'ANTHROPIC_API_KEY',
  'ANTHROPIC_API_KEYS',
  'ANTHROPIC_MODEL',
  'ANTHROPIC_TEMPERATURE',
  'ANTHROPIC_MAX_TOKENS',
  'OPENAI_API_KEY',
  'OPENAI_API_KEYS',
  'OPENAI_BASE_URL',
  'OPENAI_MODEL',
  'OPENAI_VISION_MODEL',
  'OPENAI_TEMPERATURE',
  'OLLAMA_API_BASE',
  'OLLAMA_MODEL',
  'DEEPSEEK_API_KEY',
  'DEEPSEEK_API_KEYS',
  'AIHUBMIX_KEY',
  'ANSPIRE_LLM_ENABLED',
  'ANSPIRE_LLM_BASE_URL',
  'ANSPIRE_LLM_MODEL',
  'ANSPIRE_API_KEYS',
]);
/** 匹配 LLM 通道状态键的正则模式，如 LLM_MYCHANNEL_PROTOCOL、LLM_MYCHANNEL_API_KEY 等 */
const LLM_CHANNEL_STATUS_KEY_PATTERN = /^LLM_[A-Z0-9_]+_(PROTOCOL|BASE_URL|API_KEY|API_KEYS|MODELS|EXTRA_HEADERS|ENABLED)$/;
/** Agent 后端状态面板需要展示的配置键集合，包含后端选择、模式、架构等 */
const AGENT_BACKEND_STATUS_KEYS = new Set([
  'AGENT_BACKEND',
  'AGENT_GENERATION_BACKEND',
  'AGENT_LITELLM_MODEL',
  'AGENT_MODE',
  'AGENT_ARCH',
  'AGENT_ORCHESTRATOR_TIMEOUT_S',
]);

/**
 * 判断给定配置键是否属于 LLM 通道编辑器草稿管理的键
 * 匹配以 LLM_ 开头的键或运行时密钥集合中的键
 * @param key - 配置键名
 * @returns 是否属于通道编辑器草稿键
 */
function isLlmChannelEditorDraftKey(key: string): boolean {
  const normalized = key.trim().toUpperCase();
  return normalized.startsWith('LLM_') || LLM_CHANNEL_EDITOR_RUNTIME_KEYS.has(normalized);
}

/**
 * 判断给定配置键是否属于生成后端状态面板需要展示的键
 * @param key - 配置键名
 * @returns 是否属于生成后端状态草稿键
 */
function isGenerationBackendStatusDraftKey(key: string): boolean {
  const normalized = key.trim().toUpperCase();
  return (
    GENERATION_BACKEND_STATUS_KEYS.has(normalized)
    || normalized === 'LLM_CHANNELS'
    || LLM_CHANNEL_STATUS_KEY_PATTERN.test(normalized)
  );
}

/**
 * 合并外层配置草稿项与 LLM 通道编辑器草稿项
 * 以归一化键为唯一标识，通道编辑器的值优先覆盖外层同键配置
 * @param outerItems - 外层配置草稿项数组
 * @param llmChannelItems - LLM 通道编辑器草稿项数组
 * @returns 合并去重后的草稿项数组
 */
function mergeGenerationBackendDraftItems(
  outerItems: SystemConfigUpdateItem[],
  llmChannelItems: SystemConfigUpdateItem[],
): SystemConfigUpdateItem[] {
  const merged = new Map<string, SystemConfigUpdateItem>();
  for (const item of outerItems) {
    const normalizedKey = item.key.trim().toUpperCase();
    if (isGenerationBackendStatusDraftKey(normalizedKey)) {
      merged.set(normalizedKey, item);
    }
  }
  for (const item of llmChannelItems) {
    const normalizedKey = item.key.trim().toUpperCase();
    if (isLlmChannelEditorDraftKey(normalizedKey) && isGenerationBackendStatusDraftKey(normalizedKey)) {
      merged.set(normalizedKey, item);
    }
  }
  return Array.from(merged.values());
}

/** Prompt 缓存高级设置键集合，这些设置在 UI 中折叠展示 */
const PROMPT_CACHE_ADVANCED_SETTING_KEYS = new Set([
  'LLM_PROMPT_CACHE_TELEMETRY_ENABLED',
  'LLM_PROMPT_CACHE_HINTS_ENABLED',
  'LLM_PROMPT_CACHE_DIAGNOSTICS_LEVEL',
]);

/** 判断配置项是否属于 Prompt 缓存高级设置 */
function isPromptCacheAdvancedSetting(item: { key: string }) {
  return PROMPT_CACHE_ADVANCED_SETTING_KEYS.has(item.key);
}

/** 将桌面端运行时返回的未知类型值修剪为字符串，非字符串返回空字符串 */
function trimDesktopRuntimeString(value: unknown) {
  return typeof value === 'string' ? value.trim() : '';
}

/** 将桌面端运行时返回的未知类型值归一化为数字，空值返回 null，非有限数也返回 null */
function normalizeDesktopRuntimeNumber(value: unknown) {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  const numberValue = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(numberValue) ? numberValue : null;
}

/** 获取桌面端 Electron 注入的运行时 API 对象，非桌面环境返回 undefined */
function getDesktopRuntimeApi() {
  if (typeof window === 'undefined') {
    return undefined;
  }

  return (window as DesktopWindow).hrsDesktop;
}

/** 获取桌面端应用版本号字符串 */
function getDesktopAppVersion() {
  return trimDesktopRuntimeString(getDesktopRuntimeApi()?.version);
}

/**
 * 将桌面端原始更新状态归一化为标准 DesktopUpdateState 对象
 * 对所有字段进行类型安全转换，缺失字段使用默认值
 * @param state - 原始更新状态
 * @returns 归一化后的更新状态，输入无效时返回 null
 */
function normalizeDesktopUpdateState(state: RawDesktopUpdateState | null | undefined) {
  if (!state || typeof state !== 'object') {
    return null;
  }

  return {
    status: trimDesktopRuntimeString(state.status) || 'idle',
    updateMode: trimDesktopRuntimeString(state.updateMode) || 'manual',
    currentVersion: trimDesktopRuntimeString(state.currentVersion),
    latestVersion: trimDesktopRuntimeString(state.latestVersion),
    releaseUrl: trimDesktopRuntimeString(state.releaseUrl),
    checkedAt: trimDesktopRuntimeString(state.checkedAt),
    publishedAt: trimDesktopRuntimeString(state.publishedAt),
    message: trimDesktopRuntimeString(state.message),
    releaseName: trimDesktopRuntimeString(state.releaseName),
    tagName: trimDesktopRuntimeString(state.tagName),
    downloadPercent: normalizeDesktopRuntimeNumber(state.downloadPercent),
    downloadedBytes: normalizeDesktopRuntimeNumber(state.downloadedBytes),
    totalBytes: normalizeDesktopRuntimeNumber(state.totalBytes),
  };
}

/**
 * 根据桌面端更新状态生成用户可见的通知信息
 * 映射不同状态（可更新、下载中、已下载、安装中、最新、检查中、错误）到对应文案和操作按钮
 * @param state - 桌面端更新状态
 * @param t - 翻译函数
 * @returns 通知信息对象，无有效状态时返回 null
 */
function getDesktopUpdateNotice(
  state: DesktopUpdateState | null,
  t: (key: UiTextKey, params?: Record<string, string | number>) => string,
): DesktopUpdateNotice | null {
  if (!state) {
    return null;
  }

  if (state.status === 'update-available') {
    const latestLabel = state.latestVersion || state.tagName || t('settings.desktopLatest');
    const currentLabel = state.currentVersion || getDesktopAppVersion() || WEB_BUILD_INFO.version;
    return {
      title: t('settings.desktopUpdateAvailable'),
      message: t('settings.desktopUpdateMessage', {
        current: currentLabel,
        latest: latestLabel,
        message: state.message || t('settings.desktopUpdateReleaseMessage'),
      }),
      variant: 'warning' as const,
      actionLabel: state.updateMode === 'auto' ? undefined : t('settings.desktopDownload'),
      actionKind: state.updateMode === 'auto' ? undefined : 'release',
    };
  }

  if (state.status === 'downloading') {
    const percentText = typeof state.downloadPercent === 'number' ? `（${state.downloadPercent}%）` : '';
    return {
      title: t('settings.desktopDownloading'),
      message: state.message || t('settings.desktopUpdateDownloadingMessage', { percent: percentText }),
      variant: 'warning' as const,
    };
  }

  if (state.status === 'update-downloaded') {
    return {
      title: t('settings.desktopDownloaded'),
      message: state.message || t('settings.desktopUpdateDownloadedMessage'),
      variant: 'success' as const,
      actionLabel: t('settings.desktopInstall'),
      actionKind: 'install',
    };
  }

  if (state.status === 'installing') {
    return {
      title: t('settings.desktopInstalling'),
      message: state.message || t('settings.desktopUpdateInstallingMessage'),
      variant: 'warning' as const,
    };
  }

  if (state.status === 'up-to-date') {
    return {
      title: t('settings.desktopUpToDate'),
      message: state.message || t('settings.desktopUpToDateMessage'),
      variant: 'success' as const,
    };
  }

  if (state.status === 'checking') {
    return {
      title: t('settings.desktopChecking'),
      message: state.message || t('settings.desktopUpdateCheckingMessage'),
      variant: 'warning' as const,
    };
  }

  if (state.status === 'error') {
    return {
      title: t('settings.desktopCheckError'),
      message: state.message || t('settings.desktopUpdateErrorMessage'),
      variant: 'error' as const,
      actionLabel: state.updateMode === 'auto' && state.releaseUrl ? t('settings.desktopDownload') : undefined,
      actionKind: state.updateMode === 'auto' && state.releaseUrl ? 'release' : undefined,
    };
  }

  return null;
}

/**
 * 生成环境配置备份文件的文件名
 * 格式为 `hrs-env_YYYYMMDD_HHmm.env` 或 `hrs-desktop-env_YYYYMMDD_HHmm.env`（桌面端）
 * @param isDesktopRuntime - 是否为桌面端运行环境
 * @returns 格式化的备份文件名
 */
function formatEnvBackupFilename(isDesktopRuntime: boolean) {
  const now = new Date();
  const pad = (value: number) => value.toString().padStart(2, '0');
  const date = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}`;
  const time = `${pad(now.getHours())}${pad(now.getMinutes())}`;
  return `${isDesktopRuntime ? 'hrs-desktop-env' : 'hrs-env'}_${date}_${time}.env`;
}

/** 调度时间格式正则：匹配 HH:mm（24 小时制） */
const SCHEDULE_TIME_PATTERN = /^(?:[01]\d|2[0-3]):[0-5]\d$/;
/** 调度器默认执行时间 */
const SCHEDULER_DEFAULT_TIME = '18:00';
/** 调度器相关配置键集合，用于检测配置变更后是否需要刷新调度状态 */
const SCHEDULER_SETTING_KEYS = new Set([
  'SCHEDULE_ENABLED',
  'SCHEDULE_TIME',
  'SCHEDULE_TIMES',
  'SCHEDULE_RUN_IMMEDIATELY',
]);

/**
 * 从配置项数组中查找指定键的配置项
 * @param items - 配置项数组
 * @param key - 要查找的配置键名
 * @returns 匹配的配置项，未找到返回 undefined
 */
function getConfigItem(items: SystemConfigItem[], key: string) {
  return items.find((item) => item.key === key);
}

/**
 * 将股票列表配置值解析为股票代码数组
 * @param value - 原始配置值（逗号或换行分隔的字符串）
 * @returns 解析后的股票代码数组
 */
function parseSetupStockList(value: unknown) {
  return parseStockListValue(String(value ?? ''));
}

/**
 * 判断配置值是否表示"已启用"
 * 将字符串值转为小写后与 'true' 比较
 * @param value - 配置值
 * @returns 是否为启用状态
 */
function isEnabledConfigValue(value: unknown) {
  return String(value ?? '').trim().toLowerCase() === 'true';
}

/**
 * 根据配置检查状态返回对应的图标组件
 * - configured/inherited：绿色勾选
 * - needs_action：橙色警告
 * - 其他：灰色虚线圆
 * @param check - 配置检查项
 * @returns 对应的图标 JSX 元素
 */
function getSetupCheckIcon(check: SetupStatusCheck) {
  if (check.status === 'configured' || check.status === 'inherited') {
    return <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success" aria-hidden="true" />;
  }
  if (check.status === 'needs_action') {
    return <CircleAlert className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-hidden="true" />;
  }
  return <CircleDashed className="mt-0.5 h-4 w-4 shrink-0 text-muted-text" aria-hidden="true" />;
}

/**
 * 根据配置检查状态返回本地化的状态标签文案
 * @param check - 配置检查项
 * @param t - 翻译函数
 * @returns 状态标签文案
 */
function getSetupCheckStatusLabel(
  check: SetupStatusCheck,
  t: (key: UiTextKey, params?: Record<string, string | number>) => string,
) {
  if (check.status === 'configured') return t('settings.setupStatusConfigured');
  if (check.status === 'inherited') return t('settings.setupStatusInherited');
  if (check.status === 'needs_action') return t('settings.setupStatusNeedsAction');
  return t('settings.setupStatusOptional');
}

/** 首次运行引导卡片组件的 Props 定义 */
type FirstRunSetupCardProps = {
  /** 系统初始化检查状态响应 */
  status: SetupStatusResponse | null;
  /** 是否正在加载初始化状态 */
  isLoading: boolean;
  /** 加载错误信息 */
  error: ParsedApiError | null;
  /** 首只股票代码（用于冒烟测试） */
  firstStockCode: string;
  /** 是否正在保存配置 */
  isSaving: boolean;
  /** 是否正在运行冒烟测试 */
  isRunningSmoke: boolean;
  /** 冒烟测试错误信息 */
  smokeError: ParsedApiError | null;
  /** 冒烟测试成功消息 */
  smokeSuccess: string;
  /** 刷新初始化状态的回调 */
  onRefresh: () => void | Promise<void>;
  /** 选择配置分类的回调 */
  onSelectCategory: (category: SystemConfigCategory) => void;
  /** 运行冒烟测试的回调 */
  onRunSmoke: () => void | Promise<void>;
  /** 列表分隔符（中文用「、」，英文用「, 」） */
  listSeparator: string;
  /** 翻译函数 */
  t: (key: UiTextKey, params?: Record<string, string | number>) => string;
};

/**
 * 首次运行引导卡片组件
 * 在基础配置分类下展示系统初始化检查项列表，引导用户完成必要配置
 * 支持刷新状态、跳转到对应分类配置、运行冒烟测试
 * 用户可手动折叠/展开该卡片
 */
const FirstRunSetupCard: React.FC<FirstRunSetupCardProps> = ({
  status,
  isLoading,
  error,
  firstStockCode,
  isSaving,
  isRunningSmoke,
  smokeError,
  smokeSuccess,
  onRefresh,
  onSelectCategory,
  onRunSmoke,
  listSeparator,
  t,
}) => {
  /** 卡片是否被用户手动折叠 */
  const [isHidden, setIsHidden] = useState(false);
  /** 必需但尚未完成的检查项列表 */
  const requiredMissing = status?.checks.filter((check) => check.required && check.status === 'needs_action') || [];
  /** 系统初始化是否已完成（所有必需项通过） */
  const isComplete = Boolean(status?.isComplete);
  /** 是否可以运行冒烟测试（系统就绪且有首只股票） */
  const canRunSmoke = Boolean(status?.readyForSmoke && firstStockCode);
  /** 引导卡片摘要标题（根据加载/完成/未完成状态切换） */
  const summaryTitle = !status
    ? error
      ? t('settings.setupGuideUnknownTitle')
      : t('settings.setupGuideCheckingTitle')
    : isComplete
      ? t('settings.setupGuideCompleteTitle')
      : t('settings.setupGuideIncompleteTitle');
  const summaryMessage = !status
    ? error
      ? t('settings.setupGuideUnknownSummary')
      : t('settings.setupGuideCheckingSummary')
    : requiredMissing.length
      ? t('settings.setupGuideMissingSummary', {
        count: requiredMissing.length,
        labels: requiredMissing.slice(0, 3).map((check) => check.title).join(listSeparator),
      })
      : t('settings.setupGuideReadySummary');

  if (isHidden) {
    return (
      /* ===== 折叠状态：仅显示标题和展开按钮 ===== */
      <div className="rounded-2xl border settings-border bg-card/90 px-4 py-3 shadow-soft-card">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-foreground">{t('settings.setupGuideHiddenTitle')}</p>
            <p className="mt-1 text-xs leading-5 text-muted-text">{t('settings.setupGuideHiddenDescription')}</p>
          </div>
          <Button type="button" variant="settings-secondary" size="sm" onClick={() => setIsHidden(false)}>
            {t('settings.setupGuideOpen')}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <SettingsSectionCard
      title={t('settings.setupGuideTitle')}
      description={t('settings.setupGuideDescription')}
    >
      <div data-testid="first-run-setup-card" className="space-y-4">
        {/* ===== 摘要区：状态标题 + 刷新/折叠按钮 ===== */}
        <div className="flex flex-col gap-3 rounded-2xl border settings-border bg-background/35 px-4 py-4 md:flex-row md:items-start md:justify-between">
          <div className="min-w-0">
            <p className="text-sm font-semibold text-foreground">
              {summaryTitle}
            </p>
            <p className="mt-1 text-xs leading-6 text-muted-text">
              {summaryMessage}
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            <Button
              type="button"
              variant="settings-secondary"
              size="sm"
              disabled={isLoading}
              isLoading={isLoading}
              loadingText={t('settings.setupGuideRefreshing')}
              onClick={() => void onRefresh()}
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              {t('settings.setupGuideRefresh')}
            </Button>
            <Button type="button" variant="settings-secondary" size="sm" onClick={() => setIsHidden(true)}>
              {t('settings.setupGuideHide')}
            </Button>
          </div>
        </div>

        {error ? <InlineTipCard variant="danger" error={error} /> : null}

        {isLoading && !status ? (
          <p className="text-sm text-muted-text">{t('common.loading')}</p>
        ) : null}

        {/* ===== 检查项列表区：逐项展示配置状态 ===== */}
        {status ? (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {status.checks.map((check) => (
              <div
                key={check.key}
                className="rounded-2xl border settings-border bg-card/65 px-4 py-3"
              >
                <div className="flex items-start gap-3">
                  {getSetupCheckIcon(check)}
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-semibold text-foreground">{check.title}</p>
                      <span className="rounded-full border settings-border bg-background/60 px-2 py-0.5 text-[11px] font-medium text-muted-text">
                        {getSetupCheckStatusLabel(check, t)}
                      </span>
                    </div>
                    <p className="mt-1 text-xs leading-5 text-muted-text">{check.message}</p>
                    {check.nextStep ? (
                      <p className="mt-2 text-xs leading-5 text-secondary-text">{check.nextStep}</p>
                    ) : null}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : null}

        {/* ===== 操作按钮区：跳转配置分类 + 运行冒烟测试 ===== */}
        <div className="flex flex-wrap items-center gap-2">
          <Button type="button" variant="settings-secondary" size="sm" onClick={() => onSelectCategory('ai_model')}>
            {t('settings.setupGuideConfigureLlm')}
          </Button>
          <Button type="button" variant="settings-secondary" size="sm" onClick={() => onSelectCategory('base')}>
            {t('settings.setupGuideAddStocks')}
          </Button>
          <Button type="button" variant="settings-secondary" size="sm" onClick={() => onSelectCategory('notification')}>
            {t('settings.setupGuideConfigureNotification')}
          </Button>
          <Button
            type="button"
            variant="settings-primary"
            size="sm"
            disabled={!canRunSmoke || isSaving || isRunningSmoke}
            isLoading={isRunningSmoke}
            loadingText={t('settings.setupGuideSmokeRunning')}
            title={!firstStockCode ? t('settings.setupGuideSmokeNeedsStock') : undefined}
            onClick={() => void onRunSmoke()}
          >
            <Play className="h-4 w-4" aria-hidden="true" />
            {t('settings.setupGuideRunSmoke')}
          </Button>
        </div>

        {/* ===== 冒烟测试结果提示区 ===== */}
        {!canRunSmoke && status ? (
          <p className="text-xs leading-6 text-muted-text">
            {firstStockCode ? t('settings.setupGuideSmokeNotReady') : t('settings.setupGuideSmokeNeedsStock')}
          </p>
        ) : null}
        {smokeError ? <InlineTipCard variant="danger" error={smokeError} /> : null}
        {!smokeError && smokeSuccess ? (
          <SettingsAlert title={t('settings.actionSuccess')} message={smokeSuccess} variant="success" />
        ) : null}
      </div>
    </SettingsSectionCard>
  );
};

/**
 * 解析调度时间配置值，返回时间字符串数组
 * 优先使用逗号分隔的多时间值，无值时回退到单个 fallback 值，最终回退到默认 18:00
 * @param scheduleTimesValue - 多时间配置值（逗号分隔）
 * @param fallbackValue - 单时间回退值
 * @returns 解析后的时间字符串数组
 */
function parseScheduleTimes(scheduleTimesValue?: string, fallbackValue?: string) {
  const values = String(scheduleTimesValue ?? '')
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean);

  if (values.length > 0) {
    return values;
  }

  const fallback = String(fallbackValue ?? '').trim();
  return fallback ? [fallback] : [SCHEDULER_DEFAULT_TIME];
}

/**
 * 将时间字符串数组序列化为逗号分隔的字符串
 * @param times - 时间字符串数组
 * @returns 序列化后的字符串
 */
function serializeScheduleTimes(times: string[]) {
  return times.map((time) => time.trim()).filter(Boolean).join(',');
}

/**
 * 格式化调度器时间戳为本地化的短日期时间字符串
 * @param value - 时间戳字符串
 * @param language - UI 语言
 * @returns 格式化后的字符串（MM-DD HH:mm），无效输入返回 '-'
 */
function formatSchedulerTimestamp(value: string | null | undefined, language: UiLanguage) {
  if (!value) {
    return '-';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(language === 'en' ? 'en-US' : 'zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date);
}

/** 调度器设置卡片组件的 Props 定义 */
type SchedulerSettingsCardProps = {
  /** 当前分类下的所有配置项 */
  items: SystemConfigItem[];
  /** 是否禁用所有交互（保存/加载中） */
  disabled: boolean;
  /** 按配置键索引的校验问题 */
  issueByKey: Record<string, ConfigValidationIssue[]>;
  /** 状态刷新令牌，递增时触发重新获取调度器运行状态 */
  statusRefreshToken: number;
  /** 配置值变更回调 */
  onChange: (key: string, value: string) => void;
  /** 调度器运行状态变化回调，用于外层检测 UI 与运行时的差异 */
  onSchedulerStateChange?: (payload: {
    runtimeEnabled: boolean | null;
    overrideEnabled: boolean | null;
  }) => void;
  /** 翻译函数 */
  t: (key: UiTextKey, params?: Record<string, string | number>) => string;
  /** UI 语言 */
  language: UiLanguage;
};

/**
 * 调度器设置卡片组件
 * 在系统分类下展示调度器的启用开关、执行时间列表编辑、运行状态信息
 * 支持添加/删除执行时间、立即运行调度器、刷新运行状态
 */
const SchedulerSettingsCard: React.FC<SchedulerSettingsCardProps> = ({
  items,
  disabled,
  issueByKey,
  statusRefreshToken,
  onChange,
  onSchedulerStateChange,
  t,
  language,
}) => {
  /** 调度启用配置项 */
  const scheduleEnabledItem = getConfigItem(items, 'SCHEDULE_ENABLED');
  /** 多时间调度配置项 */
  const scheduleTimesItem = getConfigItem(items, 'SCHEDULE_TIMES');
  /** 单时间调度配置项（旧版兼容） */
  const scheduleTimeItem = getConfigItem(items, 'SCHEDULE_TIME');
  /** 是否存在调度器相关配置项 */
  const hasSchedulerSettings = Boolean(scheduleEnabledItem || scheduleTimesItem || scheduleTimeItem);
  /** 调度器运行状态响应 */
  const [status, setStatus] = useState<SchedulerStatusResponse | null>(null);
  /** 是否正在刷新调度器运行状态 */
  const [isRefreshingStatus, setIsRefreshingStatus] = useState(false);
  /** 是否正在立即运行调度器 */
  const [isRunningNow, setIsRunningNow] = useState(false);
  /** 调度器状态获取错误 */
  const [statusError, setStatusError] = useState<ParsedApiError | null>(null);
  /** 立即运行错误 */
  const [runNowError, setRunNowError] = useState<ParsedApiError | null>(null);
  /** 立即运行成功消息 */
  const [runNowSuccess, setRunNowSuccess] = useState('');
  /** UI 中调度启用开关的覆盖值，用于乐观更新 */
  const [scheduleEnabledOverride, setScheduleEnabledOverride] = useState<boolean | null>(null);

  /**
   * 刷新调度器运行状态
   * 调用 API 获取最新的启用状态、下次运行时间、上次成功/失败时间等信息
   */
  const refreshSchedulerStatus = useCallback(async () => {
    setStatusError(null);
    setIsRefreshingStatus(true);
    try {
      const payload = await systemConfigApi.getSchedulerStatus();
      setStatus(payload);
    } catch (error: unknown) {
      setStatusError(getParsedApiError(error));
    } finally {
      setIsRefreshingStatus(false);
    }
  }, []);

  /**
   * 当存在调度器配置或状态刷新令牌变化时，重新获取调度器运行状态
   */
  useEffect(() => {
    if (!hasSchedulerSettings) {
      return;
    }
    void refreshSchedulerStatus();
  }, [hasSchedulerSettings, refreshSchedulerStatus, statusRefreshToken]);

  /**
   * 当调度器运行状态或 UI 覆盖值变化时，通知外层组件
   * 外层用于检测 UI 开关与运行时实际状态之间的差异
   */
  useEffect(() => {
    if (!onSchedulerStateChange) {
      return;
    }

    const runtimeEnabled = status?.enabled ?? null;
    onSchedulerStateChange({
      runtimeEnabled,
      overrideEnabled: scheduleEnabledOverride,
    });
  }, [onSchedulerStateChange, status?.enabled, scheduleEnabledOverride]);

  if (!hasSchedulerSettings) {
    return null;
  }

  /** 配置项中的调度启用状态 */
  const scheduleEnabled = isEnabledConfigValue(scheduleEnabledItem?.value);
  /** 解析后的调度时间列表 */
  const scheduleTimes = parseScheduleTimes(
    String(scheduleTimesItem?.value ?? ''),
    String(scheduleTimeItem?.value ?? ''),
  );
  /** 时间编辑的目标配置键：优先 SCHEDULE_TIMES，回退到 SCHEDULE_TIME */
  const timeTargetKey = scheduleTimesItem ? 'SCHEDULE_TIMES' : 'SCHEDULE_TIME';
  /** 运行时的调度启用状态，回退到配置项值 */
  const statusEnabled = status?.enabled ?? scheduleEnabled;
  /** 展示的调度启用状态：UI 覆盖值优先，回退到运行时状态 */
  const displayedScheduleEnabled = scheduleEnabledOverride ?? statusEnabled;
  /** 运行时生效的调度时间列表 */
  const effectiveStatusTimes = status?.scheduleTimes?.length ? status.scheduleTimes : scheduleTimes.filter(Boolean);
  /** 调度器相关的所有校验问题 */
  const validationIssues = [
    ...(issueByKey.SCHEDULE_ENABLED || []),
    ...(issueByKey.SCHEDULE_TIMES || []),
    ...(issueByKey.SCHEDULE_TIME || []),
  ];

  /**
   * 更新调度时间列表
   * 根据目标配置键决定写入 SCHEDULE_TIME（单个）还是 SCHEDULE_TIMES（逗号分隔）
   * @param nextTimes - 更新后的时间字符串数组
   */
  const updateScheduleTimes = (nextTimes: string[]) => {
    if (timeTargetKey === 'SCHEDULE_TIME') {
      onChange(timeTargetKey, nextTimes[0] || '');
      return;
    }
    onChange(timeTargetKey, serializeScheduleTimes(nextTimes));
  };

  /**
   * 立即运行调度器
   * 调用 API 触发立即执行，成功后刷新运行状态
   */
  const runSchedulerNow = async () => {
    setRunNowError(null);
    setRunNowSuccess('');
    setIsRunningNow(true);
    try {
      await systemConfigApi.runSchedulerNow();
      setRunNowSuccess(t('settings.schedulerRunAccepted'));
      await refreshSchedulerStatus();
    } catch (error: unknown) {
      setRunNowError(getParsedApiError(error));
    } finally {
      setIsRunningNow(false);
    }
  };

  return (
    <SettingsSectionCard
      title={t('settings.schedulerTitle')}
      description={t('settings.schedulerDescription')}
    >
      <div data-testid="scheduler-settings-card" className="space-y-4">
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(300px,360px)]">
          {/* ===== 左侧：启用开关 + 时间编辑区 ===== */}
          <div className="space-y-4 rounded-2xl border settings-border bg-background/35 px-4 py-4">
                <label className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    className="mt-1 h-4 w-4 rounded border-border text-cyan focus:ring-cyan/20"
                    checked={displayedScheduleEnabled}
                    data-testid="scheduler-enabled-checkbox"
                    disabled={disabled || !scheduleEnabledItem?.schema?.isEditable}
                    onChange={(event) => {
                      const nextEnabled = Boolean(event.target.checked);
                      setScheduleEnabledOverride(nextEnabled);
                      onChange('SCHEDULE_ENABLED', nextEnabled ? 'true' : 'false');
                    }}
                  />
              <span>
                <span className="block text-sm font-semibold text-foreground">{t('settings.schedulerEnable')}</span>
                <span className="block text-xs leading-6 text-muted-text">{t('settings.schedulerEnableDescription')}</span>
              </span>
            </label>

            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <Clock className="h-4 w-4" aria-hidden="true" />
                {t('settings.schedulerTimes')}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {scheduleTimes.map((time, index) => (
                  <div
                    key={index}
                    className="inline-flex h-11 shrink-0 items-center gap-1 rounded-xl border settings-border bg-card/90 p-1 shadow-inner"
                  >
                    <input
                      data-testid={`scheduler-time-input-${index}`}
                      type="time"
                      value={SCHEDULE_TIME_PATTERN.test(time) ? time : ''}
                      aria-label={t('settings.schedulerTimeInputAria', { index: index + 1 })}
                      className="h-9 w-[8.75rem] rounded-lg border-none bg-transparent px-2 text-sm font-medium text-foreground outline-none transition focus:bg-background/60 focus:ring-2 focus:ring-cyan/20"
                      disabled={disabled}
                      onChange={(event) => {
                        const nextTimes = scheduleTimes.map((currentTime, currentIndex) => (
                          currentIndex === index ? event.target.value : currentTime
                        ));
                        updateScheduleTimes(nextTimes);
                      }}
                    />
                    {scheduleTimes.length > 1 ? (
                      <Button
                        type="button"
                        variant="settings-secondary"
                        size="sm"
                        className="h-8 w-8 rounded-lg px-0"
                        aria-label={t('settings.schedulerRemoveTime')}
                        title={t('settings.schedulerRemoveTime')}
                        disabled={disabled}
                        onClick={() => {
                          updateScheduleTimes(scheduleTimes.filter((_, currentIndex) => currentIndex !== index));
                        }}
                      >
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                      </Button>
                    ) : null}
                  </div>
                ))}
                <Button
                  type="button"
                  variant="settings-secondary"
                  size="sm"
                  className="h-11 shrink-0"
                  data-testid="scheduler-add-time-button"
                  disabled={disabled}
                  onClick={() => updateScheduleTimes([...scheduleTimes, SCHEDULER_DEFAULT_TIME])}
                >
                  <Plus className="h-4 w-4" aria-hidden="true" />
                  {t('settings.schedulerAddTime')}
                </Button>
              </div>
            </div>
          </div>

          {/* ===== 右侧：运行状态信息 + 操作按钮 ===== */}
          <div className="space-y-3 rounded-2xl border settings-border bg-background/35 px-4 py-4">
            <div>
              <p className="text-sm font-semibold text-foreground">{t('settings.schedulerStatus')}</p>
              <p className="mt-1 text-xs leading-6 text-muted-text">
                {status?.running
                  ? t('settings.schedulerRunning')
                  : statusEnabled
                    ? t('settings.schedulerEnabled')
                    : t('settings.schedulerDisabled')}
              </p>
            </div>
            <dl className="grid grid-cols-1 gap-2 text-xs">
              <div className="rounded-xl border settings-border bg-card/60 px-3 py-2">
                <dt className="text-muted-text">{t('settings.schedulerEffectiveTimes')}</dt>
                <dd className="mt-1 font-medium text-foreground">{effectiveStatusTimes.join(', ') || '-'}</dd>
              </div>
              <div className="rounded-xl border settings-border bg-card/60 px-3 py-2">
                <dt className="text-muted-text">{t('settings.schedulerNextRun')}</dt>
                <dd className="mt-1 font-medium text-foreground">
                  {formatSchedulerTimestamp(status?.nextRunAt, language)}
                </dd>
              </div>
              <div className="rounded-xl border settings-border bg-card/60 px-3 py-2">
                <dt className="text-muted-text">{t('settings.schedulerLastSuccess')}</dt>
                <dd data-testid="scheduler-last-success" className="mt-1 font-medium text-foreground">
                  {formatSchedulerTimestamp(status?.lastSuccessAt, language)}
                </dd>
              </div>
              {status?.lastError ? (
                <div className="rounded-xl border border-danger/40 bg-danger/10 px-3 py-2">
                  <dt className="text-danger">{t('settings.schedulerLastError')}</dt>
                  <dd data-testid="scheduler-last-error" className="mt-1 break-words text-danger">{status.lastError}</dd>
                </div>
              ) : null}
            </dl>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                type="button"
                variant="settings-secondary"
                size="sm"
                data-testid="scheduler-refresh-status-button"
                disabled={disabled || isRefreshingStatus}
                isLoading={isRefreshingStatus}
                loadingText={t('settings.schedulerRefreshing')}
                onClick={() => void refreshSchedulerStatus()}
              >
                <RefreshCw className="h-4 w-4" aria-hidden="true" />
                {t('settings.schedulerRefresh')}
              </Button>
              <Button
                type="button"
                variant="settings-primary"
                size="sm"
                data-testid="scheduler-run-now-button"
                disabled={disabled || isRunningNow}
                isLoading={isRunningNow}
                loadingText={t('settings.schedulerRunningNow')}
                onClick={() => void runSchedulerNow()}
              >
                <Play className="h-4 w-4" aria-hidden="true" />
                {t('settings.schedulerRunNow')}
              </Button>
            </div>
          </div>
        </div>

        {/* ===== 校验问题 + 错误/成功提示区 ===== */}
        {validationIssues.length ? (
          <div className="space-y-1 text-xs text-danger">
            {validationIssues.map((issue) => (
              <p key={`${issue.key}-${issue.code}`}>{issue.message}</p>
            ))}
          </div>
        ) : null}
        {statusError ? <InlineTipCard variant="danger" error={statusError} /> : null}
        {runNowError ? <InlineTipCard variant="danger" error={runNowError} /> : null}
        {!runNowError && runNowSuccess ? (
          <SettingsAlert title={t('settings.actionSuccess')} message={runNowSuccess} variant="success" />
        ) : null}
      </div>
    </SettingsSectionCard>
  );
};

/**
 * 系统设置页主组件
 * 系统配置管理的核心页面，提供以下功能：
 * - 配置分类导航：按分类（基础/AI模型/数据源/通知/系统/Agent）浏览和编辑配置项
 * - LLM 通道编辑：管理多 LLM 通道的协议、密钥、模型等配置
 * - 生成后端状态面板：展示当前生成后端的配置状态
 * - 调度器管理：配置定时分析计划，查看运行状态，立即触发执行
 * - AlphaSift 控制：启用/禁用 AlphaSift 数据源
 * - 配置备份：导出/导入 .env 配置文件
 * - 桌面端更新检查：在 Electron 桌面端检查并安装应用更新
 * - 首次运行引导：展示初始化检查项，引导用户完成必要配置和冒烟测试
 * @returns 设置页的 JSX 元素
 */
const SettingsPage: React.FC = () => {
  /** 认证状态：是否启用登录、是否可修改密码 */
  const { authEnabled, passwordChangeable } = useAuth();
  /** UI 语言和翻译函数 */
  const { language: uiLanguage, t } = useUiLanguage();
  /** 配置备份操作错误 */
  const [envBackupActionError, setEnvBackupActionError] = useState<ParsedApiError | null>(null);
  /** 配置备份操作成功消息 */
  const [envBackupActionSuccess, setEnvBackupActionSuccess] = useState<string>('');
  /** AlphaSift 操作错误 */
  const [alphaSiftActionError, setAlphaSiftActionError] = useState<ParsedApiError | null>(null);
  /** AlphaSift 操作成功消息 */
  const [alphaSiftActionSuccess, setAlphaSiftActionSuccess] = useState<string>('');
  /** 是否正在导出环境配置 */
  const [isExportingEnv, setIsExportingEnv] = useState(false);
  /** 是否正在导入环境配置 */
  const [isImportingEnv, setIsImportingEnv] = useState(false);
  /** 是否正在更新 AlphaSift 状态 */
  const [isUpdatingAlphaSift, setIsUpdatingAlphaSift] = useState(false);
  /** 是否显示导入配置确认对话框（有未保存更改时） */
  const [showImportConfirm, setShowImportConfirm] = useState(false);
  /** 桌面端更新状态 */
  const [desktopUpdateState, setDesktopUpdateState] = useState<DesktopUpdateState | null>(null);
  /** 是否正在检查桌面端更新 */
  const [isCheckingDesktopUpdate, setIsCheckingDesktopUpdate] = useState(false);
  /** 调度器状态刷新令牌，递增时触发 SchedulerSettingsCard 重新获取状态 */
  const [schedulerStatusRefreshToken, setSchedulerStatusRefreshToken] = useState(0);
  /** 调度器运行时的启用状态（来自 API） */
  const [schedulerRuntimeEnabled, setSchedulerRuntimeEnabled] = useState<boolean | null>(null);
  /** UI 中调度启用开关的覆盖值（用户操作后的乐观值） */
  const [schedulerOverrideFromUi, setSchedulerOverrideFromUi] = useState<boolean | null>(null);
  /** 系统初始化检查状态 */
  const [setupStatus, setSetupStatus] = useState<SetupStatusResponse | null>(null);
  /** 是否正在刷新初始化状态 */
  const [isRefreshingSetupStatus, setIsRefreshingSetupStatus] = useState(false);
  /** 初始化状态加载错误 */
  const [setupStatusError, setSetupStatusError] = useState<ParsedApiError | null>(null);
  /** 是否正在运行冒烟测试 */
  const [isRunningSetupSmoke, setIsRunningSetupSmoke] = useState(false);
  /** 冒烟测试错误 */
  const [setupSmokeError, setSetupSmokeError] = useState<ParsedApiError | null>(null);
  /** 冒烟测试成功消息 */
  const [setupSmokeSuccess, setSetupSmokeSuccess] = useState('');
  /** LLM 通道编辑器草稿项（未保存的通道配置变更） */
  const [llmChannelDraftItems, setLlmChannelDraftItems] = useState<SystemConfigUpdateItem[]>([]);
  /** 配置备份文件导入的隐藏 input 引用 */
  const envBackupImportRef = useRef<HTMLInputElement | null>(null);
  /** 初始化状态请求 ID，用于防止竞态条件 */
  const setupStatusRequestIdRef = useRef(0);
  /** 桌面端 Electron 注入的运行时 API */
  const desktopRuntimeApi = getDesktopRuntimeApi();
  /** 是否运行在桌面端环境 */
  const isDesktopRuntime = Boolean(desktopRuntimeApi);
  /** 是否支持桌面端更新检查（需要所有必需 API 存在） */
  const canCheckDesktopUpdate = Boolean(
    desktopRuntimeApi?.getUpdateState && desktopRuntimeApi?.checkForUpdates && desktopRuntimeApi?.openReleasePage
  );
  /** 桌面端应用版本号 */
  const desktopAppVersion = getDesktopAppVersion();
  /** 是否显示桌面端版本卡片（仅桌面端有版本号时显示） */
  const shouldShowDesktopVersionCard = Boolean(desktopAppVersion);

  // 设置页面标题
  useEffect(() => {
    document.title = t('settings.pageTitleDocument');
  }, [t]);

  /**
   * 系统配置 Hook：提供配置分类、配置项、草稿管理与保存/加载等核心能力
   * 解构出的属性按职责分组：
   * - 配置数据：categories（分类列表）、itemsByCategory（按分类索引的配置项 Map）
   * - 当前分类：activeCategory（当前选中的分类）、setActiveCategory（切换分类）
   * - 草稿管理：hasDirty（是否有未保存变更）、dirtyCount（变更项数）、getChangedItems（获取变更项）
   * - 草稿操作：setDraftValue（设置草稿值）、resetDraft（重置草稿）
   * - 加载/保存：isLoading、isSaving、loadError、saveError、load、save、retry、retryAction
   * - 外部保存同步：refreshAfterExternalSave（外部保存后刷新指定键）、configVersion（配置版本号）
   * - 令牌掩码：maskToken（用于 API 请求的掩码令牌）
   * - Toast 提示：toast（操作结果提示）、clearToast（清除提示）
   */
  const {
    categories,
    itemsByCategory,
    issueByKey,
    activeCategory,
    setActiveCategory,
    hasDirty,
    dirtyCount,
    toast,
    clearToast,
    isLoading,
    isSaving,
    loadError,
    saveError,
    retryAction,
    load,
    retry,
    save,
    resetDraft,
    setDraftValue,
    getChangedItems,
    refreshAfterExternalSave,
    configVersion,
    maskToken,
  } = useSystemConfig();

  /** 当前已变更的配置项列表 */
  const currentChangedItems = getChangedItems();
  /** 当前已变更项的 JSON 指纹，用于 memo 依赖比较 */
  const currentChangedItemsFingerprint = JSON.stringify(currentChangedItems);
  /** LLM 通道草稿项的 JSON 指纹 */
  const llmChannelDraftItemsFingerprint = JSON.stringify(llmChannelDraftItems);
  /** 合并后的生成后端草稿项（外层变更 + LLM 通道草稿） */
  const generationBackendDraftItems = useMemo(
    () => mergeGenerationBackendDraftItems(currentChangedItems, llmChannelDraftItems),
    // Fingerprints keep the status panel from refreshing when parent renders do not change draft content.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [currentChangedItemsFingerprint, llmChannelDraftItemsFingerprint],
  );
  /** 合并后的 Agent 后端草稿项（生成后端草稿 + Agent 专属键） */
  const agentBackendDraftItems = useMemo(
    () => {
      const merged = new Map(
        generationBackendDraftItems.map((item) => [item.key.trim().toUpperCase(), item]),
      );
      for (const item of currentChangedItems) {
        const key = item.key.trim().toUpperCase();
        if (AGENT_BACKEND_STATUS_KEYS.has(key)) {
          merged.set(key, item);
        }
      }
      return Array.from(merged.values());
    },
    // The fingerprint changes only when the draft content changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [currentChangedItemsFingerprint, generationBackendDraftItems],
  );
  /** LLM 通道草稿变更回调，将通道编辑器的草稿项同步到外层状态 */
  const handleLlmChannelDraftItemsChange = useCallback((items: Array<{ key: string; value: string }>) => {
    setLlmChannelDraftItems(items);
  }, []);

  /**
   * 刷新系统初始化状态
   * 使用请求 ID 防止竞态条件，确保只有最新请求的结果会更新状态
   */
  const refreshSetupStatus = useCallback(async () => {
    const requestId = setupStatusRequestIdRef.current + 1;
    setupStatusRequestIdRef.current = requestId;
    setSetupStatusError(null);
    setIsRefreshingSetupStatus(true);
    try {
      const status = await systemConfigApi.getSetupStatus();
      if (setupStatusRequestIdRef.current !== requestId) {
        return;
      }
      setSetupStatus(status);
    } catch (error: unknown) {
      if (setupStatusRequestIdRef.current !== requestId) {
        return;
      }
      setSetupStatusError(getParsedApiError(error));
    } finally {
      if (setupStatusRequestIdRef.current === requestId) {
        setIsRefreshingSetupStatus(false);
      }
    }
  }, []);

  /** 组件挂载时加载系统配置 */
  useEffect(() => {
    void load();
  }, [load]);

  /** 从 URL 查询参数中读取分类，自动切换到指定分类 */
  useEffect(() => {
    const requestedCategory = new URLSearchParams(window.location.search).get('category');
    if (requestedCategory && categories.some((category) => category.category === requestedCategory)) {
      setActiveCategory(requestedCategory);
    }
  }, [categories, setActiveCategory]);

  /** 组件挂载时刷新初始化状态 */
  useEffect(() => {
    void refreshSetupStatus();
  }, [refreshSetupStatus]);

  /** Toast 自动消失：3.2 秒后清除 */
  useEffect(() => {
    if (!toast) {
      return;
    }

    const timer = window.setTimeout(() => {
      clearToast();
    }, 3200);

    return () => {
      window.clearTimeout(timer);
    };
  }, [clearToast, toast]);

  /**
   * 桌面端更新状态同步
   * 组件挂载时获取初始更新状态，并订阅更新状态变化事件
   * 非桌面端环境时清除状态
   */
  useEffect(() => {
    if (!canCheckDesktopUpdate) {
      setDesktopUpdateState(null);
      setIsCheckingDesktopUpdate(false);
      return;
    }

    let active = true;

    const syncDesktopUpdateState = async () => {
      try {
        const state = await desktopRuntimeApi?.getUpdateState?.();
        if (active) {
          setDesktopUpdateState(normalizeDesktopUpdateState(state));
        }
      } catch (error: unknown) {
        if (!active) {
          return;
        }
        setDesktopUpdateState({
          status: 'error',
          message: error instanceof Error ? error.message : t('settings.desktopUpdateErrorMessage'),
        });
      }
    };

    void syncDesktopUpdateState();

    const unsubscribe = desktopRuntimeApi?.onUpdateStateChange?.((state) => {
      if (!active) {
        return;
      }
      setDesktopUpdateState(normalizeDesktopUpdateState(state));
      setIsCheckingDesktopUpdate(false);
    });

    return () => {
      active = false;
      if (typeof unsubscribe === 'function') {
        unsubscribe();
      }
    };
  }, [canCheckDesktopUpdate, desktopRuntimeApi, t]);

  /** 当前分类下的所有配置项 */
  const rawActiveItems = itemsByCategory[activeCategory] || [];
  /** 当前分类配置项的键值 Map，用于快速查找 */
  const rawActiveItemMap = new Map(rawActiveItems.map((item) => [item.key, String(item.value ?? '')]));
  /** 基础配置中第一只股票代码（用于冒烟测试） */
  const firstSetupStockCode = parseSetupStockList(getConfigItem(itemsByCategory.base || [], 'STOCK_LIST')?.value)[0] || '';
  /** AlphaSift 启用配置项 */
  const alphasiftItem = (itemsByCategory.data_source || []).find((item) => item.key === 'ALPHASIFT_ENABLED');
  /** AlphaSift 是否已启用 */
  const alphasiftEnabled = String(alphasiftItem?.value ?? '').trim().toLowerCase() === 'true';
  /** 是否在基础分类下显示首次运行引导卡片 */
  const shouldShowFirstRunSetup = activeCategory === 'base';
  /** 是否在数据源分类下显示 AlphaSift 设置卡片 */
  const shouldShowAlphaSiftSettings = activeCategory === 'data_source' && Boolean(alphasiftItem);
  /** 是否已配置 LLM 通道（LLM_CHANNELS 非空） */
  const hasConfiguredChannels = Boolean((rawActiveItemMap.get('LLM_CHANNELS') || '').trim());
  /** 是否已有 LiteLLM 配置 */
  const hasLitellmConfig = Boolean((rawActiveItemMap.get('LITELLM_CONFIG') || '').trim());
  /** 调度器运行时与 UI 覆盖值是否存在差异 */
  const hasRuntimeSchedulerMismatch =
    schedulerRuntimeEnabled !== null
    && schedulerOverrideFromUi !== null
    && schedulerOverrideFromUi !== schedulerRuntimeEnabled;
  /** 调度器差异是否未在当前草稿中体现（需要额外同步） */
  const hasRuntimeSchedulerMismatchInDraft = hasRuntimeSchedulerMismatch
    && !currentChangedItems.some((item) => item.key === 'SCHEDULE_ENABLED');
  /** 有效的脏标记：草稿有变更 或 调度器存在未同步差异 */
  const effectiveHasDirty = hasDirty || hasRuntimeSchedulerMismatchInDraft;
  /** 有效的变更计数：草稿变更数 + 调度器未同步差异（1 或 0） */
  const effectiveDirtyCount = dirtyCount + (hasRuntimeSchedulerMismatchInDraft ? 1 : 0);

  /**
   * 调度器运行状态变化回调
   * 将运行时启用状态和 UI 覆盖值同步到外层状态
   */
  const handleSchedulerRuntimeStateChange = useCallback(({ runtimeEnabled, overrideEnabled }: {
    runtimeEnabled: boolean | null;
    overrideEnabled: boolean | null;
  }) => {
    setSchedulerRuntimeEnabled(runtimeEnabled);
    setSchedulerOverrideFromUi(overrideEnabled);
  }, []);

  // UI 渲染规则：通道模式下隐藏通道管理的键和旧版供应商专属 LLM 键
  // 此规则仅影响 UI 展示，不影响保存/刷新载荷或配置迁移/回滚行为
  const LLM_CHANNEL_KEY_RE = /^LLM_[A-Z0-9_]+_(PROTOCOL|BASE_URL|API_KEY|API_KEYS|MODELS|EXTRA_HEADERS|ENABLED)$/;
  /** AI 模型分类下需要隐藏的配置键集合（通道模式激活时） */
  const AI_MODEL_HIDDEN_KEYS = new Set([
    'LLM_CHANNELS',
    'LLM_TEMPERATURE',
    'LITELLM_MODEL',
    'AGENT_LITELLM_MODEL',
    'LITELLM_FALLBACK_MODELS',
    'AIHUBMIX_KEY',
    'DEEPSEEK_API_KEY',
    'DEEPSEEK_API_KEYS',
    'GEMINI_API_KEY',
    'GEMINI_API_KEYS',
    'GEMINI_MODEL',
    'GEMINI_MODEL_FALLBACK',
    'GEMINI_TEMPERATURE',
    'ANTHROPIC_API_KEY',
    'ANTHROPIC_API_KEYS',
    'ANTHROPIC_MODEL',
    'ANTHROPIC_TEMPERATURE',
    'ANTHROPIC_MAX_TOKENS',
    'OPENAI_API_KEY',
    'OPENAI_API_KEYS',
    'OPENAI_BASE_URL',
    'OPENAI_MODEL',
    'OPENAI_VISION_MODEL',
    'OPENAI_TEMPERATURE',
    'VISION_MODEL',
  ]);
  /** 系统分类下需要隐藏的配置键集合（认证开关和调度器设置由专用组件管理） */
  const SYSTEM_HIDDEN_KEYS = new Set([
    'ADMIN_AUTH_ENABLED',
    ...SCHEDULER_SETTING_KEYS,
  ]);
  /** 数据源分类下需要隐藏的配置键集合（AlphaSift 由专用卡片管理） */
  const DATA_SOURCE_HIDDEN_KEYS = new Set([
    'ALPHASIFT_ENABLED',
  ]);
  /** Agent 分类下需要隐藏的配置键集合 */
  const AGENT_HIDDEN_KEYS = new Set(['AGENT_GENERATION_BACKEND']);
  /**
   * 根据当前分类过滤配置项：
   * - ai_model：通道模式激活时隐藏通道管理的键和旧版供应商键
   * - system：隐藏认证和调度器键（由专用组件展示）
   * - data_source：隐藏 AlphaSift 键（由专用卡片展示）
   * - agent：隐藏 AGENT_GENERATION_BACKEND
   */
  // 根据当前分类过滤配置项，隐藏由专用组件管理的配置键
  const activeItems =
    activeCategory === 'ai_model'
      ? rawActiveItems.filter((item) => {
        // 通道模式激活时：隐藏通道管理的键（协议、密钥、模型等）
        if (hasConfiguredChannels && LLM_CHANNEL_KEY_RE.test(item.key)) {
          return false;
        }
        // 通道模式激活且无 LiteLLM 配置时：隐藏旧版供应商专属 LLM 键
        if (hasConfiguredChannels && !hasLitellmConfig && AI_MODEL_HIDDEN_KEYS.has(item.key)) {
          return false;
        }
        return true;
      })
      : activeCategory === 'system'
        // 系统分类：隐藏认证开关和调度器键（由专用组件展示）
        ? rawActiveItems.filter((item) => !SYSTEM_HIDDEN_KEYS.has(item.key))
      : activeCategory === 'data_source'
        // 数据源分类：隐藏 AlphaSift 键（由专用卡片展示）
        ? rawActiveItems.filter((item) => !DATA_SOURCE_HIDDEN_KEYS.has(item.key))
      : activeCategory === 'agent'
        // Agent 分类：隐藏 AGENT_GENERATION_BACKEND（由状态面板展示）
        ? rawActiveItems.filter((item) => !AGENT_HIDDEN_KEYS.has(item.key))
      : rawActiveItems;
  /** AI 模型分类下的 Prompt 缓存高级设置项（折叠展示） */
  const promptCacheAdvancedItems = activeCategory === 'ai_model'
    ? activeItems.filter(isPromptCacheAdvancedSetting)
    : [];
  /** 当前分类下可见的配置项（排除 Prompt 缓存高级设置） */
  const visibleActiveItems = activeCategory === 'ai_model'
    ? activeItems.filter((item) => !isPromptCacheAdvancedSetting(item))
    : activeItems;
  /** 当前分类是否有配置项可展示 */
  const hasActiveConfigItems = visibleActiveItems.length > 0 || promptCacheAdvancedItems.length > 0;
  /** 是否允许配置备份（桌面端或已启用认证） */
  const isEnvBackupAllowed = isDesktopRuntime || authEnabled;
  /** 配置备份按钮是否禁用 */
  const envBackupActionDisabled = isLoading || isSaving || isExportingEnv || isImportingEnv || !isEnvBackupAllowed;

  /**
   * 导出环境配置备份
   * 调用 API 获取配置内容，生成 Blob 并触发浏览器下载
   */
  const downloadEnvBackup = async () => {
    setEnvBackupActionError(null);
    setEnvBackupActionSuccess('');
    setIsExportingEnv(true);
    try {
      // 调用 API 获取环境配置内容
      const payload = await systemConfigApi.exportEnv();
      // 将配置内容包装为 Blob 对象，用于浏览器下载
      const blob = new Blob([payload.content], { type: 'text/plain;charset=utf-8' });
      // 创建临时下载链接并触发下载
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = formatEnvBackupFilename(isDesktopRuntime);
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      // 释放 Blob URL 资源
      URL.revokeObjectURL(url);
      setEnvBackupActionSuccess(t('settings.envExported'));
    } catch (error: unknown) {
      setEnvBackupActionError(getParsedApiError(error));
    } finally {
      setIsExportingEnv(false);
    }
  };

  /**
   * 开始导入环境配置
   * 如果有未保存的更改，先弹出确认对话框；否则直接触发文件选择
   */
  const beginEnvBackupImport = () => {
    setEnvBackupActionError(null);
    setEnvBackupActionSuccess('');
    if (hasDirty) {
      setShowImportConfirm(true);
      return;
    }
    envBackupImportRef.current?.click();
  };

  /**
   * 处理环境配置文件导入
   * 读取文件内容，调用导入 API，成功后重新加载配置并刷新初始化状态
   * 如果导入的配置包含调度器设置，触发调度器状态刷新
   * @param event - 文件输入变更事件
   */
  const handleEnvBackupImportFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    setShowImportConfirm(false);
    if (!file) {
      return;
    }

    setEnvBackupActionError(null);
    setEnvBackupActionSuccess('');
    setIsImportingEnv(true);
    try {
      // 读取文件文本内容
      const content = await file.text();
      // 调用导入 API，传入当前配置版本号并要求服务端立即重载
      const importResult = await systemConfigApi.importEnv({
        configVersion,
        content,
        reloadNow: true,
      });
      // 重新加载配置以获取导入后的最新配置项
      const reloaded = await load();
      if (!reloaded) {
        setEnvBackupActionError(createParsedApiError({
          title: t('settings.envImportedRefreshFailedTitle'),
          message: t('settings.envImportedRefreshFailedMessage'),
          rawMessage: t('settings.envImportedRefreshFailedRaw'),
          category: 'http_error',
        }));
        return;
      }
      if (importResult.updatedKeys.some((key) => SCHEDULER_SETTING_KEYS.has(key))) {
        setSchedulerStatusRefreshToken((current) => current + 1);
      }
      notifySystemConfigChanged();
      void refreshSetupStatus();
      setEnvBackupActionSuccess(t('settings.envImported'));
    } catch (error: unknown) {
      setEnvBackupActionError(getParsedApiError(error));
    } finally {
      setIsImportingEnv(false);
    }
  };

  /**
   * 检查桌面端更新
   * 调用桌面端运行时 API 检查更新，更新状态展示
   */
  const handleDesktopUpdateCheck = async () => {
    if (!desktopRuntimeApi?.checkForUpdates) {
      return;
    }

    setIsCheckingDesktopUpdate(true);
    setDesktopUpdateState((current) => ({
      ...(current || {}),
      status: 'checking',
      message: t('settings.desktopUpdateCheckingMessage'),
    }));

    try {
      const state = await desktopRuntimeApi.checkForUpdates();
      setDesktopUpdateState(normalizeDesktopUpdateState(state));
    } catch (error: unknown) {
      setDesktopUpdateState({
        status: 'error',
        message: error instanceof Error ? error.message : t('settings.desktopUpdateErrorMessage'),
      });
    } finally {
      setIsCheckingDesktopUpdate(false);
    }
  };

  /**
   * 更新 AlphaSift 启用状态
   * - 启用：调用 alphasiftApi.enable() 并刷新配置
   * - 禁用：直接更新 ALPHASIFT_ENABLED 为 false 并通知配置变更
   * @param nextEnabled - 目标启用状态
   */
  const updateAlphaSiftEnabled = async (nextEnabled: boolean) => {
    setAlphaSiftActionError(null);
    setAlphaSiftActionSuccess('');
    setIsUpdatingAlphaSift(true);
    try {
      if (nextEnabled) {
        // 启用 AlphaSift：调用专用 API 并刷新配置
        await alphasiftApi.enable();
        await refreshAfterExternalSave(['ALPHASIFT_ENABLED']);
        setAlphaSiftActionSuccess(t('settings.enabledAlphaSiftSuccess'));
        return;
      }

      // 禁用 AlphaSift：直接更新配置为 false 并通知配置变更
      await systemConfigApi.update({
        configVersion,
        maskToken,
        reloadNow: true,
        items: [{ key: 'ALPHASIFT_ENABLED', value: 'false' }],
      });
      notifyAlphaSiftConfigChanged();
      await refreshAfterExternalSave(['ALPHASIFT_ENABLED']);
      setAlphaSiftActionSuccess(t('settings.disabledAlphaSiftSuccess'));
    } catch (error: unknown) {
      setAlphaSiftActionError(getParsedApiError(error));
      await refreshAfterExternalSave(['ALPHASIFT_ENABLED']);
    } finally {
      setIsUpdatingAlphaSift(false);
    }
  };

  /**
   * 保存配置
   * 合并草稿变更和调度器同步项，调用 save 保存
   * 保存成功后：通知配置变更、刷新调度器状态（如涉及）、刷新初始化状态
   * 如果涉及 AlphaSift 变更，同步启用/禁用 AlphaSift 服务
   */
  const handleSaveConfig = async () => {
    const changedItems = getChangedItems();
    // 检测调度器 UI 开关与运行时状态是否存在差异且未在草稿中体现
    // 若存在差异，需要额外同步 SCHEDULE_ENABLED 配置项
    const syncRuntimeSchedulerState =
      schedulerOverrideFromUi !== null
      && schedulerRuntimeEnabled !== null
      && schedulerOverrideFromUi !== schedulerRuntimeEnabled
      && !changedItems.some((item) => item.key === 'SCHEDULE_ENABLED');
    // 构造调度器同步配置项（仅在需要同步时生成）
    const schedulerSyncItem: SystemConfigUpdateItem[] = syncRuntimeSchedulerState
      ? [{ key: 'SCHEDULE_ENABLED', value: schedulerOverrideFromUi ? 'true' : 'false' }]
      : [];
    // 合并草稿变更和调度器同步项，作为最终保存的配置项列表
    const changedItemsToSave = [...changedItems, ...schedulerSyncItem];
    // 检测是否包含 AlphaSift 启用状态变更
    const changedAlphaSiftItem = changedItems.find((item) => item.key === 'ALPHASIFT_ENABLED');
    // 检测是否包含调度器相关配置变更
    const changedSchedulerSettings = changedItemsToSave.some((item) => SCHEDULER_SETTING_KEYS.has(item.key));
    // 调用保存接口
    const result = await save(changedItemsToSave);
    if (!result.success) {
      return;
    }
    // 保存成功后：通知配置变更、刷新调度器状态和初始化状态
    notifySystemConfigChanged();
    if (changedSchedulerSettings) {
      setSchedulerStatusRefreshToken((current) => current + 1);
    }
    void refreshSetupStatus();
    // 无 AlphaSift 变更则结束
    if (!changedAlphaSiftItem) {
      return;
    }

    setAlphaSiftActionError(null);
    setAlphaSiftActionSuccess('');
    try {
      const isAlphaSiftEnabled = changedAlphaSiftItem.value.trim().toLowerCase() === 'true';
      if (isAlphaSiftEnabled) {
        await alphasiftApi.enable();
        await refreshAfterExternalSave(['ALPHASIFT_ENABLED']);
        setAlphaSiftActionSuccess(t('settings.enabledAlphaSiftSuccess'));
        return;
      }

      notifyAlphaSiftConfigChanged();
      setAlphaSiftActionSuccess(t('settings.disabledAlphaSiftSuccess'));
    } catch (error: unknown) {
      setAlphaSiftActionError(getParsedApiError(error));
      await refreshAfterExternalSave(['ALPHASIFT_ENABLED']);
    }
  };

  /** 打开桌面端发布页面（跳转到浏览器查看 Release） */
  const openDesktopReleasePage = async () => {
    if (!desktopRuntimeApi?.openReleasePage) {
      return;
    }

    await desktopRuntimeApi.openReleasePage(desktopUpdateState?.releaseUrl);
  };

  /** 安装已下载的桌面端更新 */
  const installDesktopUpdate = async () => {
    if (!desktopRuntimeApi?.installDownloadedUpdate) {
      setDesktopUpdateState((current) => ({
        ...(current || {}),
        status: 'error',
        message: t('settings.desktopManualUnsupported'),
      }));
      return;
    }

    try {
      setDesktopUpdateState((current) => ({
        ...(current || {}),
        status: 'installing',
        message: t('settings.desktopUpdateInstallingMessage'),
      }));
      await desktopRuntimeApi.installDownloadedUpdate();
    } catch (error: unknown) {
      setDesktopUpdateState((current) => ({
        ...(current || {}),
        status: 'error',
        message: error instanceof Error ? error.message : t('settings.desktopManualUnsupported'),
      }));
    }
  };

  /**
   * 运行首次配置冒烟测试
   * 使用首只股票代码发起简报类型的异步分析任务
   * 验证系统配置是否可正常完成分析流程
   */
  const handleRunSetupSmoke = async () => {
    setSetupSmokeError(null);
    setSetupSmokeSuccess('');

    if (!setupStatus?.readyForSmoke) {
      setSetupSmokeError(createParsedApiError({
        title: t('settings.setupGuideSmokeUnavailableTitle'),
        message: t('settings.setupGuideSmokeNotReady'),
        rawMessage: t('settings.setupGuideSmokeNotReady'),
        category: 'missing_params',
      }));
      return;
    }

    if (!firstSetupStockCode) {
      setSetupSmokeError(createParsedApiError({
        title: t('settings.setupGuideSmokeUnavailableTitle'),
        message: t('settings.setupGuideSmokeNeedsStock'),
        rawMessage: t('settings.setupGuideSmokeNeedsStock'),
        category: 'missing_params',
      }));
      return;
    }

    setIsRunningSetupSmoke(true);
    try {
      // 使用首只股票发起简报类型的异步分析任务，验证系统配置是否正常
      const result = await analysisApi.analyzeAsync({
        stockCode: firstSetupStockCode,
        reportType: 'brief',
        asyncMode: true,
        notify: false,
        originalQuery: firstSetupStockCode,
        selectionSource: 'manual',
      });
      // 从响应中提取任务 ID（兼容单任务和批量任务两种响应格式）
      const taskId = 'taskId' in result ? result.taskId : result.accepted?.[0]?.taskId;
      setSetupSmokeSuccess(
        taskId
          ? t('settings.setupGuideSmokeAcceptedWithTask', { stock: firstSetupStockCode, taskId })
          : t('settings.setupGuideSmokeAccepted', { stock: firstSetupStockCode }),
      );
      void refreshSetupStatus();
    } catch (error: unknown) {
      setSetupSmokeError(getParsedApiError(error));
    } finally {
      setIsRunningSetupSmoke(false);
    }
  };

  /** 桌面端更新通知信息（根据状态映射） */
  const desktopUpdateNotice = getDesktopUpdateNotice(desktopUpdateState, t);
  /** 是否需要为当前分类的配置面板添加错误边界（通知和 Agent 分类） */
  const shouldGuardActiveConfigPanel = activeCategory === 'notification' || activeCategory === 'agent';
  /** 错误边界的标题（根据分类选择） */
  const activeConfigPanelErrorTitle = activeCategory === 'agent' ? t('settings.agentSettings') : t('settings.notificationSettings');
  /** 错误边界的诊断提示文案（桌面端/Web 环境区分） */
  const settingsPanelDiagnosticHint = isDesktopRuntime
    ? uiLanguage === 'en'
      ? <>Check and provide the desktop log <code>desktop.log</code>, plus the release version, Windows version, and trigger path.</>
      : <>请查看并提供桌面端日志 <code>desktop.log</code>，同时补充 release 版本、Windows 版本和触发入口。</>
    : t('settings.diagnosticHintWeb');
  /** 当前分类的标题 */
  const activeCategoryTitle = getCategoryTitle(activeCategory as SystemConfigCategory, t('settings.activePanelTitle'), uiLanguage);
  /** 当前分类的描述 */
  const activeCategoryDescription = getCategoryDescription(activeCategory as SystemConfigCategory, '', uiLanguage);
  /** 当前选中的 Agent 后端 */
  const selectedAgentBackend = (rawActiveItemMap.get('AGENT_BACKEND') || 'auto').trim().toLowerCase();
  /** 当前选中的 Agent 架构 */
  const selectedAgentArch = (rawActiveItemMap.get('AGENT_ARCH') || 'single').trim().toLowerCase();
  /** Codex 后端与多 Agent 架构是否存在冲突 */
  const hasCodexArchitectureConflict = selectedAgentBackend === 'codex_app_server' && selectedAgentArch !== 'single';
  /** Codex 架构冲突的校验问题对象 */
  const codexArchitectureIssue: ConfigValidationIssue = {
    key: 'AGENT_ARCH',
    code: 'unsupported_agent_arch',
    message: t('settings.agentBackendSingleOnly'),
    severity: 'error',
    expected: 'single',
    actual: selectedAgentArch,
  };
  /** 当前分类的配置面板：展示配置项列表 + Prompt 缓存高级设置折叠区，无配置项时显示空状态 */
  const activeConfigPanel = hasActiveConfigItems ? (
    <SettingsSectionCard
      title={activeCategoryTitle}
      description={activeCategoryDescription || t('settings.activePanelDescription')}
    >
      {visibleActiveItems.length ? (
        <div className="divide-y divide-[var(--settings-border-soft)] overflow-hidden rounded-lg border border-[var(--settings-border)] bg-[var(--settings-surface)]">
          {visibleActiveItems.map((item) => {
            const fieldIssues = item.key === 'AGENT_ARCH' && hasCodexArchitectureConflict
              ? [...(issueByKey[item.key] || []), codexArchitectureIssue]
              : issueByKey[item.key] || [];
            return (
              <SettingsField
                key={item.key}
                item={item}
                value={item.value}
                disabled={isSaving}
                onChange={setDraftValue}
                issues={fieldIssues}
              />
            );
          })}
        </div>
      ) : null}
      {promptCacheAdvancedItems.length ? (
        <details className="group/prompt-cache overflow-hidden rounded-lg border border-[var(--settings-border)] bg-[var(--settings-surface)] transition-colors duration-200 hover:bg-[var(--settings-surface-hover)]">
          <summary className="flex cursor-pointer list-none items-start justify-between gap-3 px-4 py-4 [&::-webkit-details-marker]:hidden">
            <div className="min-w-0 space-y-1">
              <p className="text-sm font-semibold text-foreground">
                {t('settings.promptCacheAdvancedTitle')}
              </p>
              <p className="text-xs leading-5 text-muted-text">
                {t('settings.promptCacheAdvancedDescription')}
              </p>
            </div>
            <ChevronDown className="mt-0.5 h-4 w-4 shrink-0 text-muted-text transition-transform group-open/prompt-cache:rotate-180" aria-hidden="true" />
          </summary>
          <div className="divide-y divide-[var(--settings-border-soft)] border-t border-[var(--settings-border-soft)]">
            {promptCacheAdvancedItems.map((item) => (
              <SettingsField
                key={item.key}
                item={item}
                value={item.value}
                disabled={isSaving}
                onChange={setDraftValue}
                issues={issueByKey[item.key] || []}
              />
            ))}
          </div>
        </details>
      ) : null}
    </SettingsSectionCard>
  ) : (
    <EmptyState
      title={t('settings.currentCategoryEmptyTitle')}
      description={t('settings.currentCategoryEmptyDescription')}
      className="settings-surface-panel settings-border-strong border-none bg-transparent shadow-none"
    />
  );

  return (
    <div className="settings-page min-h-full px-4 pb-6 pt-4 md:px-6">
      {/* ===== 页面头部：描述 + 重置/保存按钮（页面标题已由顶部 header 展示）===== */}
      <div className="mb-4 rounded-lg border settings-border bg-card/90 px-4 py-4 shadow-soft-card backdrop-blur-sm">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div className="min-w-0">
            <p className="max-w-3xl text-xs leading-5 text-muted-text sm:text-sm sm:leading-6">
              {t('settings.pageDescription')}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant="settings-secondary"
              size="sm"
              className="px-2.5"
              onClick={resetDraft}
              disabled={isLoading || isSaving}
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              {t('settings.reset')}
            </Button>
            <Button
              type="button"
              variant="settings-primary"
              size="sm"
              className="px-2.5"
              onClick={() => void handleSaveConfig()}
              disabled={!effectiveHasDirty || isSaving || isLoading}
              isLoading={isSaving}
              loadingText={t('settings.saving')}
            >
              <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
              {isSaving
                ? t('settings.saving')
                : effectiveDirtyCount
                  ? t('settings.saveConfigWithCount', { count: effectiveDirtyCount })
                  : t('settings.saveConfig')}
            </Button>
          </div>
        </div>

        {saveError ? (
          <InlineTipCard
            variant="danger"
            className="mt-3"
            error={saveError}
            actionLabel={retryAction === 'save' ? t('settings.saveRetry') : undefined}
            onAction={retryAction === 'save' ? () => void retry() : undefined}
          />
        ) : null}
      </div>

      {/* ===== 加载错误提示区 ===== */}
      {loadError ? (
        <InlineTipCard
          variant="danger"
          error={loadError}
          actionLabel={retryAction === 'load' ? t('common.retry') : t('settings.reload')}
          onAction={() => void retry()}
          className="mb-4"
        />
      ) : null}

      {/* ===== 主内容区：加载中 / 分类导航 + 配置面板 ===== */}
      {isLoading ? (
        <SettingsLoading />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[260px_minmax(0,1fr)]">
          {/* ===== 左侧：配置分类导航 ===== */}
          <aside className="lg:sticky lg:top-4 lg:self-start">
            <SettingsCategoryNav
              categories={categories}
              itemsByCategory={itemsByCategory}
              activeCategory={activeCategory}
              onSelect={setActiveCategory}
            />
          </aside>

          {/* ===== 右侧：配置面板区 ===== */}
          <section className="space-y-4">
            {/* ===== 首次运行引导卡片（仅基础分类） ===== */}
            {shouldShowFirstRunSetup ? (
              <FirstRunSetupCard
                status={setupStatus}
                isLoading={isRefreshingSetupStatus}
                error={setupStatusError}
                firstStockCode={firstSetupStockCode}
                isSaving={isSaving}
                isRunningSmoke={isRunningSetupSmoke}
                smokeError={setupSmokeError}
                smokeSuccess={setupSmokeSuccess}
                onRefresh={refreshSetupStatus}
                onSelectCategory={setActiveCategory}
                onRunSmoke={handleRunSetupSmoke}
                listSeparator={uiLanguage === 'en' ? ', ' : '、'}
                t={t}
              />
            ) : null}
            {/* ===== AlphaSift 设置卡片（仅数据源分类） ===== */}
            {shouldShowAlphaSiftSettings ? (
              <SettingsSectionCard
                title={t('settings.alphaSift')}
                description={t('settings.alphaSiftDescription')}
              >
                <div className="flex flex-col gap-4 rounded-2xl border settings-border bg-background/35 px-4 py-4 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="text-sm font-semibold text-foreground">
                      {alphasiftEnabled ? t('settings.alphaSiftEnabled') : t('settings.alphaSiftDisabled')}
                    </p>
                    <p className="mt-1 text-xs leading-6 text-muted-text">
                      {t('settings.alphaSiftSummary')}
                    </p>
                    <p className="mt-2 text-xs leading-6 text-amber-700 dark:text-amber-300">
                      {t('settings.alphaSiftRisk')}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Button
                      type="button"
                      variant="settings-secondary"
                      onClick={() => setActiveCategory('data_source')}
                    >
                      {t('settings.viewConfigItems')}
                    </Button>
                    <Button
                      type="button"
                      variant={alphasiftEnabled ? 'settings-secondary' : 'settings-primary'}
                      onClick={() => void updateAlphaSiftEnabled(!alphasiftEnabled)}
                      disabled={isSaving || isLoading || isUpdatingAlphaSift}
                      isLoading={isUpdatingAlphaSift}
                      loadingText={alphasiftEnabled ? t('settings.disablingAlphaSift') : t('settings.enablingAlphaSift')}
                    >
                      {alphasiftEnabled ? t('settings.disableAlphaSift') : t('settings.enableAlphaSift')}
                    </Button>
                  </div>
                </div>
                {alphaSiftActionError ? (
                  <div className="mt-3">
                    <InlineTipCard variant="danger" error={alphaSiftActionError} />
                  </div>
                ) : null}
                {!alphaSiftActionError && alphaSiftActionSuccess ? (
                  <div className="mt-3">
                    <SettingsAlert title={t('settings.actionSuccess')} message={alphaSiftActionSuccess} variant="success" />
                  </div>
                ) : null}
              </SettingsSectionCard>
            ) : null}
            {/* ===== 认证设置卡片（仅系统分类） ===== */}
            {activeCategory === 'system' ? <AuthSettingsCard /> : null}
            {/* ===== 调度器设置卡片（仅系统分类） ===== */}
            {activeCategory === 'system' ? (
              <SchedulerSettingsCard
                items={rawActiveItems}
                disabled={isSaving || isLoading}
                issueByKey={issueByKey}
                statusRefreshToken={schedulerStatusRefreshToken}
                onSchedulerStateChange={handleSchedulerRuntimeStateChange}
                onChange={setDraftValue}
                t={t}
                language={uiLanguage}
              />
            ) : null}
            {/* ===== 版本信息卡片（仅系统分类） ===== */}
            {activeCategory === 'system' ? (
              <SettingsSectionCard
                title={t('settings.versionInfo')}
                description={t('settings.versionInfoDescription')}
              >
                <div
                  className={`grid grid-cols-1 gap-3 ${shouldShowDesktopVersionCard ? 'md:grid-cols-4' : 'md:grid-cols-3'}`}
                >
                  <div className="rounded-2xl border settings-border bg-background/40 px-4 py-3">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-text">
                      {t('settings.versionWebui')}
                    </p>
                    <p className="mt-2 break-all font-mono text-sm text-foreground">
                      {WEB_BUILD_INFO.version}
                    </p>
                  </div>
                  <div className="rounded-2xl border settings-border bg-background/40 px-4 py-3">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-text">
                      {t('settings.versionRevision')}
                    </p>
                    <p className="mt-2 break-all font-mono text-sm text-foreground">
                      {WEB_BUILD_INFO.revision}
                    </p>
                  </div>
                  <div className="rounded-2xl border settings-border bg-background/40 px-4 py-3">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-text">
                      {t('settings.versionBuildTime')}
                    </p>
                    <p className="mt-2 break-all font-mono text-sm text-foreground">
                      {WEB_BUILD_INFO.buildTime}
                    </p>
                  </div>
                  {shouldShowDesktopVersionCard ? (
                    <div className="rounded-2xl border settings-border bg-background/40 px-4 py-3">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-text">
                        {t('settings.versionDesktop')}
                      </p>
                      <p className="mt-2 break-all font-mono text-sm text-foreground">
                        {desktopAppVersion}
                      </p>
                    </div>
                  ) : null}
                </div>
                <p className="text-xs leading-6 text-muted-text">
                  {t('settings.updateBuildDescription')}
                </p>
                {canCheckDesktopUpdate ? (
                  <div className="mt-4 space-y-3 rounded-2xl border settings-border bg-background/30 px-4 py-4">
                    <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                      <div>
                        <p className="text-sm font-medium text-foreground">{t('settings.desktopUpdate')}</p>
                        <p className="text-xs leading-6 text-muted-text">
                          {t('settings.desktopUpdateDescription')}
                        </p>
                      </div>
                      <Button
                        type="button"
                        variant="settings-secondary"
                        onClick={() => void handleDesktopUpdateCheck()}
                        disabled={isCheckingDesktopUpdate}
                        isLoading={isCheckingDesktopUpdate}
                        loadingText={t('settings.checkingDesktopUpdate')}
                      >
                        {t('settings.checkDesktopUpdate')}
                      </Button>
                    </div>
                    {desktopUpdateNotice ? (
                      <SettingsAlert
                        title={desktopUpdateNotice.title}
                        message={desktopUpdateNotice.message}
                        variant={desktopUpdateNotice.variant}
                        actionLabel={desktopUpdateNotice.actionLabel}
                        onAction={desktopUpdateNotice.actionLabel ? () => {
                          if (desktopUpdateNotice.actionKind === 'install') {
                            void installDesktopUpdate();
                            return;
                          }
                          void openDesktopReleasePage();
                        } : undefined}
                      />
                    ) : (
                      <p className="text-xs leading-6 text-muted-text">
                        {t('settings.desktopCurrentNoStatus')}
                      </p>
                    )}
                  </div>
                ) : null}
                {WEB_BUILD_INFO.isFallbackVersion ? (
                  <p className="text-xs leading-6 text-amber-700 dark:text-amber-300">
                    {t('settings.fallbackVersionWarning')}
                  </p>
                ) : null}
              </SettingsSectionCard>
            ) : null}
            {/* ===== 配置备份卡片（仅系统分类） ===== */}
            {activeCategory === 'system' ? (
              <SettingsSectionCard
                title={t('settings.configBackup')}
                description={t('settings.configBackupDescription')}
              >
                <div className="space-y-4">
                  {!isEnvBackupAllowed ? (
                    <p className="text-xs leading-6 text-amber-700 dark:text-amber-300">
                      {t('settings.disabledAuthBackupWarning')}
                    </p>
                  ) : null}
                  <div className="flex flex-wrap items-center gap-3">
                    <Button
                      type="button"
                      variant="settings-secondary"
                      onClick={() => void downloadEnvBackup()}
                      disabled={envBackupActionDisabled}
                      isLoading={isExportingEnv}
                      loadingText={t('settings.exportingEnv')}
                    >
                      {t('settings.exportEnv')}
                    </Button>
                    <Button
                      type="button"
                      variant="settings-primary"
                      onClick={beginEnvBackupImport}
                      disabled={envBackupActionDisabled}
                      isLoading={isImportingEnv}
                      loadingText={t('settings.importingEnv')}
                    >
                      {t('settings.importEnv')}
                    </Button>
                    <input
                      ref={envBackupImportRef}
                      type="file"
                      accept=".env,.txt"
                      className="hidden"
                      onChange={(event) => {
                        void handleEnvBackupImportFile(event);
                      }}
                    />
                  </div>
                  <p className="text-xs leading-6 text-muted-text">
                    {t('settings.envExportNote')}
                  </p>
                  <p className="text-xs leading-6 text-muted-text">
                    {t('settings.envDockerNote')}
                  </p>
                  {envBackupActionError ? (
                    <InlineTipCard
                      variant="danger"
                      error={envBackupActionError}
                      actionLabel={envBackupActionError.status === 409 ? t('settings.reload') : undefined}
                      onAction={envBackupActionError.status === 409 ? () => void load() : undefined}
                    />
                  ) : null}
                  {!envBackupActionError && envBackupActionSuccess ? (
                    <SettingsAlert title={t('settings.actionSuccess')} message={envBackupActionSuccess} variant="success" />
                  ) : null}
                </div>
              </SettingsSectionCard>
            ) : null}
            {/* ===== 智能导入卡片（仅基础分类） ===== */}
            {activeCategory === 'base' ? (
              <SettingsSectionCard
                title={t('settings.intelligentImport')}
                description={t('settings.intelligentImportDescription')}
              >
                <IntelligentImport
                  stockListValue={
                    (activeItems.find((i) => i.key === 'STOCK_LIST')?.value as string) ?? ''
                  }
                  configVersion={configVersion}
                  maskToken={maskToken}
                  onMerged={async () => {
                    await refreshAfterExternalSave(['STOCK_LIST']);
                    void refreshSetupStatus();
                  }}
                  disabled={isSaving || isLoading}
                />
              </SettingsSectionCard>
            ) : null}
            {/* ===== LLM 通道与生成后端状态卡片（仅 AI 模型分类） ===== */}
            {activeCategory === 'ai_model' ? (
              <SettingsSectionCard
                title={t('settings.llmAccess')}
                description={t('settings.llmAccessDescription')}
              >
                <GenerationBackendStatusPanel
                  items={generationBackendDraftItems}
                  maskToken={maskToken}
                  disabled={isSaving || isLoading}
                />
                <LLMChannelEditor
                  items={rawActiveItems}
                  configVersion={configVersion}
                  maskToken={maskToken}
                  onDraftItemsChange={handleLlmChannelDraftItemsChange}
                  onSaved={async (updatedItems) => {
                    setLlmChannelDraftItems([]);
                    await refreshAfterExternalSave(updatedItems.map((item) => item.key));
                    void refreshSetupStatus();
                  }}
                  disabled={isSaving || isLoading}
                />
              </SettingsSectionCard>
            ) : null}
            {/* ===== 修改密码卡片（仅系统分类且允许修改密码） ===== */}
            {activeCategory === 'system' && passwordChangeable ? (
              <ChangePasswordCard />
            ) : null}
            {/* ===== 通知测试面板（仅通知分类，带错误边界保护） ===== */}
            {activeCategory === 'notification' ? (
              <SettingsPanelErrorBoundary
                title={t('settings.notificationTest')}
                resetKey={`notification-test:${configVersion}`}
                diagnosticHint={settingsPanelDiagnosticHint}
              >
                <NotificationTestPanel
                  items={rawActiveItems.map((item) => ({ key: item.key, value: String(item.value ?? '') }))}
                  maskToken={maskToken}
                  disabled={isSaving || isLoading}
                />
              </SettingsPanelErrorBoundary>
            ) : null}
            {/* ===== Agent 后端状态面板（仅 Agent 分类，带错误边界保护） ===== */}
            {activeCategory === 'agent' ? (
              <SettingsPanelErrorBoundary
                title={t('settings.agentBackendStatus')}
                resetKey={`agent-backend:${configVersion}`}
                diagnosticHint={settingsPanelDiagnosticHint}
              >
                <SettingsSectionCard
                  title={t('settings.agentBackendSectionTitle')}
                  description={t('settings.agentBackendSectionDescription')}
                >
                  <AgentBackendStatusPanel
                    items={agentBackendDraftItems}
                    maskToken={maskToken}
                    selectedBackend={selectedAgentBackend}
                    agentArch={selectedAgentArch}
                    disabled={isSaving || isLoading}
                    onUseSingleAgent={() => setDraftValue('AGENT_ARCH', 'single')}
                    onEnableAgentMode={() => setDraftValue('AGENT_MODE', 'true')}
                  />
                </SettingsSectionCard>
              </SettingsPanelErrorBoundary>
            ) : null}
            {/* ===== 当前分类配置面板（通知/Agent 分类带错误边界保护） ===== */}
            {shouldGuardActiveConfigPanel && hasActiveConfigItems ? (
              <SettingsPanelErrorBoundary
                title={activeConfigPanelErrorTitle}
                resetKey={`${activeCategory}:${configVersion}`}
                diagnosticHint={settingsPanelDiagnosticHint}
              >
                {activeConfigPanel}
              </SettingsPanelErrorBoundary>
            ) : activeConfigPanel}
          </section>
        </div>
      )}

      {/* ===== 操作结果 Toast 提示 ===== */}
      {toast ? (
        <div className="fixed bottom-5 right-5 z-50 w-[320px] max-w-[calc(100vw-24px)]">
          {toast.type === 'success'
            ? (
                <SettingsAlert
                  title={t('settings.actionSuccess')}
                  message={toast.message}
                  variant="success"
                  presentation="toast"
                />
              )
            : <InlineTipCard variant="danger" error={toast.error} />}
        </div>
      ) : null}
      <ConfirmDialog
        isOpen={showImportConfirm}
        title={t('settings.importConfirmTitle')}
        message={t('settings.importConfirmMessage')}
        confirmText={t('settings.importConfirmContinue')}
        cancelText={t('common.cancel')}
        onConfirm={() => {
          setShowImportConfirm(false);
          envBackupImportRef.current?.click();
        }}
        onCancel={() => {
          setShowImportConfirm(false);
        }}
      />
    </div>
  );
};

export default SettingsPage;
