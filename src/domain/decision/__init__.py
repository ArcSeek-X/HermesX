# -*- coding: utf-8 -*-
"""决策领域包。

对外暴露决策信号相关的纯业务规则与值对象（无框架 / ORM / 存储 / IO 依赖）。
当前成员：

- :mod:`src.domain.decision.decision_signal_data_quality`：决策信号数据质量档位的
  归一化规则（high/medium/low/poor/unknown 与别名/严重度），供复评护栏等用例复用。
- :mod:`src.domain.decision.decision_signal_summary`：决策信号低敏摘要与摘录生成规则，
  供通知、风险视图与告警链路复用。
- :mod:`src.domain.decision.decision_profile_policy`：决策 profile 偏向与 guardrail
  策略规则（版本常量/价格关系约束/动作替换），供复评用例复用。
- :mod:`src.domain.decision.action`：决策动作值对象与规范化（原 ``src.schemas.decision_action``）。
- :mod:`src.domain.decision.profile`：决策 profile 策略（原 ``src.schemas.decision_profile``）。
- :mod:`src.domain.decision.scale`：分值→档位业务规则（原 ``src.schemas.decision_scale``）。

本包采用惰性 ``__getattr__``（PEP 562）而非顶层 eager 聚合再导出：`action` 依赖
`src.domain.shared.report_language`，而 `report_language` 又依赖 `scale`，若在包 ``__init__`` 顶层
eager 导入 ``decision_profile_policy``（其依赖 ``action``），从外部先导入本包任一子模块时
会形成 ``report_language`` 部分初始化的循环导入。惰性解析仅在真正访问符号时才触发子模块
导入，从而切断该环。子模块亦可按完整 dotted 路径直接导入（全仓主要用法）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - 仅供静态类型/IDE，运行时不导入
    from src.domain.decision.action import (  # noqa: F401
        DecisionAction,
    )
    from src.domain.decision.decision_profile_policy import (  # noqa: F401
        MIN_ACTIONABLE_CONFIDENCE,
        PROFILE_POLICY_VERSION,
        SCORING_VERSION,
        SIGNAL_GENERATION_VERSION,
        DecisionSignalCandidate,
        GuardrailResult,
        PolicyResult,
        apply_decision_profile_policy,
    )
    from src.domain.decision.decision_signal_data_quality import (  # noqa: F401
        DecisionSignalDataQuality,
        normalize_decision_signal_data_quality,
    )
    from src.domain.decision.decision_signal_summary import (  # noqa: F401
        format_decision_signal_excerpt,
        summarize_decision_signal,
    )

# 符号名 -> 所属子模块（惰性解析用）。
_SYMBOL_MODULE = {
    "DecisionAction": "src.domain.decision.action",
    "MIN_ACTIONABLE_CONFIDENCE": "src.domain.decision.decision_profile_policy",
    "PROFILE_POLICY_VERSION": "src.domain.decision.decision_profile_policy",
    "SCORING_VERSION": "src.domain.decision.decision_profile_policy",
    "SIGNAL_GENERATION_VERSION": "src.domain.decision.decision_profile_policy",
    "DecisionSignalCandidate": "src.domain.decision.decision_profile_policy",
    "GuardrailResult": "src.domain.decision.decision_profile_policy",
    "PolicyResult": "src.domain.decision.decision_profile_policy",
    "apply_decision_profile_policy": "src.domain.decision.decision_profile_policy",
    "DecisionSignalDataQuality": "src.domain.decision.decision_signal_data_quality",
    "normalize_decision_signal_data_quality": "src.domain.decision.decision_signal_data_quality",
    "format_decision_signal_excerpt": "src.domain.decision.decision_signal_summary",
    "summarize_decision_signal": "src.domain.decision.decision_signal_summary",
}

__all__ = list(_SYMBOL_MODULE)


def __getattr__(name: str) -> Any:  # PEP 562 惰性再导出
    module_path = _SYMBOL_MODULE.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    return getattr(importlib.import_module(module_path), name)


def __dir__() -> list[str]:
    return sorted(__all__)
