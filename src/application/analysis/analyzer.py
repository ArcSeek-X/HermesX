# -*- coding: utf-8 -*-
"""
===================================
A股自选股智能分析系统 - AI分析层
===================================

职责：
1. 封装 LLM 调用逻辑（通过 LiteLLM 统一调用 Gemini/Anthropic/OpenAI 等）
2. 结合技术面和消息面生成分析报告
3. 解析 LLM 响应为结构化 AnalysisResult
"""

import json
import logging
import math
import re
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple, Callable

from json_repair import repair_json

from src.application.agent.provider_trace import resolved_model_provider_identity
from src.application.agent.skills.defaults import CORE_TRADING_SKILL_POLICY_ZH
from src.config import (
    Config,
    extra_litellm_params,
    get_api_keys_for_model,
    get_config,
    get_configured_llm_models,
    resolve_news_window_days,
)
from src.domain.generation.hermes_rules import (
    HERMES_CHANNEL_NAME,
    build_hermes_redaction_values,
    canonicalize_hermes_model_ref,
    filter_non_hermes_deployments,
    hermes_blocked_route_candidates,
    is_masked_secret_placeholder,
    route_deployment_origins,
    route_has_hermes,
    sanitize_hermes_error_text,
)
from src.application.generation.catalog import (
    resolve_generation_backend_id,
    resolve_generation_fallback_backend_id,
)
from src.domain.generation.backend_identity import (
    LOCAL_CLI_GENERATION_BACKEND_IDS,
    LITELLM_BACKEND_ID,
)
from src.application.generation.ports import (
    GenerationBackend,
    GenerationError,
    GenerationErrorCode,
)
from src.domain.generation.diagnostics import redact_diagnostic_text
from src.domain.generation.response_content import strip_leading_think_wrapper
from src.data.stock_mapping import STOCK_NAME_MAP
from src.domain.shared.report_language import (
    get_signal_level,
    get_no_data_text,
    get_placeholder_text,
    get_unknown_text,
    get_chip_unavailable_text,
    infer_decision_type_from_advice,
    is_chip_placeholder_value,
    localize_confidence_level,
    localize_operation_advice,
    localize_trend_prediction,
    normalize_report_language,
)
from src.domain.analysis.chip_rules import (
    build_chip_structure as _build_chip_structure_from_data,
    has_meaningful_chip_data as _has_meaningful_chip_data,
    safe_float as _safe_float,
)
from src.domain.analysis.prompt_sanitizer import (
    sanitize_trend_analysis_for_prompt as _sanitize_trend_analysis_for_prompt,
)
from src.domain.decision.action import build_action_fields
from src.domain.decision.scale import (
    CANONICAL_DECISION_SCALE_PROMPT_ZH,
    score_band_metadata,
)
from src.domain.decision.stability_rules import (
    as_dict_for_decision_guard as _as_dict_for_decision_guard,
    capital_flow_bias_with_status as _capital_flow_bias_with_status,
    first_list_value as _first_list_value,
    first_numeric_value as _first_numeric_value,
    is_significant_structural_risk as _is_significant_structural_risk,
)
from src.application.analysis.report_schema import AnalysisReportSchema
from src.domain.market.context import detect_market, get_market_role, get_market_guidelines
from src.application.market.daily_market_context import format_daily_market_context_prompt_section
from src.application.reporting.market_phase_prompt import format_market_phase_prompt_section
from src.application.reporting.market_structure_prompt import format_market_structure_prompt_section

from src.domain.analysis.result import AnalysisResult
from src.application.analysis.result_policy import (
    _localized_text,
    _normalize_risk_warning_values,
    check_content_integrity,
    apply_placeholder_fill,
    _is_value_placeholder,
    _mark_chip_structure_unavailable,
    normalize_chip_structure_availability,
    fill_chip_structure_if_needed,
    fill_price_position_if_needed,
    stabilize_decision_with_structure,
    _has_structural_risk_alert,
    _sync_stability_dashboard_fields,
    _capital_flow_status_for_stability,
    _set_decision_stability_unavailable,
    _record_decision_score_calibration,
    _bound_hold_watch_sentiment_score,
    _apply_hold_watch_dashboard,
    _downgrade_buy_without_capital_flow,
    _downgrade_to_structural_hold,
    _set_structural_hold_wording,
    populate_decision_action_fields,
)
from src.application.reporting.analysis_prompt import (
    AnalysisPromptBuilder,
    SYSTEM_PROMPT,
    LEGACY_DEFAULT_SYSTEM_PROMPT,
    TEXT_SYSTEM_PROMPT,
    _today_has_realtime_overlay,
    _today_looks_complete_daily_bar,
    _phase_aware_quote_labels,
    _should_hide_regular_session_ohlc,
)
from src.application.analysis.response_parser import AnalysisResponseParser

logger = logging.getLogger(__name__)

# --- Analyzer LLM 运行时端口 seam（§4.3 拆分 A2；T5f 同型）---
# analyzer 与 ports 同在 application/analysis 包（A3 直搬后），但仍保持 analyzer 不
# 模块级 import ports：seam 仅持有运行时绑定的端口对象，bootstrap 装配时才引用两侧类型
# （延续 S2d 断环惯例，避免包内用例件与分析器构造期的潜在导入环）。
_analyzer_llm_port = None


def set_analyzer_llm_port(port) -> None:
    """装配 Analyzer LLM 运行时端口（bootstrap 调用；幂等：仅非 None 覆盖，T5d 同型）。"""
    global _analyzer_llm_port
    if port is not None:
        _analyzer_llm_port = port


def _get_analyzer_llm_port():
    """取 Analyzer LLM 端口；未装配即 fail-fast（API/CLI 启动链路必经 bootstrap 装配，
    触发此处说明装配缺失而非运行期降级）。"""
    if _analyzer_llm_port is None:  # pragma: no cover - 正常启动链路由 bootstrap 装配
        raise RuntimeError("AnalyzerLLMPort 未装配：请经 configure_analyzer_runtime() 完成 bootstrap 装配。")
    return _analyzer_llm_port


# --- 生成链路运行时端口 seam（R2-A3；AnalyzerLLMPort 同型）---
# 调用点分散在 stream / non-stream / audit 三条路径，且测试大量直接构造 Analyzer，
# 因此采用模块级 seam + 未装配 fail-fast，而非构造注入（R2 §5.5 拍板）。
_generation_backend_factory_port = None
_generation_runtime_port = None
_generation_usage_port = None
_provider_cache_port = None


def set_generation_backend_factory_port(port) -> None:
    """装配生成后端工厂端口（bootstrap 调用；幂等：仅非 None 覆盖）。"""
    global _generation_backend_factory_port
    if port is not None:
        _generation_backend_factory_port = port


def set_generation_runtime_port(port) -> None:
    """装配生成运行时端口（bootstrap 调用；幂等）。"""
    global _generation_runtime_port
    if port is not None:
        _generation_runtime_port = port


def set_generation_usage_port(port) -> None:
    """装配用量遥测端口（bootstrap 调用；幂等）。"""
    global _generation_usage_port
    if port is not None:
        _generation_usage_port = port


def set_provider_cache_port(port) -> None:
    """装配 provider prompt-cache 端口（bootstrap 调用；幂等）。"""
    global _provider_cache_port
    if port is not None:
        _provider_cache_port = port


def _get_generation_backend_factory_port():
    if _generation_backend_factory_port is None:  # pragma: no cover
        raise RuntimeError(
            "GenerationBackendFactoryPort 未装配：请经 configure_generation_runtime() 完成 bootstrap 装配。"
        )
    return _generation_backend_factory_port


def _get_generation_runtime_port():
    if _generation_runtime_port is None:  # pragma: no cover
        raise RuntimeError(
            "GenerationRuntimePort 未装配：请经 configure_generation_runtime() 完成 bootstrap 装配。"
        )
    return _generation_runtime_port


def _get_generation_usage_port():
    if _generation_usage_port is None:  # pragma: no cover
        raise RuntimeError(
            "GenerationUsagePort 未装配：请经 configure_generation_runtime() 完成 bootstrap 装配。"
        )
    return _generation_usage_port


def _get_provider_cache_port():
    if _provider_cache_port is None:  # pragma: no cover
        raise RuntimeError(
            "ProviderCachePort 未装配：请经 configure_generation_runtime() 完成 bootstrap 装配。"
        )
    return _provider_cache_port


def call_litellm_with_param_recovery(
    call: Callable[[dict], Any],
    *,
    model: str,
    call_kwargs: dict,
    model_list: Optional[list] = None,
    cache_recovery: bool = True,
    logger: Any = None,
    log_label: str = "[LiteLLM]",
) -> Any:
    """生成参数恢复重试的模块级转发（R2-A3）。

    保留本名字是因为 ``tests/test_market_analyzer_generate_text.py`` 有 4 处
    ``patch("src.application.analysis.analyzer.call_litellm_with_param_recovery")``
    锚点；转发到 ``GenerationRuntimePort.completion_with_recovery`` 后 patch 语义
    不变。测试 re-point 后（R2-A4 同期）本函数删除。
    """
    return _get_generation_runtime_port().completion_with_recovery(
        call,
        model=model,
        call_kwargs=call_kwargs,
        model_list=model_list,
        cache_recovery=cache_recovery,
        logger=logger,
        log_label=log_label,
    )


def _legacy_market_group(stock_code: Any) -> str:
    code = str(stock_code or "").strip()
    if not code or code.lower() == "unknown":
        return "unknown"
    market = detect_market(code)
    return market if market in {"cn", "hk", "us"} else "unknown"


def _legacy_audit_marker_specs(
    context: Dict[str, Any],
    *,
    code: str,
    stock_name: str,
    report_language: str,
    news_context: Optional[str],
    analysis_context_pack_summary: Optional[str],
) -> List[Dict[str, Any]]:
    markers: List[Dict[str, Any]] = []

    def add(marker_name: str, value: Any) -> None:
        if value is None:
            return
        text = str(value).strip()
        if not text:
            return
        markers.append(
            {
                "marker_name": marker_name,
                "message_role": "user",
                "text": text,
            }
        )

    add("stock_code", code)
    add("stock_name", stock_name)
    add("analysis_date", context.get("date"))
    add("market_phase", "## Market Phase Context" if report_language in ("en", "ko") else "## 市场阶段上下文")
    add("daily_market_context", "## Daily Market Context" if report_language in ("en", "ko") else "## 大盘环境摘要")
    add("market_structure_context", "## Market Structure Context" if report_language in ("en", "ko") else "## 市场结构上下文")
    add("analysis_context_pack", analysis_context_pack_summary)
    add("quote", "## 📈 技术面数据")
    add("news_context", "## 📰 舆情情报" if news_context else None)
    return markers


def _legacy_router_provider_alias(model: str) -> str:
    """legacy Router 别名：按 provider 前缀归组（§4.3 A2 F1 型提模块级，原
    GeminiAnalyzer 静态方法；调用点均在类内，收口为裸调用）。"""
    provider = model.split("/", 1)[0] if "/" in model else "openai"
    return f"__legacy_{provider}__"


class _LiteLLMStreamError(RuntimeError):
    """Internal error wrapper that records whether any text was streamed."""

    def __init__(self, message: str, *, partial_received: bool = False):
        super().__init__(message)
        self.partial_received = partial_received


class _AllModelsFailedError(Exception):
    """Raised when every model in the fallback chain fails.

    This includes both LLM call errors and JSON parse errors (when a
    ``response_validator`` is provided to :meth:`GeminiAnalyzer._call_litellm`).

    The ``last_response_text`` attribute holds the raw text from the last model
    that *did* return a response (but whose JSON could not be validated), so
    callers can still attempt a best-effort text fallback.

    ``last_model`` and ``last_usage`` record the model name and token usage
    from the last attempt so callers can persist usage even on fallback.
    """

    def __init__(
        self,
        message: str,
        *,
        last_response_text: Optional[str] = None,
        last_model: Optional[str] = None,
        last_usage: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.last_response_text = last_response_text
        self.last_model = last_model
        self.last_usage = last_usage or {}


from src.utils.data_processing import normalize_report_signal_attribution


# ---------- chip_structure fallback (Issue #589) ----------


# W5.1：风险短语判定/数值归一/资金流方向、趋势 Prompt 清洗、筹码健康度等纯规则
# 已分别下沉到 src.domain.decision.stability_rules、src.domain.analysis.prompt_sanitizer
# 与 src.domain.analysis.chip_rules；本文件只保留编排与字段回写。


# dict 归一/列表取值/数值解析/资金流方向纯规则已下沉 src.domain.decision.stability_rules（W5.1）


class GeminiAnalyzer:
    """
    Gemini AI 分析器

    职责：
    1. 调用 Google Gemini API 进行股票分析
    2. 结合预先搜索的新闻和技术面数据生成分析报告
    3. 解析 AI 返回的 JSON 格式结果

    使用方式：
        analyzer = GeminiAnalyzer()
        result = analyzer.analyze(context, news_context)
    """

    # ========================================
    # 系统提示词 - 决策仪表盘 v2.0
    # ========================================
    # 输出格式升级：从简单信号升级为决策仪表盘
    # 核心模块：核心结论 + 数据透视 + 舆情情报 + 作战计划
    # ========================================

    LEGACY_DEFAULT_SYSTEM_PROMPT = LEGACY_DEFAULT_SYSTEM_PROMPT

    SYSTEM_PROMPT = SYSTEM_PROMPT

    TEXT_SYSTEM_PROMPT = TEXT_SYSTEM_PROMPT

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        config: Optional[Config] = None,
        skills: Optional[List[str]] = None,
        skill_instructions: Optional[str] = None,
        default_skill_policy: Optional[str] = None,
        use_legacy_default_prompt: Optional[bool] = None,
    ):
        """Initialize LLM Analyzer via LiteLLM.

        Args:
            api_key: Ignored (kept for backward compatibility). Keys are loaded from config.
        """
        self._config_override = config
        self._requested_skills = list(skills) if skills is not None else None
        self._skill_instructions_override = skill_instructions
        self._default_skill_policy_override = default_skill_policy
        self._use_legacy_default_prompt_override = use_legacy_default_prompt
        self._resolved_prompt_state: Optional[Dict[str, Any]] = None
        self._router = None
        self._legacy_router_model_list: List[Dict[str, Any]] = []
        self._litellm_available = False
        self._init_litellm()
        if not self._litellm_available:
            try:
                backend_id, _fallback_backend_id = self._resolve_generation_backend_config()
            except GenerationError:
                backend_id = ""
            if backend_id in LOCAL_CLI_GENERATION_BACKEND_IDS:
                logger.info(
                    "Analyzer generation backend: %s configured; LiteLLM API keys are not "
                    "required for stock analysis generation",
                    backend_id,
                )
            else:
                logger.warning("No LLM configured (LITELLM_MODEL / API keys), AI analysis will be unavailable")

    def _get_runtime_config(self) -> Config:
        """Return the runtime config, honoring injected overrides for tests/pipeline."""
        return getattr(self, "_config_override", None) or get_config()

    def _get_skill_prompt_sections(self) -> tuple[str, str, bool]:
        """Resolve skill instructions + default baseline + prompt mode."""
        skill_instructions = getattr(self, "_skill_instructions_override", None)
        default_skill_policy = getattr(self, "_default_skill_policy_override", None)
        use_legacy_default_prompt = getattr(self, "_use_legacy_default_prompt_override", None)

        if skill_instructions is not None and default_skill_policy is not None:
            return (
                skill_instructions,
                default_skill_policy,
                bool(use_legacy_default_prompt) if use_legacy_default_prompt is not None else False,
            )

        resolved_state = getattr(self, "_resolved_prompt_state", None)
        if resolved_state is None:
            from src.application.agent.factory import resolve_skill_prompt_state

            prompt_state = resolve_skill_prompt_state(
                self._get_runtime_config(),
                skills=getattr(self, "_requested_skills", None),
            )
            resolved_state = {
                "skill_instructions": prompt_state.skill_instructions,
                "default_skill_policy": prompt_state.default_skill_policy,
                "use_legacy_default_prompt": bool(getattr(prompt_state, "use_legacy_default_prompt", False)),
            }
            self._resolved_prompt_state = resolved_state

        return (
            skill_instructions if skill_instructions is not None else resolved_state.get("skill_instructions", ""),
            default_skill_policy if default_skill_policy is not None else resolved_state.get("default_skill_policy", ""),
            (
                use_legacy_default_prompt
                if use_legacy_default_prompt is not None
                else bool(resolved_state.get("use_legacy_default_prompt", False))
            ),
        )

    def _get_analysis_system_prompt(self, report_language: str, stock_code: str = "") -> str:
        """Build the analyzer system prompt with output-language guidance."""
        lang = normalize_report_language(report_language)
        market_role = get_market_role(stock_code, lang)
        market_guidelines = get_market_guidelines(stock_code, lang)
        skill_instructions, default_skill_policy, use_legacy_default_prompt = self._get_skill_prompt_sections()
        if use_legacy_default_prompt:
            base_prompt = self.LEGACY_DEFAULT_SYSTEM_PROMPT.replace(
                "{market_placeholder}", market_role
            ).replace(
                "{guidelines_placeholder}", market_guidelines
            )
        else:
            skills_section = ""
            if skill_instructions:
                skills_section = f"## 激活的交易技能\n\n{skill_instructions}\n"
            default_skill_policy_section = ""
            if default_skill_policy:
                default_skill_policy_section = f"{default_skill_policy}\n"
            base_prompt = (
                self.SYSTEM_PROMPT.replace("{market_placeholder}", market_role)
                .replace("{guidelines_placeholder}", market_guidelines)
                .replace("{default_skill_policy_section}", default_skill_policy_section)
                .replace("{skills_section}", skills_section)
            )
        if lang == "en":
            return base_prompt + """

## Output Language (highest priority)

- Keep all JSON keys unchanged.
- `decision_type` must remain `buy|hold|sell`.
- All human-readable JSON values must be written in English.
- Use the common English company name when you are confident; otherwise keep the original listed company name instead of inventing one.
- This includes `stock_name`, `trend_prediction`, `operation_advice`, `confidence_level`, nested dashboard text, checklist items, and all narrative summaries.
"""
        if lang == "ko":
            return base_prompt + """

## Output Language (highest priority)

- Keep all JSON keys unchanged.
- `decision_type` must remain `buy|hold|sell`.
- All human-readable JSON values must be written in Korean (한국어).
- Use the common Korean or original listed company name when confident; do not invent one.
- This includes `stock_name`, `trend_prediction`, `operation_advice`, `confidence_level`, nested dashboard text, checklist items, and all narrative summaries.
"""
        return base_prompt + """

## 输出语言（最高优先级）

- 所有 JSON 键名保持不变。
- `decision_type` 必须保持为 `buy|hold|sell`。
- 所有面向用户的人类可读文本值必须使用中文。
"""

    def _has_channel_config(self, config: Config) -> bool:
        """Check if multi-channel config (channels / YAML / legacy model_list) is active."""
        return bool(config.llm_model_list) and not all(
            e.get('model_name', '').startswith('__legacy_') for e in config.llm_model_list
        )

    @staticmethod
    def _build_legacy_router_model_list_from_config(
        model: str,
        model_list: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Build legacy-router candidates from configured legacy llm_model_list entries."""
        if not model:
            return []
        target_model = model
        target_legacy_alias = _legacy_router_provider_alias(model)
        legacy_entries: List[Dict[str, Any]] = []
        for entry in model_list or []:
            if not isinstance(entry, dict):
                continue
            model_name = str(entry.get("model_name") or "").strip()
            if model_name != target_legacy_alias:
                continue

            params = entry.get("litellm_params")
            if not isinstance(params, dict):
                continue

            api_key = str(params.get("api_key") or "").strip()
            if not api_key or len(api_key) < 8:
                continue

            deployed_params = dict(params)
            deployed_params["model"] = target_model
            deployed_params["api_key"] = api_key
            legacy_entries.append({
                "model_name": target_model,
                "litellm_params": deployed_params,
            })

        return legacy_entries

    def _init_litellm(self) -> None:
        """Initialize litellm Router from channels / YAML / legacy keys."""
        config = self._get_runtime_config()
        if self._get_hermes_config_error(config) is not None:
            logger.error("Analyzer LLM: Hermes channel configuration blocks legacy fallback")
            return
        litellm_model = config.litellm_model
        if not litellm_model:
            backend_id = ""
            try:
                backend_id = resolve_generation_backend_id(config)
            except GenerationError:
                pass
            if backend_id in LOCAL_CLI_GENERATION_BACKEND_IDS:
                logger.info(
                    "Analyzer LiteLLM: LITELLM_MODEL not configured; using %s generation backend",
                    backend_id,
                )
            else:
                logger.warning("Analyzer LLM: LITELLM_MODEL not configured")
            return

        self._litellm_available = True

        # --- Channel / YAML path: build Router from pre-built model_list ---
        if self._has_channel_config(config):
            model_list = config.llm_model_list
            if self._get_mixed_hermes_route_error(config, litellm_model) is not None:
                self._litellm_available = False
                logger.error("Analyzer LLM: mixed Hermes/non-Hermes route requires deployment-level no-proxy support")
                return
            router_model_list = model_list
            if route_has_hermes(model_list, litellm_model):
                # Hermes-only routes are dispatched directly with a request-scoped
                # no-proxy OpenAI client. Keeping them out of Router prevents the
                # default proxy-aware transport from seeing the Hermes bearer key.
                router_model_list = filter_non_hermes_deployments(model_list)
                if not router_model_list:
                    self._litellm_available = True
                    logger.info("Analyzer LLM: Hermes-only route will use direct no-proxy completion")
                    return
            # Router 构造/签名不兼容兜底收纳 AnalyzerLLMPort.build_router（§4.3 A2）；
            # 保留 try/else 形态：else 分支的初始化 info 日志仅在构造成功时打印。
            try:
                self._router = _get_analyzer_llm_port().build_router(
                    model_list=router_model_list,
                )
            except TypeError:  # pragma: no cover - 适配器内部已兜底，兼容外部 patch 形态
                self._router = None
            else:
                unique_models = list(dict.fromkeys(
                    e['litellm_params']['model'] for e in model_list
                ))
                logger.info(
                    f"Analyzer LLM: Router initialized from channels/YAML — "
                    f"{len(router_model_list)} deployment(s), models: {unique_models}"
                )
                return

        # --- Legacy path: build Router for multi-key, or use single key ---
        keys = get_api_keys_for_model(litellm_model, config)
        legacy_model_list = self._build_legacy_router_model_list_from_config(
            litellm_model,
            config.llm_model_list,
        )
        if len(legacy_model_list) <= 1 and keys:
            extra_params = extra_litellm_params(litellm_model, config)
            configured_model_list = [
                {
                    "model_name": litellm_model,
                    "litellm_params": {
                        "model": litellm_model,
                        "api_key": k,
                        **extra_params,
                    },
                }
                for k in keys
            ]
            if not legacy_model_list:
                legacy_model_list = configured_model_list
            elif len(legacy_model_list) < len(configured_model_list):
                legacy_model_list = configured_model_list

        if len(legacy_model_list) > 1:
            self._legacy_router_model_list = legacy_model_list
            # 同上：legacy 路径 Router 构造经端口，else 仅构造成功时打 info。
            try:
                self._router = _get_analyzer_llm_port().build_router(
                    model_list=legacy_model_list,
                )
            except TypeError:  # pragma: no cover - 适配器内部已兜底，兼容外部 patch 形态
                self._router = None
            else:
                logger.info(
                    f"Analyzer LLM: Legacy Router initialized with {len(legacy_model_list)} keys "
                    f"for {litellm_model}"
                )
                return

        if keys:
            logger.info(f"Analyzer LLM: litellm initialized (model={litellm_model})")
        else:
            logger.info(
                f"Analyzer LLM: litellm initialized (model={litellm_model}, "
                f"API key from environment)"
            )

    def is_available(self) -> bool:
        """Check whether the configured generation backend is available."""
        backend_error = self.get_generation_backend_config_error()
        if backend_error is not None:
            return self._can_use_generation_fallback(backend_error)
        backend_id, _fallback_backend_id = self._resolve_generation_backend_config()
        if backend_id in LOCAL_CLI_GENERATION_BACKEND_IDS:
            return True
        return self._litellm_runtime_available()

    def _litellm_runtime_available(self) -> bool:
        return self._router is not None or self._litellm_available

    def _can_use_generation_fallback(self, backend_error: GenerationError) -> bool:
        if not backend_error.fallbackable:
            return False
        try:
            _backend_id, fallback_backend_id = self._resolve_generation_backend_config()
        except GenerationError:
            return False
        return (
            fallback_backend_id == LITELLM_BACKEND_ID
            and self._litellm_runtime_available()
        )

    def _resolve_generation_backend_config(self) -> Tuple[str, Optional[str]]:
        """Resolve and validate generation backend ids."""
        config = self._get_runtime_config()
        backend_id = resolve_generation_backend_id(config)
        fallback_backend_id = resolve_generation_fallback_backend_id(config)
        return backend_id, fallback_backend_id

    def get_generation_backend_config_error(self) -> Optional[GenerationError]:
        """Return a structured backend config error, if the backend cannot run."""
        try:
            backend_id, _fallback_backend_id = self._resolve_generation_backend_config()
            config = self._get_runtime_config()
            hermes_error = self._get_hermes_config_error(config)
            if hermes_error is not None:
                return hermes_error
            for model in [getattr(config, "litellm_model", "")] + list(getattr(config, "litellm_fallback_models", []) or []):
                mixed_error = self._get_mixed_hermes_route_error(config, model)
                if mixed_error is not None:
                    return mixed_error
            if backend_id in LOCAL_CLI_GENERATION_BACKEND_IDS:
                backend = self.get_generation_backend(backend_id)
                get_config_error = getattr(backend, "get_config_error", None)
                if callable(get_config_error):
                    return get_config_error()
        except GenerationError as exc:
            return exc
        return None

    def _get_hermes_config_error(self, config: Config) -> Optional[GenerationError]:
        issues = list(getattr(config, "llm_channel_config_issues", []) or [])
        if not getattr(config, "llm_blocks_legacy_fallback", False) or not issues:
            return None
        blocked_routes = set(getattr(config, "llm_blocked_hermes_routes", []) or [])
        selected_models = [
            ("LITELLM_MODEL", getattr(config, "litellm_model", "") or ""),
            *[
                ("LITELLM_FALLBACK_MODELS", fallback_model)
                for fallback_model in list(getattr(config, "litellm_fallback_models", []) or [])
            ],
        ]
        selected_blocked_route = ""
        selected_field = ""
        for field_name, model in selected_models:
            raw_model = str(model or "").strip()
            if not raw_model:
                continue
            candidates = hermes_blocked_route_candidates(raw_model)
            candidates.add(raw_model)
            try:
                candidates.add(canonicalize_hermes_model_ref(raw_model).route_model)
            except (TypeError, ValueError) as exc:
                logger.debug("Failed to canonicalize selected Hermes route candidate %r: %s", raw_model, exc)
            matched = candidates & blocked_routes
            if matched:
                selected_blocked_route = sorted(matched)[0]
                selected_field = field_name
                break
        if blocked_routes and not selected_blocked_route and getattr(config, "llm_model_list", None):
            return None
        first = issues[0]
        code = (
            "explicit_hermes_route_invalid"
            if selected_blocked_route
            else first.get("code", "invalid_hermes_channel")
        )
        return GenerationError(
            error_code=GenerationErrorCode.UNSAFE_CONFIG,
            stage="configuration",
            retryable=False,
            fallbackable=False,
            backend=LITELLM_BACKEND_ID,
            provider=HERMES_CHANNEL_NAME,
            details={
                "field": selected_field or first.get("field", "LLM_HERMES_API_KEY"),
                "code": code,
                "reason": code,
                "message": first.get("message", "Hermes channel configuration is invalid"),
                "issues": issues,
                "route_name": selected_blocked_route or None,
            },
        )

    def _get_mixed_hermes_route_error(self, config: Config, model: str) -> Optional[GenerationError]:
        if not model:
            return None
        origins = route_deployment_origins(getattr(config, "llm_model_list", []) or [], model)
        if not origins.is_mixed:
            return None
        return GenerationError(
            error_code=GenerationErrorCode.UNSAFE_CONFIG,
            stage="configuration",
            retryable=False,
            fallbackable=False,
            backend=LITELLM_BACKEND_ID,
            provider=HERMES_CHANNEL_NAME,
            details={
                "field": "LLM_CHANNELS",
                "code": "mixed_hermes_route_unsupported",
                "reason": "router_deployment_no_proxy_unavailable",
                "route_name": model,
            },
        )

    def _hermes_redaction_values_for_model(self, config: Config, model: str = "") -> set[str]:
        redactions: set[str] = set()
        deployments = list(getattr(config, "llm_model_list", []) or [])
        selected_deployments = deployments
        if model:
            origins = route_deployment_origins(deployments, model)
            selected_deployments = list(origins.hermes_deployments or [])
            if not selected_deployments and not origins.has_hermes:
                return redactions
        for deployment in selected_deployments:
            if not isinstance(deployment, dict):
                continue
            if not route_has_hermes([deployment], str(deployment.get("model_name") or "")):
                continue
            params = deployment.get("litellm_params") or {}
            if isinstance(params, dict):
                redactions.update(build_hermes_redaction_values(params.get("api_key")))
        return redactions

    def _sanitize_hermes_exception_text(
        self,
        exc: Any,
        *,
        config: Optional[Config] = None,
        model: str = "",
    ) -> str:
        runtime_config = config or self._get_runtime_config()
        redactions = self._hermes_redaction_values_for_model(runtime_config, model)
        if not redactions:
            return str(exc)
        return sanitize_hermes_error_text(exc, redaction_values=redactions)

    def _litellm_redaction_values_for_model(self, config: Config, model: str = "") -> set[str]:
        redactions = self._hermes_redaction_values_for_model(config, model)
        try:
            redactions.update(build_hermes_redaction_values(*get_api_keys_for_model(model, config)))
        except Exception:
            pass
        origins = route_deployment_origins(getattr(config, "llm_model_list", []) or [], model)
        for deployment in (*origins.hermes_deployments, *origins.non_hermes_deployments):
            params = deployment.get("litellm_params") if isinstance(deployment, dict) else None
            if isinstance(params, dict):
                redactions.update(build_hermes_redaction_values(params.get("api_key")))
        return redactions

    def _sanitize_litellm_exception_text(
        self,
        exc: Any,
        *,
        config: Optional[Config] = None,
        model: str = "",
    ) -> str:
        runtime_config = config or self._get_runtime_config()
        redactions = self._litellm_redaction_values_for_model(runtime_config, model)
        sanitized = sanitize_hermes_error_text(exc, redaction_values=redactions)
        return redact_diagnostic_text(sanitized, limit=500)

    def _dispatch_litellm_completion(
        self,
        model: str,
        call_kwargs: Dict[str, Any],
        *,
        config: Config,
        use_channel_router: bool,
        router_model_names: set[str],
    ) -> Any:
        """Dispatch a LiteLLM completion through router or direct fallback.

        外部调用原语（无代理成对补全/零价注册/裸补全）收纳 AnalyzerLLMPort
        （§4.3 A2）；本方法保留全部路由分支策略与 kwargs 整形规则。
        """
        port = _get_analyzer_llm_port()
        origins = route_deployment_origins(config.llm_model_list, model)
        if origins.is_mixed:
            raise RuntimeError("Hermes/non-Hermes mixed generation route is not supported without deployment-level no-proxy client support")
        if origins.is_hermes_only:
            deployment = origins.hermes_deployments[0]
            params = dict(deployment.get("litellm_params") or {})
            api_key = str(params.get("api_key") or "").strip()
            base_url = str(params.get("api_base") or "").strip()
            if is_masked_secret_placeholder(api_key):
                raise RuntimeError("Hermes API key is a masked placeholder and cannot be used for generation")
            timeout = float(call_kwargs.get("timeout") or 30.0)
            hermes_kwargs = dict(call_kwargs)
            hermes_kwargs["model"] = str(params.get("model") or model)
            hermes_kwargs["stream"] = False
            hermes_kwargs.pop("api_key", None)
            hermes_kwargs.pop("api_base", None)
            return port.completion_no_proxy(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout,
                call_kwargs=hermes_kwargs,
            )

        # W4.5：厂商参数规则经 ``GenerationRuntimePort`` 取用，不再从 ``src.config``
        # 转发到 infrastructure。
        wire_models = _get_generation_runtime_port().resolve_fallback_wire_models(
            model, config.llm_model_list
        )
        port.register_fallback_pricing(wire_models)
        effective_kwargs = dict(call_kwargs)
        if use_channel_router and self._router and model in router_model_names:
            return self._router.completion(**effective_kwargs)
        if self._router and model == config.litellm_model and not use_channel_router:
            return self._router.completion(**effective_kwargs)

        keys = get_api_keys_for_model(model, config)
        if keys:
            effective_kwargs["api_key"] = keys[0]
        effective_kwargs.update(extra_litellm_params(model, config))
        return port.completion_direct(**effective_kwargs)

    def _normalize_usage(
        self,
        usage_obj: Any,
        *,
        model: str = "",
        provider: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Normalize usage objects from LiteLLM responses/chunks."""
        if not usage_obj:
            usage = _get_generation_usage_port().attach_hmacs({}, messages) if messages is not None else {}
            return _get_provider_cache_port().filter_telemetry(usage, self._get_runtime_config())
        usage = _get_generation_usage_port().normalize(usage_obj, model=model, provider=provider)
        if messages is not None:
            usage = _get_generation_usage_port().attach_hmacs(usage, messages)
        return _get_provider_cache_port().filter_telemetry(usage, self._get_runtime_config())

    @staticmethod
    def _get_response_field(obj: Any, key: str) -> Any:
        """Read a field from dict-like or object-like LiteLLM payloads."""
        if isinstance(obj, dict):
            return obj.get(key)
        return getattr(obj, key, None)

    def _extract_text_blocks(self, blocks: Any, *, strip: bool = True) -> str:
        """Extract final-answer text from OpenAI-compatible content blocks.

        Some reasoning models (including MiniMax) expose thinking and final
        answer blocks in the same list.  Thinking blocks can also carry a
        ``text`` field, so concatenating every block corrupts structured output
        by prefixing the JSON answer with chain-of-thought text.
        """
        if not blocks:
            return ""

        parts: List[str] = []
        for block in blocks:
            if isinstance(block, str):
                parts.append(block)
                continue

            block_type = ""
            text = None
            if isinstance(block, dict):
                block_type = str(block.get("type") or "").strip().lower()
                text = block.get("text")
                if text is None:
                    text = block.get("content")
            else:
                block_type = str(getattr(block, "type", "") or "").strip().lower()
                text = getattr(block, "text", None)
                if text is None:
                    text = getattr(block, "content", None)

            # Keep untyped legacy blocks for compatibility, but typed blocks
            # must explicitly represent final output text.
            if block_type and block_type not in {"text", "output_text"}:
                continue
            if isinstance(text, str) and text:
                parts.append(text)

        result = "".join(parts)
        return result.strip() if strip else result

    def _extract_completion_text(self, response: Any) -> str:
        """Extract text from non-stream LiteLLM completion responses."""
        choices = self._get_response_field(response, "choices")
        if not choices:
            return ""

        choice = choices[0]
        message = self._get_response_field(choice, "message")

        content_blocks = self._get_response_field(choice, "content_blocks")
        if content_blocks is None and message is not None:
            content_blocks = self._get_response_field(message, "content_blocks")
        block_text = self._extract_text_blocks(content_blocks)
        if block_text:
            return strip_leading_think_wrapper(block_text)

        content = None
        if message is not None:
            content = self._get_response_field(message, "content")
        if content is None:
            content = self._get_response_field(choice, "content")

        if isinstance(content, list):
            return strip_leading_think_wrapper(self._extract_text_blocks(content))
        if isinstance(content, str):
            return strip_leading_think_wrapper(content)
        return str(content).strip() if content is not None else ""

    def _extract_stream_text(self, chunk: Any) -> str:
        """Extract provider-agnostic text delta from a LiteLLM streaming chunk."""
        choices = chunk.get("choices") if isinstance(chunk, dict) else getattr(chunk, "choices", None)
        if not choices:
            return ""

        choice = choices[0]
        delta = choice.get("delta") if isinstance(choice, dict) else getattr(choice, "delta", None)
        message = choice.get("message") if isinstance(choice, dict) else getattr(choice, "message", None)

        content: Any = None
        if isinstance(delta, dict):
            content = delta.get("content")
        elif isinstance(delta, str):
            content = delta
        elif delta is not None:
            content = getattr(delta, "content", None)

        if content is None:
            if isinstance(message, dict):
                content = message.get("content")
            elif message is not None:
                content = getattr(message, "content", None)

        if isinstance(content, list):
            return self._extract_text_blocks(content, strip=False)

        return content if isinstance(content, str) else ""

    def _consume_litellm_stream(
        self,
        stream_response: Any,
        *,
        model: str,
        usage_model: Optional[str] = None,
        provider: Optional[str] = None,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """Consume a LiteLLM stream into a single text payload."""
        chunks: List[str] = []
        usage: Dict[str, Any] = {}
        chars_received = 0
        next_emit_at = 1

        try:
            for chunk in stream_response:
                chunk_usage = _get_generation_usage_port().extract_payload(chunk)
                normalized_usage = self._normalize_usage(
                    chunk_usage,
                    model=usage_model or model,
                    provider=provider,
                )
                if normalized_usage:
                    usage = normalized_usage

                delta_text = self._extract_stream_text(chunk)
                if not delta_text:
                    continue

                chunks.append(delta_text)
                chars_received += len(delta_text)
                if progress_callback and chars_received >= next_emit_at:
                    progress_callback(chars_received)
                    next_emit_at = chars_received + 160
        except Exception as exc:
            raise _LiteLLMStreamError(
                f"{model} stream interrupted: {exc}",
                partial_received=chars_received > 0,
            ) from exc

        response_text = strip_leading_think_wrapper("".join(chunks))
        if not response_text:
            raise _LiteLLMStreamError(
                f"{model} stream returned empty response",
                partial_received=False,
            )

        if progress_callback and chars_received > 0:
            progress_callback(chars_received)

        return response_text, usage

    def get_generation_backend(self, backend_id: Optional[str] = None) -> GenerationBackend:
        """Return the configured generation backend."""
        config = self._get_runtime_config()
        resolved_backend_id = backend_id or self._resolve_generation_backend_config()[0]
        return _get_generation_backend_factory_port().create(
            resolved_backend_id,
            config=config,
            litellm_completion_callable=self._call_litellm_impl,
        )

    def _call_litellm(
        self,
        prompt: str,
        generation_config: dict,
        *,
        system_prompt: Optional[str] = None,
        stream: bool = False,
        stream_progress_callback: Optional[Callable[[int], None]] = None,
        response_validator: Optional[Callable[[str], None]] = None,
        audit_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str, Dict[str, Any]]:
        """Compatibility wrapper around the configured generation backend."""
        preflight_error = self.get_generation_backend_config_error()
        if preflight_error is not None and not self._can_use_generation_fallback(preflight_error):
            raise preflight_error
        backend_id, fallback_backend_id = self._resolve_generation_backend_config()
        try:
            result = self.get_generation_backend(backend_id).generate(
                prompt,
                generation_config,
                system_prompt=system_prompt,
                stream=stream,
                stream_progress_callback=stream_progress_callback,
                response_validator=response_validator,
                audit_context=audit_context,
            )
        except GenerationError as exc:
            if not exc.fallbackable or not fallback_backend_id:
                raise
            try:
                fallback_backend = self.get_generation_backend(fallback_backend_id)
            except GenerationError as fallback_exc:
                raise GenerationError(
                    error_code=fallback_exc.error_code,
                    stage="fallback",
                    retryable=False,
                    fallbackable=False,
                    backend=fallback_backend_id,
                    provider=fallback_exc.provider,
                    details={
                        "primary_error": {
                            "error_code": exc.error_code.value,
                            "backend": exc.backend,
                            "provider": exc.provider,
                            "stage": exc.stage,
                            "details": exc.details,
                        },
                        "fallback_error": fallback_exc.details,
                    },
                ) from fallback_exc
            try:
                result = fallback_backend.generate(
                    prompt,
                    generation_config,
                    system_prompt=system_prompt,
                    stream=stream,
                    stream_progress_callback=stream_progress_callback,
                    response_validator=response_validator,
                    audit_context=audit_context,
                )
            except _AllModelsFailedError:
                raise
            except GenerationError as fallback_exc:
                raise GenerationError(
                    error_code=fallback_exc.error_code,
                    stage="fallback",
                    retryable=False,
                    fallbackable=False,
                    backend=fallback_backend_id,
                    provider=fallback_exc.provider,
                    details={
                        "reason": "fallback_backend_failed",
                        "primary_error": {
                            "error_code": exc.error_code.value,
                            "backend": exc.backend,
                            "provider": exc.provider,
                            "stage": exc.stage,
                            "details": exc.details,
                        },
                        "fallback_error": {
                            "error_code": fallback_exc.error_code.value,
                            "backend": fallback_exc.backend,
                            "provider": fallback_exc.provider,
                            "stage": fallback_exc.stage,
                            "details": fallback_exc.details,
                        },
                    },
                ) from fallback_exc
            except Exception as fallback_exc:
                raise GenerationError(
                    error_code=GenerationErrorCode.UNKNOWN_BACKEND_ERROR,
                    stage="fallback",
                    retryable=False,
                    fallbackable=False,
                    backend=fallback_backend_id,
                    provider=fallback_backend_id,
                    details={
                        "reason": "fallback_backend_failed",
                        "primary_error": {
                            "error_code": exc.error_code.value,
                            "backend": exc.backend,
                            "provider": exc.provider,
                            "stage": exc.stage,
                            "details": exc.details,
                        },
                        "fallback_error": str(fallback_exc),
                    },
                ) from fallback_exc
        return result.text, result.model, result.usage

    def _call_litellm_impl(
        self,
        prompt: str,
        generation_config: dict,
        *,
        system_prompt: Optional[str] = None,
        stream: bool = False,
        stream_progress_callback: Optional[Callable[[int], None]] = None,
        response_validator: Optional[Callable[[str], None]] = None,
        audit_context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str, Dict[str, Any]]:
        """Call LLM via litellm with fallback across configured models.

        When channels/YAML are configured, every model goes through the Router
        (which handles per-model key selection, load balancing, and retries).
        In legacy mode, the primary model may use the Router while fallback
        models fall back to direct completion via AnalyzerLLMPort
        （§4.3 A2：裸补全/无代理补全/Router 构造均经端口，见 _dispatch_litellm_completion）。

        Args:
            prompt: User prompt text.
            generation_config: Dict with optional keys: temperature, max_output_tokens, max_tokens.
            response_validator: Optional callable that accepts the raw response text and raises
                an exception if the response is unacceptable (e.g. not valid JSON).  When it
                raises, the current model is treated as failed and the next fallback model is
                tried.  If all models fail validation, :class:`_AllModelsFailedError` is raised
                with ``last_response_text`` set to the last raw response received.

        Returns:
            Tuple of (response text, model_used, usage). On success model_used is the full model
            name and usage is a dict with prompt_tokens, completion_tokens, total_tokens.
        """
        config = self._get_runtime_config()
        max_tokens = (
            generation_config.get('max_output_tokens')
            or generation_config.get('max_tokens')
            or 8192
        )
        requested_temperature = generation_config.get('temperature', 0.7)
        requested_timeout = generation_config.get("timeout")

        models_to_try = [config.litellm_model] + (config.litellm_fallback_models or [])
        models_to_try = [m for m in models_to_try if m]

        use_channel_router = self._has_channel_config(config)

        last_error = None
        last_response_text: Optional[str] = None
        last_model: Optional[str] = None
        last_usage: Dict[str, Any] = {}
        effective_system_prompt = system_prompt or self.TEXT_SYSTEM_PROMPT
        router_model_names = set(get_configured_llm_models(config.llm_model_list))
        for model in models_to_try:
            origins = route_deployment_origins(config.llm_model_list, model)
            model_stream = bool(stream and not origins.has_hermes)
            recovery_model_list = config.llm_model_list
            legacy_router_model_list = getattr(self, "_legacy_router_model_list", None) or []
            if legacy_router_model_list and model == config.litellm_model and not use_channel_router:
                recovery_model_list = legacy_router_model_list
            usage_model, usage_provider = resolved_model_provider_identity(model, recovery_model_list)

            try:
                def _attach_usage_audit(
                    usage: Dict[str, Any],
                    messages: List[Dict[str, Any]],
                ) -> Dict[str, Any]:
                    if audit_context is None:
                        return _get_provider_cache_port().filter_telemetry(
                            _get_generation_usage_port().attach_hmacs(usage, messages),
                            config,
                        )
                    effective_audit_context = dict(audit_context)
                    effective_audit_context["provider"] = usage_provider
                    effective_audit_context["transport"] = (
                        effective_audit_context.get("transport") or "litellm"
                    )
                    return _get_provider_cache_port().filter_telemetry(
                        _get_generation_usage_port().attach_legacy_audit(
                            usage,
                            messages,
                            effective_audit_context,
                        ),
                        config,
                    )

                model_short = model.split("/")[-1] if "/" in model else model
                extra = _get_generation_runtime_port().thinking_extra_body(model_short)
                call_kwargs: Dict[str, Any] = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": effective_system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": max_tokens,
                }
                if requested_timeout not in (None, ""):
                    call_kwargs["timeout"] = requested_timeout
                if extra:
                    call_kwargs["extra_body"] = extra
                uses_router = (
                    (use_channel_router and self._router and model in router_model_names)
                    or (self._router and model == config.litellm_model and not use_channel_router)
                )
                if not uses_router:
                    try:
                        keys = get_api_keys_for_model(model, config)
                    except AttributeError:
                        keys = []
                    if keys:
                        call_kwargs["api_key"] = keys[0]
                    try:
                        call_kwargs.update(extra_litellm_params(model, config))
                    except AttributeError:
                        pass
                call_kwargs = _get_generation_runtime_port().apply_params(
                    call_kwargs,
                    model,
                    requested_temperature,
                    model_list=recovery_model_list,
                )
                route_context = _get_provider_cache_port().build_route_context(
                    model=model,
                    provider=usage_provider,
                    call_kwargs=call_kwargs,
                    model_list=recovery_model_list,
                    call_type="analysis",
                )
                hint_result = _get_provider_cache_port().apply_hints(call_kwargs, route_context, config)
                call_kwargs = hint_result.call_kwargs
                if requested_timeout not in (None, ""):
                    call_kwargs["timeout"] = requested_timeout
                if hint_result.diagnostics:
                    logger.debug("[PromptCache] %s", hint_result.diagnostics)

                _stream_text: Optional[str] = None
                _stream_usage: Dict[str, Any] = {}

                if model_stream:
                    try:
                        stream_response = call_litellm_with_param_recovery(
                            lambda kwargs: self._dispatch_litellm_completion(
                                model,
                                kwargs,
                                config=config,
                                use_channel_router=use_channel_router,
                                router_model_names=router_model_names,
                            ),
                            model=model,
                            call_kwargs={**call_kwargs, "stream": True},
                            model_list=recovery_model_list,
                            cache_recovery=False,
                            logger=logger,
                        )
                        _stream_text, _stream_usage = self._consume_litellm_stream(
                            stream_response,
                            model=model,
                            usage_model=usage_model,
                            provider=usage_provider,
                            progress_callback=stream_progress_callback,
                        )
                    except _LiteLLMStreamError as exc:
                        safe_error = self._sanitize_litellm_exception_text(exc, config=config, model=model)
                        if exc.partial_received:
                            logger.warning(
                                "[LiteLLM] %s stream failed after partial output, retrying non-stream for same model: %s",
                                model,
                                safe_error,
                            )
                        else:
                            logger.warning(
                                "[LiteLLM] %s stream unavailable before first chunk, falling back to non-stream: %s",
                                model,
                                safe_error,
                            )
                        last_error = RuntimeError(f"{type(exc).__name__}: {safe_error}")
                    except Exception as exc:
                        safe_error = self._sanitize_litellm_exception_text(exc, config=config, model=model)
                        logger.warning(
                            "[LiteLLM] %s stream request failed before first chunk, falling back to non-stream: %s",
                            model,
                            safe_error,
                        )

                if _stream_text is not None:
                    last_response_text = _stream_text
                    last_model = model
                    _stream_usage = _attach_usage_audit(_stream_usage, call_kwargs["messages"])
                    last_usage = _stream_usage
                    if response_validator is not None:
                        response_validator(_stream_text)
                    return _stream_text, model, _stream_usage

                response = call_litellm_with_param_recovery(
                    lambda kwargs: self._dispatch_litellm_completion(
                        model,
                        kwargs,
                        config=config,
                        use_channel_router=use_channel_router,
                        router_model_names=router_model_names,
                    ),
                    model=model,
                    call_kwargs=call_kwargs,
                    model_list=recovery_model_list,
                    logger=logger,
                )

                content = self._extract_completion_text(response)
                if content:
                    usage_messages = None if audit_context is not None else call_kwargs["messages"]
                    usage = self._normalize_usage(
                        _get_generation_usage_port().extract_payload(response),
                        model=usage_model or model,
                        provider=usage_provider,
                        messages=usage_messages,
                    )
                    if audit_context is not None:
                        usage = _attach_usage_audit(usage, call_kwargs["messages"])
                    last_response_text = content
                    last_model = model
                    last_usage = usage
                    if response_validator is not None:
                        response_validator(content)
                    return (content, model, usage)
                raise ValueError("LLM returned empty response")

            except Exception as e:
                safe_error = self._sanitize_litellm_exception_text(e, config=config, model=model)
                logger.warning("[LiteLLM] %s failed: %s", model, safe_error)
                last_error = RuntimeError(f"{type(e).__name__}: {safe_error}")
                continue

        raise _AllModelsFailedError(
            f"All LLM models failed (tried {len(models_to_try)} model(s)). Last error: {last_error}",
            last_response_text=last_response_text,
            last_model=last_model,
            last_usage=last_usage,
        )

    def generate_text(
        self,
        prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> Optional[str]:
        """Public entry point for free-form text generation.

        External callers (e.g. MarketAnalyzer) must use this method instead of
        calling _call_litellm() directly or accessing private attributes such as
        _litellm_available, _router, _model, _use_openai, or _use_anthropic.

        Args:
            prompt:      Text prompt to send to the LLM.
            max_tokens:  Maximum tokens in the response (default 2048).
            temperature: Sampling temperature (default 0.7).

        Returns:
            Response text, or None if the LLM call fails (error is logged).
        """
        try:
            result = self._call_litellm(
                prompt,
                generation_config={"max_tokens": max_tokens, "temperature": temperature},
            )
            if isinstance(result, tuple):
                text, model_used, usage = result
                usage_port = _get_generation_usage_port()
                if usage_port.should_persist(usage):
                    usage_port.persist(usage, model_used, call_type="market_review")
                return text
            return result
        except GenerationError:
            raise
        except Exception as exc:
            logger.error("[generate_text] LLM call failed: %s", exc)
            return None

    def analyze(
        self,
        context: Dict[str, Any],
        news_context: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        stream_progress_callback: Optional[Callable[[int], None]] = None,
        analysis_context_pack_summary: Optional[str] = None,
    ) -> AnalysisResult:
        """
        分析单只股票

        流程：
        1. 格式化输入数据（技术面 + 新闻）
        2. 调用 Gemini API（带重试和模型切换）
        3. 解析 JSON 响应
        4. 返回结构化结果

        Args:
            context: 从 storage.get_analysis_context() 获取的上下文数据
            news_context: 预先搜索的新闻内容（可选）

        Returns:
            AnalysisResult 对象
        """
        def _emit_progress(progress: int, message: str) -> None:
            if progress_callback is None:
                return
            try:
                progress_callback(progress, message)
            except Exception as exc:
                logger.debug("[analyzer] progress callback skipped: %s", exc)

        code = context.get('code', 'Unknown')
        config = self._get_runtime_config()
        report_language = normalize_report_language(getattr(config, "report_language", "zh"))
        system_prompt = self._get_analysis_system_prompt(report_language, stock_code=code)
        skill_instructions, default_skill_policy, use_legacy_default_prompt = self._get_skill_prompt_sections()

        # 请求前增加延时（防止连续请求触发限流）
        request_delay = config.gemini_request_delay
        if request_delay > 0:
            logger.debug(f"[LLM] 请求前等待 {request_delay:.1f} 秒...")
            _emit_progress(65, f"{code}：LLM 请求前等待 {request_delay:.1f} 秒")
            time.sleep(request_delay)

        # 优先从上下文获取股票名称（由 main.py 传入）
        name = context.get('stock_name')
        if not name or name.startswith('股票'):
            # 备选：从 realtime 中获取
            if 'realtime' in context and context['realtime'].get('name'):
                name = context['realtime']['name']
            else:
                # 最后从映射表获取
                name = STOCK_NAME_MAP.get(code, f'股票{code}')

        backend_error = self.get_generation_backend_config_error()
        if backend_error is not None and not self._can_use_generation_fallback(backend_error):
            details = backend_error.details or {}
            field = str(details.get("field") or "GENERATION_BACKEND")
            requested_backend = str(details.get("requested_backend") or backend_error.backend)
            reason = str(details.get("reason") or backend_error.error_code.value)
            if report_language == "en":
                summary = (
                    "AI analysis is unavailable because the generation backend "
                    f"cannot start: {backend_error.error_code.value}."
                )
                risk_warning = (
                    f"Check {field}={requested_backend} ({reason}) or set a valid "
                    "backend/fallback before retrying."
                )
            elif report_language == "ko":
                summary = (
                    "생성 백엔드를 시작할 수 없어 AI 분석을 사용할 수 없습니다: "
                    f"{backend_error.error_code.value}."
                )
                risk_warning = (
                    f"{field}={requested_backend} ({reason})를 확인하거나 유효한 "
                    "백엔드/폴백을 설정한 뒤 다시 시도하세요."
                )
            else:
                summary = (
                    "AI 分析功能不可用：生成后端无法启动，"
                    f"{backend_error.error_code.value}。"
                )
                risk_warning = (
                    f"请检查 {field}={requested_backend}（{reason}），"
                    "或配置有效后端/回退后重试。"
                )
            return AnalysisResult(
                code=code,
                name=name,
                sentiment_score=50,
                trend_prediction=localize_trend_prediction('震荡', report_language),
                operation_advice=localize_operation_advice('持有', report_language),
                confidence_level=localize_confidence_level('低', report_language),
                analysis_summary=summary,
                risk_warning=risk_warning,
                success=False,
                error_message=(
                    f"{backend_error.error_code.value}: {field}={requested_backend}"
                ),
                model_used=None,
                report_language=report_language,
            )

        # 如果模型不可用，返回默认结果
        if not self.is_available():
            return AnalysisResult(
                code=code,
                name=name,
                sentiment_score=50,
                trend_prediction=localize_trend_prediction('震荡', report_language),
                operation_advice=localize_operation_advice('持有', report_language),
                confidence_level=localize_confidence_level('低', report_language),
                analysis_summary=_localized_text(
                    report_language,
                    en='AI analysis is unavailable because no API key is configured.',
                    zh='AI 分析功能未启用（未配置 API Key）',
                    ko='API 키가 설정되지 않아 AI 분석을 사용할 수 없습니다.',
                ),
                risk_warning=_localized_text(
                    report_language,
                    en='Configure an LLM API key (GEMINI_API_KEY/ANTHROPIC_API_KEY/OPENAI_API_KEY) and retry.',
                    zh='请配置 LLM API Key（GEMINI_API_KEY/ANTHROPIC_API_KEY/OPENAI_API_KEY）后重试',
                    ko='LLM API 키(GEMINI_API_KEY/ANTHROPIC_API_KEY/OPENAI_API_KEY)를 설정한 뒤 다시 시도하세요.',
                ),
                success=False,
                error_message=_localized_text(
                    report_language,
                    en='LLM API key is not configured',
                    zh='LLM API Key 未配置',
                    ko='LLM API 키가 설정되지 않았습니다',
                ),
                model_used=None,
                report_language=report_language,
            )

        try:
            # 格式化输入（包含技术面数据和新闻）
            prompt = self._format_prompt(
                context,
                name,
                news_context,
                report_language=report_language,
                analysis_context_pack_summary=analysis_context_pack_summary,
            )
            legacy_audit_context = {
                "language": report_language,
                "market_group": _legacy_market_group(code),
                "analysis_mode": "stock_analysis",
                "legacy_prompt_mode": "legacy_default" if use_legacy_default_prompt else "skill_aware",
                "skill_config": {
                    "skill_instructions": skill_instructions,
                    "default_skill_policy": default_skill_policy,
                    "use_legacy_default_prompt": use_legacy_default_prompt,
                },
                "transport": "litellm",
                "dynamic_markers": _legacy_audit_marker_specs(
                    context,
                    code=code,
                    stock_name=name,
                    report_language=report_language,
                    news_context=news_context,
                    analysis_context_pack_summary=analysis_context_pack_summary,
                ),
            }

            config = self._get_runtime_config()
            backend_id, _fallback_backend_id = self._resolve_generation_backend_config()
            model_name = config.litellm_model or "unknown"
            if backend_id in LOCAL_CLI_GENERATION_BACKEND_IDS:
                model_name = backend_id
                legacy_audit_context["transport"] = backend_id
            logger.info(f"========== AI 分析 {name}({code}) ==========")
            logger.info(f"[LLM配置] 模型: {model_name}")
            logger.info(f"[LLM配置] Prompt 长度: {len(prompt)} 字符")
            logger.info(f"[LLM配置] 是否包含新闻: {'是' if news_context else '否'}")

            # 本地 CLI backend 是进程执行能力，不记录完整 prompt。
            if backend_id in LOCAL_CLI_GENERATION_BACKEND_IDS:
                prompt_preview = redact_diagnostic_text(prompt, limit=500)
            else:
                prompt_preview = prompt[:500] + "..." if len(prompt) > 500 else prompt
            logger.info(f"[LLM Prompt 预览]\n{prompt_preview}")
            if backend_id not in LOCAL_CLI_GENERATION_BACKEND_IDS:
                logger.debug(f"=== 完整 Prompt ({len(prompt)}字符) ===\n{prompt}\n=== End Prompt ===")

            # 设置生成配置
            generation_config = {
                "temperature": config.llm_temperature,
                "max_output_tokens": 8192,
            }

            logger.info(f"[LLM调用] 开始调用 {model_name}...")
            _emit_progress(68, f"{name}：LLM 已接收请求，等待响应")

            # 使用 litellm 调用（支持完整性校验重试）
            current_prompt = prompt
            retry_count = 0
            max_retries = config.report_integrity_retry if config.report_integrity_enabled else 0

            while True:
                start_time = time.time()
                try:
                    response_text, model_used, llm_usage = self._call_litellm(
                        current_prompt,
                        generation_config,
                        system_prompt=system_prompt,
                        stream=True,
                        stream_progress_callback=stream_progress_callback,
                        response_validator=self._validate_json_response,
                        audit_context=legacy_audit_context,
                    )
                except _AllModelsFailedError as exc:
                    if exc.last_response_text is not None:
                        logger.warning(
                            "[LLM JSON] %s(%s): all models returned invalid JSON, using text fallback",
                            name,
                            code,
                        )
                        response_text = exc.last_response_text
                        model_used = exc.last_model
                        llm_usage = exc.last_usage
                    else:
                        raise
                elapsed = time.time() - start_time

                # 记录响应信息
                logger.info(
                    f"[LLM返回] {model_name} 响应成功, 耗时 {elapsed:.2f}s, 响应长度 {len(response_text)} 字符"
                )
                if backend_id in LOCAL_CLI_GENERATION_BACKEND_IDS:
                    response_preview = redact_diagnostic_text(response_text, limit=300)
                else:
                    response_preview = response_text[:300] + "..." if len(response_text) > 300 else response_text
                logger.info(f"[LLM返回 预览]\n{response_preview}")
                if backend_id not in LOCAL_CLI_GENERATION_BACKEND_IDS:
                    logger.debug(
                        f"=== {model_name} 完整响应 ({len(response_text)}字符) ===\n{response_text}\n=== End Response ==="
                    )
                # Keep parser/retry progress monotonic so task progress/message never "goes backward".
                parse_progress = min(99, 93 + retry_count * 2)
                _emit_progress(parse_progress, f"{name}：LLM 返回完成，正在解析 JSON")

                # 解析响应
                result = self._parse_response(response_text, code, name)
                result.raw_response = response_text
                result.search_performed = bool(news_context)
                result.market_snapshot = self._build_market_snapshot(context)
                result.model_used = model_used
                result.report_language = report_language
                normalize_chip_structure_availability(result, context.get("chip"))

                # 内容完整性校验（可选）
                if not config.report_integrity_enabled:
                    break
                require_phase_decision = isinstance(context.get("market_phase_context"), dict)
                pass_integrity, missing_fields = self._check_content_integrity(
                    result,
                    require_phase_decision=require_phase_decision,
                )
                if pass_integrity:
                    break
                if retry_count < max_retries:
                    current_prompt = self._build_integrity_retry_prompt(
                        prompt,
                        response_text,
                        missing_fields,
                        report_language=report_language,
                    )
                    retry_count += 1
                    logger.info(
                        "[LLM完整性] 必填字段缺失 %s，第 %d 次补全重试",
                        missing_fields,
                        retry_count,
                    )
                    retry_progress = min(99, 92 + retry_count * 2)
                    _emit_progress(
                        retry_progress,
                        f"{name}：报告字段不完整，正在补全重试（{retry_count}/{max_retries}）",
                    )
                else:
                    self._apply_placeholder_fill(result, missing_fields)
                    logger.warning(
                        "[LLM完整性] 必填字段缺失 %s，已占位补全，不阻塞流程",
                        missing_fields,
                    )
                    break

            usage_port = _get_generation_usage_port()
            if usage_port.should_persist(llm_usage):
                usage_port.persist(llm_usage, model_used, call_type="analysis", stock_code=code)

            logger.info(f"[LLM解析] {name}({code}) 分析完成: {result.trend_prediction}, 评分 {result.sentiment_score}")

            return result

        except Exception as e:
            safe_error = self._sanitize_hermes_exception_text(e)
            logger.error("AI 分析 %s(%s) 失败: %s", name, code, safe_error)
            return AnalysisResult(
                code=code,
                name=name,
                sentiment_score=50,
                trend_prediction=localize_trend_prediction('震荡', report_language),
                operation_advice=localize_operation_advice('持有', report_language),
                confidence_level=localize_confidence_level('低', report_language),
                analysis_summary=_localized_text(
                    report_language,
                    en=f'Analysis failed: {safe_error[:100]}',
                    zh=f'分析过程出错: {safe_error[:100]}',
                    ko=f'분석 중 오류가 발생했습니다: {safe_error[:100]}',
                ),
                risk_warning=_localized_text(
                    report_language,
                    en='Analysis failed. Please retry later or review manually.',
                    zh='分析失败，请稍后重试或手动分析',
                    ko='분석에 실패했습니다. 잠시 후 다시 시도하거나 수동으로 검토하세요.',
                ),
                success=False,
                error_message=safe_error,
                model_used=None,
                report_language=report_language,
            )

    def _format_prompt(
        self,
        context: Dict[str, Any],
        name: str,
        news_context: Optional[str] = None,
        report_language: str = "zh",
        analysis_context_pack_summary: Optional[str] = None,
    ) -> str:
        return AnalysisPromptBuilder(self._get_runtime_config, self._get_skill_prompt_sections).format_prompt(context=context, name=name, news_context=news_context, report_language=report_language, analysis_context_pack_summary=analysis_context_pack_summary)

    _format_volume = staticmethod(AnalysisPromptBuilder.format_volume)

    _format_amount = staticmethod(AnalysisPromptBuilder.format_amount)

    _format_percent = staticmethod(AnalysisPromptBuilder.format_percent)

    _format_price = staticmethod(AnalysisPromptBuilder.format_price)

    def _build_market_snapshot(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return AnalysisPromptBuilder(self._get_runtime_config, self._get_skill_prompt_sections).build_market_snapshot(context=context)

    def _check_content_integrity(
        self,
        result: AnalysisResult,
        *,
        require_phase_decision: bool = False,
    ) -> Tuple[bool, List[str]]:
        """Delegate to module-level check_content_integrity."""
        return check_content_integrity(result, require_phase_decision=require_phase_decision)

    def _build_integrity_complement_prompt(self, missing_fields: List[str], report_language: str = "zh") -> str:
        return AnalysisPromptBuilder(self._get_runtime_config, self._get_skill_prompt_sections).build_integrity_complement_prompt(missing_fields=missing_fields, report_language=report_language)

    def _build_integrity_retry_prompt(
        self,
        base_prompt: str,
        previous_response: str,
        missing_fields: List[str],
        report_language: str = "zh",
    ) -> str:
        return AnalysisPromptBuilder(self._get_runtime_config, self._get_skill_prompt_sections).build_integrity_retry_prompt(base_prompt=base_prompt, previous_response=previous_response, missing_fields=missing_fields, report_language=report_language)

    def _apply_placeholder_fill(self, result: AnalysisResult, missing_fields: List[str]) -> None:
        """Delegate to module-level apply_placeholder_fill."""
        apply_placeholder_fill(result, missing_fields)

    def _extract_analysis_json_object(self, response_text: str) -> Tuple[str, Dict[str, Any]]:
        return AnalysisResponseParser(self._get_runtime_config, self._resolve_generation_backend_config).extract_analysis_json_object(response_text=response_text)

    def _load_analysis_json_candidate(self, json_str: str) -> Dict[str, Any]:
        return AnalysisResponseParser(self._get_runtime_config, self._resolve_generation_backend_config).load_analysis_json_candidate(json_str=json_str)

    _contains_embedded_json_object = staticmethod(AnalysisResponseParser.contains_embedded_json_object)

    def _validate_analysis_minimal_contract(self, data: Dict[str, Any]) -> None:
        return AnalysisResponseParser(self._get_runtime_config, self._resolve_generation_backend_config).validate_analysis_minimal_contract(data=data)

    def _generation_validation_error(
        self,
        error_code: GenerationErrorCode,
        *,
        reason: str,
        message: str,
    ) -> GenerationError:
        return AnalysisResponseParser(self._get_runtime_config, self._resolve_generation_backend_config).generation_validation_error(error_code=error_code, reason=reason, message=message)

    def _parse_response(
        self,
        response_text: str,
        code: str,
        name: str
    ) -> AnalysisResult:
        return AnalysisResponseParser(self._get_runtime_config, self._resolve_generation_backend_config).parse_response(response_text=response_text, code=code, name=name)

    def _fix_json_string(self, json_str: str) -> str:
        return AnalysisResponseParser(self._get_runtime_config, self._resolve_generation_backend_config).fix_json_string(json_str=json_str)

    def _validate_json_response(self, text: str) -> None:
        return AnalysisResponseParser(self._get_runtime_config, self._resolve_generation_backend_config).validate_json_response(text=text)

    def _parse_text_response(
        self,
        response_text: str,
        code: str,
        name: str
    ) -> AnalysisResult:
        return AnalysisResponseParser(self._get_runtime_config, self._resolve_generation_backend_config).parse_text_response(response_text=response_text, code=code, name=name)

    def batch_analyze(
        self,
        contexts: List[Dict[str, Any]],
        delay_between: float = 2.0
    ) -> List[AnalysisResult]:
        """
        批量分析多只股票

        注意：为避免 API 速率限制，每次分析之间会有延迟

        Args:
            contexts: 上下文数据列表
            delay_between: 每次分析之间的延迟（秒）

        Returns:
            AnalysisResult 列表
        """
        results = []

        for i, context in enumerate(contexts):
            if i > 0:
                logger.debug(f"等待 {delay_between} 秒后继续...")
                time.sleep(delay_between)

            result = self.analyze(context)
            results.append(result)

        return results


# 便捷函数
def get_analyzer() -> GeminiAnalyzer:
    """获取 LLM 分析器实例"""
    return GeminiAnalyzer()


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)

    # 模拟上下文数据
    test_context = {
        'code': '600519',
        'date': '2026-01-09',
        'today': {
            'open': 1800.0,
            'high': 1850.0,
            'low': 1780.0,
            'close': 1820.0,
            'volume': 10000000,
            'amount': 18200000000,
            'pct_chg': 1.5,
            'ma5': 1810.0,
            'ma10': 1800.0,
            'ma20': 1790.0,
            'volume_ratio': 1.2,
        },
        'ma_status': '多头排列 📈',
        'volume_change_ratio': 1.3,
        'price_change_ratio': 1.5,
    }

    analyzer = GeminiAnalyzer()

    if analyzer.is_available():
        print("=== AI 分析测试 ===")
        result = analyzer.analyze(test_context)
        print(f"分析结果: {result.to_dict()}")
    else:
        print("Gemini API 未配置，跳过测试")
