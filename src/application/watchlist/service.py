# -*- coding: utf-8 -*-
"""自选股用例。

职责边界：

- 本层负责入参规范化与业务校验（名称非空、股票代码存在于主数据），并把仓储的
  原子操作组合成一次完整用例；
- 唯一性冲突、目标不存在等由仓储在事务内判定并抛出业务错误，避免「先查后写」
  被拆到两个事务里；
- 排序与搜索仍由前端完成，这里不引入额外查询语义。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from src.application.watchlist.errors import (
    UnknownStockCodeError,
    WatchlistValidationError,
)
from src.application.watchlist.ports import StockCodeValidatorPort, WatchlistRepositoryPort
from src.utils.pagination import PaginationParams


@dataclass(frozen=True)
class WatchlistItemsPage:
    """分页结果：当前页条目与满足条件的总数。"""

    items: List[Dict[str, Any]]
    total: int


class WatchlistService:
    """自选股分类与条目的应用用例。"""

    def __init__(
        self,
        repository: WatchlistRepositoryPort,
        stock_code_validator: StockCodeValidatorPort,
    ) -> None:
        self._repository = repository
        self._stock_code_validator = stock_code_validator

    # === 分类 ===

    def list_groups(self) -> List[Dict[str, Any]]:
        """列出未删除分类及其条目数量。"""
        return self._repository.list_groups()

    def create_group(
        self,
        *,
        name: str,
        sort_order: Optional[int] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """新增分类，名称首尾空白会被裁剪。"""
        normalized = _normalize_group_name(name)
        return self._repository.create_group(
            name=normalized,
            sort_order=sort_order,
            description=description,
        )

    def update_group(
        self,
        *,
        group_code: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        sort_order: Optional[int] = None,
    ) -> Dict[str, Any]:
        """按 ``group_code`` 更新分类；``None`` 表示该字段不变。"""
        normalized = None if name is None else _normalize_group_name(name)
        return self._repository.update_group(
            group_code=group_code,
            name=normalized,
            description=description,
            sort_order=sort_order,
        )

    def delete_group(self, group_code: str) -> None:
        """逻辑删除分类，其下条目一并逻辑删除。"""
        self._repository.delete_group(group_code)

    # === 自选股 ===

    def list_items(
        self,
        *,
        group_id: int,
        page_num: int,
        page_size: int,
    ) -> WatchlistItemsPage:
        """分页查询分类下未删除的自选股。"""
        paging = PaginationParams(page_num=page_num, page_size=page_size)
        items, total = self._repository.list_items(
            group_id,
            offset=paging.offset,
            limit=paging.limit,
        )
        return WatchlistItemsPage(items=items, total=total)

    def create_item(
        self,
        *,
        group_id: int,
        stock_code: str,
        stock_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """新增自选股；股票代码必须是主数据中已收录的规范代码。"""
        normalized = stock_code.strip()
        if not normalized:
            raise WatchlistValidationError("股票代码不能为空", error_code="invalid_code")
        # 主数据缺失时核验实现会宽松放行，避免拖垮新增功能
        if not self._stock_code_validator.is_known(normalized):
            raise UnknownStockCodeError(
                f"股票代码无效或未收录：{normalized}",
                error_code="invalid_code",
            )
        return self._repository.create_item(
            group_id=group_id,
            stock_code=normalized,
            stock_name=stock_name,
            description=description,
        )

    def update_item(
        self,
        *,
        item_id: int,
        stock_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """更新自选股名称/备注；``None`` 表示该字段不变。"""
        return self._repository.update_item(
            item_id=item_id,
            stock_name=stock_name,
            description=description,
        )

    def delete_item(self, item_id: int) -> None:
        """逻辑删除自选股。"""
        self._repository.delete_item(item_id)

    def move_item(
        self,
        *,
        item_id: int,
        target_group_id: int,
    ) -> Dict[str, Any]:
        """把自选股移动到目标分类；目标分类下已有同一股票时冲突。"""
        return self._repository.move_item(
            item_id=item_id,
            target_group_id=target_group_id,
        )


def _normalize_group_name(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        raise WatchlistValidationError("分类名称不能为空", error_code="invalid_name")
    return normalized
