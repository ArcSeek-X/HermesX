# -*- coding: utf-8 -*-
"""W4.2 依赖倒置收敛：agent tools（search_tools / data_tools）_get_db 工厂 seam 回归测试。

覆盖三件事：seam setter/getter 往返、``_get_db()`` 经装配工厂取库、以及
``bootstrap.agent.configure_tools_db`` 以 ``DatabaseManager.get_instance`` 装配两件 tools。
"""
from unittest.mock import patch

import pytest

from src.application.agent.tools import data_tools, search_tools
from src.bootstrap.agent import configure_tools_db

_MODULES = [search_tools, data_tools]
_IDS = ["search", "data"]


@pytest.mark.parametrize("mod", _MODULES, ids=_IDS)
def test_tools_db_factory_seam_accessor(mod) -> None:
    """set_db_factory 写入、_db_factory 读取往返；置 None 回退，finally 还原不污染进程级默认。"""
    sentinel = object()
    prior = mod._db_factory
    try:
        mod.set_db_factory(sentinel)
        assert mod._db_factory is sentinel
        mod.set_db_factory(None)
        assert mod._db_factory is None
    finally:
        mod._db_factory = prior


@pytest.mark.parametrize("mod", _MODULES, ids=_IDS)
def test_tools_get_db_consumes_seam_factory(mod) -> None:
    """_get_db() 应调用装配的工厂并返回其产物（收敛后的真实取库路径）。"""
    fake = object()
    prior = mod._db_factory
    try:
        mod.set_db_factory(lambda: fake)
        assert mod._get_db() is fake
    finally:
        mod._db_factory = prior


def test_configure_tools_db_wires_database_manager_get_instance_both() -> None:
    """bootstrap 装配将 DatabaseManager.get_instance 绑定为两件 tools 的默认工厂（幂等）。"""
    with patch("src.bootstrap.agent.DatabaseManager") as mock_dm, patch.object(
        search_tools, "set_db_factory"
    ) as st_set, patch.object(data_tools, "set_db_factory") as dt_set:
        configure_tools_db()
    st_set.assert_called_once_with(mock_dm.get_instance)
    dt_set.assert_called_once_with(mock_dm.get_instance)
