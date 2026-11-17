# -*- coding: utf-8 -*-
"""
@file: watchlist.py
@description: 自选股管理契约：分组与自选股条目的增删改查请求、列表项及分页响应；由 api.v1.endpoints.watchlist 与 src.application.watchlist 复用，分页结构继承 common.PaginatedResponse。
@author: Lensgcx (GaoCangxiong)

===================================
自选股管理相关模型
===================================

职责：
1. 定义自选股分类的请求/响应模型
2. 定义自选股条目的请求/响应模型
"""

from typing import Optional, List

from pydantic import BaseModel, Field

from api.v1.schemas.common import PaginatedResponse


# === 分类 ===

class WatchlistGroupCreate(BaseModel):
    """新增自选股分组请求。

    使用场景：用户在前端新建分组；group_code 由服务端生成，请求体只提交可编辑字段，避免客户端伪造唯一编码。

    @author: Lensgcx (GaoCangxiong)
    """

    # 分组名称，必填且长度 1~50；前端按此展示，服务端不强制唯一。
    name: str = Field(..., min_length=1, max_length=50, description="分类名称")
    # 分组用途说明，最长 255 字符；可为空。
    description: Optional[str] = Field(None, max_length=255, description="分类描述")
    # 展示排序权重，None 时由服务端追加到末尾。
    sort_order: Optional[int] = Field(None, description="分类排序权重")


class WatchlistGroupUpdate(BaseModel):
    """编辑自选股分组请求。

    使用场景：按 group_code 定位分组并做部分更新；所有可改字段均为可选，None 表示保持原值。

    @author: Lensgcx (GaoCangxiong)
    """

    # 服务端生成的分组唯一编码，作为定位键而非自增 ID，避免跨环境 ID 漂移。
    group_code: str = Field(..., min_length=1, description="分组编码（服务端生成，企业内唯一）")
    # 新的分组名称；None 表示不修改，提供值时仍受 1~50 长度约束。
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="分类名称")
    # 新的分组说明；None 表示不修改，最长 255 字符。
    description: Optional[str] = Field(None, max_length=255, description="分类描述")
    # 新的排序权重；None 表示不修改。
    sort_order: Optional[int] = Field(None, description="分类排序权重")


class WatchlistGroupList(BaseModel):
    """分组列表项响应。

    使用场景：分组下拉与分组管理页；item_count 由服务端聚合，避免前端为统计数量逐组拉取明细。

    @author: Lensgcx (GaoCangxiong)
    """

    # 分组数据库主键，供条目关联与移动操作定位。
    id: int
    # 分组名称，用于下拉与列表展示。
    name: str
    # 分组说明；无说明时为空字符串而非 None，便于前端直接渲染。
    description: str
    # 分组唯一编码，供更新与跨环境引用。
    group_code: str
    # 该分组下的自选股数量，默认 0；由服务端聚合计算。
    item_count: int = Field(0, description="当前分组下的个股数量")
    # 展示顺序权重，前端按此升序排列。
    sort_order: int
    # 分组创建时间字符串，用于审计与展示。
    create_date_time: str
    # 分组最后更新时间字符串。
    update_date_time: str


# === 自选股 ===

class WatchlistItemCreate(BaseModel):
    """新增自选股请求。

    使用场景：用户按规范代码添加标的；stock_name 为冗余字段，允许为空以便行情源暂不可用时不阻断添加。

    @author: Lensgcx (GaoCangxiong)
    """

    # 规范股票代码（如 600519.SH），必填且最长 32 字符，是去重的依据。
    stock_code: str = Field(..., min_length=1, max_length=32, description="规范股票代码，如 600519.SH")
    # 冗余股票名称，最长 64 字符；行情源暂不可用时可缺省。
    stock_name: Optional[str] = Field(None, max_length=64, description="冗余股票名称")
    # 用户为该标的填写的备注，可为空。
    description: Optional[str] = Field(None, description="自选股描述")


class WatchlistItemUpdate(BaseModel):
    """编辑自选股请求。

    使用场景：修改备注或纠正冗余名称；不允许改股票代码，改代码需删除后重新添加。

    @author: Lensgcx (GaoCangxiong)
    """

    # 新的备注；None 表示不修改。
    description: Optional[str] = Field(None, description="自选股描述")
    # 纠正后的冗余名称；None 表示不修改，最长 64 字符。
    stock_name: Optional[str] = Field(None, max_length=64, description="冗余股票名称")


class WatchlistItemMove(BaseModel):
    """移动自选股到其他分组的请求。

    使用场景：分组调整；目标分组必须存在且属于当前用户空间。

    @author: Lensgcx (GaoCangxiong)
    """

    # 目标分组主键；服务端需校验其存在性再执行移动。
    target_group_id: int = Field(..., description="目标分类 ID")


class WatchlistItemOut(BaseModel):
    """自选股条目的响应形状。

    使用场景：分组内列表与搜索结果；时间字段为字符串，由服务层统一格式化，避免前端处理多种时区表示。

    @author: Lensgcx (GaoCangxiong)
    """

    # 自选股条目主键，删除与移动操作据此定位。
    id: int
    # 所属分组主键，用于前端分桶与移动回填。
    group_id: int
    # 规范股票代码，供行情查询直接复用。
    stock_code: str
    # 冗余名称；未补全时为 None，前端需回退显示代码。
    stock_name: Optional[str]
    # 用户备注；未填写时为 None。
    description: Optional[str]
    # 分组内展示顺序权重。
    sort_order: int
    # 条目添加时间字符串。
    create_date_time: str
    # 条目最后更新时间字符串。
    update_date_time: str


class SimpleSuccess(BaseModel):
    """极简成功响应。

    使用场景：删除、移动等只需确认结果的写操作；固定 success=True，减少空响应体的解析歧义。

    @author: Lensgcx (GaoCangxiong)
    """

    # 操作成功标志，固定为 True；失败由统一错误体表达。
    success: bool = True


class WatchlistItemsQueryRequest(BaseModel):
    """分组内自选股的分页查询请求。

    使用场景：分组列表页；pageSize 上限 100 防止一次拉取过多，pageNum 从 1 开始。

    @author: Lensgcx (GaoCangxiong)
    """

    # 要查询的分组主键，必填；不提供跨分组聚合查询。
    group_id: int = Field(..., description="分类 ID")
    # 每页条数，默认 20，范围 1~100，防止一次拉取过多。
    pageSize: int = Field(20, ge=1, le=100, description="每页数量")
    # 当前页码，从 1 开始，默认 1。
    pageNum: int = Field(1, ge=1, description="当前页码")


class WatchlistItemsPaginatedResponse(PaginatedResponse):
    """自选股分页响应。

    使用场景：继承通用分页字段并覆写 list 元素类型，使 OpenAPI 能展开自选股条目的具体结构。

    @author: Lensgcx (GaoCangxiong)
    """

    # 当前页自选股列表；无数据为空列表，元素类型覆写为 WatchlistItemOut。
    list: List[WatchlistItemOut] = Field(default_factory=list, description="自选股列表")
