"""板块/涨跌停协议轻量化保留旧 DTO 载荷与具体源优先导入。"""

import importlib
import pickle
import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "package,kind,args,kwargs",
    [
        ("sector", "SectorRankingRequest", (), {"limit": 3, "ranking_type": "concept"}),
        ("sector", "SectorRankingResult", ([{"name": "sample"}], []), {"source": "eastmoney"}),
        ("limit_pool", "LimitPoolEntry", (), {"code": "600519", "first_limit_time": "093000"}),
        ("limit_pool", "LimitPoolRequest", (), {"pool_type": "limit_down", "date": "20260102", "limit": 3}),
        ("limit_pool", "LimitPoolResult", (), {"source": "eastmoney", "date": "20260102"}),
    ],
)
def test_old_contract_pickle_payloads_and_base_aliases_keep_identity(package, kind, args, kwargs):
    contract = importlib.import_module("data_provider." + package + ".source_contract")
    base = importlib.import_module("data_provider." + package + ".base")
    cls = getattr(contract, kind)
    assert getattr(base, kind) is cls
    value = cls(*args, **kwargs)
    payload = pickle.dumps(value, protocol=0).replace(
        ("data_provider." + package + ".source_contract").encode(),
        ("data_provider." + package + ".base").encode(),
    )
    restored = pickle.loads(payload)
    assert type(restored) is cls
    assert restored == value
    if kind == "LimitPoolEntry":
        assert restored.to_dict() == value.to_dict()


@pytest.mark.parametrize(
    "package,first",
    [
        ("sector", "eastmoney_source"),
        ("sector", "akshare_source"),
        ("sector", "coordination"),
        ("limit_pool", "akshare_source"),
        ("limit_pool", "eastmoney_source"),
        ("limit_pool", "stocksdk_source"),
    ],
)
def test_concrete_source_first_does_not_construct_default_manager(package, first):
    expected = {"eastmoney"} if package == "sector" else {"eastmoney", "stocksdk"}
    script = f"""
import importlib, sys
importlib.import_module("data_provider.{package}.{first}")
assert "data_provider.{package}.base" not in sys.modules
base = importlib.import_module("data_provider.{package}.base")
contract = importlib.import_module("data_provider.{package}.source_contract")
assert set(base._MANAGER.sources) == {expected!r}
for name in vars(contract):
    if name.startswith(("SectorRanking", "LimitPool", "LIMIT_")):
        assert getattr(base,name) is getattr(contract,name)
if {package!r} == "limit_pool":
    assert base._MANAGER.sources["stocksdk"].is_available() is False
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
