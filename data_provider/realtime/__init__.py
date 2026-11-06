# -*- coding: utf-8 -*-
"""实时行情能力包；DTO 导入不提前装配 Manager，避免旧门面循环依赖。"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from data_provider.realtime.base import RealtimeDataSourceManager, RealtimeSource

__all__ = ["RealtimeDataSourceManager", "RealtimeSource"]


def __getattr__(name: str):
    """保留包级公共入口，实际使用时再加载能力 Manager。"""
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from data_provider.realtime.base import RealtimeDataSourceManager, RealtimeSource

    exports = {"RealtimeDataSourceManager": RealtimeDataSourceManager, "RealtimeSource": RealtimeSource}
    globals().update(exports)
    return exports[name]
