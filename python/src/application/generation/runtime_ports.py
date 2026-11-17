# -*- coding: utf-8 -*-
"""生成链路运行时端口契约（application 层，R2-A3）。

分层说明（R2 §5.5）：``src/application/{analysis,runtime}`` 对生成实现
（现 ``src/infrastructure/generation/`` 的 backend factory / generation_params /
errors / usage / provider_cache / local_cli_backend）的依赖经本模块 4 个端口收口，由
``src/infrastructure/generation/adapters/`` 提供实现，``src/bootstrap/generation.py``
的 ``configure_generation_runtime()`` 装配（T5f ``ConfigProbePort`` 同型）。

端口只收纳**真正发生外部调用或跨进程状态读写**的原语；纯规则已分别下沉
``src/domain/generation/{hermes_rules,diagnostics,response_content,local_cli_policy}``。
异常与返回值语义原样穿透，不做包装：上游以原始异常类型/文案做参数恢复判定与
诊断脱敏，包装即漂移语义。

装配形态为 **seam 工厂**而非构造注入（R2 §5.5）：``Analyzer`` 的调用点分散在
stream / non-stream / audit 三条路径，且大量测试直接构造服务，构造注入会放大
改动面；模块级 ``set_*_port`` + 未装配 fail-fast 与既有 ``set_analyzer_llm_port``
先例一致。
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Protocol

from src.application.generation.ports import (
    GenerationBackend,
    GenerationCapabilities,
    GenerationError,
)


class GenerationBackendFactoryPort(Protocol):
    """生成后端装配端口（唯一 ``new 实现类`` 的跨层位置）。"""

    def create(
        self,
        backend_id: str,
        *,
        config: Any,
        litellm_completion_callable: Optional[Callable[..., Any]] = None,
    ) -> GenerationBackend:
        """按 backend_id 装配 ``GenerationBackend`` 实现。

        未知 backend 与 missing callable 均抛 ``GenerationError``（结构化错误码
        ``BACKEND_NOT_CONFIGURED``），语义与拆分前一致。
        """
        ...


class GenerationRuntimePort(Protocol):
    """生成运行时原语端口（参数整形 / 恢复重试 / local CLI 配置探测）。"""

    def apply_params(
        self,
        call_kwargs: Dict[str, Any],
        model: str,
        temperature: Optional[float],
        *,
        default_temperature: float = 0.7,
        model_list: Optional[list] = None,
        request_overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """应用 model 兼容的生成参数（temperature 直令 + 进程内恢复缓存）。"""
        ...

    def completion_with_recovery(
        self,
        call: Callable[[Dict[str, Any]], Any],
        *,
        model: str,
        call_kwargs: Dict[str, Any],
        model_list: Optional[list] = None,
        cache_recovery: bool = True,
        logger: Any = None,
        log_label: str = "[LiteLLM]",
    ) -> Any:
        """调用一次；命中显式生成参数错误时按 recovery 重试一次并缓存。

        SDK 异常原样穿透（非参数类错误直接抛出，不改写类型或文案）。
        """
        ...

    def resolve_preset(self, backend_id: str) -> Any:
        """解析 local CLI 安全预设；未知预设抛 ``UNSAFE_CONFIG``。"""
        ...

    def config_error(self, config: Any, backend_id: str) -> Optional[GenerationError]:
        """按预设构造 local CLI 后端并返回可执行文件/配置校验错误（不执行 prompt）。"""
        ...

    def capabilities(self) -> GenerationCapabilities:
        """local CLI 后端能力表（实现类类属性，唯一真源）。"""
        ...

    # --- W4.5：厂商手写参数规则（application 不得直连 infra）---
    def thinking_extra_body(self, model: str) -> Optional[Dict[str, Any]]:
        """返回模型的 thinking ``extra_body`` 载荷；无需显式开启时返回 ``None``。

        规则表（deepseek-reasoner / deepseek-chat 等）属厂商语义，留在 infra；
        用例层经本端口取用，迁移前走 ``src.config`` 的延迟薄委托。
        """
        ...

    def resolve_fallback_wire_models(
        self,
        model: str,
        model_list: Optional[list] = None,
    ) -> list:
        """返回某配置别名可达的全部 LiteLLM wire 模型（用于回退定价注册）。"""
        ...


class GenerationUsagePort(Protocol):
    """用量遥测端口（整形 + HMAC 附加，后者触达 secret 文件 IO）。"""

    def normalize(
        self,
        usage_obj: Any,
        *,
        model: str = "",
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """归一化 provider usage 对象，不改变请求/响应行为。"""
        ...

    def extract_payload(self, response: Any) -> Any:
        """按 public → private 顺序取 usage 载荷（含 streaming chunk 兜底）。"""
        ...

    def attach_hmacs(self, usage: Dict[str, Any], messages: Any) -> Dict[str, Any]:
        """附加消息级 HMAC 字段（不落 prompt 原文）。"""
        ...

    def attach_legacy_audit(
        self,
        usage: Dict[str, Any],
        messages: Any,
        audit_context: Any = None,
    ) -> Dict[str, Any]:
        """附加 P0.5a legacy 消息稳定性诊断。"""
        ...

    def should_persist(self, usage: Any) -> bool:
        """判断是否应作为 provider telemetry 落库。"""
        ...

    def persist(
        self,
        usage: Any,
        model: str,
        *,
        call_type: str,
        stock_code: Optional[str] = None,
    ) -> None:
        """将一条 LLM 用量遥测写入持久层（fire-and-forget，不抛异常）。

        调用方须先用 :meth:`should_persist` 判定；``call_type`` / ``stock_code``
        为落库维度标签，取值语义与既有 ``persist_llm_usage`` 逐字一致。
        """
        ...


class ProviderCachePort(Protocol):
    """provider prompt-cache 端口（能力表 + 键整形 + 遥测过滤）。"""

    def apply_hints(self, call_kwargs: Dict[str, Any], route_context: Any, config: Any) -> Any:
        """按能力表写入 prompt-cache 提示，返回含 ``call_kwargs``/``diagnostics`` 的结果。"""
        ...

    def build_route_context(
        self,
        *,
        model: str,
        provider: Any,
        call_kwargs: Dict[str, Any],
        model_list: Any,
        call_type: str,
    ) -> Any:
        """构造 prompt-cache 路由上下文（不透明对象）。"""
        ...

    def filter_telemetry(self, usage: Dict[str, Any], config: Any) -> Dict[str, Any]:
        """按配置过滤/标注 prompt-cache 遥测字段。"""
        ...
