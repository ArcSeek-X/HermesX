# -*- coding: utf-8 -*-
"""通知域纯规则。

分层约定：

- 本包只放**与具体渠道实现无关、零 IO 的纯规则**：渠道能力契约（配置组判定）、
  路由渠道解析与校验（R2-B1 后的 B2 首子步）。
- 需要真实网络请求、SDK 或文件 IO 的渠道实现留在 ``src/infrastructure/notification/senders/``
  （物理搬层归 R2-B5）。
- 本包 ``__init__`` **不做 eager 聚合**，避免 ``config -> domain`` 拉起重依赖
  （见 ``documents/framework/refactoring/architecture_migration_progress.md`` 历史坑 #3），
  消费方一律按子模块精确导入：``src.domain.notification.contracts`` /
  ``src.domain.notification.routing``。
- 旧路径 ``src/notification_contracts`` / ``src/notification_routing`` 垫片已在
  R2-B2 次子步删除（仓库内消费方已全量 re-point）；若有外部脚本按旧路径导入，
  需改指上述子模块。
- ``src/infrastructure/notification/senders/gotify_sender.py`` / ``ntfy_sender.py`` 对
  ``endpoints`` 保留 re-export，供 sender 模块自身与 ``senders/__init__``
  的包聚合面使用（测试未 patch 这两个函数），R2-B5 搬包已随之收敛。
"""
