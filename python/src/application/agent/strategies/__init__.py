# -*- coding: utf-8 -*-
"""
Compatibility re-exports for the legacy strategy namespace.

Provides:
- :class:`StrategyAgent` — legacy alias of :class:`SkillAgent`
- :class:`StrategyRouter` — legacy alias of :class:`SkillRouter`
- :class:`StrategyAggregator` — legacy alias of :class:`SkillAggregator`

旧 ``strategies`` 命名空间的兼容重导出，提供 Strategy* 到 Skill* 的别名。
"""

from src.application.agent.strategies.strategy_agent import StrategyAgent
from src.application.agent.strategies.router import StrategyRouter
from src.application.agent.strategies.aggregator import StrategyAggregator

__all__ = [
    "StrategyAgent",
    "StrategyRouter",
    "StrategyAggregator",
]
