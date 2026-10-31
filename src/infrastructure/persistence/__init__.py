# -*- coding: utf-8 -*-
"""数据库持久化：唯一 ORM Base、模型、会话生命周期与 schema 兼容升级。

目录职责（对应 ``ARCHITECTURE_TARGET.md`` 第 3、5.1 节）：

- ``base``：唯一 ``Base`` / metadata、UTC 时间归一化、schema 版本常量。
- ``models/``：按业务域拆分的表结构；导入 ``models`` 包即完成注册。
- ``session``：引擎、SQLite PRAGMA、Session 工厂、写事务重试与 ``atexit`` 释放。
- ``schema_compat``：启动期幂等迁移（``_ensure_*``）与 ``apply_startup_migrations()``。
- 仓储实现按 P2-B2b 切片继续从 ``src/storage.py`` 迁入；迁移完成前
  ``src/storage.py`` 仍是 ``DatabaseManager`` 业务方法（与同名薄委托）的宿主。

约定：不要在别处创建第二个 ``Base``；``create_all()`` 只建缺失表，已有表的
增量变更必须走幂等的 schema 兼容函数。
"""
