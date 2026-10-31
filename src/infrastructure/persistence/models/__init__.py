# -*- coding: utf-8 -*-
"""ORM 模型包：按业务域拆分的表结构声明。

导入本包即把全部模型注册到 :mod:`src.infrastructure.persistence.base` 的唯一
``Base.metadata`` 上——``Base.metadata.create_all()`` 依赖这一点，任何新增
模型模块都必须在这里登记，否则建表时会静默漏表。

这里只导入子模块（不重导出符号）：使用方按业务域从具体模块导入，避免又出现
一个「什么都从这里取」的聚合入口。
"""

from src.infrastructure.persistence.models import (  # noqa: F401
    agent,
    alert,
    analysis,
    decision,
    intelligence,
    market_data,
    portfolio,
    schema,
    watchlist,
)
