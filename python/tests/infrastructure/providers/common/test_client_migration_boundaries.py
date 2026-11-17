"""规范客户端路径保持唯一类型、可序列化及共享状态；旧内部别名已按 R2 退出。"""

import importlib
import pickle
from types import SimpleNamespace

import pytest

@pytest.mark.parametrize("module,symbol", [
    ("calendar.wallstreetcn_source", "CalendarEventEntry"),
    ("news.wallstreetcn_live", "LiveNewsEntry"),
    ("institutional.tw_client", "TwInstitutionalFetcher"),
    ("clients.stockdb", "StockDbSettings"),
    ("clients.stocksdk.bridge", "StockSdkSettings"),
])
def test_canonical_module_and_pickle_resolve_unique_class(module, symbol):
    canonical = importlib.import_module("data_provider." + module)
    cls = getattr(canonical, symbol)
    assert cls.__module__ == canonical.__name__
    assert pickle.loads(pickle.dumps(cls)) is cls


@pytest.mark.parametrize("module,getter", [
    ("clients.stockdb", "get_stockdb_client"),
    ("clients.stocksdk.bridge", "get_stocksdk_client"),
])
def test_shared_client_singleton_can_be_reset_without_duplicate_owner(
    module, getter, monkeypatch
):
    canonical = importlib.import_module("data_provider." + module)
    monkeypatch.setattr(canonical, "_CLIENT", None)
    monkeypatch.setattr("src.config.get_config", lambda: SimpleNamespace())
    client = getattr(canonical, getter)()
    try:
        assert getattr(canonical, getter)() is client
        monkeypatch.setattr(canonical, "_CLIENT", None)
        replacement = getattr(canonical, getter)()
        assert replacement is not client
        assert getattr(canonical, getter)() is replacement
        if hasattr(replacement, "_session"):
            replacement._session.close()
    finally:
        if hasattr(client, "_session"):
            client._session.close()


def test_stockdb_request_cache_and_failure_cooldown_share_original_session(monkeypatch):
    from data_provider.clients import stockdb

    calls = []
    value = {"rows": []}

    def get(url, **kwargs):
        calls.append((url, kwargs))
        if len(calls) > 1:
            raise stockdb.requests.ConnectionError("offline")
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: value)

    session = SimpleNamespace(get=get)
    monkeypatch.setattr(stockdb.requests, "Session", lambda: session)
    monkeypatch.setattr(stockdb, "time", SimpleNamespace(time=lambda: 100))
    client = stockdb.StockDbClient(
        stockdb.StockDbSettings(True, "http://stockdb.test", 500, 5, 60, 10)
    )
    result = client.fetch_daily_bars("600519", limit=500)
    assert result is value
    value["rows"].append("original shared payload")
    assert client.fetch_daily_bars("600519", limit=500) is value
    assert len(calls) == 1
    assert calls[0][1]["params"]["num"] == -5
    assert calls[0][1]["params"]["t"] == "日k"
    assert session.trust_env is False
    with pytest.raises(stockdb.StockDbError, match="不可达"):
        client.fetch_minute_bars("600519")
    # Existing cooldown is checked before the cache; do not silently change to stale serving.
    with pytest.raises(stockdb.StockDbError, match="冷却期"):
        client.fetch_daily_bars("600519", limit=500)
    assert len(calls) == 2


@pytest.mark.parametrize(
    "failure,code,status",
    [
        ("timeout", "stocksdk_timeout", 504),
        ("spawn", "stocksdk_spawn_failed", 503),
        ("empty", "stocksdk_empty_response", 502),
        ("bad_json", "stocksdk_bad_json", 502),
        ("exit", "stocksdk_bridge_failed", 502),
        ("api_error", "denied", 502),
    ],
)
def test_bridge_keeps_error_mapping_and_repository_cwd(
    failure, code, status, monkeypatch
):
    from data_provider.clients.stocksdk import bridge
    from tests.support.paths import get_repo_root

    assert bridge.REPO_ROOT == get_repo_root()
    assert (
        bridge.DEFAULT_BRIDGE_ENTRY
        == get_repo_root() / "scripts/stocksdk_bridge/bridge.mjs"
    )
    settings = bridge.StockSdkSettings(
        True, "node", str(bridge.DEFAULT_BRIDGE_ENTRY), 1234, 3, True
    )
    client = bridge.StockSdkBridgeClient(settings)
    monkeypatch.setattr(client, "_resolve_node_binary", lambda: "node")

    def run(command, **kwargs):
        assert kwargs["cwd"] == str(get_repo_root())
        assert kwargs["timeout"] == 1.234
        assert kwargs["check"] is False
        if failure == "timeout":
            raise bridge.subprocess.TimeoutExpired(command, 1.234)
        if failure == "spawn":
            raise OSError("spawn")
        outputs = {
            "empty": (0, ""),
            "bad_json": (0, "x"),
            "exit": (1, '{"ok": true}'),
            "api_error": (
                1,
                '{"ok": false, "error": {"code": "denied", "message": "denied"}}',
            ),
        }
        returncode, stdout = outputs[failure]
        return SimpleNamespace(returncode=returncode, stdout=stdout, stderr="failure")

    monkeypatch.setattr(bridge.subprocess, "run", run)
    with pytest.raises(bridge.StockSdkBridgeError) as caught:
        client.invoke("ping", {})
    assert caught.value.code == code
    assert caught.value.status_code == status
