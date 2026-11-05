# -*- coding: utf-8 -*-
"""
@file: stocks.py
@description: 股票行情契约：实时行情、日线数据点、历史行情、当日分时以及图片股票代码提取结果；由 api.v1.endpoints.stocks 返回，前端 K 线组件直接消费 KLineData / StockTimelinePoint。
@author: Lensgcx (GaoCangxiong)

===================================
股票数据相关模型
===================================

职责：
1. 定义股票实时行情模型
2. 定义历史 K 线数据模型
3. 定义单票分时（当日）数据模型
"""

from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field


class StockQuote(BaseModel):
    """单只股票的实时行情快照。

    使用场景：列表与详情页的价格展示；估值、换手等字段在部分市场缺失，因此除代码与最新价外统一允许 None。

    @author: Lensgcx (GaoCangxiong)
    """
    
    # 规范股票代码，标识行情归属。
    stock_code: str = Field(..., description="股票代码")
    # 股票名称；代码映射失败时为 None。
    stock_name: Optional[str] = Field(None, description="股票名称")
    # 最新成交价，必填；停牌时可能沿用上一交易日收盘价。
    current_price: float = Field(..., description="当前价格")
    # 相对昨收的涨跌额；缺失时为 None。
    change: Optional[float] = Field(None, description="涨跌额")
    # 相对昨收的涨跌幅百分比；缺失时为 None。
    change_percent: Optional[float] = Field(None, description="涨跌幅 (%)")
    # 今开价；集合竞价前为 None。
    open: Optional[float] = Field(None, description="开盘价")
    # 当日最高价；缺失时为 None。
    high: Optional[float] = Field(None, description="最高价")
    # 当日最低价；缺失时为 None。
    low: Optional[float] = Field(None, description="最低价")
    # 昨收价，涨跌额与涨跌幅的计算基准。
    prev_close: Optional[float] = Field(None, description="昨收价")
    # 当日成交量，单位股；缺失时为 None。
    volume: Optional[float] = Field(None, description="成交量（股）")
    # 当日成交额，单位元；缺失时为 None。
    amount: Optional[float] = Field(None, description="成交额（元）")
    # 换手率百分比；部分市场不提供。
    turnover_rate: Optional[float] = Field(None, description="换手率（%）")
    # 总市值，单位元；缺失时为 None。
    total_mv: Optional[float] = Field(None, description="总市值（元）")
    # 行情快照时间，用于提示数据时效性。
    update_time: Optional[str] = Field(None, description="更新时间")
    
    # 仅用于 OpenAPI 展示实时行情示例。
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "stock_code": "600519",
            "stock_name": "贵州茅台",
            "current_price": 1800.00,
            "change": 15.00,
            "change_percent": 0.84,
            "open": 1785.00,
            "high": 1810.00,
            "low": 1780.00,
            "prev_close": 1785.00,
            "volume": 10000000,
            "amount": 18000000000,
            "update_time": "2024-01-01T15:00:00"
        }
    })


class KLineData(BaseModel):
    """历史日线数据点。

    使用场景：StockHistoryResponse.data 的元素；按 date 升序返回，前端直接绘制 OHLC 柱状与成交量。

    @author: Lensgcx (GaoCangxiong)
    """
    
    # 交易日日期，前端按此升序排列。
    date: str = Field(..., description="日期")
    # 当日开盘价，必填。
    open: float = Field(..., description="开盘价")
    # 当日最高价，必填。
    high: float = Field(..., description="最高价")
    # 当日最低价，必填。
    low: float = Field(..., description="最低价")
    # 当日收盘价，必填。
    close: float = Field(..., description="收盘价")
    # 当日成交量；数据源未提供时为 None。
    volume: Optional[float] = Field(None, description="成交量")
    # 当日成交额；数据源未提供时为 None。
    amount: Optional[float] = Field(None, description="成交额")
    # 相对前一交易日收盘价的涨跌幅百分比；首日或缺失时为 None。
    change_percent: Optional[float] = Field(None, description="涨跌幅 (%)")
    
    # 仅用于 OpenAPI 展示日线数据示例。
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "date": "2024-01-01",
            "open": 1785.00,
            "high": 1810.00,
            "low": 1780.00,
            "close": 1800.00,
            "volume": 10000000,
            "amount": 18000000000,
            "change_percent": 0.84
        }
    })


class ExtractItem(BaseModel):
    """图片中单条股票代码的提取结果。

    使用场景：图片识别结果的结构化展示，附带名称与置信度供用户确认；code 为 None 表示该条解析失败。

    @author: Lensgcx (GaoCangxiong)
    """
    # 识别出的股票代码；None 表示该条无法解析成有效代码。
    code: Optional[str] = Field(None, description="股票代码，None 表示解析失败")
    # 模型给出的股票名称（如有），仅作辅助展示，不参与代码匹配。
    name: Optional[str] = Field(None, description="股票名称（如有）")
    # 置信度 high / medium / low，默认 medium；供前端决定是否要求用户确认。
    confidence: str = Field("medium", description="置信度：high/medium/low")


class ExtractFromImageResponse(BaseModel):
    """图片股票代码提取响应。

    使用场景：/stocks/extract-from-image 返回；codes 为向后兼容的扁平列表，items 提供更细的置信度信息。

    @author: Lensgcx (GaoCangxiong)
    """

    # 去重后的代码列表，保留该字段以兼容只消费扁平列表的旧前端。
    codes: List[str] = Field(..., description="提取的股票代码（已去重，向后兼容）")
    # 带名称与置信度的结构化结果明细；默认空列表。
    items: List[ExtractItem] = Field(default_factory=list, description="提取结果明细（代码+名称+置信度）")
    # LLM 原始响应文本，仅用于调试排查；正常响应中可为 None。
    raw_text: Optional[str] = Field(None, description="原始 LLM 响应（调试用）")


class StockHistoryResponse(BaseModel):
    """股票历史行情响应。

    使用场景：历史 K 线接口；data 为空列表表示区间内无可用数据，与请求失败通过 HTTP 状态码区分。

    @author: Lensgcx (GaoCangxiong)
    """
    
    # 请求的规范股票代码。
    stock_code: str = Field(..., description="股票代码")
    # 股票名称；未取到时为 None。
    stock_name: Optional[str] = Field(None, description="股票名称")
    # K 线周期标识（如 daily），决定 date 粒度。
    period: str = Field(..., description="K 线周期")
    # 历史数据点列表；无数据时为空列表，区别于请求失败。
    data: List[KLineData] = Field(default_factory=list, description="K 线数据列表")
    
    # 仅用于 OpenAPI 展示历史行情示例。
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "stock_code": "600519",
            "stock_name": "贵州茅台",
            "period": "daily",
            "data": []
        }
    })


class StockTimelinePoint(BaseModel):
    """分时数据点（KLinePoint 形态，前端 KLineChart / KLineView 直接渲染）。

    date 已由服务层标准化为 YYYY-MM-DD HH:mm:ss；open/high/low 缺失时等于 close（桥接回退路径为 tick 线，无 OHLC）。

    使用场景：当日分时图；保持与 K 线点同形，避免图表组件分支渲染。

    @author: Lensgcx (GaoCangxiong)
    """

    # 分时点时间，格式 YYYY-MM-DD HH:mm:ss，由服务层统一标准化。
    date: str = Field(..., description="分时时间（YYYY-MM-DD HH:mm:ss）")
    # 该分钟开盘价；tick 回退路径下等于 close，可为 None。
    open: Optional[float] = Field(None, description="开盘价")
    # 该分钟最新价，分时曲线的主要取值；可为 None。
    close: Optional[float] = Field(None, description="收盘价（该分钟最新价）")
    # 该分钟最高价；无 OHLC 时等于 close，可为 None。
    high: Optional[float] = Field(None, description="最高价")
    # 该分钟最低价；无 OHLC 时等于 close，可为 None。
    low: Optional[float] = Field(None, description="最低价")
    # 该分钟成交量，单位股；缺失时为 None。
    volume: Optional[float] = Field(None, description="成交量（股）")
    # 该分钟成交额，单位元；缺失时为 None。
    amount: Optional[float] = Field(None, description="成交额（元）")


class StockTimelineResponse(BaseModel):
    """股票当日分时响应。

    使用场景：分时图首次加载；prev_close 提供涨跌幅基准线，points 为空表示休市或数据源拉取失败。

    @author: Lensgcx (GaoCangxiong)
    """

    # 请求的规范股票代码。
    stock_code: str = Field(..., description="股票代码")
    # 股票名称；未取到时为 None。
    stock_name: Optional[str] = Field(None, description="股票名称")
    # 昨收价，作为分时图涨跌幅基准线；缺失时前端不绘制百分比轴。
    prev_close: Optional[float] = Field(None, description="昨收价（分时基准线）")
    # 分时点列表；拉取失败或休市无数据时为空列表，避免用 None 表达空集合。
    points: List[StockTimelinePoint] = Field(
        default_factory=list, description="分时数据点（拉取失败或休市无数据时为空列表）"
    )

    # 仅用于 OpenAPI 展示分时响应示例。
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "stock_code": "600519",
            "stock_name": "贵州茅台",
            "prev_close": 1785.00,
            "points": [
                {
                    "date": "2024-01-02 09:30:00",
                    "open": 1785.00,
                    "close": 1786.00,
                    "high": 1787.00,
                    "low": 1785.00,
                    "volume": 12000,
                    "amount": 21432000,
                }
            ]
        }
    })
