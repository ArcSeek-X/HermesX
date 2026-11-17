"""Compatibility wrapper for the legacy strategy agent import path.

旧 strategy agent 导入路径的兼容包装，重导出 SkillAgent / StrategyAgent。
"""

from src.application.agent.skills.skill_agent import SkillAgent, StrategyAgent

__all__ = ["SkillAgent", "StrategyAgent"]
