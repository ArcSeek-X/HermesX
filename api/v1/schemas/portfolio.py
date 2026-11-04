# -*- coding: utf-8 -*-
"""Portfolio API schemas.

组合（Portfolio）相关 API 的 Pydantic 请求/响应模型，涵盖账户、交易、资金流水、公司行动、持仓快照、文件导入与风险查询。
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class PortfolioAccountCreateRequest(BaseModel):
    """创建投资组合账户的请求体（名称、券商、市场、基准货币、归属人）。"""

    name: str = Field(..., min_length=1, max_length=64)
    broker: Optional[str] = Field(None, max_length=64)
    market: Literal["cn", "hk", "us", "jp", "kr", "tw"] = "cn"
    base_currency: str = Field("CNY", min_length=3, max_length=8)
    owner_id: Optional[str] = Field(None, max_length=64)


class PortfolioAccountUpdateRequest(BaseModel):
    """更新投资组合账户的请求体，所有字段均可选。"""

    name: Optional[str] = Field(None, min_length=1, max_length=64)
    broker: Optional[str] = Field(None, max_length=64)
    market: Optional[Literal["cn", "hk", "us", "jp", "kr", "tw"]] = None
    base_currency: Optional[str] = Field(None, min_length=3, max_length=8)
    owner_id: Optional[str] = Field(None, max_length=64)
    is_active: Optional[bool] = None


class PortfolioAccountItem(BaseModel):
    """投资组合账户详情项。"""

    id: int
    owner_id: Optional[str] = None
    name: str
    broker: Optional[str] = None
    market: str
    base_currency: str
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PortfolioAccountListResponse(BaseModel):
    """投资组合账户列表响应。"""

    accounts: List[PortfolioAccountItem] = Field(default_factory=list)


class PortfolioTradeCreateRequest(BaseModel):
    """新建交易记录的请求体（账户、标的、日期、买卖方向、数量与价格等）。"""

    account_id: int
    symbol: str = Field(..., min_length=1, max_length=16)
    trade_date: date
    side: Literal["buy", "sell"]
    quantity: float = Field(..., gt=0)
    price: float = Field(..., gt=0)
    fee: float = Field(0.0, ge=0)
    tax: float = Field(0.0, ge=0)
    market: Optional[Literal["cn", "hk", "us", "jp", "kr", "tw"]] = None
    currency: Optional[str] = Field(None, min_length=3, max_length=8)
    trade_uid: Optional[str] = Field(None, max_length=128)
    note: Optional[str] = Field(None, max_length=255)


class PortfolioCashLedgerCreateRequest(BaseModel):
    """新建资金流水（入金/出金）的请求体。"""

    account_id: int
    event_date: date
    direction: Literal["in", "out"]
    amount: float = Field(..., gt=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=8)
    note: Optional[str] = Field(None, max_length=255)


class PortfolioCorporateActionCreateRequest(BaseModel):
    """新建公司行动（分红、送转、拆合股等）的请求体。"""

    account_id: int
    symbol: str = Field(..., min_length=1, max_length=16)
    effective_date: date
    action_type: Literal["cash_dividend", "split_adjustment"]
    market: Optional[Literal["cn", "hk", "us", "jp", "kr", "tw"]] = None
    currency: Optional[str] = Field(None, min_length=3, max_length=8)
    cash_dividend_per_share: Optional[float] = Field(None, ge=0)
    split_ratio: Optional[float] = Field(None, gt=0)
    note: Optional[str] = Field(None, max_length=255)


class PortfolioEventCreatedResponse(BaseModel):
    """组合事件（交易/流水/公司行动）创建结果响应。"""

    id: int


class PortfolioDeleteResponse(BaseModel):
    """组合资源删除结果响应。"""

    deleted: int


class PortfolioTradeListItem(BaseModel):
    """交易记录列表项。"""

    id: int
    account_id: int
    trade_uid: Optional[str] = None
    symbol: str
    market: str
    currency: str
    trade_date: str
    side: str
    quantity: float
    price: float
    fee: float
    tax: float
    note: Optional[str] = None
    created_at: Optional[str] = None


class PortfolioTradeListResponse(BaseModel):
    """交易记录分页列表响应。"""

    items: List[PortfolioTradeListItem] = Field(default_factory=list)
    total: int
    page: int
    page_size: int


class PortfolioCashLedgerListItem(BaseModel):
    """资金流水列表项。"""

    id: int
    account_id: int
    event_date: str
    direction: str
    amount: float
    currency: str
    note: Optional[str] = None
    created_at: Optional[str] = None


class PortfolioCashLedgerListResponse(BaseModel):
    """资金流水分页列表响应。"""

    items: List[PortfolioCashLedgerListItem] = Field(default_factory=list)
    total: int
    page: int
    page_size: int


class PortfolioCorporateActionListItem(BaseModel):
    """公司行动列表项。"""

    id: int
    account_id: int
    symbol: str
    market: str
    currency: str
    effective_date: str
    action_type: str
    cash_dividend_per_share: Optional[float] = None
    split_ratio: Optional[float] = None
    note: Optional[str] = None
    created_at: Optional[str] = None


class PortfolioCorporateActionListResponse(BaseModel):
    """公司行动分页列表响应。"""

    items: List[PortfolioCorporateActionListItem] = Field(default_factory=list)
    total: int
    page: int
    page_size: int


class PortfolioPositionItem(BaseModel):
    """单个持仓明细项（数量、成本、市值与盈亏等）。"""

    symbol: str
    market: str
    currency: str
    quantity: float
    avg_cost: float
    total_cost: float
    last_price: float
    market_value_base: float
    unrealized_pnl_base: float
    unrealized_pnl_pct: Optional[float] = None
    valuation_currency: str
    price_source: str = "unknown"
    price_provider: Optional[str] = None
    price_date: Optional[str] = None
    price_stale: bool = False
    price_available: bool = True
    data_quality: str = "ok"
    limitations: List[str] = Field(default_factory=list)


class PortfolioPositionAnalysisRequest(BaseModel):
    """持仓分析请求体。"""

    account_id: Optional[int] = Field(None, description="Optional account id; required when a symbol is held in multiple accounts")
    analysis_phase: Literal["auto", "premarket", "intraday", "postmarket"] = "auto"
    force: bool = Field(False, description="Force refresh analysis inputs without bypassing duplicate in-flight tasks")


class PortfolioAccountSnapshot(BaseModel):
    """账户快照：持仓、现金、汇率与估值等汇总数据。"""

    account_id: int
    account_name: str
    owner_id: Optional[str] = None
    broker: Optional[str] = None
    market: str
    base_currency: str
    as_of: str
    cost_method: str
    total_cash: float
    total_market_value: float
    total_equity: float
    realized_pnl: float
    unrealized_pnl: float
    fee_total: float
    tax_total: float
    fx_stale: bool
    data_quality: str = "ok"
    limitations: List[str] = Field(default_factory=list)
    positions: List[PortfolioPositionItem] = Field(default_factory=list)


class PortfolioSnapshotResponse(BaseModel):
    """账户快照查询响应。"""

    as_of: str
    cost_method: str
    currency: str
    account_count: int
    total_cash: float
    total_market_value: float
    total_equity: float
    realized_pnl: float
    unrealized_pnl: float
    fee_total: float
    tax_total: float
    fx_stale: bool
    data_quality: str = "ok"
    limitations: List[str] = Field(default_factory=list)
    accounts: List[PortfolioAccountSnapshot] = Field(default_factory=list)


class PortfolioImportTradeItem(BaseModel):
    """导入文件中解析出的单条交易记录。"""

    trade_date: str
    symbol: str
    side: Literal["buy", "sell"]
    quantity: float
    price: float
    fee: float
    tax: float
    trade_uid: Optional[str] = None
    dedup_hash: str
    currency: Optional[str] = None


class PortfolioImportParseResponse(BaseModel):
    """交易文件解析结果响应（含预览记录与可识别的券商）。"""

    broker: str
    record_count: int
    skipped_count: int
    error_count: int
    records: List[PortfolioImportTradeItem] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class PortfolioImportCommitResponse(BaseModel):
    """交易导入提交结果响应（含成功/跳过条数）。"""

    account_id: int
    record_count: int
    inserted_count: int
    duplicate_count: int
    failed_count: int
    dry_run: bool
    errors: List[str] = Field(default_factory=list)


class PortfolioImportBrokerItem(BaseModel):
    """支持的交易记录导入券商项。"""

    broker: str
    aliases: List[str] = Field(default_factory=list)
    display_name: Optional[str] = None


class PortfolioImportBrokerListResponse(BaseModel):
    """支持的交易记录导入券商列表响应。"""

    brokers: List[PortfolioImportBrokerItem] = Field(default_factory=list)


class PortfolioFxRefreshResponse(BaseModel):
    """汇率刷新结果响应。"""

    as_of: str
    account_count: int
    refresh_enabled: bool
    disabled_reason: Optional[str] = None
    pair_count: int
    updated_count: int
    stale_count: int
    error_count: int


class PortfolioDecisionSignalRiskItem(BaseModel):
    """组合内单个决策信号对应的风险项。"""

    account_id: Optional[int] = None
    symbol: str
    market: str
    signal: Dict[str, Any] = Field(default_factory=dict)


class PortfolioDecisionSignalRiskBlock(BaseModel):
    """组合决策信号风险的分块汇总。"""

    available: bool = True
    total: int = 0
    actions: Dict[str, int] = Field(default_factory=dict)
    items: List[PortfolioDecisionSignalRiskItem] = Field(default_factory=list)


class PortfolioRiskResponse(BaseModel):
    """组合风险查询响应。"""

    as_of: str
    account_id: Optional[int] = None
    cost_method: str
    currency: str
    thresholds: Dict[str, Any] = Field(default_factory=dict)
    concentration: Dict[str, Any] = Field(default_factory=dict)
    sector_concentration: Dict[str, Any] = Field(default_factory=dict)
    drawdown: Dict[str, Any] = Field(default_factory=dict)
    stop_loss: Dict[str, Any] = Field(default_factory=dict)
    decision_signal_risk: PortfolioDecisionSignalRiskBlock = Field(default_factory=PortfolioDecisionSignalRiskBlock)
