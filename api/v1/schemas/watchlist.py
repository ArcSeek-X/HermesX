# -*- coding: utf-8 -*-
"""
===================================
自选股管理相关模型
===================================

职责：
1. 定义自选股分类的请求/响应模型
2. 定义自选股条目的请求/响应模型
"""

from typing import Optional

from pydantic import BaseModel, Field


# === 分类 ===

class WatchlistGroupCreate(BaseModel):
    """新增分类请求"""

    name: str = Field(..., min_length=1, max_length=50, description="分类名称")


class WatchlistGroupUpdate(BaseModel):
    """编辑分类请求"""

    name: Optional[str] = Field(None, min_length=1, max_length=50, description="分类名称")
    sort_order: Optional[int] = Field(None, description="分类排序权重")


class WatchlistGroupOut(BaseModel):
    """分类响应"""

    id: int
    name: str
    sort_order: int
    created_at: str
    updated_at: str


# === 自选股 ===

class WatchlistItemCreate(BaseModel):
    """新增自选股请求"""

    stock_code: str = Field(..., min_length=1, max_length=32, description="规范股票代码，如 600519.SH")
    stock_name: Optional[str] = Field(None, max_length=64, description="冗余股票名称")
    note: Optional[str] = Field(None, max_length=255, description="用户备注")


class WatchlistItemUpdate(BaseModel):
    """编辑自选股请求"""

    note: Optional[str] = Field(None, max_length=255, description="用户备注")
    stock_name: Optional[str] = Field(None, max_length=64, description="冗余股票名称")


class WatchlistItemMove(BaseModel):
    """移动归类请求"""

    target_group_id: int = Field(..., description="目标分类 ID")


class WatchlistItemOut(BaseModel):
    """自选股响应"""

    id: int
    group_id: int
    stock_code: str
    stock_name: Optional[str]
    note: Optional[str]
    sort_order: int
    created_at: str
    updated_at: str


class SimpleSuccess(BaseModel):
    """通用成功响应"""

    success: bool = True
