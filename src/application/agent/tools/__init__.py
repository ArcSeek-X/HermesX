# -*- coding: utf-8 -*-
"""
Agent tools package.

Provides ToolRegistry, @tool decorator, and wrapped tools
for the stock analysis agent.

Agent 工具包，提供 ToolRegistry、@tool 装饰器与面向股票分析 Agent 的封装工具。
"""

from src.application.agent.tools.registry import ToolRegistry, ToolDefinition, ToolParameter, ToolPolicy, tool

__all__ = ["ToolRegistry", "ToolDefinition", "ToolParameter", "ToolPolicy", "tool"]
