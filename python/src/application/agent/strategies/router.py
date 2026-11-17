"""Compatibility wrapper for the legacy strategy router import path.

旧 strategy 路由导入路径的兼容包装，重导出 SkillRouter / StrategyRouter 及默认配置。
"""

from src.application.agent.skills.router import SkillRouter, StrategyRouter, _DEFAULT_STRATEGIES, _DEFAULT_SKILLS

__all__ = ["SkillRouter", "StrategyRouter", "_DEFAULT_SKILLS", "_DEFAULT_STRATEGIES"]
