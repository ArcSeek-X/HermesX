# -*- coding: utf-8 -*-
"""
@file: portfolio.py
@description: 投资组合接口契约：账户、交易、资金流水、公司行动、持仓与账户快照、券商流水导入、汇率刷新与组合风险；由 api.v1.endpoints.portfolio 返回，金额统一按账户基准货币折算。
@author: Lensgcx (GaoCangxiong)

Portfolio API schemas.

Defines account, trade, cash-ledger and corporate-action payloads,
position and account snapshots, broker-file import results, FX
refresh outcomes and portfolio risk blocks.

组合（Portfolio）相关 API 的 Pydantic 请求/响应模型，涵盖账户、交易、资金流水、公司行动、持仓快照、文件导入与风险查询。
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class PortfolioAccountCreateRequest(BaseModel):
    """创建投资组合账户的请求体（名称、券商、市场、基准货币、归属人）。

    使用场景：新建模拟账户；默认 A 股市场与 CNY 基准货币，其余字段可后置补充。

    @author: Lensgcx (GaoCangxiong)
    """

    # 账户名称，长度 1~64，必填（更新请求中为可选）。
    name: str = Field(..., min_length=1, max_length=64)
    # 券商名称，最长 64 字符；可为空。
    broker: Optional[str] = Field(None, max_length=64)
    # 账户默认市场，默认 cn；决定新建交易的市场缺省值。
    market: Literal["cn", "hk", "us", "jp", "kr", "tw"] = "cn"
    # 账户基准货币，默认 CNY，长度 3~8。
    base_currency: str = Field("CNY", min_length=3, max_length=8)
    # 账户归属人标识，用于多用户场景隔离；可为空。
    owner_id: Optional[str] = Field(None, max_length=64)


class PortfolioAccountUpdateRequest(BaseModel):
    """更新投资组合账户的请求体，所有字段均可选。

    使用场景：局部修改账户配置；None 表示保持原值，is_active 可单独用于停用账户。

    @author: Lensgcx (GaoCangxiong)
    """

    # 账户名称，长度 1~64，必填（更新请求中为可选）。
    name: Optional[str] = Field(None, min_length=1, max_length=64)
    # 券商名称，最长 64 字符；可为空。
    broker: Optional[str] = Field(None, max_length=64)
    # 标的市场标识 cn / hk / us / jp / kr / tw。
    market: Optional[Literal["cn", "hk", "us", "jp", "kr", "tw"]] = None
    # 账户基准货币代码，长度 3~8，所有汇总金额折算到该币种。
    base_currency: Optional[str] = Field(None, min_length=3, max_length=8)
    # 账户归属人标识，用于多用户场景隔离；可为空。
    owner_id: Optional[str] = Field(None, max_length=64)
    # 账户是否启用；停用账户不参与快照与风险统计。
    is_active: Optional[bool] = None


class PortfolioAccountItem(BaseModel):
    """投资组合账户详情项。

    使用场景：账户下拉与管理列表；is_active 决定该账户是否参与快照与风险计算。

    @author: Lensgcx (GaoCangxiong)
    """

    # 记录主键，供详情与删除操作定位。
    id: int
    # 账户归属人标识，用于多用户场景隔离；可为空。
    owner_id: Optional[str] = None
    # 账户名称，长度 1~64，必填（更新请求中为可选）。
    name: str
    # 券商名称，最长 64 字符；可为空。
    broker: Optional[str] = None
    # 账户所属市场标识。
    market: str
    # 账户基准货币，汇总金额按此折算。
    base_currency: str
    # 账户是否启用；停用账户不参与快照与风险统计。
    is_active: bool
    # 记录创建时间字符串；历史数据可能为 None。
    created_at: Optional[str] = None
    # 记录最后更新时间字符串；历史数据可能为 None。
    updated_at: Optional[str] = None


class PortfolioAccountListResponse(BaseModel):
    """投资组合账户列表响应。

    使用场景：一次性返回全部账户，故不做分页。

    @author: Lensgcx (GaoCangxiong)
    """

    # 账户列表，一次性返回全部账户，默认空列表。
    accounts: List[PortfolioAccountItem] = Field(default_factory=list)


class PortfolioTradeCreateRequest(BaseModel):
    """新建交易记录的请求体（账户、标的、日期、买卖方向、数量与价格等）。

    使用场景：手工录入或导入提交；trade_uid 为空时由服务端生成，用于重复导入去重。

    @author: Lensgcx (GaoCangxiong)
    """

    # 写入交易的目标账户主键，必填。
    account_id: int
    # 标的代码，长度 1~16（创建请求侧约束）。
    symbol: str = Field(..., min_length=1, max_length=16)
    # 成交日期，必填；影响持仓成本的时间顺序。
    trade_date: date
    # 买卖方向，必填；sell 数量超过持仓时由服务层校验。
    side: Literal["buy", "sell"]
    # 成交数量，必须大于 0。
    quantity: float = Field(..., gt=0)
    # 成交单价，必须大于 0。
    price: float = Field(..., gt=0)
    # 手续费，默认 0 且不得为负。
    fee: float = Field(0.0, ge=0)
    # 税费，默认 0 且不得为负。
    tax: float = Field(0.0, ge=0)
    # 标的市场；为空时回退到账户默认市场。
    market: Optional[Literal["cn", "hk", "us", "jp", "kr", "tw"]] = None
    # 交易或估值使用的货币代码，长度 3~8；为空时回退到账户基准货币。
    currency: Optional[str] = Field(None, min_length=3, max_length=8)
    # 外部交易唯一号，最长 128 字符；为空时服务端生成，用于导入去重。
    trade_uid: Optional[str] = Field(None, max_length=128)
    # 用户备注，最长 255 字符；可为空。
    note: Optional[str] = Field(None, max_length=255)


class PortfolioCashLedgerCreateRequest(BaseModel):
    """新建资金流水（入金/出金）的请求体。

    使用场景：记录账户现金变动；金额必须为正，方向由 direction 单独表达。

    @author: Lensgcx (GaoCangxiong)
    """

    # 写入流水的目标账户主键，必填。
    account_id: int
    # 资金变动发生日期，必填。
    event_date: date
    # 资金方向 in 入金 / out 出金。
    direction: Literal["in", "out"]
    # 变动金额，必须大于 0；方向由 direction 表达。
    amount: float = Field(..., gt=0)
    # 交易或估值使用的货币代码，长度 3~8；为空时回退到账户基准货币。
    currency: Optional[str] = Field(None, min_length=3, max_length=8)
    # 用户备注，最长 255 字符；可为空。
    note: Optional[str] = Field(None, max_length=255)


class PortfolioCorporateActionCreateRequest(BaseModel):
    """新建公司行动（分红、送转、拆合股等）的请求体。

    使用场景：录入除权除息事件以修正持仓成本与数量；两类行动分别使用 cash_dividend_per_share 与 split_ratio。

    @author: Lensgcx (GaoCangxiong)
    """

    # 写入公司行动的目标账户主键，必填。
    account_id: int
    # 标的代码，长度 1~16（创建请求侧约束）。
    symbol: str = Field(..., min_length=1, max_length=16)
    # 除权除息生效日期，必填。
    effective_date: date
    # 行动类型 cash_dividend 现金分红 / split_adjustment 拆合股调整。
    action_type: Literal["cash_dividend", "split_adjustment"]
    # 标的市场；为空时回退到账户默认市场。
    market: Optional[Literal["cn", "hk", "us", "jp", "kr", "tw"]] = None
    # 交易或估值使用的货币代码，长度 3~8；为空时回退到账户基准货币。
    currency: Optional[str] = Field(None, min_length=3, max_length=8)
    # 每股现金分红，不得为负；仅分红类型使用。
    cash_dividend_per_share: Optional[float] = Field(None, ge=0)
    # 拆合股比例，必须大于 0；仅拆合股类型使用。
    split_ratio: Optional[float] = Field(None, gt=0)
    # 用户备注，最长 255 字符；可为空。
    note: Optional[str] = Field(None, max_length=255)


class PortfolioEventCreatedResponse(BaseModel):
    """组合事件（交易/流水/公司行动）创建结果响应。

    使用场景：写操作返回新记录主键，供前端跳转或撤销。

    @author: Lensgcx (GaoCangxiong)
    """

    # 记录主键，供详情与删除操作定位。
    id: int


class PortfolioDeleteResponse(BaseModel):
    """组合资源删除结果响应。

    使用场景：删除端点回传实际删除条数，便于前端判断是否命中。

    @author: Lensgcx (GaoCangxiong)
    """

    # 实际删除的资源数；0 表示目标不存在。
    deleted: int


class PortfolioTradeListItem(BaseModel):
    """交易记录列表项。

    使用场景：交易流水页；日期与时间为字符串，由服务层统一格式化。

    @author: Lensgcx (GaoCangxiong)
    """

    # 记录主键，供详情与删除操作定位。
    id: int
    # 所属组合账户主键。
    account_id: int
    # 交易唯一号；手工录入的历史记录可能为 None。
    trade_uid: Optional[str] = None
    # 标的代码，长度 1~16（创建请求侧约束）。
    symbol: str
    # 标的市场标识 cn / hk / us / jp / kr / tw。
    market: str
    # 交易或估值使用的货币代码，长度 3~8；为空时回退到账户基准货币。
    currency: str
    # 成交日期字符串，由服务层统一格式化。
    trade_date: str
    # 买卖方向字符串。
    side: str
    # 成交数量，必须大于 0。
    quantity: float
    # 成交单价，必须大于 0。
    price: float
    # 手续费，默认 0 且不得为负。
    fee: float
    # 税费，默认 0 且不得为负。
    tax: float
    # 用户备注，最长 255 字符；可为空。
    note: Optional[str] = None
    # 记录创建时间字符串；历史数据可能为 None。
    created_at: Optional[str] = None


class PortfolioTradeListResponse(BaseModel):
    """交易记录分页列表响应。

    使用场景：交易流水页按页拉取。

    @author: Lensgcx (GaoCangxiong)
    """

    # 当前页或当前区块的记录列表；无数据为空列表。
    items: List[PortfolioTradeListItem] = Field(default_factory=list)
    # 符合条件的记录总数，或风险区块的信号总数。
    total: int
    # 当前页码，从 1 开始。
    page: int
    # 每页条数，与请求参数一致。
    page_size: int


class PortfolioCashLedgerListItem(BaseModel):
    """资金流水列表项。

    使用场景：现金变动记录页。

    @author: Lensgcx (GaoCangxiong)
    """

    # 记录主键，供详情与删除操作定位。
    id: int
    # 所属组合账户主键。
    account_id: int
    # 资金变动日期字符串。
    event_date: str
    # 资金方向 in / out。
    direction: str
    # 变动金额，恒为正值。
    amount: float
    # 交易或估值使用的货币代码，长度 3~8；为空时回退到账户基准货币。
    currency: str
    # 用户备注，最长 255 字符；可为空。
    note: Optional[str] = None
    # 记录创建时间字符串；历史数据可能为 None。
    created_at: Optional[str] = None


class PortfolioCashLedgerListResponse(BaseModel):
    """资金流水分页列表响应。

    使用场景：现金变动记录页按页拉取。

    @author: Lensgcx (GaoCangxiong)
    """

    # 当前页或当前区块的记录列表；无数据为空列表。
    items: List[PortfolioCashLedgerListItem] = Field(default_factory=list)
    # 符合条件的记录总数，或风险区块的信号总数。
    total: int
    # 当前页码，从 1 开始。
    page: int
    # 每页条数，与请求参数一致。
    page_size: int


class PortfolioCorporateActionListItem(BaseModel):
    """公司行动列表项。

    使用场景：除权除息记录页；两类行动的参数互斥，未使用的一个为 None。

    @author: Lensgcx (GaoCangxiong)
    """

    # 记录主键，供详情与删除操作定位。
    id: int
    # 所属组合账户主键。
    account_id: int
    # 标的代码，长度 1~16（创建请求侧约束）。
    symbol: str
    # 标的市场标识 cn / hk / us / jp / kr / tw。
    market: str
    # 交易或估值使用的货币代码，长度 3~8；为空时回退到账户基准货币。
    currency: str
    # 公司行动生效日期字符串。
    effective_date: str
    # 行动类型标识。
    action_type: str
    # 每股现金分红；非分红类型为 None。
    cash_dividend_per_share: Optional[float] = None
    # 拆合股比例；非拆合股类型为 None。
    split_ratio: Optional[float] = None
    # 用户备注，最长 255 字符；可为空。
    note: Optional[str] = None
    # 记录创建时间字符串；历史数据可能为 None。
    created_at: Optional[str] = None


class PortfolioCorporateActionListResponse(BaseModel):
    """公司行动分页列表响应。

    使用场景：除权除息记录页按页拉取。

    @author: Lensgcx (GaoCangxiong)
    """

    # 当前页或当前区块的记录列表；无数据为空列表。
    items: List[PortfolioCorporateActionListItem] = Field(default_factory=list)
    # 符合条件的记录总数，或风险区块的信号总数。
    total: int
    # 当前页码，从 1 开始。
    page: int
    # 每页条数，与请求参数一致。
    page_size: int


class PortfolioPositionItem(BaseModel):
    """单个持仓明细项（数量、成本、市值与盈亏等）。

    使用场景：账户快照的持仓区；带出价格来源与新鲜度，让前端能标注「价格过期」而不是把估算值当实时价。

    @author: Lensgcx (GaoCangxiong)
    """

    # 标的代码，长度 1~16（创建请求侧约束）。
    symbol: str
    # 标的市场标识 cn / hk / us / jp / kr / tw。
    market: str
    # 该持仓计价货币，与账户基准货币可能不同。
    currency: str
    # 当前持有数量。
    quantity: float
    # 按 cost_method 计算的持仓均价。
    avg_cost: float
    # 持仓总成本，按持仓计价货币表示。
    total_cost: float
    # 最新价；无法取价时可能为 0 或沿用上次价格，需结合 price_available 判断。
    last_price: float
    # 折算到账户基准货币的持仓市值。
    market_value_base: float
    # 折算到账户基准货币的未实现盈亏。
    unrealized_pnl_base: float
    # 未实现盈亏百分比；成本为零或无法计算时为 None。
    unrealized_pnl_pct: Optional[float] = None
    # 本次估值实际采用的货币，说明折算口径。
    valuation_currency: str
    # 价格来源标识，默认 unknown；用于解释估值依据。
    price_source: str = "unknown"
    # 提供价格的数据源；未知时为 None。
    price_provider: Optional[str] = None
    # 价格对应日期；未知时为 None，需结合 price_stale 判断时效。
    price_date: Optional[str] = None
    # 价格是否已过期，默认 False；为 True 时前端应标注非实时。
    price_stale: bool = False
    # 是否取得可用价格，默认 True；False 时市值可能为估算值。
    price_available: bool = True
    # 数据质量等级，默认 ok；降级时由服务层给出其他取值。
    data_quality: str = "ok"
    # 该持仓估值的低敏限制说明列表，默认空列表。
    limitations: List[str] = Field(default_factory=list)


class PortfolioPositionAnalysisRequest(BaseModel):
    """持仓分析请求体。

    使用场景：对当前持仓触发分析；同一标的被多个账户持有时必须指定 account_id，force 只刷新输入，不绕过进行中任务的去重。

    @author: Lensgcx (GaoCangxiong)
    """

    # 指定分析账户；同一标的被多个账户持有时必填，否则无法唯一定位持仓。
    account_id: Optional[int] = Field(None, description="Optional account id; required when a symbol is held in multiple accounts")
    # 分析阶段 auto / premarket / intraday / postmarket，默认 auto。
    analysis_phase: Literal["auto", "premarket", "intraday", "postmarket"] = "auto"
    # 是否强制刷新分析输入，默认 False；不会绕过进行中任务的去重。
    force: bool = Field(False, description="Force refresh analysis inputs without bypassing duplicate in-flight tasks")


class PortfolioAccountSnapshot(BaseModel):
    """账户快照：持仓、现金、汇率与估值等汇总数据。

    使用场景：单账户维度的资产总览；所有金额已折算到 base_currency，fx_stale 与 limitations 提示估值可信度。

    @author: Lensgcx (GaoCangxiong)
    """

    # 该快照对应的账户主键。
    account_id: int
    # 账户名称，用于多账户下钻时区分。
    account_name: str
    # 账户归属人标识，用于多用户场景隔离；可为空。
    owner_id: Optional[str] = None
    # 券商名称，最长 64 字符；可为空。
    broker: Optional[str] = None
    # 标的市场标识 cn / hk / us / jp / kr / tw。
    market: str
    # 账户基准货币代码，长度 3~8，所有汇总金额折算到该币种。
    base_currency: str
    # 该账户快照的生成时间点。
    as_of: str
    # 持仓成本计算方法标识，决定均价与已实现盈亏口径。
    cost_method: str
    # 账户现金余额，已折算到基准货币。
    total_cash: float
    # 持仓总市值，已折算到基准货币。
    total_market_value: float
    # 账户总权益 = 现金 + 持仓市值。
    total_equity: float
    # 已实现盈亏，来自已平仓交易。
    realized_pnl: float
    # 未实现盈亏，来自当前持仓的浮动盈亏。
    unrealized_pnl: float
    # 累计手续费。
    fee_total: float
    # 累计税费。
    tax_total: float
    # 汇率是否已过期；为 True 时跨币种估值需标注可信度下降。
    fx_stale: bool
    # 数据质量等级，默认 ok；降级时由服务层给出其他取值。
    data_quality: str = "ok"
    # 低敏的数据局限说明列表，默认空列表。
    limitations: List[str] = Field(default_factory=list)
    # 持仓明细列表，默认空列表。
    positions: List[PortfolioPositionItem] = Field(default_factory=list)


class PortfolioSnapshotResponse(BaseModel):
    """账户快照查询响应。

    使用场景：组合首页跨账户汇总；account_count 为纳入统计的账户数，accounts 提供逐账户明细以支持下钻。

    @author: Lensgcx (GaoCangxiong)
    """

    # 快照或刷新结果对应的时间点，用于判断数据新鲜度。
    as_of: str
    # 持仓成本计算方法标识，决定均价与已实现盈亏口径。
    cost_method: str
    # 跨账户汇总所使用的统一货币。
    currency: str
    # 纳入汇总的账户数量。
    account_count: int
    # 账户现金余额，已折算到基准货币。
    total_cash: float
    # 持仓总市值，已折算到基准货币。
    total_market_value: float
    # 账户总权益 = 现金 + 持仓市值。
    total_equity: float
    # 已实现盈亏，来自已平仓交易。
    realized_pnl: float
    # 未实现盈亏，来自当前持仓的浮动盈亏。
    unrealized_pnl: float
    # 累计手续费。
    fee_total: float
    # 累计税费。
    tax_total: float
    # 汇率是否已过期；为 True 时跨币种估值需标注可信度下降。
    fx_stale: bool
    # 数据质量等级，默认 ok；降级时由服务层给出其他取值。
    data_quality: str = "ok"
    # 低敏的数据局限说明列表，默认空列表。
    limitations: List[str] = Field(default_factory=list)
    # 逐账户快照列表，默认空列表。
    accounts: List[PortfolioAccountSnapshot] = Field(default_factory=list)


class PortfolioImportTradeItem(BaseModel):
    """导入文件中解析出的单条交易记录。

    使用场景：导入预览与提交；dedup_hash 由解析阶段计算，是重复导入判定的依据。

    @author: Lensgcx (GaoCangxiong)
    """

    # 从文件解析出的成交日期字符串。
    trade_date: str
    # 标的代码，长度 1~16（创建请求侧约束）。
    symbol: str
    # 买卖方向 buy / sell。
    side: Literal["buy", "sell"]
    # 成交数量，必须大于 0。
    quantity: float
    # 成交单价，必须大于 0。
    price: float
    # 手续费，默认 0 且不得为负。
    fee: float
    # 税费，默认 0 且不得为负。
    tax: float
    # 文件中的原始交易号；缺失时为 None。
    trade_uid: Optional[str] = None
    # 按关键字段计算的去重哈希，是重复导入判定的依据。
    dedup_hash: str
    # 交易或估值使用的货币代码，长度 3~8；为空时回退到账户基准货币。
    currency: Optional[str] = None


class PortfolioImportParseResponse(BaseModel):
    """交易文件解析结果响应（含预览记录与可识别的券商）。

    使用场景：导入第一步；解析只预览不写库，skipped_count / error_count 说明文件质量。

    @author: Lensgcx (GaoCangxiong)
    """

    # 识别出的券商标识，决定后续提交时使用哪套映射规则。
    broker: str
    # 成功解析出的交易条数。
    record_count: int
    # 因格式或业务规则被跳过的行数。
    skipped_count: int
    # 解析失败的行数。
    error_count: int
    # 可预览的交易记录列表，默认空列表。
    records: List[PortfolioImportTradeItem] = Field(default_factory=list)
    # 解析或导入失败原因列表；为空表示无错误。
    errors: List[str] = Field(default_factory=list)


class PortfolioImportCommitResponse(BaseModel):
    """交易导入提交结果响应（含成功/跳过条数）。

    使用场景：导入第二步；dry_run=True 时只统计不写库，duplicate_count 让前端解释为何并非全部记录被插入。

    @author: Lensgcx (GaoCangxiong)
    """

    # 本次导入写入的目标账户主键。
    account_id: int
    # 参与本次提交的记录数。
    record_count: int
    # 实际插入的记录数。
    inserted_count: int
    # 因 dedup_hash 已存在而跳过的记录数。
    duplicate_count: int
    # 写入失败的记录数。
    failed_count: int
    # 是否为试提交；True 时只统计不写库。
    dry_run: bool
    # 解析或导入失败原因列表；为空表示无错误。
    errors: List[str] = Field(default_factory=list)


class PortfolioImportBrokerItem(BaseModel):
    """支持的交易记录导入券商项。

    使用场景：导入页展示可识别的券商格式；aliases 用于文件名/表头模糊匹配。

    @author: Lensgcx (GaoCangxiong)
    """

    # 券商稳定标识，作为导入请求的入参。
    broker: str
    # 券商别名列表，用于文件名与表头模糊匹配，默认空列表。
    aliases: List[str] = Field(default_factory=list)
    # 券商展示名称；缺省时为 None。
    display_name: Optional[str] = None


class PortfolioImportBrokerListResponse(BaseModel):
    """支持的交易记录导入券商列表响应。

    使用场景：导入页初始化候选列表。

    @author: Lensgcx (GaoCangxiong)
    """

    # 支持的券商列表，默认空列表。
    brokers: List[PortfolioImportBrokerItem] = Field(default_factory=list)


class PortfolioFxRefreshResponse(BaseModel):
    """汇率刷新结果响应。

    使用场景：手动刷新汇率后回报各货币对的更新情况；refresh_enabled=False 时用 disabled_reason 解释原因。

    @author: Lensgcx (GaoCangxiong)
    """

    # 快照或刷新结果对应的时间点，用于判断数据新鲜度。
    as_of: str
    # 本次汇率刷新涉及的账户数。
    account_count: int
    # 刷新是否实际启用；False 时查 disabled_reason。
    refresh_enabled: bool
    # 刷新被禁用的原因；启用时为 None。
    disabled_reason: Optional[str] = None
    # 本次处理的货币对数量。
    pair_count: int
    # 成功更新的货币对数。
    updated_count: int
    # 仍使用过期汇率的货币对数。
    stale_count: int
    # 刷新失败的货币对数。
    error_count: int


class PortfolioDecisionSignalRiskItem(BaseModel):
    """组合内单个决策信号对应的风险项。

    使用场景：把信号与持仓标的关联；account_id 可为 None 表示跨账户汇总。

    @author: Lensgcx (GaoCangxiong)
    """

    # 信号关联账户；跨账户汇总时为 None。
    account_id: Optional[int] = None
    # 标的代码，长度 1~16（创建请求侧约束）。
    symbol: str
    # 标的市场标识 cn / hk / us / jp / kr / tw。
    market: str
    # 信号摘要字典，默认空字典；结构随信号来源变化。
    signal: Dict[str, Any] = Field(default_factory=dict)


class PortfolioDecisionSignalRiskBlock(BaseModel):
    """组合决策信号风险的分块汇总。

    使用场景：风险响应中的独立区块；available=False 表示信号数据不可用，此时计数不应被解读为零风险。

    @author: Lensgcx (GaoCangxiong)
    """

    # 信号风险数据是否可用，默认 True；False 时 total=0 不代表零风险。
    available: bool = True
    # 命中的信号数量，默认 0。
    total: int = 0
    # 按决策动作聚合的信号数量，默认空字典。
    actions: Dict[str, int] = Field(default_factory=dict)
    # 当前页或当前区块的记录列表；无数据为空列表。
    items: List[PortfolioDecisionSignalRiskItem] = Field(default_factory=list)


class PortfolioRiskResponse(BaseModel):
    """组合风险查询响应。

    使用场景：风险页一次返回集中度、行业集中度、回撤、止损与信号风险；各区块用字典承载以便按配置扩展指标而不改响应结构。

    @author: Lensgcx (GaoCangxiong)
    """

    # 快照或刷新结果对应的时间点，用于判断数据新鲜度。
    as_of: str
    # 查询指定的账户；跨账户汇总时为 None。
    account_id: Optional[int] = None
    # 持仓成本计算方法标识，决定均价与已实现盈亏口径。
    cost_method: str
    # 交易或估值使用的货币代码，长度 3~8；为空时回退到账户基准货币。
    currency: str
    # 本次风险计算采用的阈值字典，默认空字典。
    thresholds: Dict[str, Any] = Field(default_factory=dict)
    # 个股集中度指标字典，默认空字典。
    concentration: Dict[str, Any] = Field(default_factory=dict)
    # 行业集中度指标字典，默认空字典。
    sector_concentration: Dict[str, Any] = Field(default_factory=dict)
    # 回撤指标字典，默认空字典。
    drawdown: Dict[str, Any] = Field(default_factory=dict)
    # 止损相关指标字典，默认空字典。
    stop_loss: Dict[str, Any] = Field(default_factory=dict)
    # 决策信号风险区块；缺省时由默认工厂创建空区块。
    decision_signal_risk: PortfolioDecisionSignalRiskBlock = Field(default_factory=PortfolioDecisionSignalRiskBlock)
