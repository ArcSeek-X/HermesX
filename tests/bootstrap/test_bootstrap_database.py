# -*- coding: utf-8 -*-
"""数据库装配（``src/bootstrap/database.py``）的行为回归。

锁定两点：
- ``api.deps`` 只是原样转出 ``get_db`` / ``get_database_manager``，保证
  ``Depends(...)`` 与 ``dependency_overrides[...]`` 拿到同一个函数对象；
- ``get_db`` 在依赖退出（含异常）时关闭 Session，且不隐式提交。
"""

import unittest
from unittest.mock import patch

import api.deps as api_deps
import src.bootstrap.database as bootstrap_database


class _FakeSession:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _FakeManager:
    def __init__(self, session: _FakeSession) -> None:
        self._session = session
        self.calls = 0

    def get_session(self) -> _FakeSession:
        self.calls += 1
        return self._session


class ApiDepsReexportTestCase(unittest.TestCase):
    def test_api_deps_reexports_the_bootstrap_callables(self):
        self.assertIs(api_deps.get_db, bootstrap_database.get_db)
        self.assertIs(api_deps.get_database_manager, bootstrap_database.get_database_manager)


class GetDbDependencyTestCase(unittest.TestCase):
    def test_yields_manager_session_and_closes_on_exit(self):
        session = _FakeSession()
        manager = _FakeManager(session)

        with patch.object(bootstrap_database, "get_database_manager", return_value=manager):
            dependency = bootstrap_database.get_db()
            yielded = next(dependency)
            with self.assertRaises(StopIteration):
                next(dependency)

        self.assertIs(yielded, session)
        self.assertEqual(manager.calls, 1)
        self.assertTrue(session.closed)

    def test_closes_session_when_consumer_raises(self):
        session = _FakeSession()
        manager = _FakeManager(session)

        with patch.object(bootstrap_database, "get_database_manager", return_value=manager):
            dependency = bootstrap_database.get_db()
            next(dependency)
            with self.assertRaises(RuntimeError):
                dependency.throw(RuntimeError("boom"))

        self.assertTrue(session.closed)


if __name__ == "__main__":
    unittest.main()
