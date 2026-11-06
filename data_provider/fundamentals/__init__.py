"""基本面能力包；按需加载默认能力，避免厂商实现导入时提前装配。"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from data_provider.fundamentals.base import FundamentalsDataSourceManager, FundamentalsRequest, FundamentalsResult

__all__ = ["FundamentalsDataSourceManager", "FundamentalsRequest", "FundamentalsResult"]


def __getattr__(name: str):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from data_provider.fundamentals.base import FundamentalsDataSourceManager, FundamentalsRequest, FundamentalsResult

    exports = dict(
        FundamentalsDataSourceManager=FundamentalsDataSourceManager,
        FundamentalsRequest=FundamentalsRequest,
        FundamentalsResult=FundamentalsResult,
    )
    globals().update(exports)
    return exports[name]
