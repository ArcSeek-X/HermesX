# -*- coding: utf-8 -*-
"""SystemConfig 运行时外调适配器（§4.3 拆分 F3，收纳真实外部调用）。

application 侧经 ``src.application.runtime.system_config_ports`` 的三个端口
（ConfigProbePort / NotificationDispatchPort / RuntimeResetPort）消费本模块，
由 ``src.bootstrap.system_config.configure_system_config_runtime`` 装配
（T5e hrs_alphasift_bridge 同型）。本模块持有：

- LLM 渠道探测：OpenAI 兼容 ``/models`` HTTP 发现（requests Session/get）、
  litellm 补全试调用与参数恢复桥、Hermes 无代理客户端、兜底价格注册
  （``src.infrastructure.agent_runtime.llm_adapter``）、运行态 temperature（``Config._load_from_env``
  跨类私有读取收纳于本层——application 层守卫禁止该类访问）、事件告警规则
  运行期校验（``src.application.alert.events``）；
- 通知渠道试发：14 个 ``src.infrastructure.notification.senders`` Sender 的构造与真实发送；
- 运行时单例重置：``src.infrastructure.agent_runtime.market_data_provider.DataFetcherManagerAdapter.reset`` 与
  ``src.application.intelligence.search_service.reset_search_service``。

异常分类/脱敏、结果整形与消息文案规则全部留在用例层：网络与 SDK 异常按原始
类型穿透端口（``litellm.completion`` 属性调用期解析，保持 monkey-patch 语义，
T5e-0b 拍板）。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import requests

from src.application.runtime.system_config_ports import EventAlertRulesValidationError
from src.config import Config
from src.infrastructure.generation.errors import call_litellm_with_param_recovery
from src.infrastructure.generation.hermes import open_hermes_no_proxy_client

logger = logging.getLogger(__name__)


class SystemConfigProbeAdapter:
    """``ConfigProbePort`` 实现：LLM 渠道探测与运行态配置读取原语。"""

    def fetch_models_snapshot(
        self,
        *,
        url: str,
        headers: Dict[str, str],
        timeout_seconds: float,
        trust_env: bool,
    ) -> Any:
        if not trust_env:
            session = requests.Session()
            session.trust_env = False
            try:
                return session.get(
                    url,
                    headers=headers,
                    timeout=timeout_seconds,
                    allow_redirects=False,
                )
            finally:
                session.close()
        return requests.get(
            url,
            headers=headers,
            timeout=timeout_seconds,
            allow_redirects=False,
        )

    def open_no_proxy_client(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout_seconds: float,
    ) -> Any:
        return open_hermes_no_proxy_client(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
        )

    def completion_with_recovery(
        self,
        *,
        model: str,
        call_kwargs: Dict[str, Any],
        log_label: str,
    ) -> Any:
        import litellm

        return call_litellm_with_param_recovery(
            lambda kwargs: litellm.completion(**kwargs),
            model=model,
            call_kwargs=call_kwargs,
            logger=logger,
            log_label=log_label,
        )

    def litellm_completion(self, **kwargs: Any) -> Any:
        import litellm

        return litellm.completion(**kwargs)

    def register_fallback_pricing(self, resolved_model: str, config_model_list: Any) -> None:
        from src.infrastructure.agent_runtime.llm_adapter import (
            register_fallback_model_pricing,
            resolve_fallback_litellm_wire_models,
        )

        # Register fallback pricing for OpenAI-compatible models to prevent cost calculation errors
        register_fallback_model_pricing(
            resolve_fallback_litellm_wire_models(resolved_model, config_model_list)
        )

    def runtime_llm_temperature(self) -> float:
        config = Config._load_from_env()
        try:
            return float(getattr(config, "llm_temperature", 0.7))
        except (TypeError, ValueError):
            return 0.7

    def validate_event_alert_rules(self, parsed: Any) -> None:
        from src.application.alert.events import parse_event_alert_rules, validate_event_alert_rule

        rule_index = 0
        try:
            for rule_index, rule in enumerate(parse_event_alert_rules(parsed), start=1):
                validate_event_alert_rule(rule)
        except ValueError as exc:
            raise EventAlertRulesValidationError(str(exc), rule_index=rule_index) from exc


class NotificationDispatchAdapter:
    """``NotificationDispatchPort`` 实现：通知渠道真实试发。"""

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
        from src.infrastructure.notification.senders import (
            AstrbotSender,
            DiscordSender,
            EmailSender,
            FeishuSender,
            GotifySender,
            NtfySender,
            PushoverSender,
            PushplusSender,
            Serverchan3Sender,
            SlackSender,
            TelegramSender,
            WechatSender,
            DingtalkSender,
        )

        dispatch = {
            "wechat": lambda: WechatSender(config).send_to_wechat(titled_content, timeout_seconds=timeout_seconds),
            "dingtalk": lambda: DingtalkSender(config).send_to_dingtalk(titled_content, title="Test Message", timeout_seconds=timeout_seconds),
            "feishu": lambda: FeishuSender(config).send_to_feishu(titled_content, timeout_seconds=timeout_seconds),
            "telegram": lambda: TelegramSender(config).send_to_telegram(titled_content, timeout_seconds=timeout_seconds),
            "email": lambda: EmailSender(config).send_to_email(content, subject=title, timeout_seconds=timeout_seconds),
            "pushover": lambda: PushoverSender(config).send_to_pushover(content, title=title, timeout_seconds=timeout_seconds),
            "ntfy": lambda: NtfySender(config).send_to_ntfy(content, title=title, timeout_seconds=timeout_seconds),
            "gotify": lambda: GotifySender(config).send_to_gotify(content, title=title, timeout_seconds=timeout_seconds),
            "pushplus": lambda: PushplusSender(config).send_to_pushplus(content, title=title, timeout_seconds=timeout_seconds),
            "serverchan3": lambda: Serverchan3Sender(config).send_to_serverchan3(content, title=title, timeout_seconds=timeout_seconds),
            "discord": lambda: DiscordSender(config).send_to_discord(titled_content, timeout_seconds=timeout_seconds),
            "slack": lambda: SlackSender(config).send_to_slack(titled_content, timeout_seconds=timeout_seconds),
            "astrbot": lambda: AstrbotSender(config).send_to_astrbot(titled_content, timeout_seconds=timeout_seconds),
        }

        return bool(dispatch[channel]())

    def test_custom_webhooks(
        self,
        *,
        config: Any,
        content: str,
        timeout_seconds: float,
    ) -> List[Dict[str, Any]]:
        from src.infrastructure.notification.senders import CustomWebhookSender

        return CustomWebhookSender(config).test_custom_webhooks(
            content,
            timeout_seconds=timeout_seconds,
        )


class RuntimeResetAdapter:
    """``RuntimeResetPort`` 实现：配置重载后的进程级单例重置。"""

    def reload_runtime_singletons(self) -> None:
        from src.infrastructure.agent_runtime.market_data_provider import DataFetcherManagerAdapter
        from src.application.intelligence.search_service import reset_search_service

        DataFetcherManagerAdapter.reset()
        reset_search_service()
