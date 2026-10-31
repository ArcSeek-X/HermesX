# -*- coding: utf-8 -*-
"""持仓用例的端口定义。

端口只描述用例需要的取数能力，返回「纯数据」形状（``list[dict]`` /
``(price, provider)`` 元组），不暴露 ``data_provider`` 的 dataclass。选源、回退、
限速、健康冷却仍由 ``data_provider/`` 负责（ADR-001），本端口不做二次封装。

失败语义：
- ``BelongBoardsPort``：取数失败或桥接不可用时实现方返回空列表（best-effort），
  由用例按「无板块信息」降级；与迁移前 ``_get_data_manager`` 初始化失败返回
  ``None``、上层降级为空列表的语义一致。
- ``PortfolioRealtimeQuotePort``：适配器只把 ``DataFetcherManager`` 的实时取数转成
  端口形状，异常一律上抛，由用例 ``_fetch_realtime_position_price`` 捕获并降级为
  ``(None, None)``（价格有效性 float/``>0`` 校验留应用层），与迁移前调用点 try/except
  的告警与降级语义逐字一致。

实现方：
- :class:`~src.infrastructure.providers.portfolio_belong_boards_provider.DataProviderPortfolioBelongBoards`
- :class:`~src.infrastructure.providers.portfolio_realtime_provider.DataProviderPortfolioRealtimeQuote`

PP-4 持久化收口：本模块新增
:class:`PortfolioRepositoryPort`（持仓仓储读写端口）与三个跨层异常
（:class:`DuplicateTradeUidError` / :class:`DuplicateTradeDedupHashError` /
:class:`PortfolioBusyError`）的**单一真源**：异常由 infra 仓储 raise、应用/API/测试
catch，上收到本模块后由 ``src.infrastructure.persistence.repositories.portfolio_repository``
反向 import（infra→application 合法），避免多处定义漂移。仓储实现经下方
``set_portfolio_repository_factory`` 工厂 seam 由 bootstrap 装配（因构造点散装、非单一
漏斗，同 PP-1 intelligence：工厂持有者存**可调用**而非已构造实例，使每次构造绑定当下
``DatabaseManager`` 单例、适配 ``reset_instance()``）。
"""

from __future__ import annotations

from datetime import date
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Protocol,
    Tuple,
)


class BelongBoardsPort(Protocol):
    """个股所属板块（行业 / 概念）取数能力。

    只暴露 ``PortfolioRiskService._fetch_belong_boards`` 实际需要的能力；返回每项
    含 ``name`` / ``type`` 的字典列表，取不到或异常时返回空列表（best-effort）。
    """

    def get_belong_boards(self, *, code: str) -> List[Dict[str, Any]]:
        """取个股 ``code`` 所属板块列表；不可用或异常返回空列表（best-effort）。"""


class PortfolioRealtimeQuotePort(Protocol):
    """持仓快照估值所需的实时行情取数能力（best-effort）。

    只暴露 ``PortfolioService`` 实际需要的两项能力：批量预热缓存与单票取价。
    返回 ``data_provider`` 之外的中立形状（单票返回 ``(原始 price, provider 字符串)``），
    不暴露 ``UnifiedRealtimeQuote`` dataclass；价的有效性（``float`` / ``>0``）由用例校验，
    取数异常上抛由用例降级（与迁移前调用点 try/except 语义一致）。

    实现方：:class:`~src.infrastructure.providers.portfolio_realtime_provider.DataProviderPortfolioRealtimeQuote`
    """

    def prefetch_quotes(self, *, codes: List[str]) -> None:
        """批量预热实时行情缓存（``>=5`` 只时调用）；仅暖缓存、返回值不被消费。"""

    def fetch_price_and_source(
        self, *, code: str
    ) -> Optional[Tuple[Any, Optional[str]]]:
        """取单票实时价与来源，返回 ``(原始 price, provider 字符串)``；无数据返回 ``None``。

        ``log_final_failure=False``（源侧末次失败不告警）由实现方保持；取数异常上抛，
        由用例 ``_fetch_realtime_position_price`` 捕获并降级为 ``(None, None)``。
        """


# ---------------------------------------------------------------------------
# 跨层异常单一真源（PP-4）：由 infra 仓储 raise、应用/API/测试 catch。
# ---------------------------------------------------------------------------
class DuplicateTradeUidError(Exception):
    """Raised when trade_uid conflicts with existing record in one account."""


class DuplicateTradeDedupHashError(Exception):
    """Raised when dedup hash conflicts with existing record in one account."""


class PortfolioBusyError(Exception):
    """Raised when SQLite write serialization cannot acquire the ledger lock."""


# ---------------------------------------------------------------------------
# 仓储读写端口（PP-4）：方法面 = 应用层（4 个 service）实际调用集，每域最小端口。
# 返回持久化行以 ``Any`` 表示（鸭子序列化，避免 application import infra ORM 类）；
# ``session`` 参数同理以 ``Any`` 透传（由 ``portfolio_write_session()`` 产出的事务会话）。
# ---------------------------------------------------------------------------
class PortfolioRepositoryPort(Protocol):
    """持仓仓储端口：账户/交易/现金/公司行动/快照/行情的持久化读写契约。"""

    def create_account(
        self,
        *,
        name: str,
        broker: Optional[str],
        market: str,
        base_currency: str,
        owner_id: Optional[str] = None,
    ) -> Any: ...

    def get_account(self, account_id: int, include_inactive: bool = False) -> Any: ...

    def list_accounts(self, include_inactive: bool = False) -> List[Any]: ...

    def get_account_in_session(
        self, *, session: Any, account_id: int, include_inactive: bool = False
    ) -> Any: ...

    def update_account(self, account_id: int, fields: Dict[str, Any]) -> Any: ...

    def deactivate_account(self, account_id: int) -> bool: ...

    def portfolio_write_session(self) -> Any: ...

    def add_trade_in_session(
        self,
        *,
        session: Any,
        account_id: int,
        trade_uid: Optional[str],
        symbol: str,
        market: str,
        currency: str,
        trade_date: date,
        side: str,
        quantity: float,
        price: float,
        fee: float,
        tax: float,
        note: Optional[str] = None,
        dedup_hash: Optional[str] = None,
    ) -> Any: ...

    def add_cash_ledger_in_session(
        self,
        *,
        session: Any,
        account_id: int,
        event_date: date,
        direction: str,
        amount: float,
        currency: str,
        note: Optional[str] = None,
    ) -> Any: ...

    def add_corporate_action_in_session(
        self,
        *,
        session: Any,
        account_id: int,
        symbol: str,
        market: str,
        currency: str,
        effective_date: date,
        action_type: str,
        cash_dividend_per_share: Optional[float] = None,
        split_ratio: Optional[float] = None,
        note: Optional[str] = None,
    ) -> Any: ...

    def delete_trade_in_session(self, *, session: Any, trade_id: int) -> bool: ...

    def delete_cash_ledger_in_session(self, *, session: Any, entry_id: int) -> bool: ...

    def delete_corporate_action_in_session(self, *, session: Any, action_id: int) -> bool: ...

    def has_trade_uid(self, account_id: int, trade_uid: Optional[str]) -> bool: ...

    def has_trade_dedup_hash(self, account_id: int, dedup_hash: Optional[str]) -> bool: ...

    def has_trade_uid_in_session(
        self, *, session: Any, account_id: int, trade_uid: str
    ) -> bool: ...

    def has_trade_dedup_hash_in_session(
        self, *, session: Any, account_id: int, dedup_hash: str
    ) -> bool: ...

    def list_trades(self, account_id: int, as_of: date) -> List[Any]: ...

    def list_trades_in_session(
        self, *, session: Any, account_id: int, as_of: date
    ) -> List[Any]: ...

    def list_cash_ledger(self, account_id: int, as_of: date) -> List[Any]: ...

    def list_corporate_actions(self, account_id: int, as_of: date) -> List[Any]: ...

    def list_corporate_actions_in_session(
        self, *, session: Any, account_id: int, as_of: date
    ) -> List[Any]: ...

    def get_first_activity_date(self, *, account_id: int, as_of: date) -> Any: ...

    def query_trades(
        self,
        *,
        account_id: Optional[int],
        date_from: Optional[date],
        date_to: Optional[date],
        symbols: Optional[List[str]],
        side: Optional[str],
        page: int,
        page_size: int,
    ) -> Tuple[List[Any], int]: ...

    def query_cash_ledger(
        self,
        *,
        account_id: Optional[int],
        date_from: Optional[date],
        date_to: Optional[date],
        direction: Optional[str],
        page: int,
        page_size: int,
    ) -> Tuple[List[Any], int]: ...

    def query_corporate_actions(
        self,
        *,
        account_id: Optional[int],
        date_from: Optional[date],
        date_to: Optional[date],
        symbols: Optional[List[str]],
        action_type: Optional[str],
        page: int,
        page_size: int,
    ) -> Tuple[List[Any], int]: ...

    def get_latest_close_with_date(self, symbol: str, as_of: date) -> Any: ...

    def save_fx_rate(
        self,
        *,
        from_currency: str,
        to_currency: str,
        rate_date: date,
        rate: float,
        source: str = "manual",
        is_stale: bool = False,
    ) -> None: ...

    def get_latest_fx_rate(
        self, *, from_currency: str, to_currency: str, as_of: date
    ) -> Any: ...

    def list_daily_snapshots_for_risk(
        self,
        *,
        as_of: date,
        cost_method: str,
        account_id: Optional[int] = None,
        lookback_days: int = 180,
    ) -> List[Any]: ...

    def list_cached_position_identities(
        self, *, account_id: Optional[int] = None
    ) -> List[Tuple[str, str]]: ...

    def replace_positions_lots_and_snapshot(
        self,
        *,
        account_id: int,
        snapshot_date: date,
        cost_method: str,
        base_currency: str,
        total_cash: float,
        total_market_value: float,
        total_equity: float,
        unrealized_pnl: float,
        realized_pnl: float,
        fee_total: float,
        tax_total: float,
        fx_stale: bool,
        payload: str,
        positions: Iterable[Dict[str, Any]],
        lots: Iterable[Dict[str, Any]],
        valuation_currency: str,
    ) -> None: ...


# ---------------------------------------------------------------------------
# 仓储工厂 seam（PP-1 同型）：持**可调用工厂**而非已构造实例。
# ---------------------------------------------------------------------------
_portfolio_repository_factory: (
    "Callable[[Optional[Any]], PortfolioRepositoryPort] | None"
) = None


def set_portfolio_repository_factory(
    factory: "Callable[[Optional[Any]], PortfolioRepositoryPort] | None",
) -> None:
    """装配持仓仓储端口工厂（bootstrap 调用；幂等：仅非 None 覆盖，与 PP-1 同型）。"""
    global _portfolio_repository_factory
    if factory is not None:
        _portfolio_repository_factory = factory


def get_portfolio_repository(db_manager: Optional[Any] = None) -> PortfolioRepositoryPort:
    """调用已注册工厂现建仓储（传入 db_manager 时绑定该管理器，否则仓储内部取单例）；
    未装配即 fail-fast（与 PP-1 一致：启动链路必经 bootstrap 装配）。"""
    if _portfolio_repository_factory is None:  # pragma: no cover - 正常启动链路由 bootstrap 装配
        raise RuntimeError(
            "portfolio repository port is not configured; call "
            "src.bootstrap.portfolio.configure_portfolio_repository()"
        )
    return _portfolio_repository_factory(db_manager)
