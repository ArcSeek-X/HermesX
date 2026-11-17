# -*- coding: utf-8 -*-
"""自选股用例的端口定义。

端口只描述用例真正需要的能力，不复制 ORM 或数据源的完整接口。实现方：

- :class:`WatchlistRepositoryPort` →
  :class:`~src.infrastructure.persistence.repositories.watchlist_repo.SqlAlchemyWatchlistRepository`
- :class:`StockCodeValidatorPort` →
  :class:`~src.infrastructure.indexing.stock_code_validator.StockIndexCodeValidator`
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, Tuple


class WatchlistRepositoryPort(Protocol):
    """自选股持久化能力。

    每个写方法都是一次原子操作：仓储在同一个事务内完成「存在性检查 + 写入」，
    用例层不跨方法拼装事务；删除分类连带软删条目也由单次调用完成。

    读取返回 ``to_dict()`` 形状的普通字典，与既有 HTTP 响应契约一致；这样用例层
    不必为了分层而复制一套只做字段搬运的领域模型。
    """

    def list_groups(self) -> List[Dict[str, Any]]:
        """按 ``sort_order`` 升序返回未删除分类，并附带条目计数。"""

    def create_group(
        self,
        *,
        name: str,
        sort_order: Optional[int],
        description: Optional[str],
    ) -> Dict[str, Any]:
        """新增分类；重名时抛冲突错误。"""

    def update_group(
        self,
        *,
        group_code: str,
        name: Optional[str],
        description: Optional[str],
        sort_order: Optional[int],
    ) -> Dict[str, Any]:
        """按 ``group_code`` 更新分类；不存在或重名时抛错。"""

    def delete_group(self, group_code: str) -> None:
        """逻辑删除分类，并连带逻辑删除其下条目。"""

    def list_items(
        self,
        group_id: int,
        *,
        offset: int,
        limit: int,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """分页返回分类下未删除条目及总数；分类不存在时抛错。"""

    def create_item(
        self,
        *,
        group_id: int,
        stock_code: str,
        stock_name: Optional[str],
        description: Optional[str],
    ) -> Dict[str, Any]:
        """新增自选股；分类不存在或同分类重复时抛错。"""

    def update_item(
        self,
        *,
        item_id: int,
        stock_name: Optional[str],
        description: Optional[str],
    ) -> Dict[str, Any]:
        """更新自选股名称/备注；不存在时抛错。"""

    def delete_item(self, item_id: int) -> None:
        """逻辑删除自选股；不存在时抛错。"""

    def move_item(
        self,
        *,
        item_id: int,
        target_group_id: int,
    ) -> Dict[str, Any]:
        """把自选股移到目标分类，同分类内已有该股票时抛错。"""


class StockCodeValidatorPort(Protocol):
    """股票代码主数据核验。"""

    def is_known(self, stock_code: str) -> bool:
        """判断代码是否存在于股票主数据索引。"""
