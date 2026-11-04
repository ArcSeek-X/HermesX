# -*- coding: utf-8 -*-
"""Structured Market Light snapshot schema.

Market Light 市场灯号的结构化快照 schema（Pydantic 模型），供告警与复盘消费。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


MarketRegion = Literal["cn", "hk", "us", "jp", "kr"]
MarketLightStatus = Literal["green", "yellow", "red"]
MarketLightDataQuality = Literal["ok", "partial", "unavailable"]
MARKET_LIGHT_REGIONS = frozenset(("cn", "hk", "us"))


class MarketLightDimension(BaseModel):
    """A single Market Light scoring dimension.

    Market Light 的单个评分维度（分数 0-100 + 是否可用）。
    """

    score: int = Field(ge=0, le=100)
    available: bool


class MarketLightDimensions(BaseModel):
    """Canonical Market Light dimension scores.

    Market Light 三个标准维度评分集合（广度 / 指数 / 涨跌停）。
    """

    breadth: MarketLightDimension
    index: MarketLightDimension
    limit: MarketLightDimension


class MarketLightSnapshot(BaseModel):
    """Structured Market Light snapshot persisted and consumed by alerts.

    Market Light 的完整快照（区域 / 交易日 / 灯号状态 / 分数 / 标签 / 理由 /
    指引 / 各维度评分 / 数据质量），落库并被告警逻辑消费。
    """

    region: MarketRegion
    trade_date: str
    status: MarketLightStatus
    score: int = Field(ge=0, le=100)
    label: str
    temperature_label: str
    reasons: list[str]
    guidance: str
    dimensions: MarketLightDimensions
    data_quality: MarketLightDataQuality
