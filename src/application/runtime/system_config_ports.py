# -*- coding: utf-8 -*-
"""SystemConfigService 运行时外部依赖端口（application 层契约，§4.3 拆分 F3）。

分层说明（ARCHITECTURE_TARGET §4.3）：``system_config_service`` 对 LLM 渠道探测
（OpenAI 兼容 ``/models`` HTTP 发现、litellm 补全试调用、Hermes 无代理客户端、
事件告警规则运行时校验、运行态 temperature 读取）、通知渠道试发（14 个 sender SDK）
与进程级单例重置（``src.application.agent.tools.data_tools`` / ``src.application.intelligence.search_service``）的依赖
经本端口绑定 ``src/infrastructure/providers/system_config_runtime.py`` 适配器，由
bootstrap ``configure_system_config_runtime`` 装配（T5e AlphaSiftRuntimePort 同型）。

用例层保留全部策略校验、异常分类/脱敏与结果整形规则，端口只收纳"真正发生外部
调用"的原语。``fetch_models_snapshot`` / ``litellm_completion`` /
``completion_with_recovery`` 以不透明 ``Any`` 返回传输/SDK 响应对象（T5e
``create_hotspot_provider`` 同型），网络与 SDK 异常原样穿透端口：上游异常分类
（``_classify_llm_exception`` 等）以原始异常类型与文案为判定输入，包装会漂移语义。
``litellm_completion`` 在调用时解析 ``litellm.completion`` 属性，保持既有
monkey-patch 测试语义（T5e-0b 拍板）。``config`` 类参数按 ``Any`` 收口，避免
application 契约钉死 ``src.config.Config`` 具体类型（T5b 同策）。
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any, Dict, List, Protocol


class EventAlertRulesValidationError(ValueError):
    """事件告警规则校验失败（由 ``src.application.alert.events`` 运行期校验收纳适配器抛出）。

    继承 ``ValueError`` 保持与拆分前一致的捕获面；``rule_index`` 复刻原实现
    ``for rule_index, rule in enumerate(...)`` 循环变量的失败规则序号语义
    （解析阶段即失败时为 0，调用方按 ``rule_index or 1`` 兜底）。
    """

    def __init__(self, message: str, *, rule_index: int = 0):
        super().__init__(message)
        self.rule_index = rule_index


class ConfigProbePort(Protocol):
    """LLM 渠道探测/运行态配置读取端口。"""

    def fetch_models_snapshot(
        self,
        *,
        url: str,
        headers: Dict[str, str],
        timeout_seconds: float,
        trust_env: bool,
    ) -> Any:
        """GET OpenAI 兼容 ``/models`` 端点，返回原始响应对象。

        ``trust_env=False`` 走 ``Session(trust_env=False)``（Hermes 保留渠道忽略
        进程代理环境），``True`` 走裸 ``requests.get``；``allow_redirects=False``。
        网络异常（``requests.RequestException`` 族）原样抛出。
        """
        ...

    def open_no_proxy_client(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout_seconds: float,
    ) -> AbstractContextManager[Any]:
        """Hermes 无代理 OpenAI 客户端上下文（退出即关闭，T5e runtime_env 同型）。"""
        ...

    def completion_with_recovery(
        self,
        *,
        model: str,
        call_kwargs: Dict[str, Any],
        log_label: str,
    ) -> Any:
        """litellm completion 试调用（含参数自动恢复桥），返回原始响应对象。"""
        ...

    def litellm_completion(self, **kwargs: Any) -> Any:
        """裸 ``litellm.completion`` 调用（能力探测用，属性调用期解析）。"""
        ...

    def register_fallback_pricing(self, resolved_model: str, config_model_list: Any) -> None:
        """为 OpenAI 兼容模型注册兜底价格，防止成本计算报错（src.agent 收纳）。"""
        ...

    def runtime_llm_temperature(self) -> float:
        """读取当前环境配置的 LLM temperature（读取失败回退 0.7）。"""
        ...

    def validate_event_alert_rules(self, parsed: Any) -> None:
        """经 ``src.application.alert.events`` 校验事件告警规则 JSON，失败抛
        :class:`EventAlertRulesValidationError`（携带失败规则序号）。"""
        ...


class NotificationDispatchPort(Protocol):
    """通知渠道试发端口（真实发送，不落库）。"""

    def send_channel_test(
        self,
        *,
        channel: str,
        config: Any,
        titled_content: str,
        title: str,
        content: str,
        timeout_seconds: float,
    ) -> bool:
        """按渠道调用对应 Sender 发送测试消息，返回发送是否成功。

        各 Sender 的入参形状（titled/content/subject/固定 title）属于渠道 SDK
        细节，由适配器内部收口；渠道枚举由用例层先行校验。
        """
        ...

    def test_custom_webhooks(
        self,
        *,
        config: Any,
        content: str,
        timeout_seconds: float,
    ) -> List[Dict[str, Any]]:
        """自定义 Webhook 多目标试发，返回逐目标 attempt 列表。"""
        ...


class RuntimeResetPort(Protocol):
    """配置保存后的进程级运行时单例重置端口。"""

    def reload_runtime_singletons(self) -> None:
        """重置 fetcher manager 与 search service 进程级单例（跨层副作用收纳）。"""
        ...
