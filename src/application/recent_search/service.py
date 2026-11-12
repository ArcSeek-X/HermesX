# -*- coding: utf-8 -*-
"""个股最近搜索用例。

职责边界：

- 本层负责入参规范化与业务校验（代码归一、队列上限），把「记录 / 列表 / 清空」
  组织成完整用例；查重、顶置与裁剪由仓储在单个写事务内完成。
- 股票代码在业务层做跨市场等价归一（``600519.SH`` 与 ``600519`` 视为同一条），
  避免同一只股票因跳转入口不同产生重复卡片。
- 行情与名称快照不在此层拉取：卡片的实时价格由前端批量接口补齐。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.application.recent_search.errors import RecentSearchValidationError
from src.application.recent_search.ports import RecentSearchRepositoryPort
from src.domain.market.stock_codes import canonical_stock_code, is_hk_stock_code, normalize_stock_code

DEFAULT_USER_ID = "default"
MAX_RECENT_SEARCH_RECORDS = 100


def normalize_recent_search_user_id(user_id: Optional[str]) -> str:
    """把用户标识归一为落库值：空白或缺省时回落到单用户默认值。"""
    normalized = (user_id or "").strip()
    return normalized or DEFAULT_USER_ID


def normalize_recent_search_code(stock_code: str) -> str:
    """归一股票代码；空值或超长值视为非法入参。

    Args:
        stock_code: 待记录的原始股票代码。

    Returns:
        str: 跨市场等价的标准代码形式。

    Raises:
        RecentSearchValidationError: 代码为空或归一后超过 32 字符。
    """
    raw = (stock_code or "").strip()
    if not raw:
        raise RecentSearchValidationError("股票代码不能为空")
    normalized = canonical_stock_code(normalize_stock_code(raw))
    if not normalized or len(normalized) > 32:
        raise RecentSearchValidationError("股票代码不合法")
    return normalized


def infer_recent_search_market(stock_code: str) -> str:
    """由已归一的股票代码推断市场段（``cn`` / ``hk`` / ``us``）。"""
    if is_hk_stock_code(stock_code):
        return "hk"
    if stock_code.isalpha():
        return "us"
    return "cn"


class RecentSearchService:
    """个股最近搜索的应用用例。"""

    def __init__(self, repository: RecentSearchRepositoryPort) -> None:
        """构造最近搜索用例并保存仓储端口。"""
        self._repository = repository

    def list_recent(self, *, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出该用户最近搜索记录（最多 :data:`MAX_RECENT_SEARCH_RECORDS` 条）。"""
        return self._repository.list_recent(
            user_id=normalize_recent_search_user_id(user_id),
            limit=MAX_RECENT_SEARCH_RECORDS,
        )

    def record(
        self,
        *,
        stock_code: str,
        stock_name: Optional[str] = None,
        market: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """记录一次搜索：同代码刷新并顶置，超出队列上限的旧记录被裁剪。"""
        normalized_code = normalize_recent_search_code(stock_code)
        return self._repository.record_upsert(
            user_id=normalize_recent_search_user_id(user_id),
            stock_code=normalized_code,
            stock_name=(stock_name or "").strip() or None,
            market=(market or "").strip() or infer_recent_search_market(normalized_code),
            max_records=MAX_RECENT_SEARCH_RECORDS,
        )

    def clear_all(self, *, user_id: Optional[str] = None) -> None:
        """清空该用户的全部最近搜索记录。"""
        self._repository.clear_all(user_id=normalize_recent_search_user_id(user_id))
