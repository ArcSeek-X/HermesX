# -*- coding: utf-8 -*-
"""UTC-naive 时间量纲工具（stdlib-only 中立层）。

SQLite ``DateTime`` 列统一以 *naive UTC* 存储（历史上曾混用本地时区，导致
「东八区时间被当成 UTC」的量纲漂移）。全仓读写该量纲的规范化入口收敛在
:func:`utc_naive_now` / :func:`to_utc_naive_datetime`。

本模块刻意不依赖 ``src.infrastructure``：``src/infrastructure`` 对
``src/application/`` 是禁入边界，而这两个纯 stdlib 规范化函数既被持久层
（``src.infrastructure.persistence.base`` 再导出，ORM 默认值/仓储写入）使用，
也被应用层用例（决策信号序列化/有效期判断）使用，因此上提到中立 util 层，
两侧从同一真源导入，不产生平行实现。

原实现位于 ``src/infrastructure/persistence/base.py``，§0.71（D 线 D3）逐字上提。
"""

from __future__ import annotations

from datetime import datetime, timezone


def utc_naive_now() -> datetime:
    """Return current UTC time without tzinfo for SQLite DateTime columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_utc_naive_datetime(value: datetime) -> datetime:
    """Normalize aware datetimes to UTC-naive; treat naive values as UTC-naive."""
    if value.tzinfo is not None and value.utcoffset() is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value
