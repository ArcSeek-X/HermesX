# -*- coding: utf-8 -*-
"""
@file: usage.py
@description: LLM 用量追踪接口的请求/响应模型，包含按调用类型与模型的分项汇总、单次调用明细和看板响应；由 api.v1.endpoints.usage 返回，数据源为 src.application.usage 的统计结果。
@author: Lensgcx (GaoCangxiong)

Schemas for LLM usage tracking API.

Defines per-call-type and per-model token breakdowns, individual call
records and the dashboard payload assembled by the usage query service.

LLM 用量追踪接口的 Pydantic 请求/响应模型，含按调用类型与模型的分项汇总、单次调用记录及看板响应。token 数用于成本观测，不参与计费结算。
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class CallTypeBreakdown(BaseModel):
    """按调用类型汇总的用量与 token 数。

    使用场景：用量看板中区分 analysis / agent / market_review 的消耗，便于定位哪类任务带来主要成本。

    @author: Lensgcx (GaoCangxiong)
    """

    # 调用类型标识：analysis（个股分析）/ agent（会话）/ market_review（大盘复盘）。
    call_type: str = Field(..., description="'analysis' | 'agent' | 'market_review'")
    # 该类型在统计区间内的调用次数。
    calls: int
    # 该类型累计输入 token，默认 0；旧记录缺字段时按 0 计。
    prompt_tokens: int = 0
    # 该类型累计输出 token，默认 0。
    completion_tokens: int = 0
    # 该类型输入与输出 token 之和，用于成本观测。
    total_tokens: int


class ModelBreakdown(BaseModel):
    """按模型汇总的调用次数与 token 数。

    使用场景：对比不同模型的调用规模与上下文长度，max_total_tokens 用于识别接近上下文上限的长请求。

    @author: Lensgcx (GaoCangxiong)
    """

    # 模型标识，与运行时配置的模型名一致。
    model: str
    # 该模型在统计区间内的调用次数。
    calls: int
    # 该模型累计输入 token，默认 0。
    prompt_tokens: int = 0
    # 该模型累计输出 token，默认 0。
    completion_tokens: int = 0
    # 该模型输入与输出 token 之和。
    total_tokens: int
    # 单次调用的最大 token 数，默认 0；用于识别接近上下文上限的请求。
    max_total_tokens: int = 0


class UsageCallRecord(BaseModel):
    """单次 LLM 调用的明细记录。

    使用场景：看板的近期调用列表；stock_code 允许 None，因为大盘复盘等非个股任务没有标的维度。

    @author: Lensgcx (GaoCangxiong)
    """

    # 调用记录的数据库主键，用于明细去重与排序。
    id: int
    # 调用发生时间（ISO 8601 字符串），看板按此倒序展示。
    called_at: str = Field(..., description="ISO datetime string")
    # 调用类型标识，与 CallTypeBreakdown.call_type 口径一致。
    call_type: str
    # 本次实际使用的模型标识；降级切换后可能与配置默认值不同。
    model: str
    # 关联的股票代码；大盘复盘等非个股任务为 None。
    stock_code: Optional[str] = None
    # 本次输入 token 数。
    prompt_tokens: int
    # 本次输出 token 数。
    completion_tokens: int
    # 本次输入与输出 token 合计。
    total_tokens: int


class UsageSummaryResponse(BaseModel):
    """用量汇总响应。

    使用场景：/api/v1/usage/summary 按统计周期返回总量与两个维度的分项；from_date / to_date 明确统计区间，避免前端按本地时区自行推算。

    @author: Lensgcx (GaoCangxiong)
    """

    # 统计周期：today / month / all，决定日期区间的取法。
    period: str = Field(..., description="'today' | 'month' | 'all'")
    # 统计区间起始日期（ISO date），含端点。
    from_date: str = Field(..., description="ISO date string")
    # 统计区间结束日期（ISO date），含端点。
    to_date: str = Field(..., description="ISO date string")
    # 区间内总调用次数，与两个维度的分项之和一致。
    total_calls: int
    # 区间内总输入 token，默认 0。
    total_prompt_tokens: int = 0
    # 区间内总输出 token，默认 0。
    total_completion_tokens: int = 0
    # 区间内输入与输出 token 合计。
    total_tokens: int
    # 按调用类型的分项明细列表，无序。
    by_call_type: List[CallTypeBreakdown]
    # 按模型的分项明细列表，无序。
    by_model: List[ModelBreakdown]


class UsageDashboardResponse(UsageSummaryResponse):
    """用量看板响应。

    使用场景：继承汇总字段并附带最近调用明细，一次请求即可渲染看板全部区块。

    @author: Lensgcx (GaoCangxiong)
    """

    # 最近的调用明细列表，由看板端点按时间倒序截取。
    recent_calls: List[UsageCallRecord]
