# -*- coding: utf-8 -*-
"""GeminiAnalyzer 运行时外部调用端口（application 层契约，§4.3 拆分 A2）。

分层说明（ARCHITECTURE_TARGET §4.3/§4.1）：``src/application/analysis/analyzer.py`` 是点名的"高耦合
拆分对象"，其对 litellm SDK（``Router`` 构造、``litellm.completion`` 直调、
Hermes 无代理客户端成对调用、fallback 模型零价注册）的依赖经本端口绑定
``src/infrastructure/providers/analyzer_runtime.py`` 适配器，由 bootstrap
``configure_analyzer_runtime`` 装配（T5f ConfigProbePort 同型）。

用例层保留全部分支策略（mixed-route 阻断、deployment 入参整形、kwargs 构造）与
异常分类/脱敏规则，端口只收纳"真正发生外部调用"的原语。``build_router`` /
``completion_direct`` / ``completion_no_proxy`` 返回不透明 SDK 句柄/响应对象
（``Any``，T5e create_hotspot_provider 同型）：Router 句柄随后由编排层以
``handle.completion(**kwargs)`` 方法形态多态调用，不透明句柄参数化是形状例外
（docstring 注明）。SDK/网络异常原样穿透端口——上游
``call_litellm_with_param_recovery`` 以原始异常类型与文案为恢复判定输入，
包装即漂移语义。适配器对 ``litellm.completion`` / ``litellm.Router`` /
``open_hermes_no_proxy_client`` 均按调用时刻解析属性/命名空间，保持既有
monkey-patch 测试语义（T5e-0b 拍板先例）。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol


class AnalyzerLLMPort(Protocol):
    """analyzer LLM 运行时外部调用原语端口。"""

    def build_router(self, *, model_list: List[Dict[str, Any]]) -> Optional[Any]:
        """从 deployment 列表构造 litellm ``Router``；返回不透明 Router 句柄。

        构造形状钉死 ``Router(model_list=..., routing_strategy="simple-shuffle",
        num_retries=2)``；构造方签名不兼容（``TypeError``）时返回 ``None`` 并在
        适配器内保留原 debug 文案——复刻拆分前 ``try/except TypeError:
        self._router = None`` 的兜底分支。``model_list`` 为空/假值时直接返回
        ``None``（不触构造）。
        """
        ...

    def completion_direct(self, **kwargs: Any) -> Any:
        """裸 ``litellm.completion(**kwargs)`` 直调，返回原始响应对象。

        按调用时刻解析 ``litellm`` 模块属性，测试可经适配器命名空间或
        ``litellm`` 共享模块对象 monkey-patch；异常原样穿透。
        """
        ...

    def completion_no_proxy(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout: float,
        call_kwargs: Dict[str, Any],
    ) -> Any:
        """Hermes 无代理客户端成对调用：开 client → 注入 → completion → 关闭。

        ``open_hermes_no_proxy_client`` contextmanager 与 ``litellm.completion``
        的成对修改/还原语义不可拆（T5f ``open_no_proxy_client`` 同型形状例外），
        故客户端构造与补全调用合并为本单一方法；``client`` 键由适配器注入进
        kwargs 副本，``call_kwargs`` 原字典不被修改。
        """
        ...

    def register_fallback_pricing(self, models: List[str]) -> None:
        """为未知 OpenAI 兼容 wire 模型注册零价（litellm 全局成本表写侧）。"""
        ...
