# -*- coding: utf-8 -*-
"""策略信号规范化的纯领域规则。

原位于 `src.application.agent.protocols`，因其仅依赖 stdlib、不引用任何框架 /
ORM / 存储 / 外层，且被复评护栏等纯业务规则（如 skill opinion outcome 评估）消费，
按分层下沉到 `src/domain/decision/`。`src.application.agent.protocols` re-export
本模块的 :func:`normalize_strategy_signal`，以保持既有消费方导入路径不变。

单一规范化入口，契约见 docs/multi-strategy-contract.md §"Canonical Signal 与 Valid 判定"。
"""

from __future__ import annotations

from typing import Any, Dict


_STRATEGY_SIGNAL_ALIASES: Dict[str, str] = {
    "strong_buy": "strong_buy",
    "strong buy": "strong_buy",
    "strong-buy": "strong_buy",
    "strongbuy": "strong_buy",
    "buy": "buy",
    "hold": "hold",
    "neutral": "hold",
    "sell": "sell",
    "strong_sell": "strong_sell",
    "strong sell": "strong_sell",
    "strong-sell": "strong_sell",
    "strongsell": "strong_sell",
}


def normalize_strategy_signal(signal: Any, default: str = "hold") -> tuple[str, bool, str]:
    """Normalize strategy signal labels while preserving invalid input state.

    Single normalization entrypoint for the entire multi-strategy pipeline. See
    docs/multi-strategy-contract.md §"Canonical Signal 与 Valid 判定".

    Returns (canonical, invalid, original):
    - canonical: canonical lowercase label; falls back to `default` when invalid
    - invalid: True when input cannot be mapped to any canonical label
    - original: original stripped string form (used for diagnostics only)
    """
    if signal is None:
        original = ""
    elif hasattr(signal, "value"):
        original = str(signal.value).strip()
    else:
        original = str(signal).strip()
    normalized = original.lower().replace("/", "_")
    canonical = _STRATEGY_SIGNAL_ALIASES.get(normalized)
    if canonical is not None:
        return canonical, False, original
    return default, True, original
