# -*- coding: utf-8 -*-
"""运行时用例的装配。

``TaskService`` 的历史查询只依赖历史仓储端口，具体适配器绑定到
``DatabaseManager`` 全局单例；``application`` 层不接触 ``src.storage``，
需要数据库句柄时经此装配（bootstrap→storage 合法）。
"""

from __future__ import annotations

from src.storage import DatabaseManager


def configure_task_service() -> None:
    """装配 TaskService 历史查询用例的历史仓储默认端口。

    进程启动时调用一次（CLI 入口 / API lifespan）；``set_history_repo`` 幂等，
    重复调用只会重新指向同一个适配器。以 ``DatabaseManager`` 门面作
    :class:`~src.application.history.ports.HistoryRepositoryPort` 适配器，与迁移前
    用例内部 ``get_db()`` 取全局单例的语义逐字等价。
    """
    from src.application.runtime.task_service import set_history_repo

    set_history_repo(DatabaseManager.get_instance())
