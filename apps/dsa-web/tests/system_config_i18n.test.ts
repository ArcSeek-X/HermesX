/**
 * 文件介绍（system_config_i18n.test.ts）
 * ============================================================
 * 本文件是「系统配置（system config）国际化（i18n）」的综合契约测试，覆盖
 * 配置项的中文标题/描述映射、下拉选项的中文标签、帮助文案（help content）
 * 的隐私边界与措辞、以及生成后端状态面板的双语文案。
 *
 * 功能概括：
 * 1. 校验一批「已知存在的配置 key」都具备中文标题与中文描述（不得原样回退为 key）；
 * 2. 针对 SearXNG、LLM 用量 HMAC 等具体字段，校验中文文案的措辞与隐私提示；
 * 3. 覆盖大量下拉选项的本地化标签（报告类型、语言、严重级别、日志级别、Agent 模式等）；
 * 4. 校验帮助文案对「持久化边界」的描述准确（只影响新记录，不改动旧记录、不关闭当次构建）；
 * 5. 校验「生成后端」相关文案使用面向用户的业务语言（个股分析、问股助手等），而非实现术语；
 * 6. 校验生成后端状态面板的双语文案（主/备后端、JSON 冒烟测试等）；
 * 7. 反向校验：未真实存在的「占位」DecisionSignal 配置不得伪造翻译（应原样回退）。
 */

// 引入 Vitest 测试原语
import { describe, expect, it } from 'vitest';
// 引入全局 UI 文案资源（中英双语键值对）
import { UI_TEXT } from '../src/i18n/uiText';
// 引入设置页帮助文案获取函数
import { getSettingsHelpContent } from '../src/locales/settingsHelp';
// 引入配置项国际化辅助函数：标题/描述/选项标签（中文）
import { getFieldDescriptionZh, getFieldOptionLabelZh, getFieldTitleZh } from '../src/utils/systemConfigI18n';

// 需要被本地化覆盖的「已知配置 key」清单（来自系统配置各模块）
// 涵盖：Tickflow、行情、PYTDX、BIAS、生成后端、LLM、各通知渠道、
// 报告、调度、WebUI、Agent 等几乎所有配置域
const requiredLocalizedKeys = [
  'TICKFLOW_API_KEY',
  'TICKFLOW_PRIORITY',
  'TICKFLOW_KLINE_ADJUST',
  'TICKFLOW_BATCH_DAILY_ENABLED',
  'TICKFLOW_BATCH_SIZE',
  'STOCK_INDEX_REMOTE_UPDATE_ENABLED',
  'SEARXNG_BASE_URLS',
  'ENABLE_REALTIME_QUOTE',
  'ENABLE_CHIP_DISTRIBUTION',
  'PYTDX_HOST',
  'PYTDX_PORT',
  'PYTDX_SERVERS',
  'BIAS_THRESHOLD',
  'GENERATION_BACKEND',
  'GENERATION_FALLBACK_BACKEND',
  'GENERATION_BACKEND_TIMEOUT_SECONDS',
  'GENERATION_BACKEND_MAX_OUTPUT_BYTES',
  'GENERATION_BACKEND_MAX_CONCURRENCY',
  'LOCAL_CLI_BACKEND_MAX_CONCURRENCY',
  'LLM_PROMPT_CACHE_TELEMETRY_ENABLED',
  'LLM_PROMPT_CACHE_HINTS_ENABLED',
  'LLM_PROMPT_CACHE_DIAGNOSTICS_LEVEL',
  'LLM_USAGE_HMAC_SECRET',
  'LLM_USAGE_HMAC_KEY_VERSION',
  'TELEGRAM_BOT_TOKEN',
  'TELEGRAM_CHAT_ID',
  'TELEGRAM_MESSAGE_THREAD_ID',
  'FEISHU_STREAM_ENABLED',
  'DINGTALK_STREAM_ENABLED',
  'EMAIL_SENDER',
  'EMAIL_PASSWORD',
  'EMAIL_RECEIVERS',
  'DISCORD_WEBHOOK_URL',
  'DISCORD_BOT_TOKEN',
  'DISCORD_MAIN_CHANNEL_ID',
  'DISCORD_INTERACTIONS_PUBLIC_KEY',
  'SLACK_BOT_TOKEN',
  'SLACK_CHANNEL_ID',
  'SLACK_WEBHOOK_URL',
  'PUSHPLUS_TOPIC',
  'PUSHOVER_USER_KEY',
  'PUSHOVER_API_TOKEN',
  'SERVERCHAN3_SENDKEY',
  'ASTRBOT_URL',
  'ASTRBOT_TOKEN',
  'CUSTOM_WEBHOOK_BEARER_TOKEN',
  'WEBHOOK_VERIFY_SSL',
  'SINGLE_STOCK_NOTIFY',
  'REPORT_TYPE',
  'REPORT_LANGUAGE',
  'REPORT_TEMPLATES_DIR',
  'REPORT_INTEGRITY_ENABLED',
  'REPORT_RENDERER_ENABLED',
  'REPORT_INTEGRITY_RETRY',
  'REPORT_HISTORY_COMPARE_N',
  'MERGE_EMAIL_NOTIFICATION',
  'NOTIFICATION_REPORT_CHANNELS',
  'NOTIFICATION_ALERT_CHANNELS',
  'NOTIFICATION_SYSTEM_ERROR_CHANNELS',
  'NOTIFICATION_DEDUP_TTL_SECONDS',
  'NOTIFICATION_COOLDOWN_SECONDS',
  'NOTIFICATION_QUIET_HOURS',
  'NOTIFICATION_TIMEZONE',
  'NOTIFICATION_MIN_SEVERITY',
  'NOTIFICATION_DAILY_DIGEST_ENABLED',
  'SCHEDULE_ENABLED',
  'SCHEDULE_RUN_IMMEDIATELY',
  'TRADING_DAY_CHECK_ENABLED',
  'WEBUI_HOST',
  'LOG_DIR',
  'WEBUI_ENABLED',
  'WEBUI_AUTO_BUILD',
  'ADMIN_AUTH_ENABLED',
  'TRUST_X_FORWARDED_FOR',
  'RUN_IMMEDIATELY',
  'MARKET_REVIEW_ENABLED',
  'DAILY_MARKET_CONTEXT_ENABLED',
  'MARKET_REVIEW_REGION',
  'ANALYSIS_DELAY',
  'SAVE_CONTEXT_SNAPSHOT',
  'DEBUG',
  'AGENT_GENERATION_BACKEND',
  'AGENT_NL_ROUTING',
  'AGENT_DEEP_RESEARCH_BUDGET',
  'AGENT_DEEP_RESEARCH_TIMEOUT',
  'AGENT_EVENT_MONITOR_ENABLED',
  'AGENT_EVENT_MONITOR_INTERVAL_MINUTES',
  'AGENT_EVENT_ALERT_RULES_JSON',
] as const;

// 测试套件：系统配置必需 key 的本地化覆盖
describe('systemConfigI18n required key coverage', () => {
  // 用例：为每个已知 key 提供中文标题与中文描述（不得原样回退为 key/兜底文案）
  it('provides zh title and description mapping for known missing keys', () => {
    requiredLocalizedKeys.forEach((key) => {
      // 标题不得等于 key 本身（说明已存在中文映射）
      expect(getFieldTitleZh(key, key)).not.toBe(key);
      // 描述不得等于兜底文案（说明已存在中文描述）
      expect(getFieldDescriptionZh(key, 'schema fallback description')).not.toBe('schema fallback description');
    });
  });

  // 用例：SearXNG 地址字段应使用中文主标题而非英文直译
  it('uses a Chinese primary title for SearXNG base URLs', () => {
    const title = getFieldTitleZh('SEARXNG_BASE_URLS', 'SEARXNG_BASE_URLS');

    expect(title).toBe('SearXNG 自建实例地址');
    expect(title).not.toBe('SearXNG Base URLs');
  });

  // 用例：LLM 用量 HMAC 密钥的帮助文案需说明隐私边界（中英文均含 HMAC 与勿泄露提示）
  it('documents LLM usage HMAC privacy boundaries', () => {
    const zh = getSettingsHelpContent('settings.ai_model.LLM_USAGE_HMAC_SECRET', undefined, 'zh-CN');
    const en = getSettingsHelpContent('settings.ai_model.LLM_USAGE_HMAC_SECRET', undefined, 'en');

    expect(zh?.summary).toContain('HMAC');
    expect(zh?.notes?.join(' ')).toContain('不要'); // 中文提示：不要泄露密钥
    expect(en?.summary).toContain('HMAC');
    expect(en?.notes?.join(' ')).toContain('Do not'); // 英文提示：Do not ...
  });
});

// 测试套件：系统配置下拉选项的标签本地化
describe('systemConfigI18n option label localization', () => {
  // 真实存在的下拉选项样例：[字段key, 选项值, 英文兜底标签, 期望中文标签]
  const realSelectOptionCases = [
    ['NEWS_STRATEGY_PROFILE', 'ultra_short', undefined, '超短线（1天）'],
    ['NEWS_STRATEGY_PROFILE', 'short', undefined, '短期（3天）'],
    ['NEWS_STRATEGY_PROFILE', 'medium', undefined, '中期（7天）'],
    ['NEWS_STRATEGY_PROFILE', 'long', undefined, '长期（30天）'],
    ['REPORT_TYPE', 'simple', undefined, '简洁'],
    ['REPORT_TYPE', 'full', undefined, '完整'],
    ['REPORT_TYPE', 'brief', undefined, '简报'],
    ['REPORT_LANGUAGE', 'zh', 'Chinese', '中文'],
    ['REPORT_LANGUAGE', 'en', 'English', '英文'],
    ['REPORT_LANGUAGE', 'ko', 'Korean', '韩文'],
    ['NOTIFICATION_MIN_SEVERITY', '', 'Not set', '未设置'],
    ['NOTIFICATION_MIN_SEVERITY', 'info', 'info', '信息'],
    ['NOTIFICATION_MIN_SEVERITY', 'warning', 'warning', '警告'],
    ['NOTIFICATION_MIN_SEVERITY', 'error', 'error', '错误'],
    ['NOTIFICATION_MIN_SEVERITY', 'critical', 'critical', '严重'],
    ['LOG_LEVEL', 'DEBUG', undefined, '调试'],
    ['LOG_LEVEL', 'INFO', undefined, '信息'],
    ['LOG_LEVEL', 'WARNING', undefined, '警告'],
    ['LOG_LEVEL', 'ERROR', undefined, '错误'],
    ['LOG_LEVEL', 'CRITICAL', undefined, '严重'],
    ['LLM_PROMPT_CACHE_DIAGNOSTICS_LEVEL', 'off', undefined, '关闭'],
    ['LLM_PROMPT_CACHE_DIAGNOSTICS_LEVEL', 'basic', undefined, '基础'],
    ['LLM_PROMPT_CACHE_DIAGNOSTICS_LEVEL', 'debug', undefined, '调试'],
    ['MARKET_REVIEW_COLOR_SCHEME', 'green_up', 'Green Up / Red Down', '绿涨红跌'],
    ['MARKET_REVIEW_COLOR_SCHEME', 'red_up', 'Red Up / Green Down', '红涨绿跌'],
    ['GENERATION_BACKEND', 'litellm', undefined, '默认模型配置'],
    ['GENERATION_FALLBACK_BACKEND', 'litellm', undefined, '默认模型配置'],
    ['AGENT_GENERATION_BACKEND', 'auto', 'Auto', '自动'],
    ['AGENT_GENERATION_BACKEND', 'litellm', undefined, '默认模型配置'],
    ['AGENT_ARCH', 'single', 'Single Agent', '单 Agent'],
    ['AGENT_ARCH', 'multi', 'Multi Agent (Orchestrator)', '多 Agent（编排）'],
    ['AGENT_ORCHESTRATOR_MODE', 'quick', 'Quick', '快速'],
    ['AGENT_ORCHESTRATOR_MODE', 'standard', 'Standard', '标准'],
    ['AGENT_ORCHESTRATOR_MODE', 'full', 'Full', '完整'],
    ['AGENT_ORCHESTRATOR_MODE', 'specialist', 'Specialist', '专家'],
    ['AGENT_SKILL_ROUTING', 'auto', 'Auto (Regime-based)', '自动（按市场状态）'],
    ['AGENT_SKILL_ROUTING', 'manual', 'Manual (Use AGENT_SKILLS)', '手动（使用 AGENT_SKILLS）'],
  ] as const;

  // 用例：校验所有真实下拉选项都被正确本地化为中文标签
  it('localizes all select options currently exposed by system config schema', () => {
    realSelectOptionCases.forEach(([key, value, fallbackLabel, expectedLabel]) => {
      const label = getFieldOptionLabelZh(key, value, fallbackLabel);

      // 中文标签应等于期望值
      expect(label).toBe(expectedLabel);
      // 不应回退为原始选项值
      expect(label).not.toBe(value);
      // 若提供了英文兜底，说明已本地化、不应等于兜底
      if (fallbackLabel) {
        expect(label).not.toBe(fallbackLabel);
      }
    });
  });

  // 用例：自由文本型配置 key（如地区列表）的选项标签应原样透传
  it('treats free-text config keys as passthrough for option labels', () => {
    expect(getFieldOptionLabelZh('MARKET_REVIEW_REGION', 'cn')).toBe('cn');
    expect(getFieldOptionLabelZh('MARKET_REVIEW_REGION', 'cn,us,jp,kr')).toBe('cn,us,jp,kr');
  });
});

// 测试套件：SAVE_CONTEXT_SNAPSHOT 帮助文案的持久化边界契约
describe('SAVE_CONTEXT_SNAPSHOT settings help contract', () => {
  // 用例：帮助文案需准确描述持久化边界——只影响新记录，不改动旧记录/不关闭当次构建
  it('describes the persistence boundary without implying old records are changed', () => {
    const help = getSettingsHelpContent('settings.system.SAVE_CONTEXT_SNAPSHOT', undefined, 'zh-CN');
    const text = [
      help?.summary,
      help?.usage,
      ...(help?.valueNotes ?? []),
      ...(help?.impact ?? []),
      ...(help?.notes ?? []),
    ].join('\n');

    // 正向断言：文案包含「新历史记录」「不关闭当次构建」「不关闭 LLM Prompt」
    expect(text).toContain('新历史记录');
    expect(text).toContain('不关闭当次 AnalysisContextPack 构建');
    expect(text).toContain('不关闭 LLM Prompt');
    // 反向断言：不得暗示「旧记录」会被改动（避免误导用户）
    expect(text).not.toContain('旧记录');
  });
});

// 测试套件：生成后端（generation backend）帮助文案契约
describe('generation backend settings help contract', () => {
  // 用例：使用面向用户的业务文案，而非实现层术语
  it('uses user-facing generation channel copy instead of implementation terms', () => {
    // 收集内联标题/描述（中文）文本
    const zhInlineText = [
      getFieldTitleZh('GENERATION_BACKEND', ''),
      getFieldDescriptionZh('GENERATION_BACKEND', ''),
      getFieldTitleZh('GENERATION_FALLBACK_BACKEND', ''),
      getFieldDescriptionZh('GENERATION_FALLBACK_BACKEND', ''),
      getFieldTitleZh('GENERATION_BACKEND_TIMEOUT_SECONDS', ''),
      getFieldDescriptionZh('GENERATION_BACKEND_TIMEOUT_SECONDS', ''),
      getFieldTitleZh('GENERATION_BACKEND_MAX_OUTPUT_BYTES', ''),
      getFieldDescriptionZh('GENERATION_BACKEND_MAX_OUTPUT_BYTES', ''),
      getFieldTitleZh('GENERATION_BACKEND_MAX_CONCURRENCY', ''),
      getFieldDescriptionZh('GENERATION_BACKEND_MAX_CONCURRENCY', ''),
      getFieldTitleZh('LOCAL_CLI_BACKEND_MAX_CONCURRENCY', ''),
      getFieldDescriptionZh('LOCAL_CLI_BACKEND_MAX_CONCURRENCY', ''),
      getFieldTitleZh('AGENT_GENERATION_BACKEND', ''),
      getFieldDescriptionZh('AGENT_GENERATION_BACKEND', ''),
    ].join('\n');

    // 获取主/备/问股生成方式的中英文帮助文案
    const zhBackend = getSettingsHelpContent('settings.ai_model.GENERATION_BACKEND', undefined, 'zh-CN');
    const enBackend = getSettingsHelpContent('settings.ai_model.GENERATION_BACKEND', undefined, 'en');
    const zhFallback = getSettingsHelpContent('settings.ai_model.GENERATION_FALLBACK_BACKEND', undefined, 'zh-CN');
    const enFallback = getSettingsHelpContent('settings.ai_model.GENERATION_FALLBACK_BACKEND', undefined, 'en');
    const zhAgent = getSettingsHelpContent('settings.agent.AGENT_GENERATION_BACKEND', undefined, 'zh-CN');
    const enAgent = getSettingsHelpContent('settings.agent.AGENT_GENERATION_BACKEND', undefined, 'en');

    // 拼接中文帮助长文本（标题/摘要/用法/备注等）
    const zhText = [
      zhBackend?.title,
      zhBackend?.summary,
      zhBackend?.usage,
      ...(zhBackend?.valueNotes ?? []),
      ...(zhBackend?.impact ?? []),
      ...(zhBackend?.notes ?? []),
      zhFallback?.title,
      zhFallback?.summary,
      zhFallback?.usage,
      ...(zhFallback?.valueNotes ?? []),
      ...(zhFallback?.impact ?? []),
      ...(zhFallback?.notes ?? []),
      zhAgent?.title,
      zhAgent?.summary,
      zhAgent?.usage,
      ...(zhAgent?.valueNotes ?? []),
      ...(zhAgent?.impact ?? []),
      ...(zhAgent?.notes ?? []),
    ].join('\n');

    // 拼接英文帮助长文本
    const enText = [
      enBackend?.title,
      enBackend?.summary,
      enBackend?.usage,
      ...(enBackend?.valueNotes ?? []),
      ...(enBackend?.impact ?? []),
      ...(enBackend?.notes ?? []),
      enFallback?.title,
      enFallback?.summary,
      enFallback?.usage,
      ...(enFallback?.valueNotes ?? []),
      ...(enFallback?.impact ?? []),
      ...(enFallback?.notes ?? []),
      enAgent?.title,
      enAgent?.summary,
      enAgent?.usage,
      ...(enAgent?.valueNotes ?? []),
      ...(enAgent?.impact ?? []),
      ...(enAgent?.notes ?? []),
    ].join('\n');

    // 中文标题断言
    expect(zhBackend?.title).toBe('分析生成方式');
    expect(zhFallback?.title).toBe('备用生成方式');
    expect(zhAgent?.title).toBe('问股生成方式');
    // 中文子字段标题断言
    expect(getFieldTitleZh('GENERATION_BACKEND_TIMEOUT_SECONDS', '')).toBe('生成超时（秒）');
    expect(getFieldTitleZh('GENERATION_BACKEND_MAX_OUTPUT_BYTES', '')).toBe('最大输出大小（字节）');
    expect(getFieldTitleZh('GENERATION_BACKEND_MAX_CONCURRENCY', '')).toBe('模型生成最大并发');
    expect(getFieldTitleZh('LOCAL_CLI_BACKEND_MAX_CONCURRENCY', '')).toBe('本地命令行最大并发');
    // 不展示内部字段 key，且 examples 为空（面向用户）
    expect(zhBackend?.showFieldKey).toBe(false);
    expect(zhFallback?.showFieldKey).toBe(false);
    expect(zhAgent?.showFieldKey).toBe(false);
    expect(zhBackend?.examples).toEqual([]);
    expect(zhFallback?.examples).toEqual([]);
    expect(zhAgent?.examples).toEqual([]);
    // 中文内联文案应体现业务场景（个股分析/问股助手/当前可用的方式）
    expect(zhInlineText).toContain('个股分析');
    expect(zhInlineText).toContain('问股助手');
    expect(zhInlineText).toContain('当前可用的方式');
    expect(zhInlineText).not.toContain('沿用当前可用的模型通道');
    // 中文帮助长文本应体现业务场景，且不包含实现术语
    expect(zhText).toContain('个股分析');
    expect(zhText).toContain('大盘复盘');
    expect(zhText).toContain('自动');
    expect(zhBackend?.usage).toContain('默认模型配置');
    expect(zhFallback?.usage).toContain('默认模型配置');
    expect(zhAgent?.usage).toContain('当前可用的方式');
    expect(zhAgent?.valueNotes).toContain('如果不确定，选择“自动”即可。');
    expect(zhText).not.toContain('优先选择当前可用');
    // 反向断言：不得出现任何实现层术语（避免暴露内部细节给用户）
    [
      'Backend',
      'backend',
      'backend-level',
      'generation backend',
      'self fallback',
      'stdout',
      'stderr',
      'contract',
      'MAX_WORKERS',
      'Router',
      'diagnostics',
      'executable',
      'coding-agent',
      'experimental/limited',
      'fail-fast',
      'LiteLLM',
    ].forEach((term) => {
      expect(zhInlineText).not.toContain(term);
      expect(zhText).not.toContain(term);
    });

    // 英文标题断言
    expect(enBackend?.title).toBe('Analysis Generation Method');
    expect(enFallback?.title).toBe('Fallback Generation Method');
    expect(enAgent?.title).toBe('Ask-Stock Generation Method');
    // 英文文案应体现业务场景
    expect(enText).toContain('stock analysis');
    expect(enText).toContain('market reviews');
    expect(enText).toContain('Auto');
    expect(enBackend?.usage).toContain('Default model settings');
    expect(enFallback?.usage).toContain('Default model settings');
    expect(enAgent?.usage).toContain('currently available method');
    expect(enAgent?.valueNotes).toContain('If you are unsure, choose Auto.');
    expect(enBackend?.notes?.join('\n')).toContain('Default model settings continue');
    expect(enBackend?.notes?.join('\n')).not.toContain('Advanced note');
    expect(enBackend?.notes?.join('\n')).not.toContain('LiteLLM');
    expect(enText).not.toContain('current available model channel');
    // 反向断言：英文也不应出现实现层术语
    expect(enText).not.toContain('unsupported_tool_calling');
    expect(enText).not.toContain('run_agent_loop');
  });
});

// 测试套件：生成后端状态面板的 i18n 契约（中英文案）
describe('generation backend status panel i18n contract', () => {
  // 用例：状态面板的中英文案保持本地化且不混用实现术语
  it('keeps the new status panel copy localized in both UI languages', () => {
    // 中文断言
    expect(UI_TEXT.zh['settings.generationBackendStatus']).toBe('生成后端状态');
    expect(UI_TEXT.zh['settings.generationBackendSmokeTest']).toBe('JSON 冒烟测试');
    expect(UI_TEXT.zh['settings.generationBackendPrimary']).toBe('主后端');
    expect(UI_TEXT.zh['settings.generationBackendFallback']).toBe('备用后端');
    expect(UI_TEXT.zh['settings.generationBackendGenerationOnly']).toBe('仅生成');
    expect(UI_TEXT.zh['settings.generationBackendStatusDescription']).toContain('快速检查');
    expect(UI_TEXT.zh['settings.generationBackendStatusDescription']).not.toContain('cheap check');
    expect(UI_TEXT.zh['settings.generationBackendSmokePassed']).not.toContain('Smoke test');

    // 英文断言
    expect(UI_TEXT.en['settings.generationBackendStatus']).toBe('Generation backend status');
    expect(UI_TEXT.en['settings.generationBackendSmokeTest']).toBe('JSON smoke test');
    expect(UI_TEXT.en['settings.generationBackendPrimary']).toBe('Primary backend');
    expect(UI_TEXT.en['settings.generationBackendFallback']).toBe('Fallback backend');
    expect(UI_TEXT.en['settings.generationBackendGenerationOnly']).toBe('Generation only');
  });
});

// 测试套件：决策信号（DecisionSignal）配置守卫
describe('decision signal settings guard', () => {
  // 用例：未真实存在的「占位」DecisionSignal 配置不得伪造翻译，必须原样回退
  it('does not add placeholder DecisionSignal setting translations without a real schema field', () => {
    // 这些 key 仅作为占位，不应在 i18n 中出现对应翻译
    const placeholderKeys = [
      'DECISION_SIGNAL_ENABLED',
      'DECISION_SIGNALS_ENABLED',
      'DECISION_SIGNAL_WRITE_ENABLED',
      'DECISION_SIGNAL_EXTRACT_ENABLED',
    ];

    placeholderKeys.forEach((key) => {
      // 标题应回退为 key 本身
      expect(getFieldTitleZh(key, key)).toBe(key);
      // 描述应回退为兜底文案
      expect(getFieldDescriptionZh(key, 'schema fallback description')).toBe('schema fallback description');
    });
  });
});
