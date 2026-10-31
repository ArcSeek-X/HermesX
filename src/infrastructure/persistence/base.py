# -*- coding: utf-8 -*-
"""持久化基座：唯一 ORM ``Base``、UTC 时间归一化与 schema 版本标记。

本模块是 ``src.infrastructure.persistence`` 的依赖底座，只放三件事：

1. ``Base``：全仓唯一的 declarative base。任何模型都必须注册在它上面，
   不允许在别处再 ``declarative_base()``，否则 ``create_all()`` 会漏表。
2. 时间归一化：所有 ``DateTime`` 列存 **UTC naive**。写入前用
   :func:`to_utc_naive_datetime` 归一，避免「东八区时间被当成 UTC」与
   「同一字段混存带时区/不带时区」两类问题；新代码取当前时间用
   :func:`utc_naive_now`，不要用 ``datetime.now``。两函数真源已上提到
   中立层 :mod:`src.utils.time`（应用层不得 import ``src.infrastructure``，
   需从同一入口取用），本模块仅再导出以保持持久层既有 import 面不变。
3. schema 版本标记：``CURRENT_SCHEMA_VERSION`` 是记录在 ``schema_migrations``
   表的基线版本，仅在需要重建表结构的破坏性变更时递增；补列 / 补索引类
   增量变更走 ``schema_compat`` 的幂等 ``_ensure_*``，不改动该值。

存储约定（修改持久化层时务必遵守）：

- 金额统一为元，涨跌幅统一为百分比数值（``1.5`` 表示 ``1.5%``），不做小数/百分数混用。
- 股票代码统一为纯代码字符串（``600519`` / ``hk00700`` / ``AAPL``），不带交易所后缀；
  跨市场等价归一化在业务层做，不在存储层隐式转换。
- JSON 以 ``Text`` 存字符串，读取方负责解析；模型只保证可存，结构契约由对应 schema 定义。
- 多数流水表不物理删除，由保留期任务按时间清理。

模型按业务域放在 :mod:`src.infrastructure.persistence.models`；导入该包即完成注册。
"""

from sqlalchemy.orm import declarative_base

# UTC-naive 时间工具再导出（真源在 src.utils.time，stdlib-only、无循环依赖）：
# 持久层既有 ``from src.infrastructure.persistence.base import utc_naive_now`` 面不变。
from src.utils.time import to_utc_naive_datetime, utc_naive_now  # noqa: F401

# SQLAlchemy ORM 基类：全仓唯一。
Base = declarative_base()

# 基线 schema 版本标记，记录在 schema_migrations 表。
# 仅在「需要重建表结构」的破坏性变更时才递增；补列/补索引类变更不改动此值。
CURRENT_SCHEMA_VERSION = "2026-06-05-create-all-baseline"

# 统一重要度业务量纲迁移标记（记录在 schema_migrations 表）。
# 背景：快讯 importance 原为上游 score（1=普通 / 2=重要 / 3=非常重要），
# 与消息日历（1~4）量纲不一致。现统一为业务量纲 0~4：
#   0=无 / 1=普通 / 2=较重要 / 3=重要 / 4=非常重要
# 快讯按语义守恒映射 {1→1, 2→3, 3→4}，上游无字段填 0。
# 迁移前后取值集合存在交集（前 {1,2,3} / 后 {0,1,3,4}），无法从数据形态判断
# 是否已迁移，因此必须用该标记做幂等，禁止依赖数据形态判断。
LIVE_NEWS_IMPORTANCE_RESCALE_VERSION = "2026-09-02-live-news-importance-rescale-v1"
