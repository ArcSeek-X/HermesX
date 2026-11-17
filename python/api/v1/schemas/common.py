# -*- coding: utf-8 -*-
"""
@file: common.py
@description: 全局通用响应模型：健康检查、错误体、成功体与分页基类；被 api.app 的健康检查、全局异常处理器及各列表端点复用，是前后端响应形状的公共契约。
@author: Lensgcx (GaoCangxiong)

===================================
通用响应模型
===================================

职责：
1. 定义通用的响应模型（HealthResponse, ErrorResponse 等）
2. 提供统一的响应格式
"""

from typing import Optional, Any, Generic, List, TypeVar

from pydantic import BaseModel, ConfigDict, Field

# 泛型占位类型，供外部按需复用；本模块当前未将其参数化，保留以兼容既有导出。
T = TypeVar("T")


class RootResponse(BaseModel):
    """API 根路由响应。

    使用场景：标识服务身份与版本，供人工访问根路径或部署脚本确认服务已启动；不携带依赖状态，探活请用 HealthResponse。

    @author: Lensgcx (GaoCangxiong)
    """
    
    # API 运行状态文本，必填；由根路由固定返回，用于人工确认服务可用。
    message: str = Field(..., description="API 运行状态消息", json_schema_extra={"example": "HermesX API is running"})
    # API 版本号；允许 None，存在时应与 api.__version__ 保持一致。
    version: Optional[str] = Field(None, description="API 版本", json_schema_extra={"example": "1.0.0"})
    
    # 仅用于 OpenAPI 展示响应示例，不参与字段校验或序列化。
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "message": "HermesX API is running",
            "version": "1.0.0"
        }
    })


class HealthResponse(BaseModel):
    """健康检查响应。

    使用场景：/health、/api/health 与 /api/v1/health 探活。刻意不检查数据库等外部依赖，避免依赖抖动导致负载均衡误摘实例。

    @author: Lensgcx (GaoCangxiong)
    """
    
    # 服务状态标识，正常为 ok；探活只判断进程存活，不代表下游依赖健康。
    status: str = Field(..., description="服务状态", json_schema_extra={"example": "ok"})
    # 探活响应的生成时间（ISO 8601），便于核对实例时钟与响应新鲜度。
    timestamp: Optional[str] = Field(None, description="时间戳")
    
    # 仅用于 OpenAPI 展示探活响应示例。
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "status": "ok",
            "timestamp": "2024-01-01T12:00:00"
        }
    })


class ErrorResponse(BaseModel):
    """统一错误响应契约。

    使用场景：在 OpenAPI 文档中声明错误体形状；运行时由 api.v1.errors.error_body 与全局异常处理器产出同构字典，前端可固定按 error / message / detail 解析。

    @author: Lensgcx (GaoCangxiong)
    """
    
    # 机器可识别的错误码，前端据此做分支处理，不应随文案本地化而变化。
    error: str = Field(..., description="错误类型", json_schema_extra={"example": "validation_error"})
    # 面向用户的错误描述，不应包含堆栈、密钥等内部细节。
    message: str = Field(..., description="错误详情", json_schema_extra={"example": "请求参数错误"})
    # 可选诊断信息；校验失败时为逐字段错误列表，生产环境 500 时为 None。
    detail: Optional[Any] = Field(None, description="附加错误信息")
    
    # 仅用于 OpenAPI 展示错误响应示例。
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "error": "not_found",
            "message": "资源不存在",
            "detail": None
        }
    })


class SuccessResponse(BaseModel):
    """通用成功响应。

    使用场景：无业务数据返回的写操作端点，用 success / message / data 三段形状避免各端点自定义空响应结构。

    @author: Lensgcx (GaoCangxiong)
    """
    
    # 操作结果标志，默认 True；保留该字段使空响应与错误体形状可区分。
    success: bool = Field(True, description="是否成功")
    # 可选成功提示；None 表示无需向用户展示额外文案。
    message: Optional[str] = Field(None, description="成功消息")
    # 可选业务载荷，结构由具体端点决定；None 表示该操作无返回数据。
    data: Optional[Any] = Field(None, description="响应数据")
    
    # 仅用于 OpenAPI 展示成功响应示例。
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "message": "操作成功",
            "data": None
        }
    })


class PaginatedResponse(BaseModel):
    """通用分页响应基类。

    使用场景：由列表端点继承并覆写 list 的元素类型，保持前端分页字段一致；pageSize / pageNum 沿用前端驼峰命名，不额外做 alias 转换。

    @author: Lensgcx (GaoCangxiong)
    """

    # 当前页数据；无匹配时为空列表而非 None，前端可直接遍历。
    list: List[Any] = Field(default_factory=list, description="数据列表")
    # 符合查询条件的总条数，与分页参数无关，用于计算总页数。
    total: int = Field(0, description="总条数")
    # 每页条数，默认 20；字段名遵循前端驼峰约定，未设置上限约束。
    pageSize: int = Field(20, description="每页数量")
    # 总页数，默认 0 表示无数据；由 total 与 pageSize 推导。
    pages: int = Field(0, description="总页数")
    # 当前页码，从 1 开始，默认 1；与 pageSize 共同决定查询偏移。
    pageNum: int = Field(1, description="当前页码")
