# -*- coding: utf-8 -*-
"""
===================================
通用响应模型
===================================

职责：
1. 定义通用的响应模型（HealthResponse, ErrorResponse 等）
2. 提供统一的响应格式
"""

from typing import Optional, Any, Generic, List, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class RootResponse(BaseModel):
    """API 根路由响应"""
    
    message: str = Field(..., description="API 运行状态消息", json_schema_extra={"example": "HermesX API is running"})
    version: Optional[str] = Field(None, description="API 版本", json_schema_extra={"example": "1.0.0"})
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "message": "HermesX API is running",
            "version": "1.0.0"
        }
    })


class HealthResponse(BaseModel):
    """健康检查响应"""
    
    status: str = Field(..., description="服务状态", json_schema_extra={"example": "ok"})
    timestamp: Optional[str] = Field(None, description="时间戳")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "status": "ok",
            "timestamp": "2024-01-01T12:00:00"
        }
    })


class ErrorResponse(BaseModel):
    """错误响应"""
    
    error: str = Field(..., description="错误类型", json_schema_extra={"example": "validation_error"})
    message: str = Field(..., description="错误详情", json_schema_extra={"example": "请求参数错误"})
    detail: Optional[Any] = Field(None, description="附加错误信息")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "error": "not_found",
            "message": "资源不存在",
            "detail": None
        }
    })


class SuccessResponse(BaseModel):
    """通用成功响应"""
    
    success: bool = Field(True, description="是否成功")
    message: Optional[str] = Field(None, description="成功消息")
    data: Optional[Any] = Field(None, description="响应数据")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "message": "操作成功",
            "data": None
        }
    })


class PaginatedResponse(BaseModel):
    """通用分页响应模型。

    统一的分页响应格式，供所有支持分页的列表接口使用。
    """

    list: List[Any] = Field(default_factory=list, description="数据列表")
    total: int = Field(0, description="总条数")
    pageSize: int = Field(20, description="每页数量")
    pages: int = Field(0, description="总页数")
    pageNum: int = Field(1, description="当前页码")
