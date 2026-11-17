# -*- coding: utf-8 -*-
"""数据库装配：把进程级 ``DatabaseManager`` 单例暴露给上层入口。

``api`` / ``bot`` 不允许直接依赖 ``src.storage``（见架构守卫规则），需要数据库
句柄时从这里取。首次调用 ``DatabaseManager.get_instance()`` 才会建库与执行
启动期 schema 升级；导入本模块本身不打开数据库。
"""

from __future__ import annotations

from typing import Generator

from sqlalchemy.orm import Session

from src.storage import DatabaseManager


def get_database_manager() -> DatabaseManager:
    """返回当前进程的数据库管理器单例。"""
    return DatabaseManager.get_instance()


def get_db() -> Generator[Session, None, None]:
    """FastAPI 会话依赖：请求结束后关闭 Session（不隐式提交）。

    需要写事务的调用方应继续使用 ``DatabaseManager._run_write_transaction``，
    本依赖只提供读取用的会话。
    """
    session = get_database_manager().get_session()
    try:
        yield session
    finally:
        session.close()
