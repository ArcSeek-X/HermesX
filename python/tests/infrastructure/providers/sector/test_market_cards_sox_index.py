# -*- coding: utf-8 -*-
"""港美补充指数（SOX / TSX）链路与新浪兜底源的回归用例。"""

from types import SimpleNamespace
from unittest.mock import Mock

from data_provider.sector import market_cards_source as cards
from data_provider.sector import sina_source

SINA_OK = (
    'var hq_str_gb_sox="费交所半导体股指数,9011.1375,-12.25,2026-11-06 06:16:01,'
    '-1257.5168,9806.3111,9838.1305,8997.3853,14655.2861,6160.0449,0,0,0,0.00,--,'
    '0.00,0.00,0.00,0.00,0,0,0.0000,0.00,0.00,,Nov 05 05:16PM EST,10268.6543,0,1,2026,'
    '0.0000,0.0000,0.0000,0.0000,0.0000,0.0000";\n'
)


def _index(code: str, price: float = 100.0) -> dict:
    return {
        "name": code,
        "code": code,
        "price": price,
        "changePercent": -1.0,
        "change": -1.0,
        "amount": None,
        "high": 110.0,
        "low": 90.0,
        "preClose": 101.0,
    }


def _hk_us_indices() -> list:
    return [_index(code) for code in ("HSI", "HSCEI", "HSTECH", "DJI", "INX", "IXIC")]


def _supplements() -> list:
    return [_index("SOX", 9011.14), _index("TSX", 35605.27)]


def _run_cards(monkeypatch, main_indices, supplements):
    monkeypatch.setattr(cards, "_get_market_indices", Mock(return_value=main_indices))
    supplement_mock = Mock(return_value=supplements or [])
    monkeypatch.setattr(cards, "_get_supplement_indices", supplement_mock)
    return cards._build_index_cards_for_market("hk-us"), supplement_mock


def _run_supplement_chain(monkeypatch, eastmoney_rows, sina_row=None):
    monkeypatch.setattr(
        cards, "get_cached_market_indices_from_eastmoney", Mock(return_value=eastmoney_rows)
    )
    sina = Mock(return_value=sina_row)
    monkeypatch.setattr(cards, "get_cached_sox_index_from_sina", sina)
    return cards._get_supplement_indices(), sina


def test_parse_sox_quote_normalizes_payload() -> None:
    item = sina_source.parse_sox_quote(SINA_OK)
    assert item["name"] == "费城半导体指数"
    assert item["code"] == "SOX"
    assert item["price"] == 9011.1375
    assert item["changePercent"] == -12.25
    assert item["change"] == -1257.5168
    assert item["high"] == 9838.1305
    assert item["low"] == 8997.3853
    assert item["preClose"] == 10268.6543
    assert item["amount"] is None


def test_to_float_keeps_zero_and_rejects_placeholders() -> None:
    assert sina_source._to_float(0) == 0.0
    assert sina_source._to_float("0.00") == 0.0
    assert sina_source._to_float("--") is None
    assert sina_source._to_float(None) is None
    assert sina_source._to_float("nan") is None


def test_parse_sox_quote_rejects_invalid_payload() -> None:
    assert sina_source.parse_sox_quote("Forbidden") is None
    assert sina_source.parse_sox_quote("") is None
    assert sina_source.parse_sox_quote('var hq_str_gb_sox="短字段,1,2";') is None
    assert sina_source.parse_sox_quote('var hq_str_gb_sox="' + ",".join(["x"] * 30) + '";') is None


def test_fetch_sox_index_decodes_sina_payload(monkeypatch) -> None:
    response = Mock(text=SINA_OK)
    session = Mock()
    session.get = Mock(return_value=response)
    monkeypatch.setattr(sina_source, "_session", session)
    assert sina_source.fetch_sox_index()["price"] == 9011.1375
    assert session.get.call_args.args[0] == sina_source.SINA_QUOTE_URL
    response.raise_for_status.assert_called_once_with()


def test_cached_sox_index_reuses_fresh_data_and_keeps_last_good(monkeypatch) -> None:
    clock = [100.0]
    monkeypatch.setattr(sina_source, "time", SimpleNamespace(time=lambda: clock[0]))
    monkeypatch.setattr(sina_source, "_SOX_CACHE", {"data": None, "timestamp": 0.0, "ttl": 60})
    fetch = Mock(return_value=_index("SOX", 9011.14))
    monkeypatch.setattr(sina_source, "fetch_sox_index", fetch)

    assert sina_source.get_cached_sox_index() == _index("SOX", 9011.14)
    assert sina_source.get_cached_sox_index() == _index("SOX", 9011.14)
    fetch.assert_called_once_with()

    clock[0] = 200.0
    fetch.return_value = None
    assert sina_source.get_cached_sox_index() == _index("SOX", 9011.14)
    assert fetch.call_count == 2


def test_hk_us_appends_both_supplement_cards_with_unique_keys(monkeypatch) -> None:
    result, supplement_mock = _run_cards(monkeypatch, _hk_us_indices(), _supplements())
    assert len(result) == 8
    assert [card["cardKey"] for card in result[-2:]] == ["index_quote:SOX", "index_quote:TSX"]
    assert len({card["cardKey"] for card in result}) == 8
    supplement_mock.assert_called_once_with()


def test_hk_us_deduplicates_supplements_from_eastmoney_fallback(monkeypatch) -> None:
    main = _hk_us_indices() + _supplements()
    result, _ = _run_cards(monkeypatch, main, _supplements())
    assert len(result) == 8
    assert len({card["cardKey"] for card in result}) == 8


def test_hk_us_keeps_original_cards_when_supplements_unavailable(monkeypatch) -> None:
    result, _ = _run_cards(monkeypatch, _hk_us_indices(), [])
    assert len(result) == 6
    assert not {"SOX", "TSX"} & {card["payload"]["code"] for card in result}


def test_hk_us_keeps_single_supplement_when_other_missing(monkeypatch) -> None:
    result, _ = _run_cards(monkeypatch, _hk_us_indices(), [_index("SOX", 9011.14)])
    assert len(result) == 7
    assert result[-1]["cardKey"] == "index_quote:SOX"


def test_hk_us_does_not_show_orphan_supplements_when_main_indices_empty(monkeypatch) -> None:
    result, _ = _run_cards(monkeypatch, [], _supplements())
    assert result == []


def test_other_markets_do_not_touch_supplement_source(monkeypatch) -> None:
    monkeypatch.setattr(cards, "_get_market_indices", Mock(return_value=[_index("N225")]))
    supplement_mock = Mock(return_value=_supplements())
    monkeypatch.setattr(cards, "_get_supplement_indices", supplement_mock)
    assert len(cards._build_index_cards_for_market("jp-kr")) == 1
    supplement_mock.assert_not_called()


def test_supplement_chain_prefers_eastmoney_for_both(monkeypatch) -> None:
    rows = [_index("DJIA"), _index("SOX", 9011.14), _index("TSX", 35605.27)]
    result, sina = _run_supplement_chain(monkeypatch, rows, _index("SOX", 9999.0))
    assert [item["code"] for item in result] == ["SOX", "TSX"]
    assert result[0]["price"] == 9011.14
    sina.assert_not_called()


def test_supplement_chain_falls_back_to_sina_when_eastmoney_missing_sox(monkeypatch) -> None:
    result, sina = _run_supplement_chain(
        monkeypatch, [_index("DJIA"), _index("TSX", 35605.27)], _index("SOX", 9011.14)
    )
    assert [item["code"] for item in result] == ["SOX", "TSX"]
    assert result[0]["price"] == 9011.14
    sina.assert_called_once_with()


def test_supplement_chain_falls_back_when_eastmoney_raises(monkeypatch) -> None:
    monkeypatch.setattr(
        cards,
        "get_cached_market_indices_from_eastmoney",
        Mock(side_effect=RuntimeError("eastmoney down")),
    )
    sina = Mock(return_value=_index("SOX", 9011.14))
    monkeypatch.setattr(cards, "get_cached_sox_index_from_sina", sina)
    # TSX 无备用源：东财整体不可用时只保留 SOX。
    assert [item["code"] for item in cards._get_supplement_indices()] == ["SOX"]
    sina.assert_called_once_with()


def test_supplement_chain_skips_eastmoney_row_without_price(monkeypatch) -> None:
    broken = _index("SOX")
    broken["price"] = None
    result, sina = _run_supplement_chain(
        monkeypatch, [broken, _index("TSX", 35605.27)], _index("SOX", 9011.14)
    )
    assert [item["code"] for item in result] == ["SOX", "TSX"]
    assert result[0]["price"] == 9011.14
    sina.assert_called_once_with()


def test_tsx_has_no_sina_fallback(monkeypatch) -> None:
    result, sina = _run_supplement_chain(monkeypatch, [_index("DJIA")], _index("SOX", 9011.14))
    assert [item["code"] for item in result] == ["SOX"]
    sina.assert_called_once_with()


def test_supplement_chain_keeps_configured_order(monkeypatch) -> None:
    result, _ = _run_supplement_chain(
        monkeypatch, [_index("TSX", 35605.27), _index("SOX", 9011.14)], None
    )
    assert [item["code"] for item in result] == ["SOX", "TSX"]
