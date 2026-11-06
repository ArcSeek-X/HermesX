"""limit_pool 能力包；使用公开入口时再加载默认装配。"""

__all__ = [
    "LIMIT_DOWN",
    "LIMIT_UP",
    "LimitPoolDataSource",
    "LimitPoolDataSourceManager",
    "LimitPoolEntry",
    "LimitPoolRequest",
    "LimitPoolResult",
    "get_limit_pool",
    "resolve_limit_pool_source_order",
]


def __getattr__(name: str):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from data_provider.limit_pool import base

    value = getattr(base, name)
    globals()[name] = value
    return value
