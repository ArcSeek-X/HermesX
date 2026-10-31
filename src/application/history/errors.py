# -*- coding: utf-8 -*-
"""分析历史用例的业务错误。

错误只携带业务语义（``error_code`` + 消息），HTTP 状态码由 ``api`` 层映射。
"""

from __future__ import annotations


class HistoryError(Exception):
    """分析历史用例的基类错误。"""

    def __init__(self, message: str, *, error_code: str) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class HistoryValidationError(HistoryError):
    """入参不合法（如股票代码为空）。"""


class HistoryMarkdownGenerationError(HistoryError):
    """报告重建失败（内部错误，非“记录不存在”）。"""

    def __init__(self, message: str) -> None:
        super().__init__(message, error_code="generation_failed")
