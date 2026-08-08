# -*- coding: utf-8 -*-
"""
===================================
K 线数据相关模型
===================================

职责：
1. 定义 K 线数据点模型
2. 定义 K 线响应模型
3. 定义股票搜索结果模型
4. 定义股票实时信息模型
"""

from typing import Optional, List

from pydantic import BaseModel, Field


class KLinePoint(BaseModel):
    """K 线数据点"""

    date: str = Field(..., description="日期时间")
    open: float = Field(..., description="开盘价")
    close: float = Field(..., description="收盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    volume: Optional[float] = Field(None, description="成交量（股）")
    amount: Optional[float] = Field(None, description="成交额（元）")
    change_percent: Optional[float] = Field(None, description="涨跌幅 (%)")
    turnover_rate: Optional[float] = Field(None, description="换手率 (%)")


class KLineResponse(BaseModel):
    """K 线数据响应"""

    stock_code: str = Field(..., description="股票代码")
    stock_name: Optional[str] = Field(None, description="股票名称")
    period: str = Field(..., description="K 线周期")
    secid: str = Field(..., description="东方财富 secid")
    prev_close: Optional[float] = Field(None, description="昨收价（分时图用于计算涨跌幅百分比）")
    data: List[KLinePoint] = Field(..., description="K 线数据列表")


class StockSearchResult(BaseModel):
    """股票搜索结果"""

    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    market: str = Field(..., description="市场")
    secid: str = Field(..., description="东方财富 secid")


class StockSearchResponse(BaseModel):
    """股票搜索响应"""

    results: List[StockSearchResult] = Field(..., description="搜索结果列表")


class StockInfoResponse(BaseModel):
    """股票实时信息响应"""

    stock_code: str = Field(..., description="股票代码")
    stock_name: Optional[str] = Field(None, description="股票名称")
    current_price: float = Field(..., description="当前价格")
    change: Optional[float] = Field(None, description="涨跌额")
    change_percent: Optional[float] = Field(None, description="涨跌幅 (%)")
    open: Optional[float] = Field(None, description="今开")
    prev_close: Optional[float] = Field(None, description="昨收")
    high: Optional[float] = Field(None, description="最高")
    low: Optional[float] = Field(None, description="最低")
    volume: Optional[float] = Field(None, description="成交量（股）")
    amount: Optional[float] = Field(None, description="成交额（元）")
    turnover_rate: Optional[float] = Field(None, description="换手率 (%)")
    amplitude: Optional[float] = Field(None, description="振幅 (%)")
    pe_ratio_ttm: Optional[float] = Field(None, description="市盈率（TTM）")
    total_market_cap: Optional[float] = Field(None, description="总市值（元）")
    update_time: Optional[str] = Field(None, description="更新时间")
