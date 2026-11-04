"""Read-only setup status checks; never saves or reloads configuration."""

from __future__ import annotations
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
from src.config import (
    ANSPIRE_LLM_BASE_URL_DEFAULT,
    ANSPIRE_LLM_MODEL_DEFAULT,
    _get_litellm_provider,
    _uses_direct_env_provider,
    canonicalize_llm_channel_protocol,
    channel_allows_empty_api_key,
    normalize_agent_litellm_model,
    normalize_llm_channel_model,
    parse_env_bool,
    resolve_llm_channel_protocol,
)
from src.domain.generation.hermes_rules import (
    HERMES_DEFAULT_BASE_URL,
    HERMES_DEFAULT_MODEL,
    HERMES_DEFAULT_PROTOCOL,
    is_reserved_hermes_name,
    parse_hermes_channel,
)
from src.application.generation.catalog import normalize_backend_id
from src.domain.generation.backend_identity import (
    AUTO_AGENT_BACKEND_ID,
    CODEX_CLI_BACKEND_ID,
    GENERATION_ONLY_BACKEND_IDS,
    LOCAL_CLI_GENERATION_BACKEND_IDS,
    LITELLM_BACKEND_ID,
)
from src.application.generation.runtime_ports import GenerationRuntimePort
from src.domain.notification.contracts import is_feishu_static_env_configured
from src.domain.notification.endpoints import resolve_gotify_message_endpoint, resolve_ntfy_endpoint
from src.domain.market.stock_list_parser import split_stock_list
from src.application.runtime.llm_config_validation import (
    _anspire_legacy_llm_enabled,
    _collect_hermes_channel_models_from_map,
    _collect_non_hermes_channel_models_from_map,
    _collect_yaml_models_from_map,
    _split_csv,
)
from typing import Callable


class SetupStatusBuilder:
    """Read-only first-run checks from an explicit effective configuration."""

    def __init__(self, generation_runtime_provider: Callable[[], GenerationRuntimePort]):
        """构造初始化状态检查服务并装配依赖。"""
        self._generation_runtime_provider = generation_runtime_provider

    def get_setup_status(self, effective_map: Dict[str, str]) -> Dict[str, Any]:
        """Return read-only first-run setup status without mutating runtime state."""
        llm_check = self._build_setup_primary_llm_check(effective_map)
        agent_check = self._build_setup_agent_llm_check(effective_map, llm_check)
        checks = [
            llm_check,
            agent_check,
            self._build_setup_stock_list_check(effective_map),
            self._build_setup_notification_check(effective_map),
            self._build_setup_storage_check(effective_map),
        ]

        required_missing = [check["key"] for check in checks if check["required"] and check["status"] == "needs_action"]
        smoke_blocking_missing = [
            check["key"]
            for check in checks
            if check["key"] in {"llm_primary", "stock_list"} and check["status"] == "needs_action"
        ]
        return {
            "is_complete": not required_missing,
            "ready_for_smoke": not smoke_blocking_missing,
            "required_missing_keys": required_missing,
            "next_step_key": required_missing[0] if required_missing else None,
            "checks": checks,
        }

    @staticmethod
    def _setup_check(
        key: str,
        title: str,
        category: str,
        required: bool,
        status: str,
        message: str,
        next_step: Optional[str] = None,
    ) -> Dict[str, Any]:
        """构造单项检查结果字典。"""
        return {
            "key": key,
            "title": title,
            "category": category,
            "required": required,
            "status": status,
            "message": message,
            "next_step": next_step,
        }

    @staticmethod
    def _has_any_config_value(effective_map: Dict[str, str], keys: Sequence[str]) -> bool:
        """判断配置映射中是否存在任意非空值。"""
        return any((effective_map.get(key) or "").strip() for key in keys)

    @staticmethod
    def _has_valid_ntfy_endpoint(effective_map: Dict[str, str]) -> bool:
        """校验 ntfy 端点配置是否有效。"""
        ntfy_server_url, ntfy_topic = resolve_ntfy_endpoint(effective_map.get("NTFY_URL"))
        return bool(ntfy_server_url and ntfy_topic)

    @staticmethod
    def _has_valid_gotify_config(effective_map: Dict[str, str]) -> bool:
        """校验 Gotify 配置是否有效。"""
        return bool(
            resolve_gotify_message_endpoint(effective_map.get("GOTIFY_URL"))
            and (effective_map.get("GOTIFY_TOKEN") or "").strip()
        )

    @classmethod
    def _provider_has_setup_credentials(cls, provider: str, effective_map: Dict[str, str]) -> bool:
        """判断供应商是否已配置所需凭据。"""
        normalized = canonicalize_llm_channel_protocol(provider)
        if normalized == "ollama":
            return True
        if normalized == "gemini" or normalized == "vertex_ai":
            return cls._has_any_config_value(effective_map, ("GEMINI_API_KEYS", "GEMINI_API_KEY"))
        if normalized == "anthropic":
            return cls._has_any_config_value(effective_map, ("ANTHROPIC_API_KEYS", "ANTHROPIC_API_KEY"))
        if normalized == "deepseek":
            return cls._has_any_config_value(effective_map, ("DEEPSEEK_API_KEYS", "DEEPSEEK_API_KEY"))
        if normalized == "openai":
            if cls._has_any_config_value(effective_map, ("OPENAI_API_KEYS", "OPENAI_API_KEY", "AIHUBMIX_KEY")):
                return True
            if _anspire_legacy_llm_enabled(effective_map) and cls._has_any_config_value(
                effective_map, ("ANSPIRE_API_KEYS",)
            ):
                return True
            base_url = (effective_map.get("OPENAI_BASE_URL") or "").strip()
            return channel_allows_empty_api_key("openai", base_url)

        env_prefix = normalized.upper().replace("-", "_")
        return cls._has_any_config_value(
            effective_map,
            (f"{env_prefix}_API_KEYS", f"{env_prefix}_API_KEY"),
        )

    @classmethod
    def _has_setup_runtime_source_for_model(cls, model: str, effective_map: Dict[str, str]) -> bool:
        """判断模型是否有可用的运行时来源配置。"""
        normalized_model = (model or "").strip()
        if not normalized_model:
            return False
        provider = _get_litellm_provider(normalized_model)
        return cls._provider_has_setup_credentials(provider, effective_map)

    @classmethod
    def _collect_setup_channel_models(cls, effective_map: Dict[str, str]) -> List[str]:
        """收集各通知渠道涉及的模型配置。"""
        models: List[str] = []
        seen: Set[str] = set()
        for raw_name in _split_csv(effective_map.get("LLM_CHANNELS") or ""):
            name = raw_name.strip()
            if not name:
                continue
            prefix = f"LLM_{name.upper()}"
            enabled_raw = effective_map.get(f"{prefix}_ENABLED")
            if name.lower() == "anspire" and not (enabled_raw or "").strip():
                enabled_raw = effective_map.get("ANSPIRE_LLM_ENABLED")
            enabled = parse_env_bool(enabled_raw, default=True)
            if not enabled:
                continue

            base_url = (effective_map.get(f"{prefix}_BASE_URL") or "").strip()
            if name.lower() == "anspire" and not base_url:
                base_url = (effective_map.get("ANSPIRE_LLM_BASE_URL") or ANSPIRE_LLM_BASE_URL_DEFAULT).strip()
            protocol = (effective_map.get(f"{prefix}_PROTOCOL") or "").strip()
            if name.lower() == "anspire" and not protocol:
                protocol = "openai"
            api_key = (effective_map.get(f"{prefix}_API_KEYS") or "").strip() or (
                effective_map.get(f"{prefix}_API_KEY") or ""
            ).strip()
            if name.lower() == "anspire" and not api_key:
                api_key = (effective_map.get("ANSPIRE_API_KEYS") or "").strip()
            raw_models = _split_csv(effective_map.get(f"{prefix}_MODELS") or "")
            if name.lower() == "anspire" and not raw_models:
                raw_models = [(effective_map.get("ANSPIRE_LLM_MODEL") or ANSPIRE_LLM_MODEL_DEFAULT).strip()]
            if is_reserved_hermes_name(name):
                result = parse_hermes_channel(
                    enabled=True,
                    protocol=protocol or HERMES_DEFAULT_PROTOCOL,
                    base_url=base_url or HERMES_DEFAULT_BASE_URL,
                    api_key=(effective_map.get(f"{prefix}_API_KEY") or "").strip(),
                    api_keys_raw=(effective_map.get(f"{prefix}_API_KEYS") or "").strip(),
                    extra_headers_raw=(effective_map.get(f"{prefix}_EXTRA_HEADERS") or "").strip(),
                    models=raw_models or [HERMES_DEFAULT_MODEL],
                )
                channel = result.channel or {}
                for raw_model in channel.get("models") or []:
                    if raw_model and raw_model not in seen:
                        seen.add(raw_model)
                        models.append(raw_model)
                continue
            resolved_protocol = resolve_llm_channel_protocol(
                protocol,
                base_url=base_url,
                models=raw_models,
                channel_name=name,
            )
            if not raw_models or not resolved_protocol:
                continue
            if not api_key and not channel_allows_empty_api_key(resolved_protocol, base_url):
                continue

            for raw_model in raw_models:
                normalized_model = normalize_llm_channel_model(raw_model, resolved_protocol, base_url)
                if normalized_model and normalized_model not in seen:
                    seen.add(normalized_model)
                    models.append(normalized_model)
        return models

    @classmethod
    def _infer_setup_legacy_primary_model(cls, effective_map: Dict[str, str]) -> str:
        """推断遗留配置中的主模型。"""
        if cls._has_any_config_value(effective_map, ("GEMINI_API_KEYS", "GEMINI_API_KEY")):
            model = (effective_map.get("GEMINI_MODEL") or "gemini-3.1-pro-preview").strip()
            return model if "/" in model else f"gemini/{model}"
        if cls._has_any_config_value(effective_map, ("ANTHROPIC_API_KEYS", "ANTHROPIC_API_KEY")):
            model = (effective_map.get("ANTHROPIC_MODEL") or "claude-sonnet-4-6").strip()
            return model if "/" in model else f"anthropic/{model}"
        if cls._has_any_config_value(effective_map, ("DEEPSEEK_API_KEYS", "DEEPSEEK_API_KEY")):
            return "deepseek/deepseek-chat"
        if cls._has_any_config_value(effective_map, ("OPENAI_API_KEYS", "OPENAI_API_KEY", "AIHUBMIX_KEY")):
            model = (effective_map.get("OPENAI_MODEL") or "gpt-5.5").strip()
            return model if "/" in model else f"openai/{model}"
        if _anspire_legacy_llm_enabled(effective_map) and cls._has_any_config_value(
            effective_map, ("ANSPIRE_API_KEYS",)
        ):
            model = (
                effective_map.get("ANSPIRE_LLM_MODEL") or effective_map.get("OPENAI_MODEL") or ANSPIRE_LLM_MODEL_DEFAULT
            ).strip()
            return model if "/" in model else f"openai/{model}"
        if (effective_map.get("OLLAMA_API_BASE") or "").strip():
            model = (effective_map.get("OLLAMA_MODEL") or "").strip()
            return model if model.startswith("ollama/") else (f"ollama/{model}" if model else "ollama/local")
        return ""

    def _resolve_setup_primary_model(self, effective_map: Dict[str, str]) -> Tuple[str, str]:
        """解析当前生效的主模型及其来源。"""
        explicit_model = (effective_map.get("LITELLM_MODEL") or "").strip()
        yaml_models = _collect_yaml_models_from_map(effective_map)
        channel_models = self._collect_setup_channel_models(effective_map)

        if explicit_model:
            if _uses_direct_env_provider(explicit_model):
                return explicit_model, "explicit"
            has_direct_source = self._has_setup_runtime_source_for_model(explicit_model, effective_map)
            if yaml_models and explicit_model not in set(yaml_models):
                return "", "主模型未出现在当前 LiteLLM YAML model_list 中"
            if channel_models and explicit_model not in set(channel_models):
                return "", "主模型未出现在当前启用渠道模型列表中"
            if yaml_models or channel_models or has_direct_source:
                return explicit_model, "explicit"
            return "", "主模型缺少可用渠道或匹配的 API Key"

        if yaml_models:
            return yaml_models[0], "yaml"
        if channel_models:
            return channel_models[0], "channel"

        legacy_model = self._infer_setup_legacy_primary_model(effective_map)
        if legacy_model:
            return legacy_model, "legacy"

        return "", "尚未检测到主模型配置"

    def _build_setup_primary_llm_check(self, effective_map: Dict[str, str]) -> Dict[str, Any]:
        """构建主 LLM 配置的初始化检查项。"""
        generation_backend = normalize_backend_id(
            effective_map.get("GENERATION_BACKEND"),
            default=LITELLM_BACKEND_ID,
        )
        if generation_backend in LOCAL_CLI_GENERATION_BACKEND_IDS:
            preset = self._generation_runtime_provider().resolve_preset(generation_backend)
            if shutil.which(preset.executable):
                return self._setup_check(
                    "llm_primary",
                    "LLM 主渠道",
                    "ai_model",
                    True,
                    "configured",
                    f"已启用 {preset.display_name} 本地生成 Backend（experimental/limited）。",
                )
            return self._setup_check(
                "llm_primary",
                "LLM 主渠道",
                "ai_model",
                True,
                "needs_action",
                (
                    "已选择 codex_cli，但 HRS 后端进程当前 PATH 中找不到 codex 可执行文件。"
                    if generation_backend == CODEX_CLI_BACKEND_ID
                    else f"已选择 {generation_backend}，但未找到 {preset.executable} 可执行文件。"
                ),
                (
                    "请确认 Codex CLI 已安装到后端 PATH 可见目录；桌面端请完全退出并重开。"
                    "打开 Codex CLI 交互窗口不会改变已运行后端的 PATH；若找到后仍失败，再检查 Codex CLI 登录态，"
                    "或将 GENERATION_BACKEND 设回 litellm。"
                    if generation_backend == CODEX_CLI_BACKEND_ID
                    else "请先安装并登录对应 CLI，或将 GENERATION_BACKEND 设回 litellm。"
                ),
            )

        model, source = self._resolve_setup_primary_model(effective_map)
        if model:
            source_label = {
                "explicit": "显式主模型",
                "yaml": "LiteLLM YAML",
                "channel": "LLM 渠道",
                "legacy": "legacy provider",
            }.get(source, source)
            return self._setup_check(
                "llm_primary",
                "LLM 主渠道",
                "ai_model",
                True,
                "configured",
                f"已检测到 {source_label}: {model}",
            )
        return self._setup_check(
            "llm_primary",
            "LLM 主渠道",
            "ai_model",
            True,
            "needs_action",
            source,
            "请配置 LITELLM_MODEL、LLM_CHANNELS、LITELLM_CONFIG 或 legacy provider API Key。",
        )

    def _build_setup_agent_llm_check(
        self,
        effective_map: Dict[str, str],
        primary_check: Dict[str, Any],
    ) -> Dict[str, Any]:
        """构建 Agent LLM 配置的初始化检查项。"""
        generation_backend = normalize_backend_id(
            effective_map.get("GENERATION_BACKEND"),
            default=LITELLM_BACKEND_ID,
        )
        agent_backend = normalize_backend_id(
            effective_map.get("AGENT_GENERATION_BACKEND"),
            default=AUTO_AGENT_BACKEND_ID,
        )
        if agent_backend in GENERATION_ONLY_BACKEND_IDS:
            return self._setup_check(
                "llm_agent",
                "Agent 渠道",
                "agent",
                True,
                "needs_action",
                f"Agent 工具调用暂不支持 {agent_backend} text-only backend。",
                "请将 AGENT_GENERATION_BACKEND 设为 auto 或 litellm，并配置 LiteLLM 工具调用渠道。",
            )

        agent_model_raw = (effective_map.get("AGENT_LITELLM_MODEL") or "").strip()
        hermes_routes = set(_collect_hermes_channel_models_from_map(effective_map))
        non_hermes_routes = set(_collect_non_hermes_channel_models_from_map(effective_map))
        if not agent_model_raw:
            if generation_backend in LOCAL_CLI_GENERATION_BACKEND_IDS:
                litellm_model, _source = self._resolve_setup_primary_model(effective_map)
                if litellm_model:
                    if litellm_model in hermes_routes and litellm_model not in non_hermes_routes:
                        return self._setup_check(
                            "llm_agent",
                            "Agent 渠道",
                            "agent",
                            True,
                            "needs_action",
                            "普通分析使用 Codex CLI；但当前 LiteLLM Agent 路径继承的是 Hermes-only 模型，"
                            "Hermes Phase 3 不支持 Agent 工具调用。",
                            "如需使用 Ask-Stock Agent，请配置非 Hermes 的 AGENT_LITELLM_MODEL，"
                            "或配置包含非 Hermes deployment 的 mixed Agent route。",
                        )
                    return self._setup_check(
                        "llm_agent",
                        "Agent 渠道",
                        "agent",
                        True,
                        "configured",
                        f"普通分析使用 Codex CLI；Agent 工具调用仍使用 LiteLLM 主模型: {litellm_model}",
                    )
                if agent_backend == LITELLM_BACKEND_ID:
                    return self._setup_check(
                        "llm_agent",
                        "Agent 渠道",
                        "agent",
                        True,
                        "needs_action",
                        "AGENT_GENERATION_BACKEND 已选择 litellm，但未检测到可用 LiteLLM 模型配置。",
                        "如需使用 Ask-Stock Agent，请配置 AGENT_LITELLM_MODEL、LITELLM_MODEL、LLM_CHANNELS 或 LITELLM_CONFIG。",
                    )
                return self._setup_check(
                    "llm_agent",
                    "Agent 渠道",
                    "agent",
                    True,
                    "needs_action",
                    "Agent 工具调用需要 LiteLLM 模型配置；local CLI 主生成方式不会被自动继承。",
                    "如需使用 Ask-Stock Agent，请配置 LiteLLM 模型，或将 AGENT_GENERATION_BACKEND 固定为 litellm 后补齐模型配置。",
                )
            if primary_check["status"] == "configured":
                primary_model, _source = self._resolve_setup_primary_model(effective_map)
                if primary_model in hermes_routes and primary_model not in non_hermes_routes:
                    return self._setup_check(
                        "llm_agent",
                        "Agent 渠道",
                        "agent",
                        True,
                        "needs_action",
                        "Hermes Phase 3 不支持 Agent 工具调用，且当前继承的主模型没有非 Hermes deployment。",
                        "请选择非 Hermes Agent 模型，或配置包含非 Hermes deployment 的 mixed Agent route。",
                    )
                return self._setup_check(
                    "llm_agent",
                    "Agent 渠道",
                    "agent",
                    True,
                    "inherited",
                    "未单独配置 Agent 主模型，将继承 LLM 主渠道。",
                )
            return self._setup_check(
                "llm_agent",
                "Agent 渠道",
                "agent",
                True,
                "needs_action",
                "Agent 未配置独立模型，且 LLM 主渠道尚不可用。",
                "请先补齐 LLM 主渠道配置。",
            )

        configured_models = set(
            _collect_yaml_models_from_map(effective_map) or self._collect_setup_channel_models(effective_map)
        )
        agent_model = normalize_agent_litellm_model(agent_model_raw, configured_models=configured_models)
        if agent_model in hermes_routes and agent_model not in non_hermes_routes:
            return self._setup_check(
                "llm_agent",
                "Agent 渠道",
                "agent",
                True,
                "needs_action",
                f"Agent 主模型 {agent_model} 只有 Hermes deployment，Phase 3 不支持 Agent 工具调用。",
                "请选择非 Hermes Agent 模型，或配置 mixed route 中的非 Hermes deployment。",
            )
        configured_agent_message = f"已配置 Agent 主模型: {agent_model}"
        if generation_backend == CODEX_CLI_BACKEND_ID:
            configured_agent_message = f"普通分析使用 Codex CLI；Agent 工具调用仍使用 LiteLLM 主模型: {agent_model}"
        if _uses_direct_env_provider(agent_model):
            return self._setup_check(
                "llm_agent",
                "Agent 渠道",
                "agent",
                True,
                "configured",
                configured_agent_message,
            )
        if (
            not configured_models and self._has_setup_runtime_source_for_model(agent_model, effective_map)
        ) or agent_model in configured_models:
            return self._setup_check(
                "llm_agent",
                "Agent 渠道",
                "agent",
                True,
                "configured",
                configured_agent_message,
            )

        return self._setup_check(
            "llm_agent",
            "Agent 渠道",
            "agent",
            True,
            "needs_action",
            f"Agent 主模型 {agent_model} 缺少可用渠道或匹配的 API Key。",
            "请调整 AGENT_LITELLM_MODEL 或补齐对应渠道配置。",
        )

    def _build_setup_stock_list_check(self, effective_map: Dict[str, str]) -> Dict[str, Any]:
        """构建股票列表配置的初始化检查项。"""
        stocks = split_stock_list(effective_map.get("STOCK_LIST") or "")
        if stocks:
            return self._setup_check(
                "stock_list",
                "自选股",
                "base",
                True,
                "configured",
                f"已配置 {len(stocks)} 只股票。",
            )
        return self._setup_check(
            "stock_list",
            "自选股",
            "base",
            True,
            "needs_action",
            "当前 STOCK_LIST 为空。",
            "请至少添加 1 只股票用于首次试跑。",
        )

    def _build_setup_notification_check(self, effective_map: Dict[str, str]) -> Dict[str, Any]:
        """构建通知渠道配置的初始化检查项。"""
        configured = (
            self._has_any_config_value(
                effective_map, ("WECHAT_WEBHOOK_URL", "DISCORD_WEBHOOK_URL", "DINGTALK_WEBHOOK_URL")
            )
            or is_feishu_static_env_configured(effective_map)
            or (
                self._has_any_config_value(effective_map, ("TELEGRAM_BOT_TOKEN",))
                and self._has_any_config_value(effective_map, ("TELEGRAM_CHAT_ID",))
            )
            or (
                self._has_any_config_value(effective_map, ("EMAIL_SENDER",))
                and self._has_any_config_value(effective_map, ("EMAIL_PASSWORD",))
            )
            or (
                self._has_any_config_value(effective_map, ("DINGTALK_APP_KEY",))
                and self._has_any_config_value(effective_map, ("DINGTALK_APP_SECRET",))
            )
            or (
                self._has_any_config_value(effective_map, ("DISCORD_BOT_TOKEN",))
                and self._has_any_config_value(effective_map, ("DISCORD_MAIN_CHANNEL_ID", "DISCORD_CHANNEL_ID"))
            )
            or (
                self._has_any_config_value(effective_map, ("PUSHOVER_USER_KEY",))
                and self._has_any_config_value(effective_map, ("PUSHOVER_API_TOKEN",))
            )
            or self._has_any_config_value(effective_map, ("SLACK_WEBHOOK_URL",))
            or (
                self._has_any_config_value(effective_map, ("SLACK_BOT_TOKEN",))
                and self._has_any_config_value(effective_map, ("SLACK_CHANNEL_ID",))
            )
            or self._has_any_config_value(
                effective_map,
                (
                    "PUSHPLUS_TOKEN",
                    "SERVERCHAN3_SENDKEY",
                    "CUSTOM_WEBHOOK_URLS",
                    "WECOM_WEBHOOK_URL",
                    "ASTRBOT_URL",
                ),
            )
            or self._has_valid_ntfy_endpoint(effective_map)
            or self._has_valid_gotify_config(effective_map)
        )
        if configured:
            return self._setup_check(
                "notification",
                "通知渠道",
                "notification",
                False,
                "configured",
                "已检测到至少一个通知渠道配置。",
            )
        return self._setup_check(
            "notification",
            "通知渠道",
            "notification",
            False,
            "optional",
            "通知为可选项，未配置也不影响首次跑通。",
            "需要推送时可稍后配置飞书、钉钉、Telegram、邮件或其他通知渠道。",
        )

    def _build_setup_storage_check(self, effective_map: Dict[str, str]) -> Dict[str, Any]:
        """构建存储配置的初始化检查项。"""
        db_path = Path((effective_map.get("DATABASE_PATH") or "./data/stock_analysis.db").strip()).expanduser()
        parent = db_path.parent if db_path.parent != Path("") else Path(".")
        probe = parent
        while not probe.exists() and probe != probe.parent:
            probe = probe.parent

        if not probe.exists() or not probe.is_dir():
            return self._setup_check(
                "storage",
                "数据库 / 本地存储",
                "system",
                True,
                "needs_action",
                f"数据库路径父目录不可用: {parent}",
                "请检查 DATABASE_PATH 或上级目录权限。",
            )

        if os.access(probe, os.W_OK):
            detail = f"数据库路径可用: {db_path}"
            if not parent.exists():
                detail = f"数据库上级目录可创建: {parent}"
            return self._setup_check(
                "storage",
                "数据库 / 本地存储",
                "system",
                True,
                "configured",
                detail,
            )

        return self._setup_check(
            "storage",
            "数据库 / 本地存储",
            "system",
            True,
            "needs_action",
            f"数据库路径上级目录不可写: {probe}",
            "请调整 DATABASE_PATH 或目录权限。",
        )
