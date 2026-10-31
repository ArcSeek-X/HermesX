# -*- coding: utf-8 -*-
"""自选股用例的业务错误。

错误只携带业务语义与对外 ``error_code``，不含 HTTP 状态码；驱动层（FastAPI、Bot）
负责把错误类型映射成各自协议的状态与响应体。
"""

from __future__ import annotations


class WatchlistError(Exception):
    """自选股用例错误的基类。"""

    def __init__(self, message: str, *, error_code: str) -> None:
        super().__init__(message)
        self.error_code = error_code


class WatchlistNotFoundError(WatchlistError):
    """分类或自选股不存在。"""


class WatchlistValidationError(WatchlistError):
    """入参未通过业务校验。"""


class WatchlistConflictError(WatchlistError):
    """与已有数据冲突（分类重名、同一分类下重复股票）。"""


class UnknownStockCodeError(WatchlistValidationError):
    """股票代码为空或不在主数据索引中。"""
