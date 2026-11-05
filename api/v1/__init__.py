# -*- coding: utf-8 -*-
"""
@file: __init__.py
@description: API v1 包入口：把聚合后的路由以 api_v1_router 导出，供 api.app 挂载到
    /api/v1 前缀；也是外部代码引用 v1 路由的约定入口。
@author: Lensgcx (GaoCangxiong)

===================================
API v1 模块初始化
===================================

职责：
1. 导出 v1 版本 API 的路由
"""

from api.v1.router import router as api_v1_router

# 显式导出，避免包级 import * 泄漏 APIRouter 内部符号；导出顺序不影响路由匹配顺序。
__all__ = ["api_v1_router"]
