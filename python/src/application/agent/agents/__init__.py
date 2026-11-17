# -*- coding: utf-8 -*-
"""
Specialised agents for the multi-agent pipeline.

Each agent class inherits from :class:`BaseAgent` and implements
a focused analysis scope (technical, intelligence, decision, risk).

多智能体流水线的专用 Agent，均继承 BaseAgent，各自负责一个分析面
（技术 / 情报 / 决策 / 风险 / 组合）。
"""

from src.application.agent.agents.base_agent import BaseAgent
from src.application.agent.agents.technical_agent import TechnicalAgent
from src.application.agent.agents.intel_agent import IntelAgent
from src.application.agent.agents.decision_agent import DecisionAgent
from src.application.agent.agents.risk_agent import RiskAgent
from src.application.agent.agents.portfolio_agent import PortfolioAgent

__all__ = [
    "BaseAgent",
    "TechnicalAgent",
    "IntelAgent",
    "DecisionAgent",
    "RiskAgent",
    "PortfolioAgent",
]
