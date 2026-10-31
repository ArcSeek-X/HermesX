# -*- coding: utf-8 -*-
"""告警用例的外部能力端口。

``DailyBarFetcherPort`` 描述告警评估所需的日线取数能力：按代码和天数窗口返回
``(pd.DataFrame, str)`` 元组（数据 + 数据源名称）。实现方由 bootstrap 装配注入，
``src/application/alert/`` 不直接依赖 ``data_provider``。

契约：
- ``stock_code``：已归一化的标准代码（由 alert_worker 在调用前完成归一化）；
- ``days``：期望覆盖的交易日跨度；
- 返回：``(pd.DataFrame, str)`` 元组；失败时向上抛出，不吞异常（由用例层降级为错误响应）。

实现方：``src.infrastructure.providers.alert_daily_bar.DataProviderAlertDailyBarFetcher``。

以下 4 个 ``*Row`` Protocol 是告警序列化所需的持久化行**读形端口**（structural）：
``alert_service`` 的只读序列化方法只需按名读取 ORM 行上的少量字段，不实例化也不做
类型判断；因此以只读 Protocol 描述行形，使应用层不直接依赖
``src.infrastructure.persistence.models.alert`` 中的具体 ORM 类（搬入
``src/application/alert/`` 的禁入前置）。仓储返回的 ORM 行结构性满足这些 Protocol。

``AlertRepositoryPort`` 是告警仓储的**读写端口**：具体
:class:`~src.infrastructure.persistence.repositories.alert_repository.AlertRepository`
由 ``src.bootstrap.alert.build_alert_service`` 装配后自上向下注入，替代原先
``src/application/alert/service.py`` 对 ``src.repositories.AlertRepository`` 的直接依赖。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol, Tuple


class DailyBarFetcherPort(Protocol):
    """日线取数端口（量/指标告警评估前所需的历史行情窗口）。"""

    def get_daily_data(self, stock_code: str, days: int) -> Any:
        """返回 ``(pd.DataFrame, source_name)`` 元组，或抛出异常。"""
        ...


class RealtimeQuotePort(Protocol):
    """实时行情取数端口（价格/涨跌幅告警评估所需的即时快照）。

    返回原始行情对象（``data_provider`` 的 ``UnifiedRealtimeQuote`` 或字典），
    以 ``Any`` 描述使 ``src/application/alert/`` 不直接依赖 ``data_provider``：
    ``EventMonitor`` 仅按名鸭子读取 ``price`` / ``change_pct`` 等字段，不引入具体类型。

    实现方：``src.infrastructure.providers.alert_realtime_quote.DataProviderRealtimeQuote``，
    由 ``src.bootstrap.alert`` 装配后写入 ``EventMonitor`` 的模块级端口 seam。
    """

    def get_realtime_quote(self, stock_code: str) -> Any:
        """按代码取实时行情快照；无有效数据返回 ``None``。"""
        ...


class AlertRepositoryPort(Protocol):
    """告警仓储端口：规则/触发/通知/冷却的持久化读写契约。

    实现方由 ``src.bootstrap.alert.build_alert_service`` 自顶向下注入具体
    :class:`~src.infrastructure.persistence.repositories.alert_repository.AlertRepository`，
    使 ``src/application/alert/`` 不直接依赖 ``src.storage`` 之上的仓储实现。

    返回值以 ``Any`` 表示持久化行（结构性满足本模块的 ``Alert*Row`` 只读 Protocol），
    避免应用层 import ``src.infrastructure.persistence.models.alert`` 中的具体 ORM 类。
    方法签名（含关键字-only 参数与默认值）与实现保持一致，以满足结构化类型检查。
    """

    def create_rule(self, fields: Dict[str, Any]) -> Any: ...

    def get_rule(self, rule_id: int) -> Optional[Any]: ...

    def update_rule(self, rule_id: int, fields: Dict[str, Any]) -> Optional[Any]: ...

    def delete_rule(self, rule_id: int) -> bool: ...

    def list_rules(
        self,
        *,
        enabled: Optional[bool] = None,
        alert_type: Optional[str] = None,
        target_scope: Optional[str] = None,
        target: Optional[str] = None,
        source: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Any], int]: ...

    def list_enabled_rules(self, *, limit: int = 1000) -> List[Any]: ...

    def create_trigger(self, fields: Dict[str, Any]) -> Any: ...

    def create_trigger_if_absent(self, fields: Dict[str, Any]) -> Tuple[Any, bool]: ...

    def record_notification_attempt(self, fields: Dict[str, Any]) -> Any: ...

    def get_active_cooldown(
        self,
        *,
        rule_id: int,
        target: str,
        severity: Optional[str],
        now: Optional[datetime] = None,
    ) -> Optional[Any]: ...

    def upsert_cooldown(
        self,
        *,
        rule_id: int,
        rule_key: Optional[str],
        target: str,
        severity: Optional[str],
        last_triggered_at: datetime,
        cooldown_until: datetime,
        reason: Optional[str] = None,
        state: str = "active",
    ) -> Any: ...

    def get_rule_cooldown_summary(
        self,
        *,
        rule_id: int,
        target: str,
        severity: Optional[str],
    ) -> Optional[Any]: ...

    def list_triggers(
        self,
        *,
        rule_id: Optional[int] = None,
        target: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Any], int]: ...

    def list_notifications(
        self,
        *,
        trigger_id: Optional[int] = None,
        channel: Optional[str] = None,
        success: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Any], int]: ...


class AlertRuleRow(Protocol):
    """告警规则行的只读形（序列化/运行时载荷构建所需字段）。"""

    @property
    def id(self) -> int: ...
    @property
    def name(self) -> str: ...
    @property
    def target_scope(self) -> str: ...
    @property
    def target(self) -> str: ...
    @property
    def alert_type(self) -> str: ...
    @property
    def parameters(self) -> Optional[str]: ...
    @property
    def severity(self) -> Optional[str]: ...
    @property
    def enabled(self) -> Any: ...
    @property
    def source(self) -> Optional[str]: ...
    @property
    def cooldown_policy(self) -> Optional[str]: ...
    @property
    def notification_policy(self) -> Optional[str]: ...
    @property
    def created_at(self) -> Optional[datetime]: ...
    @property
    def updated_at(self) -> Optional[datetime]: ...


class AlertCooldownRow(Protocol):
    """告警冷却行的只读形。"""

    @property
    def state(self) -> Optional[str]: ...
    @property
    def cooldown_until(self) -> Optional[datetime]: ...
    @property
    def last_triggered_at(self) -> Optional[datetime]: ...


class AlertTriggerRow(Protocol):
    """告警触发行的只读形。"""

    @property
    def id(self) -> int: ...
    @property
    def rule_id(self) -> Optional[int]: ...
    @property
    def target(self) -> Optional[str]: ...
    @property
    def observed_value(self) -> Any: ...
    @property
    def threshold(self) -> Any: ...
    @property
    def reason(self) -> Optional[str]: ...
    @property
    def data_source(self) -> Optional[str]: ...
    @property
    def data_timestamp(self) -> Optional[datetime]: ...
    @property
    def triggered_at(self) -> Optional[datetime]: ...
    @property
    def status(self) -> Optional[str]: ...
    @property
    def diagnostics(self) -> Optional[str]: ...


class AlertNotificationRow(Protocol):
    """告警通知行的只读形。"""

    @property
    def id(self) -> int: ...
    @property
    def trigger_id(self) -> Optional[int]: ...
    @property
    def channel(self) -> Optional[str]: ...
    @property
    def attempt(self) -> Optional[int]: ...
    @property
    def success(self) -> Any: ...
    @property
    def error_code(self) -> Optional[str]: ...
    @property
    def retryable(self) -> Any: ...
    @property
    def latency_ms(self) -> Optional[int]: ...
    @property
    def diagnostics(self) -> Optional[str]: ...
    @property
    def created_at(self) -> Optional[datetime]: ...
