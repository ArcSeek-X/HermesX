# -*- coding: utf-8 -*-
"""配置包：运行时配置、字段元数据与 `.env` 读写的统一入口。

职责划分（对应 ``ARCHITECTURE_TARGET.md`` 第 3、5.2 节）：

- ``settings``：运行时配置值。``Config`` 数据类、环境变量解析/归一化、
  ``setup_env()`` 加载与 ``get_config()`` 单例。
- ``env_parsers``：环境变量解析与档位归一化助手（布尔/整数/浮点、TickFlow、
  新闻窗口、Agent 上下文压缩预设），由 ``settings`` 转发导出。
- ``llm_channels``：LLM 渠道协议推断、模型 provider 前缀补全、温度解析与
  Agent 主模型/尝试顺序，由 ``settings`` 转发导出。
- ``registry``：Web 设置页字段元数据（分类、控件、校验区间、帮助文案锚点），
  是界面可见性的唯一事实源；字段声明与帮助文案分别存放在
  ``field_definitions`` 与 ``field_help``。
- ``env_file``：``.env`` 文件的原子读写与 ``ConfigManager``，不解析运行时语义。

本模块只做「门面转发」，不新增配置语义。业务代码继续使用
``from src.config import Config, get_config``；需要精确模块时再直接导入子模块。
"""

from src.config.settings import (  # noqa: F401
    AGENT_CONTEXT_COMPRESSION_DEFAULT_PROFILE,
    AGENT_CONTEXT_COMPRESSION_PROFILES,
    AGENT_MAX_STEPS_DEFAULT,
    ANSPIRE_LLM_BASE_URL_DEFAULT,
    ANSPIRE_LLM_MODEL_DEFAULT,
    DEFAULT_ALPHASIFT_INSTALL_SPEC,
    FUNDAMENTAL_STAGE_TIMEOUT_SECONDS_DEFAULT,
    NEWS_STRATEGY_WINDOWS,
    PROMPT_CACHE_DIAGNOSTICS_LEVELS,
    SUPPORTED_AGENT_BACKENDS,
    SUPPORTED_LLM_CHANNEL_PROTOCOLS,
    TICKFLOW_KLINE_ADJUST_VALUES,
    AgentContextCompressionPreset,
    Config,
    ConfigIssue,
    canonicalize_llm_channel_protocol,
    channel_allows_empty_api_key,
    extra_litellm_params,
    get_agent_context_compression_preset,
    get_api_keys_for_model,
    get_config,
    get_configured_llm_models,
    get_effective_agent_models_to_try,
    get_effective_agent_primary_model,
    normalize_agent_context_compression_profile,
    normalize_agent_litellm_model,
    normalize_llm_channel_model,
    normalize_news_strategy_profile,
    normalize_tickflow_kline_adjust,
    parse_agent_context_compression_int,
    parse_env_bool,
    parse_env_float,
    parse_env_int,
    parse_prompt_cache_diagnostics_level,
    resolve_llm_channel_protocol,
    resolve_news_window_days,
    resolve_unified_llm_temperature,
    setup_env,
)
from src.config.settings import (  # noqa: F401
    _get_litellm_provider,
    _uses_direct_env_provider,
)
