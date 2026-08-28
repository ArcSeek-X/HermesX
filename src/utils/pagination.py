# -*- coding: utf-8 -*-
"""
===================================
分页工具类
===================================

提供通用的分页计算辅助函数，供 API 层和服务层复用。
"""

import math
from dataclasses import dataclass
from typing import Any, Sequence


@dataclass
class PaginationParams:
    """分页参数。"""

    page_num: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        """SQL OFFSET 值。"""
        return (max(1, self.page_num) - 1) * self.page_size

    @property
    def limit(self) -> int:
        """SQL LIMIT 值。"""
        return self.page_size


def compute_pages(total: int, page_size: int) -> int:
    """根据总条数和每页数量计算总页数。"""
    if page_size <= 0:
        return 0
    return math.ceil(total / page_size)


def paginate_response(
    items: Sequence[Any],
    total: int,
    page_num: int,
    page_size: int,
) -> dict:
    """构造统一的分页响应字典。

    可直接用于 Pydantic 模型的 **kwargs 解包。
    """
    return {
        "list": list(items),
        "total": total,
        "pageSize": page_size,
        "pages": compute_pages(total, page_size),
        "pageNum": page_num,
    }
