# -*- coding: utf-8 -*-
"""
@file: kline.py
@description: K 线与行情查询契约：定义 K 线数据点、K 线响应、代码搜索结果及实时信息响应；由 api.v1.endpoints.kline 与行情用例返回，前端图表直接消费。
@author: Lensgcx (GaoCangxiong)

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
    """单个 K 线周期的 OHLCV 数据点。

    使用场景：作为 KLineResponse.data 的元素，被前端 K 线组件按 date 升序渲染；缺失的衍生指标允许为 None，不阻断基础 K 线绘制。

    @author: Lensgcx (GaoCangxiong)
    """

    # 该 K 线周期的起始时间，日线为日期、分钟线含时分秒，由服务层标准化。
    date: str = Field(..., description="日期时间")
    # 周期开盘价，必填；分时回退路径下可能等于 close。
    open: float = Field(..., description="开盘价")
    # 周期收盘价（分时口径为最新价），必填。
    close: float = Field(..., description="收盘价")
    # 周期内最高价，必填。
    high: float = Field(..., description="最高价")
    # 周期内最低价，必填。
    low: float = Field(..., description="最低价")
    # 周期成交量，单位股；数据源未提供时为 None。
    volume: Optional[float] = Field(None, description="成交量（股）")
    # 周期成交额，单位元；数据源未提供时为 None。
    amount: Optional[float] = Field(None, description="成交额（元）")
    # 相对上一周期的涨跌幅百分比；首根 K 线或缺失时为 None。
    change_percent: Optional[float] = Field(None, description="涨跌幅 (%)")
    # 换手率百分比；仅部分数据源提供，缺失时为 None。
    turnover_rate: Optional[float] = Field(None, description="换手率 (%)")


class KLineResponse(BaseModel):
    """K 线查询响应。

    使用场景：/api/v1/kline 返回整段 K 线；source 暴露实际命中的数据源，便于多源降级时定位问题，prev_close 供分时图换算涨跌幅。

    @author: Lensgcx (GaoCangxiong)
    """

    # 请求对应的规范股票代码，便于前端核对响应归属。
    stock_code: str = Field(..., description="股票代码")
    # 股票名称；代码无法映射到名称时为 None，不影响行情数据使用。
    stock_name: Optional[str] = Field(None, description="股票名称")
    # K 线周期标识（如 daily / weekly / 60m），决定 date 的格式。
    period: str = Field(..., description="K 线周期")
    # 东方财富行情标识，透传供前端复用，避免二次代码转换。
    secid: str = Field(..., description="东方财富 secid")
    # 昨收价，分时图据此把价格换算为涨跌幅百分比；缺失时前端退化为显示绝对价格。
    prev_close: Optional[float] = Field(None, description="昨收价（分时图用于计算涨跌幅百分比）")
    # 实际命中的数据源标识；多源降级时用于解释数据口径差异。
    source: Optional[str] = Field(None, description="实际命中的数据源标识")
    # 按时间升序排列的 K 线点列表，必填；无数据时为空列表。
    data: List[KLinePoint] = Field(..., description="K 线数据列表")


class StockSearchResult(BaseModel):
    """股票代码搜索的单个命中项。

    使用场景：前端自动补全下拉项；secid 是东方财富接口的行情标识，选中后无需再次反查即可拉取行情。

    @author: Lensgcx (GaoCangxiong)
    """

    # 规范股票代码，作为后续行情查询的入参。
    code: str = Field(..., description="股票代码")
    # 股票名称，用于下拉项展示。
    name: str = Field(..., description="股票名称")
    # 所属市场标识，用于区分同代码跨市场冲突。
    market: str = Field(..., description="市场")
    # 东方财富 secid，选中后可直接用于行情接口。
    secid: str = Field(..., description="东方财富 secid")


class StockSearchResponse(BaseModel):
    """股票代码搜索响应。

    使用场景：包装搜索命中列表；无结果时为空列表，由端点短 TTL 缓存承接高频输入。

    @author: Lensgcx (GaoCangxiong)
    """

    # 搜索命中列表；无匹配时为空列表，端点侧有短 TTL 缓存。
    results: List[StockSearchResult] = Field(..., description="搜索结果列表")


class StockInfoResponse(BaseModel):
    """单只股票的实时行情快照。

    使用场景：个股详情页展示价格、估值与换手等指标；估值类字段在部分市场可能缺失，故统一允许 None。

    @author: Lensgcx (GaoCangxiong)
    """

    # 请求的规范股票代码。
    stock_code: str = Field(..., description="股票代码")
    # 股票名称；未取到时为 None。
    stock_name: Optional[str] = Field(None, description="股票名称")
    # 最新成交价，必填；停牌等场景可能沿用上一交易日收盘价。
    current_price: float = Field(..., description="当前价格")
    # 相对昨收的涨跌额；缺失时为 None。
    change: Optional[float] = Field(None, description="涨跌额")
    # 相对昨收的涨跌幅百分比；缺失时为 None。
    change_percent: Optional[float] = Field(None, description="涨跌幅 (%)")
    # 今开价；集合竞价前或数据源缺失时为 None。
    open: Optional[float] = Field(None, description="今开")
    # 昨收价，是涨跌额与涨跌幅的计算基准。
    prev_close: Optional[float] = Field(None, description="昨收")
    # 当日最高价；缺失时为 None。
    high: Optional[float] = Field(None, description="最高")
    # 当日最低价；缺失时为 None。
    low: Optional[float] = Field(None, description="最低")
    # 当日累计成交量，单位股；缺失时为 None。
    volume: Optional[float] = Field(None, description="成交量（股）")
    # 当日累计成交额，单位元；缺失时为 None。
    amount: Optional[float] = Field(None, description="成交额（元）")
    # 换手率百分比；部分市场或数据源不提供。
    turnover_rate: Optional[float] = Field(None, description="换手率 (%)")
    # 振幅百分比，反映当日波动幅度；缺失时为 None。
    amplitude: Optional[float] = Field(None, description="振幅 (%)")
    # 滚动市盈率；亏损或无估值数据时为 None。
    pe_ratio_ttm: Optional[float] = Field(None, description="市盈率（TTM）")
    # 总市值，单位元；缺失时为 None。
    total_market_cap: Optional[float] = Field(None, description="总市值（元）")
    # 行情快照时间；用于提示数据时效性，非服务器本地时间。
    update_time: Optional[str] = Field(None, description="更新时间")
    # 实际命中的数据源标识，多源降级时用于解释口径差异。
    source: Optional[str] = Field(None, description="实际命中的数据源标识")
