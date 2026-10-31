# -*- coding: utf-8 -*-
"""数据库连接与会话生命周期。

本模块是持久化层唯一的「引擎 + Session 工厂」持有者，负责四件事：

1. 建引擎：统一 ``pool_pre_ping``，SQLite 额外传 ``timeout``（来自
   ``SQLITE_BUSY_TIMEOUT_MS``）。
2. 连接参数：SQLite 每个新连接安装 ``busy_timeout``，文件库按配置开 WAL。
   内存库（``:memory:``）跳过 WAL——它没有持久化文件，开了也没有意义。
3. 会话：``create_session()`` 返回裸 Session（调用方 ``with`` 使用），
   ``session_scope()`` 提供提交 / 回滚包装。
4. 写事务重试：``write_transaction()`` 是**唯一推荐的写入入口**。SQLite 并发
   写会抛 ``database is locked``，这里用 ``BEGIN IMMEDIATE`` 提前拿写锁 +
   指数退避重试；业务代码直接开 session 写库会绕过重试，随机失败。

约定：本模块只管「怎么连、怎么写」，不含任何业务语义与表结构；schema 升级见
:mod:`src.infrastructure.persistence.schema_compat`。
"""

from __future__ import annotations

import logging
import threading
import time
from contextlib import contextmanager
from typing import Callable, Optional, TypeVar

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

T = TypeVar("T")

# atexit 钩子持有锁：进程退出时可能与请求线程并发访问引擎
_cleanup_lock = threading.Lock()


def is_sqlite_locked_error(exc: OperationalError) -> bool:
    """判断是否为 SQLite 锁冲突（可重试）错误。"""
    err_text = str(getattr(exc, "orig", exc)).lower()
    return any(
        token in err_text
        for token in (
            "database is locked",
            "database schema is locked",
            "database table is locked",
        )
    )


def is_sqlite_duplicate_column_error(exc: OperationalError, column: str) -> bool:
    """判断是否为「列已存在」错误，用于幂等补列时忽略重复添加。"""
    err_text = str(getattr(exc, "orig", exc)).lower()
    return "duplicate column name" in err_text and column.lower() in err_text


def dispose_engine(engine: Optional[Engine]) -> None:
    """释放引擎连接（atexit 钩子）。失败只告警，不影响进程退出。"""
    with _cleanup_lock:
        try:
            if engine is not None:
                engine.dispose()
                logger.debug("数据库引擎已清理")
        except Exception as exc:  # noqa: BLE001 - 退出阶段不允许抛错
            logger.warning("清理数据库引擎时出错: %s", exc)


class DatabaseSession:
    """引擎、Session 工厂与写事务重试的持有者。

    Args:
        db_url: 数据库连接 URL。
        sqlite_busy_timeout_ms: SQLite 连接超时（毫秒），<=0 表示不显式设置。
        sqlite_wal_enabled: 文件型 SQLite 是否开启 WAL。
        sqlite_write_retry_max: 写锁冲突最大重试次数（仅 SQLite 生效）。
        sqlite_write_retry_base_delay: 重试退避基数（秒），按 ``base * 2**n`` 递增。
    """

    def __init__(
        self,
        db_url: str,
        *,
        sqlite_busy_timeout_ms: int = 0,
        sqlite_wal_enabled: bool = True,
        sqlite_write_retry_max: int = 0,
        sqlite_write_retry_base_delay: float = 0.1,
    ) -> None:
        self.db_url = db_url
        self.sqlite_busy_timeout_ms = sqlite_busy_timeout_ms
        self.sqlite_wal_enabled = sqlite_wal_enabled
        self.sqlite_write_retry_max = sqlite_write_retry_max
        self.sqlite_write_retry_base_delay = sqlite_write_retry_base_delay

        engine_kwargs: dict = {"echo": False, "pool_pre_ping": True}
        if str(db_url).startswith("sqlite:") and self.sqlite_busy_timeout_ms > 0:
            engine_kwargs["connect_args"] = {
                "timeout": self.sqlite_busy_timeout_ms / 1000,
            }

        self.engine: Engine = create_engine(db_url, **engine_kwargs)
        self.is_sqlite = self.engine.url.get_backend_name() == "sqlite"
        self.is_file_sqlite = self.is_sqlite and self._detect_file_sqlite()
        self._install_sqlite_pragma_handler()

        self.session_factory = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
        )

    # ------------------------------------------------------------------ 引擎

    def _detect_file_sqlite(self) -> bool:
        """判断是否为**文件型** SQLite（排除内存库 ``:memory:``）。"""
        database = (self.engine.url.database or "").strip()
        return bool(database) and database.lower() != ":memory:"

    def _install_sqlite_pragma_handler(self) -> None:
        """为每个新建的 SQLite 连接安装竞争保护参数。"""
        if not self.is_sqlite:
            return

        @event.listens_for(self.engine, "connect")
        def _configure_sqlite_connection(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute(f"PRAGMA busy_timeout={int(self.sqlite_busy_timeout_ms)}")
                if self.is_file_sqlite and self.sqlite_wal_enabled:
                    cursor.execute("PRAGMA journal_mode=WAL")
            except Exception as exc:  # noqa: BLE001 - PRAGMA 失败不影响连接可用
                logger.warning("初始化 SQLite PRAGMA 失败: %s", exc)
            finally:
                cursor.close()

    def dispose(self) -> None:
        """释放本会话持有的引擎。"""
        dispose_engine(self.engine)

    # ------------------------------------------------------------------ 会话

    def create_session(self) -> Session:
        """创建一个新的 Session。

        调用方负责关闭：``with db_session.create_session() as session:``。
        """
        return self.session_factory()

    @contextmanager
    def session_scope(self):
        """事务作用域：正常结束提交，异常回滚，最后一定关闭。"""
        session = self.create_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ------------------------------------------------------------- 写事务重试

    def write_transaction(
        self,
        operation_name: str,
        write_operation: Callable[[Session], T],
    ) -> T:
        """执行写入事务，并在 SQLite 锁冲突时自动重试。

        Args:
            operation_name: 操作名，仅用于日志定位。
            write_operation: 实际写入逻辑，接收 session 并返回结果。

        Returns:
            ``write_operation`` 的返回值。

        Raises:
            OperationalError: 非锁冲突错误，或重试次数用尽后仍冲突。
        """
        max_retries = self.sqlite_write_retry_max if self.is_sqlite else 0

        for attempt in range(max_retries + 1):
            session = self.create_session()
            try:
                if self.is_sqlite:
                    # 在任何读取之前先拿到 SQLite 写锁，使写入前的存在性检查与
                    # 随后的 upsert 处于同一个一致窗口，避免并发下重复插入
                    session.connection().exec_driver_sql("BEGIN IMMEDIATE")
                result = write_operation(session)
                session.commit()
                return result
            except OperationalError as exc:
                session.rollback()
                if (
                    self.is_sqlite
                    and is_sqlite_locked_error(exc)
                    and attempt < max_retries
                ):
                    delay = self.sqlite_write_retry_base_delay * (2 ** attempt)
                    logger.warning(
                        "SQLite 写入锁冲突，准备重试: %s (%s/%s, %.2fs)",
                        operation_name,
                        attempt + 1,
                        max_retries,
                        delay,
                    )
                    if delay > 0:
                        time.sleep(delay)
                    continue
                raise
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
