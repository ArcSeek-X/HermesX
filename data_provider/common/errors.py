"""数据源异常及异常链摘要的唯一实现；旧 base 入口继续导出同一对象。"""

from typing import Tuple


def unwrap_exception(exc: Exception) -> Exception:
    """
    Follow chained exceptions and return the deepest non-cyclic cause.
    """
    current = exc
    visited = set()

    while current is not None and id(current) not in visited:
        visited.add(id(current))
        next_exc = current.__cause__ or current.__context__
        if next_exc is None:
            break
        current = next_exc

    return current



def summarize_exception(exc: Exception) -> Tuple[str, str]:
    """
    Build a stable summary for logs while preserving the application-layer message.
    """
    root = unwrap_exception(exc)
    error_type = type(root).__name__
    message = str(exc).strip() or str(root).strip() or error_type
    return error_type, " ".join(message.split())



class DataFetchError(Exception):
    """数据获取异常基类"""
    pass



class RateLimitError(DataFetchError):
    """API 速率限制异常"""
    pass



class DataSourceUnavailableError(DataFetchError):
    """数据源不可用异常"""
    pass

