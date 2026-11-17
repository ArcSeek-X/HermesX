"""Compatibility wrapper for the legacy strategy aggregator import path.

旧 strategy 聚合器导入路径的兼容包装，重导出 SkillAggregator / StrategyAggregator。
"""

from src.application.agent.skills.aggregator import SkillAggregator, StrategyAggregator

__all__ = ["SkillAggregator", "StrategyAggregator"]
