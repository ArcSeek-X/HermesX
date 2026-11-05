# -*- coding: utf-8 -*-
"""
@file: __init__.py
@description: API 中间件包入口：向 api.app 等装配方导出可直接注册的中间件类。
    认证中间件通过 api.middlewares.auth.add_auth_middleware 注册，故不在此转出。
@author: Lensgcx (GaoCangxiong)

===================================
API 中间件模块初始化
===================================

职责：
1. 导出所有中间件
"""

from api.middlewares.error_handler import ErrorHandlerMiddleware

# 只转出期望被外部复用的中间件类；注册函数留在各自模块，避免导入即产生装配副作用。
__all__ = ["ErrorHandlerMiddleware"]
