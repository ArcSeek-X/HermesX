"""筹码拆分保留提供方解析、domain 真源、配额输入与独立半开熔断。"""

import sys
from types import SimpleNamespace
from unittest.mock import Mock, call

import pandas as pd
import pytest

from data_provider.runtime.manager import DataFetcherManager
from data_provider.chip.base import _is_meaningful_chip_distribution
from data_provider.runtime.fetchers.akshare import AkshareFetcher
from data_provider.runtime.fetchers.tushare import TushareFetcher
from src.domain.analysis.chip_rules import has_meaningful_chip_data
from src.domain.market.chip_distribution import ChipDistribution


def test_provider_validation_keeps_dictionary_distinct_from_analysis_context():
    value = {"avg_cost": 10, "concentration_90": 0}
    assert has_meaningful_chip_data(value)
    assert not _is_meaningful_chip_distribution(value)


def test_provider_validation_keeps_falsey_attribute_object_semantics():
    class FalseyChip:
        avg_cost, concentration_90, concentration_70 = 10, 0, None

        def __bool__(self):
            return False

    value = FalseyChip()
    assert _is_meaningful_chip_distribution(value)
    assert not has_meaningful_chip_data(value)


@pytest.mark.parametrize("valid", [True, False])
def test_tushare_chip_keeps_trade_window_api_sequence_and_domain_input(valid):
    owner = TushareFetcher.__new__(TushareFetcher)
    source = owner._chip_source()
    raw = pd.DataFrame({"price": [12, 8, 10], "percent": [10, 20, 70]})
    owner.get_trade_time = Mock(return_value="20261105")
    owner._call_api_with_rate_limit = Mock(
        side_effect=[raw if valid else raw.drop(columns="price"), pd.DataFrame({"close": [10]})]
    )
    result = source.get_chip_distribution("600519")
    owner.get_trade_time.assert_called_once_with(early_time="00:00", late_time="19:00")
    assert owner._call_api_with_rate_limit.call_args_list == [
        call("cyq_chips", ts_code="600519.SH", start_date="20261105", end_date="20261105"),
        call("daily", ts_code="600519.SH", start_date="20261105", end_date="20261105"),
    ]
    if valid:
        assert type(result) is ChipDistribution
        assert result.date == "2026-11-05"
        assert result.profit_ratio == 0.9
        assert result.avg_cost == 9.8
        assert result.concentration_90 == 0.2
        assert result.concentration_70 == 0.1111
    else:
        assert result is None


def test_chip_half_open_empty_probe_reopens_and_fallback_uses_same_breaker(monkeypatch):
    import src.config
    from data_provider.common import health
    from data_provider.common.health import get_chip_circuit_breaker

    clock = [100.0]
    chip = health.CircuitBreaker(failure_threshold=1, cooldown_seconds=10)
    realtime = health.CircuitBreaker(failure_threshold=1, cooldown_seconds=10)
    monkeypatch.setattr(health, "_chip_circuit_breaker", chip)
    monkeypatch.setattr(health, "_realtime_circuit_breaker", realtime)
    monkeypatch.setattr(health, "time", SimpleNamespace(time=lambda: clock[0]))
    monkeypatch.setattr(src.config, "get_config", lambda: SimpleNamespace(enable_chip_distribution=True))
    chip.record_failure("first_chip", "offline")
    clock[0] = 111.0
    first = SimpleNamespace(name="FirstFetcher", priority=0, get_chip_distribution=Mock(return_value=None))
    valid = ChipDistribution(code="600519", avg_cost=10, concentration_90=0)
    second = SimpleNamespace(name="SecondFetcher", priority=1, get_chip_distribution=Mock(return_value=valid))
    owner = DataFetcherManager(fetchers=[first, second])
    assert owner.get_chip_distribution("SH600519") is valid
    first.get_chip_distribution.assert_called_once_with("600519")
    second.get_chip_distribution.assert_called_once_with("600519")
    assert get_chip_circuit_breaker() is chip
    assert chip.get_status()["first_chip"] == chip.OPEN
    assert chip._states["first_chip"]["half_open_calls"] == 0
    assert realtime.get_status() == {}


def test_akshare_chip_keeps_latest_row_units_and_domain_model(monkeypatch):
    owner = AkshareFetcher.__new__(AkshareFetcher)
    owner._set_random_user_agent = Mock()
    owner._enforce_rate_limit = Mock()
    frame = pd.DataFrame(
        {
            "日期": ["2026-11-04", "2026-11-05"],
            "获利比例": [0.1, 0.6],
            "平均成本": [10, 20],
            "90成本-低": [8, 18],
            "90成本-高": [12, 22],
            "90集中度": [0.2, 0.1],
            "70成本-低": [9, 19],
            "70成本-高": [11, 21],
            "70集中度": [0.1, 0.05],
        }
    )
    before = frame.copy(deep=True)
    query = Mock(return_value=frame)
    monkeypatch.setitem(sys.modules, "akshare", SimpleNamespace(stock_cyq_em=query))
    result = owner.get_chip_distribution("600519")
    assert type(result) is ChipDistribution
    assert result.date == "2026-11-05" and result.avg_cost == 20
    assert result.profit_ratio == 0.6 and result.concentration_90 == 0.1
    query.assert_called_once_with(symbol="600519")
    owner._enforce_rate_limit.assert_called_once_with()
    pd.testing.assert_frame_equal(frame, before)
