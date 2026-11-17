# -*- coding: utf-8 -*-
"""AlphaSift 运行时外部依赖端口（application 层契约）。

分层说明（ARCHITECTURE_TARGET §4.3）：``alphasift_service`` 对 litellm 生成后端、
东财热点 provider、HRS 行情取数桥（``data_provider``/``search_service``）的依赖经
本端口绑定 ``src/infrastructure/providers/hrs_alphasift_bridge.py`` 适配器，由
bootstrap 装配（T5d NewsSourcePort 同型）。用例层保留策略校验、结果规整、热点
缓存/路由编排；env 注入、monkey-patch 桥、取数与生成调用收纳在适配器内。

``runtime_env``/``daily_history_env``/``litellm_headers`` 以上下文管理器形态暴露：
它们成对修改/还原进程级状态（``os.environ``、外部 alphasift 包属性、ContextVar
headers 路由），调用方必须 ``with`` 使用，退出即还原——这与 ``screen`` 一次调用的
事务边界一致，无法拆成普通返回值。``config`` 参数按 ``Any`` 收口：端口签名只消费
其公开属性（litellm_model/llm_model_list/tushare_token 等），避免 application 契约
钉死 ``src.config.Config`` 具体类型（T5b MarketSnapshotPort 同策）。
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any, Dict, List, Protocol, Tuple


class AlphaSiftRuntimePort(Protocol):
    """AlphaSift 屏选/热点用例的运行时端口。"""

    def runtime_env(self, config: Any, *, max_results: Any = None) -> AbstractContextManager[None]:
        """注入本次请求作用域的 AlphaSift 运行时 env（退出还原）。"""
        ...

    def daily_history_env(self) -> AbstractContextManager[None]:
        """将外部 alphasift 包日线取数替换为 HRS 桥（退出还原）。"""
        ...

    def litellm_headers(self, config: Any) -> AbstractContextManager[None]:
        """按模型路由注入 litellm completion headers（monkey-patch 桥，退出还原）。"""
        ...

    def screen_context(self, config: Any, *, max_results: Any = None) -> Dict[str, Any]:
        """组装屏选 context（LLM 模型/行情快照/候选上限等运行参数）。"""
        ...

    def enrich_candidates(self, candidates: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """对候选做 HRS 行情/基本面/资讯富化，返回新候选列表与富化元信息。"""
        ...

    def create_hotspot_provider(self) -> Any:
        """构造东财热点 provider（akshare 形状协议实现）。"""
        ...

    def is_eastmoney_hotspot_provider(self, provider: Any) -> bool:
        """宽松判定：provider 是否为东财热点 provider（含子类）。"""
        ...

    def is_exact_eastmoney_hotspot_provider(self, provider: Any) -> bool:
        """严格判定：provider 是否恰为东财热点 provider 本类（排除子类）。

        hotspot_detail 主取数路径原语义 ``type(...) is 类``，与上一条共存且不可合并：
        tests 的 FakeProvider 依赖两处语义差异分别命中降级判定与主取数分支。
        """
        ...

    def summarize_event_with_llm(self, *, topic: str, text: str, config: Any) -> str:
        """litellm 生成热点事件摘要；失败/无模型返回空串（调用方本地兜底）。"""
        ...
