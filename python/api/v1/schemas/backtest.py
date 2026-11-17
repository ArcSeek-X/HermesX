# -*- coding: utf-8 -*-
"""
@file: backtest.py
@description: 回测接口契约：运行参数、运行汇总、单条回测结果、结果列表与表现指标；由 api.v1.endpoints.backtest 返回，数据来自 src.application.backtest.service 对历史分析结论的事后评估。
@author: Lensgcx (GaoCangxiong)

Backtest API schemas.

Defines the request/response payloads used to evaluate historical
analysis calls against subsequent price action, including direction
accuracy, stop-loss/take-profit hits and simulated returns.

回测以历史分析记录为输入，用其后的真实行情评估结论质量；模拟收益仅为策略观测，不构成实际成交。
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from api.v1.schemas.market_phase import MarketPhaseSummary
from src.domain.decision.action import DecisionAction


class BacktestRunRequest(BaseModel):
    """回测运行请求体。

    使用场景：手动触发批量回测；所有筛选条件均为可选且可组合，未指定时使用服务端默认评估窗口与记录上限。

    @author: Lensgcx (GaoCangxiong)
    """
    # 仅回测指定股票代码；None 表示覆盖全部候选记录。
    code: Optional[str] = Field(None, description="仅回测指定股票")
    # 是否强制重算已有结果，默认 False；开启后可复核引擎版本变更后的结论。
    force: bool = Field(False, description="强制重新计算")
    # 评估窗口的交易日数，范围 1~120；None 表示采用服务端默认窗口。
    eval_window_days: Optional[int] = Field(None, ge=1, le=120, description="评估窗口（交易日数）")
    # 分析记录最小天龄，范围 0~365；0 表示不限，用于排除尚无法评估的新记录。
    min_age_days: Optional[int] = Field(None, ge=0, le=365, description="分析记录最小天龄（0=不限）")
    # 分析日期下界（含），与 to 组合限定回测样本范围。
    analysis_date_from: Optional[date] = Field(None, description="分析日期起始（含）")
    # 分析日期上界（含）；早于 from 时由服务端校验拒绝。
    analysis_date_to: Optional[date] = Field(None, description="分析日期结束（含）")
    # 单次最多处理的分析记录数，默认 200、上限 2000，防止长时间阻塞请求。
    limit: int = Field(200, ge=1, le=2000, description="最多处理的分析记录数")


class BacktestRunResponse(BaseModel):
    """回测运行响应体。

    使用场景：一次回测任务的结果汇总；各计数字段互斥累加，message 与 diagnostics 用于解释为何候选被跳过或结果为空。

    @author: Lensgcx (GaoCangxiong)
    """
    # 进入筛选的候选记录数，包含后续被判定为数据不足或出错的记录。
    processed: int = Field(..., description="候选记录数")
    # 实际写入持久层的回测结果数。
    saved: int = Field(..., description="写入回测结果数")
    # 完成评估并得出结论的记录数。
    completed: int = Field(..., description="完成回测数")
    # 因后续行情不足而无法评估的记录数。
    insufficient: int = Field(..., description="数据不足数")
    # 评估过程异常的记录数；单条失败不影响整批继续。
    errors: int = Field(..., description="错误数")
    # 本次实际生效的评估窗口；请求未指定时回传默认值，便于结果复现。
    applied_eval_window_days: Optional[int] = Field(
        ...,
        description="实际生效的评估窗口（交易日数）",
    )
    # 空结果或发生降级时的诊断说明；正常且有结果时为 None。
    message: Optional[str] = Field(None, description="空结果或降级时的诊断说明")
    # 筛选条件与降级原因的结构化诊断信息，默认空字典。
    diagnostics: Dict[str, Any] = Field(default_factory=dict, description="回测筛选与诊断信息")


class BacktestResultItem(BaseModel):
    """单条历史分析记录的回测结果。

    使用场景：结果列表与详情页；同一记录同时保留原始分析结论、窗口内真实价格表现与模拟交易结果，便于对照复盘。

    @author: Lensgcx (GaoCangxiong)
    """
    # 被回测的分析记录主键，是结果与原始报告的关联键。
    analysis_history_id: int
    # 股票代码，用于结果筛选与分组统计。
    code: str
    # 股票名称；历史记录未保存时为 None。
    stock_name: Optional[str] = None
    # 原始分析的产生日期；与评估窗口起点共同决定样本有效性。
    analysis_date: Optional[str] = None
    # 该条结果实际采用的评估窗口交易日数。
    eval_window_days: int
    # 回测引擎版本；引擎升级后可据此区分不同口径的结果。
    engine_version: str
    # 评估状态（完成 / 数据不足 / 出错），决定其余字段是否可信。
    eval_status: str
    # 回测执行时间；未评估时为 None。
    evaluated_at: Optional[str] = None
    # 原始分析给出的操作建议文本，用于与后续表现对照。
    operation_advice: Optional[str] = None
    # 规范化后的决策动作枚举；旧记录无法映射时为 None。
    action: Optional[DecisionAction] = None
    # 决策动作的展示文案，便于前端直接渲染。
    action_label: Optional[str] = None
    # 原始分析对趋势方向的预测文本。
    trend_prediction: Optional[str] = None
    # 分析发生时的市场阶段简写；旧记录缺失时为 None。
    market_phase: Optional[str] = None
    # 分析发生时的完整阶段摘要；旧记录缺失时为 None。
    market_phase_summary: Optional[MarketPhaseSummary] = None
    # 原始分析给出的仓位建议文本。
    position_recommendation: Optional[str] = None
    # 评估窗口起点的基准价格；行情缺失时为 None。
    start_price: Optional[float] = None
    # 评估窗口终点收盘价；行情缺失时为 None。
    end_close: Optional[float] = None
    # 窗口内最高价，用于判断止盈是否触及。
    max_high: Optional[float] = None
    # 窗口内最低价，用于判断止损是否触及。
    min_low: Optional[float] = None
    # 窗口内标的涨跌幅百分比，衡量未择时的基准收益。
    stock_return_pct: Optional[float] = None
    # 按原始建议方向折算的实际收益百分比。
    actual_return_pct: Optional[float] = None
    # 窗口内实际走势分类（上涨 / 下跌 / 震荡）。
    actual_movement: Optional[str] = None
    # 原始结论预期方向，与 direction_correct 配套使用。
    direction_expected: Optional[str] = None
    # 方向预测是否正确；方向不明确时为 None，不计入准确率。
    direction_correct: Optional[bool] = None
    # 本次回测的最终归类（盈利 / 亏损 / 中性 / 未评估）。
    outcome: Optional[str] = None
    # 原始分析给出的止损价；未给出时为 None。
    stop_loss: Optional[float] = None
    # 原始分析给出的止盈价；未给出时为 None。
    take_profit: Optional[float] = None
    # 窗口内是否触及止损价；无止损价时为 None。
    hit_stop_loss: Optional[bool] = None
    # 窗口内是否触及止盈价；无止盈价时为 None。
    hit_take_profit: Optional[bool] = None
    # 止损与止盈中先被触及的一方；两者同日触及或均未触及时的取值由引擎判定。
    first_hit: Optional[str] = None
    # 首次触及止盈/止损的日期。
    first_hit_date: Optional[str] = None
    # 从分析日到首次触及所经历的交易日数，用于评估信号时效性。
    first_hit_trading_days: Optional[int] = None
    # 模拟建仓价格；未进入模拟交易时为 None。
    simulated_entry_price: Optional[float] = None
    # 模拟平仓价格；持仓到窗口结束或提前触发退出时不同。
    simulated_exit_price: Optional[float] = None
    # 模拟平仓原因（止盈 / 止损 / 窗口结束），用于分析退出逻辑。
    simulated_exit_reason: Optional[str] = None
    # 按模拟建平仓价格计算的收益百分比，仅为策略观测值。
    simulated_return_pct: Optional[float] = None


class BacktestResultsResponse(BaseModel):
    """回测结果分页列表响应体。

    使用场景：结果页按页拉取；total 为符合条件的总数，与当前页 items 长度不等价。

    @author: Lensgcx (GaoCangxiong)
    """
    # 符合筛选条件的回测结果总数，用于分页计算。
    total: int
    # 当前页码，从 1 开始。
    page: int
    # 当前页的最大条数，与请求参数一致。
    limit: int
    # 当前页结果列表；无数据为空列表。
    items: List[BacktestResultItem] = Field(default_factory=list)


class PerformanceMetrics(BaseModel):
    """回测表现聚合指标。

    使用场景：看板按全市场或单只股票统计胜率、方向准确率与触发率；比率类字段在无样本时为 None，避免用 0 掩盖「无数据」。

    @author: Lensgcx (GaoCangxiong)
    """
    # 统计范围标识（全市场或单只股票），决定 code 是否有值。
    scope: str
    # 统计范围对应的股票代码；全市场统计时为 None。
    code: Optional[str] = None
    # 本次统计所采用的评估窗口交易日数。
    eval_window_days: int
    # 结果所属的回测引擎版本，避免跨版本口径混合。
    engine_version: str
    # 指标计算时间；未计算时为 None。
    computed_at: Optional[str] = None

    # 参与统计的回测结果总数，是各状态计数的分母。
    total_evaluations: int
    # 状态为已完成的评估数。
    completed_count: int
    # 因行情不足而未能评估的数量。
    insufficient_count: int
    # 结论偏向持有的评估数。
    long_count: int
    # 结论偏向持币的评估数。
    cash_count: int
    # 结果为盈利的评估数。
    win_count: int
    # 结果为亏损的评估数。
    loss_count: int
    # 结果为中性的评估数，通常不计入胜率分子。
    neutral_count: int

    # 方向预测正确率百分比；无可判定样本时为 None。
    direction_accuracy_pct: Optional[float] = None
    # 盈利占比百分比；无有效样本时为 None。
    win_rate_pct: Optional[float] = None
    # 中性结果占比百分比；无有效样本时为 None。
    neutral_rate_pct: Optional[float] = None
    # 标的基准涨跌幅的平均值，作为策略表现的对照基线。
    avg_stock_return_pct: Optional[float] = None
    # 模拟收益平均值，与基准对比可观察择时增益。
    avg_simulated_return_pct: Optional[float] = None

    # 止损触发率百分比；样本未给出止损价时为 None。
    stop_loss_trigger_rate: Optional[float] = None
    # 止盈触发率百分比；样本未给出止盈价时为 None。
    take_profit_trigger_rate: Optional[float] = None
    # 止盈止损同日触及等歧义样本占比，用于提示指标可信度。
    ambiguous_rate: Optional[float] = None
    # 平均首次触及止盈/止损所需交易日数，衡量信号有效期。
    avg_days_to_first_hit: Optional[float] = None

    # 按操作建议分类的分布统计，默认空字典。
    advice_breakdown: Dict[str, Any] = Field(default_factory=dict)
    # 统计口径与降级说明，默认空字典。
    diagnostics: Dict[str, Any] = Field(default_factory=dict)
