# -*- coding: utf-8 -*-
"""个股最近搜索用例的业务错误类型。"""

from __future__ import annotations


class RecentSearchValidationError(ValueError):
    """入参不合法（如股票代码为空）。"""

    def __init__(self, message: str) -> None:
        """构造校验错误，并固定业务错误码。"""
        super().__init__(message)
        self.error_code = "invalid_recent_search"
