# -*- coding: utf-8 -*-
"""生成用例契约层。

分层约定：

- 本包只放**契约与策略**（DTO / ``Protocol`` / backend 路由表），不放具体实现。
- 具体后端实现在 ``src/infrastructure/generation/``（R2-A4 搬包后落位）。
- 本包 ``__init__`` **不做 eager 聚合**，避免 ``config -> application`` 循环导入
  （见 ``documents/framework/refactoring/architecture_migration_progress.md`` 历史坑 #3）。
"""
