# -*- coding: utf-8 -*-
"""
@file: history.py
@description: 历史记录与分析报告契约：列表摘要、删除请求、新闻情报、完整报告分区（meta / summary / strategy / details）、上下文包低敏摘要、个股栏与运行诊断摘要；由 api.v1.endpoints.history 返回。
@author: Lensgcx (GaoCangxiong)

===================================
历史记录相关模型
===================================

职责：
1. 定义历史记录列表和详情模型
2. 定义分析报告完整模型
"""

from typing import Optional, List, Any, Dict, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from api.v1.schemas.market_phase import MarketPhaseSummary
from src.domain.decision.action import DecisionAction


class HistoryItem(BaseModel):
    """历史记录摘要（列表展示用）。

    使用场景：历史列表页；字段是报告结论的扁平快照，避免为渲染列表逐条解析完整报告。部分字段来自旧数据，故统一允许 None。

    @author: Lensgcx (GaoCangxiong)
    """

    # 历史记录主键 ID；来自无持久化主键的旧数据时为 None。
    id: Optional[int] = Field(None, description="分析历史记录主键 ID")
    # 分析记录关联 ID；批量分析时多条记录共享，是报告与历史的关联键。
    query_id: str = Field(..., description="分析记录关联 query_id（批量分析时重复）")
    # 规范股票代码，标识报告对应的标的。
    stock_code: str = Field(..., description="股票代码")
    # 股票名称；历史记录未保存或映射失败时为 None。
    stock_name: Optional[str] = Field(None, description="股票名称")
    # 报告类型（simple / detailed / full / brief），决定前端采用的展示模板。
    report_type: Optional[str] = Field(None, description="报告类型")
    # 大盘复盘实际执行的规范化市场范围；个股分析记录为 None。
    region: Optional[str] = Field(
        None,
        description="大盘复盘实际执行的 canonical 市场范围",
    )
    # 报告给出的趋势方向预测文本。
    trend_prediction: Optional[str] = Field(None, description="趋势预测")
    # 报告关键结论摘要，供列表页直接展示而无需解析整篇报告。
    analysis_summary: Optional[str] = Field(None, description="分析摘要")
    # 情绪评分；历史数据可能超出 0~100，读取时刻意不加范围约束以免旧报告被拒。
    sentiment_score: Optional[int] = Field(
        None,
        description="情绪评分（历史数据可能超出 0-100 范围，读取时不做约束）",
    )
    # 报告给出的操作建议原文。
    operation_advice: Optional[str] = Field(None, description="操作建议")
    # 规范化后的建议动作枚举；旧报告无法映射时为 None。
    action: Optional[DecisionAction] = Field(None, description="结构化建议动作 taxonomy")
    # 建议动作的展示文案，前端无需自行翻译枚举值。
    action_label: Optional[str] = Field(None, description="建议动作展示标签")
    # 分析时刻的股价快照，用于与当前价格对照。
    current_price: Optional[float] = Field(None, description="分析时股价")
    # 分析时刻的涨跌幅百分比快照。
    change_pct: Optional[float] = Field(None, description="分析时涨跌幅(%)")
    # 分析时刻的量比快照；旧记录未保存时为 None。
    volume_ratio: Optional[float] = Field(None, description="分析时量比")
    # 分析时刻的换手率快照；旧记录未保存时为 None。
    turnover_rate: Optional[float] = Field(None, description="分析时换手率")
    # 历史元数据中的模型名快照，仅供展示，不参与运行时模型路由或配置决策。
    model_used: Optional[str] = Field(
        None,
        description="分析历史记录中的模型快照，仅用于展示历史元数据；不参与模型配置或运行时路由决策",
    )
    # 分析时刻的市场阶段低敏摘要；旧记录缺失时为 None。
    market_phase_summary: Optional[MarketPhaseSummary] = Field(
        None,
        description="本次分析市场阶段低敏摘要",
    )
    # 记录创建时间字符串，用于列表排序与展示。
    created_at: Optional[str] = Field(None, description="创建时间")
    
    # 仅用于 OpenAPI 展示响应示例，不参与字段校验或运行时行为。
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": 1234,
            "query_id": "abc123",
            "stock_code": "600519",
            "stock_name": "贵州茅台",
            "report_type": "detailed",
            "sentiment_score": 75,
            "operation_advice": "持有",
            "created_at": "2024-01-01T12:00:00"
        }
    })


class HistoryListResponse(BaseModel):
    """历史记录列表响应。

    使用场景：历史列表分页接口；total 为符合条件的总数，items 为空列表表示无匹配而非请求失败。

    @author: Lensgcx (GaoCangxiong)
    """
    
    # 符合条件的记录总数，用于分页计算或数量展示。
    total: int = Field(..., description="总记录数")
    # 当前页码，从 1 开始。
    page: int = Field(..., description="当前页码")
    # 每页条数，与请求参数一致。
    limit: int = Field(..., description="每页数量")
    # 当前页历史记录列表；无匹配为空列表。
    items: List[HistoryItem] = Field(default_factory=list, description="记录列表")
    
    # 仅用于 OpenAPI 展示响应示例，不参与字段校验或运行时行为。
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "total": 100,
            "page": 1,
            "limit": 20,
            "items": []
        }
    })


class DeleteHistoryRequest(BaseModel):
    """删除历史记录请求。

    使用场景：批量删除；以记录主键列表为输入，空列表等价于不删除，由端点决定是否拒绝。

    @author: Lensgcx (GaoCangxiong)
    """

    # 待删除的历史记录主键列表，默认空列表；不做逐项存在性预校验。
    record_ids: List[int] = Field(default_factory=list, description="要删除的历史记录主键 ID 列表")


class DeleteHistoryResponse(BaseModel):
    """删除历史记录响应。

    使用场景：回传实际删除条数，便于前端判断是否有记录被跳过。

    @author: Lensgcx (GaoCangxiong)
    """

    # 实际删除的记录数；小于请求数表示部分 ID 不存在或无权删除。
    deleted: int = Field(..., description="实际删除的历史记录数量")


class NewsIntelItem(BaseModel):
    """新闻情报条目。

    使用场景：报告详情的新闻区；snippet 允许为空字符串，保证无摘要时标题与链接仍可展示。

    @author: Lensgcx (GaoCangxiong)
    """

    # 新闻标题，必填。
    title: str = Field(..., description="新闻标题")
    # 新闻摘要，默认空字符串；检索源未给摘要时仍可展示标题与链接。
    snippet: str = Field("", description="新闻摘要（最多200字）")
    # 新闻原文链接，前端以新窗口打开。
    url: str = Field(..., description="新闻链接")

    # 仅用于 OpenAPI 展示响应示例，不参与字段校验或运行时行为。
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "title": "公司发布业绩快报，营收同比增长 20%",
            "snippet": "公司公告显示，季度营收同比增长 20%...",
            "url": "https://example.com/news/123"
        }
    })


class NewsIntelResponse(BaseModel):
    """新闻情报响应。

    使用场景：新闻检索结果；items 为空列表表示无命中。

    @author: Lensgcx (GaoCangxiong)
    """

    # 本次检索命中的新闻条数。
    total: int = Field(..., description="新闻条数")
    # 新闻条目列表；无命中为空列表。
    items: List[NewsIntelItem] = Field(default_factory=list, description="新闻列表")

    # 仅用于 OpenAPI 展示响应示例，不参与字段校验或运行时行为。
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "total": 2,
            "items": []
        }
    })


class ReportMeta(BaseModel):
    """报告元信息。

    使用场景：完整报告的 meta 区；携带分析时刻的价格与模型快照，用于回看结论所依据的上下文。含 model_used 字段，故关闭 Pydantic protected namespace 警告而非改名，以免破坏既有报告结构。

    @author: Lensgcx (GaoCangxiong)
    """

    # 关闭 protected_namespaces 告警，使 model_used 字段不触发 Pydantic 命名冲突警告；不改字段名以兼容既有报告。
    model_config = ConfigDict(protected_namespaces=("model_validate", "model_dump"))

    # 历史记录主键；非持久化来源（如实时生成的报告）为 None。
    id: Optional[int] = Field(None, description="分析历史记录主键 ID（仅历史报告有此字段）")
    # 分析记录关联 ID；批量分析时多条记录共享，是报告与历史的关联键。
    query_id: str = Field(..., description="分析记录关联 query_id（批量分析时重复）")
    # 规范股票代码，标识报告对应的标的。
    stock_code: str = Field(..., description="股票代码")
    # 股票名称；历史记录未保存或映射失败时为 None。
    stock_name: Optional[str] = Field(None, description="股票名称")
    # 报告类型（simple / detailed / full / brief），决定前端采用的展示模板。
    report_type: Optional[str] = Field(None, description="报告类型")
    # 报告输出语言标识；旧报告未记录时为 None。
    report_language: Optional[str] = Field(None, description="报告输出语言（zh/en）")
    # 记录创建时间字符串，用于列表排序与展示。
    created_at: Optional[str] = Field(None, description="创建时间")
    # 分析时刻股价快照，用于回看结论的价格背景。
    current_price: Optional[float] = Field(None, description="分析时股价")
    # 分析时刻涨跌幅百分比快照。
    change_pct: Optional[float] = Field(None, description="分析时涨跌幅(%)")
    # 历史元数据中的模型名快照，仅供展示，不参与运行时模型路由或配置决策。
    model_used: Optional[str] = Field(
        None,
        description="历史报告元数据中的模型快照，仅用于展示；不参与运行时模型调用路径或配置路由",
    )
    # 分析时刻的市场阶段低敏摘要；旧记录缺失时为 None。
    market_phase_summary: Optional[MarketPhaseSummary] = Field(
        None,
        description="本次分析市场阶段低敏摘要",
    )


class ReportSummary(BaseModel):
    """报告概览区。

    使用场景：报告首屏的核心结论；情绪评分为兼容历史越界值不做范围约束。

    @author: Lensgcx (GaoCangxiong)
    """
    
    # 报告关键结论摘要，供列表页直接展示而无需解析整篇报告。
    analysis_summary: Optional[str] = Field(None, description="关键结论")
    # 报告给出的操作建议原文。
    operation_advice: Optional[str] = Field(None, description="操作建议")
    # 规范化后的建议动作枚举；旧报告无法映射时为 None。
    action: Optional[DecisionAction] = Field(None, description="结构化建议动作 taxonomy")
    # 建议动作的展示文案，前端无需自行翻译枚举值。
    action_label: Optional[str] = Field(None, description="建议动作展示标签")
    # 报告给出的趋势方向预测文本。
    trend_prediction: Optional[str] = Field(None, description="趋势预测")
    # 情绪评分；历史数据可能超出 0~100，读取时刻意不加范围约束以免旧报告被拒。
    sentiment_score: Optional[int] = Field(
        None,
        description="情绪评分（历史数据可能超出 0-100 范围，读取时不做约束）",
    )
    # 情绪评分对应的可读标签（如乐观 / 中性），前端直接展示。
    sentiment_label: Optional[str] = Field(None, description="情绪标签")


class ReportStrategy(BaseModel):
    """策略点位区。

    使用场景：展示买卖与止盈止损价位；均为字符串以保留报告原文的区间与单位表达（如「1800~1820」），不强制转成浮点数。

    @author: Lensgcx (GaoCangxiong)
    """
    
    # 理想买入价或区间，字符串保留报告原始表达。
    ideal_buy: Optional[str] = Field(None, description="理想买入价")
    # 第二买入价或回踩买点，未给出时为 None。
    secondary_buy: Optional[str] = Field(None, description="第二买入价")
    # 止损价位，未给出时为 None。
    stop_loss: Optional[str] = Field(None, description="止损价")
    # 止盈价位，未给出时为 None。
    take_profit: Optional[str] = Field(None, description="止盈价")


class AnalysisContextPackOverviewSubject(BaseModel):
    """AnalysisContextPack 可见摘要的标的信息。

    使用场景：说明上下文包描述的是哪只标的；仅含可公开字段，避免泄露账户与持仓。

    @author: Lensgcx (GaoCangxiong)
    """

    # 上下文包描述的股票代码。
    code: str = Field(..., description="股票代码")
    # 股票名称；历史记录未保存或映射失败时为 None。
    stock_name: Optional[str] = Field(None, description="股票名称")
    # 标的市场标识；无法确定时为 None。
    market: Optional[str] = Field(None, description="市场")


class AnalysisContextPackOverviewBlock(BaseModel):
    """AnalysisContextPack 可见摘要的单个数据块。

    使用场景：报告详情展示各输入数据的质量状态；status 取值逐一标明降级原因，用户可据此判断结论可信度。

    @author: Lensgcx (GaoCangxiong)
    """

    # 数据块/组件的稳定标识，用于前后端映射，不随展示文案变化。
    key: str = Field(..., description="数据块稳定 key")
    # 数据块的展示名称，如「实时行情」「新闻检索」。
    label: str = Field(..., description="数据块展示名称")
    # 数据块质量状态，取值见 Literal 逐项注释；决定前端是否显示降级提示。
    status: Literal[
        "available",      # 数据完整可用
        "missing",        # 上游未提供该数据块
        "not_supported",  # 当前市场或标的不支持该数据块
        "fallback",       # 主来源失败，已回退到备用来源
        "stale",          # 数据过期但可展示，需标注时效
        "estimated",      # 数值为估算而非实测
        "partial",        # 仅部分字段可用
        "fetch_failed",   # 抓取失败，无可用数据
    ] = Field(..., description="数据块质量状态")
    # 该数据块实际使用的数据来源标识；完全缺失时为 None。
    source: Optional[str] = Field(None, description="数据来源")
    # 数据质量告警码列表；无告警时为空列表。
    warnings: List[str] = Field(default_factory=list, description="数据块告警码")
    # 数据缺失/降级的原因码列表，默认空列表。
    missing_reasons: List[str] = Field(default_factory=list, description="缺失原因")


class AnalysisContextPackOverviewCounts(BaseModel):
    """AnalysisContextPack 可见摘要的状态计数。

    使用场景：概览区按状态聚合数据块数量，与 AnalysisContextPackOverviewBlock.status 的取值一一对应。

    @author: Lensgcx (GaoCangxiong)
    """

    # 状态为 available 的数据块数量。
    available: int = 0
    # 状态为 missing 的数据块数量。
    missing: int = 0
    # 状态为 not_supported 的数据块数量。
    not_supported: int = 0
    # 状态为 fallback 的数据块数量。
    fallback: int = 0
    # 状态为 stale 的数据块数量。
    stale: int = 0
    # 状态为 estimated 的数据块数量。
    estimated: int = 0
    # 状态为 partial 的数据块数量。
    partial: int = 0
    # 状态为 fetch_failed 的数据块数量。
    fetch_failed: int = 0


class AnalysisContextPackOverviewMetadata(BaseModel):
    """AnalysisContextPack 可见摘要元数据。

    使用场景：说明上下文包的触发来源与新闻样本量，用于解释数据为何偏少。

    @author: Lensgcx (GaoCangxiong)
    """

    # 本次上下文包构建的触发来源，用于追溯任务入口。
    trigger_source: Optional[str] = Field(None, description="触发来源")
    # 新闻检索返回的原始结果数；未执行检索时为 None。
    news_result_count: Optional[int] = Field(None, description="新闻结果数量")


class AnalysisContextPackOverviewDataQuality(BaseModel):
    """AnalysisContextPack 可见摘要的数据质量评分。

    使用场景：给出输入数据整体质量分与等级；limitations 以低敏文案说明局限，不暴露原始内部细节。

    @author: Lensgcx (GaoCangxiong)
    """

    # 输入数据质量总分 0~100；无法评估时为 None。
    overall_score: Optional[int] = Field(None, ge=0, le=100, description="输入数据质量总分")
    # 质量等级 good / usable / limited / poor；无法评估时为 None。
    level: Optional[Literal["good", "usable", "limited", "poor"]] = Field(
        None,
        description="输入数据质量等级",
    )
    # 各固定数据块的质量分字典，默认空字典。
    block_scores: Dict[str, int] = Field(default_factory=dict, description="固定数据块质量分")
    # 低敏的数据局限说明列表，默认空列表。
    limitations: List[str] = Field(default_factory=list, description="低敏数据限制说明")


class AnalysisContextPackOverview(BaseModel):
    """历史/API 可见的低敏 AnalysisContextPack 摘要。

    使用场景：报告详情与历史记录展示分析输入质量；pack_version 用于兼容不同版本的上下文包结构。

    @author: Lensgcx (GaoCangxiong)
    """

    # 上下文包结构版本号，前端据此选择解析与展示方式。
    pack_version: str = Field(..., description="AnalysisContextPack 版本")
    # 上下文包创建时间；旧记录未保存时为 None。
    created_at: Optional[str] = Field(None, description="创建时间")
    # 上下文包描述的标的信息，必填。
    subject: AnalysisContextPackOverviewSubject
    # 各数据块的质量明细列表，默认空列表。
    blocks: List[AnalysisContextPackOverviewBlock] = Field(default_factory=list)
    # 按质量状态聚合的计数，必填。
    counts: AnalysisContextPackOverviewCounts
    # 整体质量评分摘要；旧版本上下文包为 None。
    data_quality: Optional[AnalysisContextPackOverviewDataQuality] = Field(
        None,
        description="本次分析输入数据质量低敏摘要",
    )
    # 顶层数据质量提醒码列表，默认空列表。
    warnings: List[str] = Field(default_factory=list, description="顶层数据质量提醒")
    # 上下文包元数据；缺省时由默认工厂创建空元数据。
    metadata: AnalysisContextPackOverviewMetadata = Field(default_factory=AnalysisContextPackOverviewMetadata)


class ReportDetails(BaseModel):
    """报告详情区。

    使用场景：展开报告时提供新闻、原始结果与上下文快照；包含向后兼容的 model_validator，能从旧上下文快照补齐新字段。

    @author: Lensgcx (GaoCangxiong)
    """
    
    # 报告中的新闻摘要正文；无新闻输入时为 None。
    news_content: Optional[str] = Field(None, description="新闻摘要")
    # 原始分析结果的 JSON 结构，保留以便排查与后续字段扩展。
    raw_result: Optional[Any] = Field(None, description="原始分析结果（JSON）")
    # 分析时刻的完整上下文快照 JSON，是派生字段的回溯来源。
    context_snapshot: Optional[Any] = Field(None, description="分析时上下文快照（JSON）")
    # 输入上下文包的低敏摘要；旧报告无该结构时为 None。
    analysis_context_pack_overview: Optional[AnalysisContextPackOverview] = Field(
        None,
        description="本次分析输入上下文包低敏摘要",
    )
    # 结构化财报摘要，来自 fundamental_context；未取到时为 None。
    financial_report: Optional[Any] = Field(None, description="结构化财报摘要（来自 fundamental_context）")
    # 结构化分红指标（含 TTM 口径）；未取到时为 None。
    dividend_metrics: Optional[Any] = Field(None, description="结构化分红指标（含 TTM 口径）")
    # 标的关联板块列表；未取到时为 None。
    belong_boards: Optional[Any] = Field(None, description="关联板块列表")
    # 行业板块涨跌榜，结构为 {top, bottom}；旧报告由验证器补齐。
    sector_rankings: Optional[Any] = Field(None, description="板块涨跌榜（结构 {top, bottom}）")
    # 概念板块涨跌榜，结构为 {top, bottom}；旧报告从 context_snapshot 派生。
    concept_rankings: Optional[Any] = Field(None, description="概念板块涨跌榜（结构 {top, bottom}）")
    # 市场结构上下文（题材层 + 个股位置层）；旧报告由验证器从快照与原始结果派生。
    market_structure: Optional[Any] = Field(None, description="市场结构上下文（题材层 + 个股位置层）")

    @model_validator(mode="after")
    def populate_context_derived_details(self) -> "ReportDetails":
        """填充由上下文快照派生的历史详情字段。

        为旧报告补齐 concept_rankings 与 market_structure：新报告已直接落库这些字段，只有历史数据需要从 context_snapshot / raw_result 反解。提取失败时静默置 None，保证旧数据仍能被读取。

        Args:
            无显式参数；读取 self.context_snapshot 与 self.raw_result。

        Returns:
            ReportDetails: 返回 self，符合 Pydantic after-validator 约定。

        Raises:
            不向外抛出；提取函数异常被捕获并降级为 None。

        Side Effects:
            原地修改 self.concept_rankings 与 self.market_structure。
        """
        if self.concept_rankings is None and self.context_snapshot is not None:
            try:
                from src.utils.data_processing import extract_board_detail_fields

                extracted = extract_board_detail_fields(self.context_snapshot)
                self.concept_rankings = extracted.get("concept_rankings")
            except Exception:
                self.concept_rankings = None
        if self.market_structure is None:
            try:
                from src.utils.data_processing import extract_market_structure_detail_field

                self.market_structure = extract_market_structure_detail_field(
                    self.context_snapshot,
                    self.raw_result,
                )
            except Exception:
                self.market_structure = None
        return self


class AnalysisReport(BaseModel):
    """完整分析报告。

    使用场景：历史报告详情接口；按 meta / summary / strategy / details 分区，后两区允许缺失以兼容精简报告。

    @author: Lensgcx (GaoCangxiong)
    """

    # 报告元信息区，必填。
    meta: ReportMeta = Field(..., description="元信息")
    # 报告概览区，必填。
    summary: ReportSummary = Field(..., description="概览区")
    # 策略点位区；精简报告可能没有该区，为 None。
    strategy: Optional[ReportStrategy] = Field(None, description="策略点位区")
    # 报告详情区；精简报告或旧数据为 None。
    details: Optional[ReportDetails] = Field(None, description="详情区")

    # 仅用于 OpenAPI 展示响应示例，不参与字段校验或运行时行为。
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "meta": {
                "query_id": "abc123",
                "stock_code": "600519",
                "stock_name": "贵州茅台",
                "report_type": "detailed",
                "report_language": "zh",
                "created_at": "2024-01-01T12:00:00"
            },
            "summary": {
                "analysis_summary": "技术面向好，建议持有",
                "operation_advice": "持有",
                "trend_prediction": "看多",
                "sentiment_score": 75,
                "sentiment_label": "乐观"
            },
            "strategy": {
                "ideal_buy": "1800.00",
                "secondary_buy": "1750.00",
                "stop_loss": "1700.00",
                "take_profit": "2000.00"
            },
            "details": None
        }
    })


class MarkdownReportResponse(BaseModel):
    """Markdown 格式报告响应。

    使用场景：导出与复制场景，直接返回可渲染的整篇 Markdown 文本。

    @author: Lensgcx (GaoCangxiong)
    """

    # 可直接渲染或导出的整篇 Markdown 报告文本，必填。
    content: str = Field(..., description="Markdown 格式的完整报告内容")

    # 仅用于 OpenAPI 展示响应示例，不参与字段校验或运行时行为。
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "content": "# 📊 贵州茅台 (600519) 分析报告\n\n> 分析日期：**2024-01-01**\n\n..."
        }
    })


class StockBarItem(BaseModel):
    """个股栏条目（去重后的股票维度摘要）。

    使用场景：个股侧栏按股票聚合，只展示该股最新一次分析的结论；analysis_count 提供历史深度，避免用户误以为只有一次分析。

    @author: Lensgcx (GaoCangxiong)
    """

    # 该股票最新一次分析的历史记录主键，供点击跳转到对应报告。
    id: int = Field(..., description="该股最新一次分析的历史记录主键 ID")
    # 规范股票代码，标识报告对应的标的。
    stock_code: str = Field(..., description="股票代码")
    # 股票名称；历史记录未保存或映射失败时为 None。
    stock_name: Optional[str] = Field(None, description="股票名称")
    # 报告类型（simple / detailed / full / brief），决定前端采用的展示模板。
    report_type: Optional[str] = Field(None, description="报告类型")
    # 情绪评分；历史数据可能超出 0~100，读取时刻意不加范围约束以免旧报告被拒。
    sentiment_score: Optional[int] = Field(
        None,
        description="最新情绪评分",
    )
    # 报告给出的操作建议原文。
    operation_advice: Optional[str] = Field(None, description="最新操作建议")
    # 规范化后的建议动作枚举；旧报告无法映射时为 None。
    action: Optional[DecisionAction] = Field(None, description="结构化建议动作 taxonomy")
    # 建议动作的展示文案，前端无需自行翻译枚举值。
    action_label: Optional[str] = Field(None, description="建议动作展示标签")
    # 该股票的历史分析总次数，用于提示结论样本量。
    analysis_count: int = Field(..., description="该股票的历史分析总次数")
    # 最近一次分析时间；无历史分析时为 None。
    last_analysis_time: Optional[str] = Field(None, description="最近一次分析时间")
    # 历史元数据中的模型名快照，仅供展示，不参与运行时模型路由或配置决策。
    model_used: Optional[str] = Field(
        None,
        description="最新分析使用的模型快照，仅用于列表展示；不改动运行时调用与配置路径",
    )
    # 分析时刻的市场阶段低敏摘要；旧记录缺失时为 None。
    market_phase_summary: Optional[MarketPhaseSummary] = Field(
        None,
        description="最新分析市场阶段低敏摘要",
    )
    # 仅用于 OpenAPI 展示响应示例，不参与字段校验或运行时行为。
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": 1234,
            "stock_code": "600519",
            "stock_name": "贵州茅台",
            "report_type": "detailed",
            "sentiment_score": 75,
            "operation_advice": "持有",
            "analysis_count": 18,
            "last_analysis_time": "2024-01-01T12:00:00",
            "model_used": "Gemini 2.5 Pro",
        }
    })


class StockBarResponse(BaseModel):
    """个股栏列表响应。

    使用场景：侧栏一次性返回去重后的个股摘要列表。

    @author: Lensgcx (GaoCangxiong)
    """

    # 去重后的个股数量，与 items 长度在单页返回时一致。
    total: int = Field(..., description="不重复个股数")
    # 去重后的个股摘要列表；无数据为空列表。
    items: List[StockBarItem] = Field(default_factory=list, description="个股列表")


class WatchlistRequest(BaseModel):
    """自选队列操作请求。

    使用场景：从历史页把标的加入/移出自选队列；代码至少 1 字符。

    @author: Lensgcx (GaoCangxiong)
    """

    # 要加入/移出自选队列的股票代码，至少 1 字符。
    stock_code: str = Field(..., description="股票代码", min_length=1)


class WatchlistResponse(BaseModel):
    """自选队列响应。

    使用场景：回传操作后的完整代码列表，前端无需本地推导增删结果。

    @author: Lensgcx (GaoCangxiong)
    """

    # 操作后完整的自选队列代码列表，默认空列表。
    stock_codes: List[str] = Field(default_factory=list, description="当前自选队列股票代码列表")
    # 操作结果描述，供前端提示。
    message: str = Field(..., description="操作结果描述")


class RunDiagnosticComponent(BaseModel):
    """单个运行诊断组件摘要。

    使用场景：运行诊断卡片按链路组件展开，details 默认折叠，避免首屏被技术细节淹没。

    @author: Lensgcx (GaoCangxiong)
    """

    # 数据块/组件的稳定标识，用于前后端映射，不随展示文案变化。
    key: str = Field(..., description="组件键")
    # 面向用户的展示名称。
    label: str = Field(..., description="组件显示名称")
    # 组件状态：ok / degraded / failed / unknown / not_configured / skipped。
    status: str = Field(..., description="组件状态：ok/degraded/failed/unknown/not_configured/skipped")
    # 该组件的用户可读摘要，避免直接暴露技术堆栈。
    message: str = Field(..., description="用户可读摘要")
    # 折叠展示的诊断细节字典；无细节时为 None。
    details: Optional[Dict[str, Any]] = Field(None, description="折叠展示的诊断细节")


class RunDiagnosticSummaryResponse(BaseModel):
    """历史报告运行诊断摘要。

    使用场景：解释某次分析为何降级或失败；copy_text 是脱敏后的排障文本，可直接提供给支持人员。

    @author: Lensgcx (GaoCangxiong)
    """

    # 诊断 trace ID，用于日志串联；旧记录为 None。
    trace_id: Optional[str] = Field(None, description="诊断 trace ID")
    # 关联任务 ID；同步分析或旧记录为 None。
    task_id: Optional[str] = Field(None, description="任务 ID")
    # 关联分析记录 ID；用于回查报告。
    query_id: Optional[str] = Field(None, description="分析 query ID")
    # 被诊断分析的股票代码；大盘复盘任务可能为 None。
    stock_code: Optional[str] = Field(None, description="股票代码")
    # 分析触发来源，用于区分定时、手动与 API 调用。
    trigger_source: Optional[str] = Field(None, description="触发来源")
    # 总体状态：normal / degraded / failed / unknown。
    status: str = Field(..., description="总体状态：normal/degraded/failed/unknown")
    # 总体状态的中文标签，前端直接展示。
    status_label: str = Field(..., description="总体状态中文标签")
    # 最主要的诊断原因，如「实时行情失败：timeout」。
    reason: str = Field(..., description="最主要的诊断原因")
    # 按组件 key 索引的关键链路诊断结果，默认空字典。
    components: Dict[str, RunDiagnosticComponent] = Field(default_factory=dict, description="关键链路诊断组件")
    # 脱敏后的可复制排障文本，便于用户提交问题反馈。
    copy_text: str = Field(..., description="可复制的脱敏排障文本")

    # 仅用于 OpenAPI 展示响应示例，不参与字段校验或运行时行为。
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "trace_id": "task_abc123",
            "query_id": "task_abc123",
            "stock_code": "600519",
            "status": "degraded",
            "status_label": "部分降级",
            "reason": "实时行情失败：timeout",
            "components": {},
            "copy_text": "trace_id: task_abc123\nstock_code: 600519\n...",
        }
    })
