# -*- coding: utf-8 -*-
"""
@file: __init__.py
@description: API 包入口：声明 API 版本并导出包级公共接口，被 server.py 与 api.app
    引用；此处刻意不导入子模块，避免包初始化阶段触发循环依赖或提前加载 FastAPI。
@author: Lensgcx (GaoCangxiong)

===================================
API 模块初始化
===================================

职责：
1. 导出 API 模块的公共接口
2. 统一版本管理
"""

# 对外公开的 API 版本号，需与 api.app.create_app() 中 FastAPI(version=...) 保持一致。
__version__ = "1.0.0"
