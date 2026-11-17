# -*- coding: utf-8 -*-
"""搜索 Provider 外部调用簇的 infrastructure 落点（ARCHITECTURE_TARGET §4.3 L255）。

对上层（bootstrap 装配工厂、测试）暴露统一入口：8 个具体搜索引擎 Provider、
``BaseSearchProvider`` 抽象基类，以及按优先级构造 Provider 列表的 ``build_search_providers``
工厂。``SearchService``（application 用例层）不直接 import 本包，改由 bootstrap 注册
provider-builder hook 间接调用，保持 application 不依赖 infrastructure 的分层方向。
"""

from src.infrastructure.search.providers import (
    AnspireSearchProvider,
    BaseSearchProvider,
    BochaSearchProvider,
    BraveSearchProvider,
    MiniMaxSearchProvider,
    SerpAPISearchProvider,
    SearXNGSearchProvider,
    TavilySearchProvider,
    build_search_providers,
)

__all__ = [
    "BaseSearchProvider",
    "TavilySearchProvider",
    "SerpAPISearchProvider",
    "BochaSearchProvider",
    "AnspireSearchProvider",
    "MiniMaxSearchProvider",
    "BraveSearchProvider",
    "SearXNGSearchProvider",
    "build_search_providers",
]
