# -*- coding: utf-8 -*-
"""
@file: __init__.py
@description: API v1 端点包入口：集中声明路由模块，供 api.v1.router 按模块名导入。
    __all__ 只覆盖核心业务域，其余端点由 router 直接按模块路径导入，不依赖此清单。
@author: Lensgcx (GaoCangxiong)

===================================
API v1 Endpoints 模块初始化
===================================

职责：
1. 声明所有 endpoint 路由模块

使用场景：新增端点时在 api.v1.router 中导入并 include_router；此处的 __all__ 只影响
包级 import *，不参与路由注册，因此与 router.py 的导入清单不要求一一对应。
"""

from api.v1.endpoints import (
    health,
    analysis,
    history,
    stocks,
    backtest,
    system_config,
    auth,
    agent,
    usage,
    portfolio,
    alerts,
    decision_signals,
    alphasift,
)

# 核心业务域端点清单，仅用于包级导出，不是已注册路由的完整列表。
__all__ = [
    "health",
    "analysis",
    "history",
    "stocks",
    "backtest",
    "system_config",
    "auth",
    "agent",
    "usage",
    "portfolio",
    "alerts",
    "decision_signals",
    "alphasift",
]
