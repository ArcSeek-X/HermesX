# -*- coding: utf-8 -*-
"""
@file: health.py
@description: v1 健康检查端点：暴露 /api/v1/health 供负载均衡器与监控系统探活；由 api.v1.router 挂载，鉴权中间件将其列入免登录白名单。
@author: Lensgcx (GaoCangxiong)

===================================
健康检查接口
===================================

职责：
1. 提供 /api/v1/health 健康检查接口
2. 用于负载均衡器和监控系统
"""

from datetime import datetime

from fastapi import APIRouter

from api.v1.schemas.common import HealthResponse

# 本模块的 APIRouter；由 api.v1.router 以 tags=Health 挂载到 /api/v1。
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """健康检查接口，用于负载均衡器或监控系统检查服务状态。

    只判断进程是否存活，不探测数据库或数据源，避免下游抖动导致实例被误摘除。

    Args:
        无参数。

    Returns:
        HealthResponse: 包含 status=ok 与当前 ISO 时间戳。

    Side Effects:
        无。
    """
    return HealthResponse(
        status="ok",
        timestamp=datetime.now().isoformat()
    )
