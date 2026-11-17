# -*- coding: utf-8 -*-
"""个股最近搜索接口的请求 / 响应模型。

传输字段沿用本层既有约定 snake_case；前端 ``api/recentSearch.ts`` 统一
``toCamelCase`` 后再消费，与 ``watchlist`` 接口保持一致。
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RecentSearchRecordCreate(BaseModel):
    """记录一次搜索的请求体。"""

    model_config = ConfigDict(
        json_schema_extra={"example": {"stock_code": "600519", "stock_name": "贵州茅台", "market": "cn"}}
    )

    stock_code: str = Field(..., min_length=1, max_length=64, description="股票代码（服务端归一）")
    stock_name: Optional[str] = Field(None, max_length=128, description="股票名称快照")
    market: Optional[str] = Field(None, max_length=16, description="市场段 cn/hk/us（缺省由代码推断）")
    user_id: Optional[str] = Field(None, max_length=64, description="用户标识（缺省 default）")


class RecentSearchItem(BaseModel):
    """一条最近搜索记录。"""

    id: int = Field(..., description="记录主键")
    user_id: str = Field(..., description="用户标识")
    stock_code: str = Field(..., description="归一后的股票代码")
    stock_name: Optional[str] = Field(None, description="股票名称快照")
    market: Optional[str] = Field(None, description="市场段")
    create_date_time: Optional[str] = Field(None, description="首次记录时间（ISO 8601）")
    update_date_time: Optional[str] = Field(None, description="最近一次记录时间（ISO 8601）")


class RecentSearchListResponse(BaseModel):
    """最近搜索列表响应。"""

    items: List[RecentSearchItem] = Field(default_factory=list, description="按最近搜索时间倒序")


class RecentSearchRecordResponse(BaseModel):
    """记录一次搜索的响应。"""

    item: RecentSearchItem = Field(..., description="被记录或更新的条目")


class SimpleSuccess(BaseModel):
    """仅需返回成功标志的响应。"""

    success: bool = Field(..., description="操作是否成功")
