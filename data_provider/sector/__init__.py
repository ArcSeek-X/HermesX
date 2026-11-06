"""sector 能力包；使用公开入口时再加载默认装配。"""

__all__ = ["SectorDataSourceManager", "SectorRankingRequest", "SectorRankingResult"]


def __getattr__(name: str):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from data_provider.sector import base

    value = getattr(base, name)
    globals()[name] = value
    return value
