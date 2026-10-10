# -*- coding: utf-8 -*-
"""腾讯基础信息兜底源离线测试（mock 网络，不依赖外部可达性）。"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

import data_provider.stock_info.tencent_source as txmod
from data_provider.stock_info.tencent_source import TencentStockInfoSource, _parse_fields


def _build_payload(symbol: str) -> bytes:
    """构造与真实腾讯行情同构的 ~ 分隔样例（仅关键下标填真实值）。"""
    fields = [""] * 53
    fields[0] = "51"
    fields[1] = "湖北宜化"
    fields[2] = symbol
    fields[3] = "11.28"   # 现价
    fields[4] = "11.52"   # 昨收
    fields[5] = "11.52"   # 今开
    fields[6] = "127435"  # 成交量(手)
    fields[31] = "-0.24"  # 涨跌
    fields[32] = "-2.08"  # 涨跌幅(%)
    fields[33] = "11.65"  # 最高
    fields[34] = "11.21"  # 最低
    fields[37] = "14568"  # 成交额(万元)
    fields[38] = "1.19"   # 换手率(%)
    fields[43] = "3.82"   # 振幅(%)
    fields[44] = "120.38" # 总市值(亿元)
    fields[52] = "19.2"   # 市盈率(TTM)
    return f'v_{symbol}="' + "~".join(fields) + '";\n'.encode("gbk")


@pytest.fixture
def patched_session(monkeypatch):
    captured = {}

    def fake_get(url, params=None, timeout=None, headers=None):
        captured["url"] = url
        captured["params"] = params
        return SimpleNamespace(content=_build_payload(params["q"]), raise_for_status=lambda: None)

    monkeypatch.setattr(txmod, "_SESSION", SimpleNamespace(get=fake_get))
    return captured


def test_parse_fields_strips_wrapper():
    fields = _parse_fields('v_sz000422="51~湖北宜化~000422~11.28~11.52";'.encode("gbk"))
    assert fields[0] == "51"
    assert fields[1] == "湖北宜化"
    assert fields[3] == "11.28"


def test_fetch_strips_suffix_and_converts_units(patched_session):
    captured = patched_session
    result = TencentStockInfoSource().fetch("000422.SZ")

    assert result is not None
    assert captured["params"]["q"] == "sz000422"  # 交易所后缀已剥离
    assert result.stock_name == "湖北宜化"
    assert result.current_price == 11.28
    assert result.prev_close == 11.52
    assert result.open == 11.52
    assert result.high == 11.65
    assert result.low == 11.21
    assert result.change == -0.24
    assert result.change_percent == -2.08
    assert result.volume == 127435 * 100          # 手 -> 股
    assert result.amount == 14568 * 10000         # 万元 -> 元
    assert result.turnover_rate == 1.19
    assert result.amplitude == 3.82
    assert result.pe_ratio_ttm == 19.2
    assert result.total_market_cap == pytest.approx(120.38 * 1e8)  # 亿元 -> 元
    assert result.source == "tencent"


def test_fetch_rejects_short_payload(monkeypatch):
    monkeypatch.setattr(
        txmod, "_SESSION", SimpleNamespace(get=lambda **_: SimpleNamespace(content=b'v_x="1~name";', raise_for_status=lambda: None))
    )
    assert TencentStockInfoSource().fetch("000422.SZ") is None
