"""Tests for scripts/stock_index_catalog/reorder_stock_index.py.

覆盖排序核心逻辑（sort_key）与 main 的写盘 / 幂等；不依赖网络。
"""

import importlib
import json
import sys

from tests.support.paths import get_repo_root

FETCHER_DIR = get_repo_root() / "scripts" / "stock_index_catalog"
if str(FETCHER_DIR) not in sys.path:
    sys.path.insert(0, str(FETCHER_DIR))

mod = importlib.import_module("reorder_stock_index")
index_sort = importlib.import_module("index_sort")


def _rec(code, market, list_date=""):
    row = [""] * 11
    row[0] = code
    row[6] = market
    row[10] = list_date
    return row


def test_top_level_market_order():
    records = [
        _rec("AAPL", "US", "1980-12-12"),
        _rec("00700.HK", "HK", "2004-06-16"),
        _rec("000001.SZ", "CN", "1991-04-03"),
        _rec("7203.T", "JP", "1949-05-16"),
        _rec("005930.KS", "KR", "1975-06-11"),
    ]
    ordered = sorted(records, key=index_sort.sort_key)
    assert [r[6] for r in ordered if r[6] in ("CN", "BSE")] == ["CN"]
    assert [r[6] for r in ordered] == ["CN", "HK", "US", "JP", "KR"]


def test_a_share_exchange_order_within_group():
    records = [
        _rec("920000.BJ", "BSE", "2020-12-23"),
        _rec("600519.SH", "CN", "2001-08-27"),
        _rec("000001.SZ", "CN", "1991-04-03"),
    ]
    ordered = sorted(records, key=index_sort.sort_key)
    assert [r[0] for r in ordered] == ["600519.SH", "000001.SZ", "920000.BJ"]


def test_date_ascending_within_exchange_group():
    # 同一交易所（.SZ）内，按上市日期从早到晚升序
    records = [
        _rec("000004.SZ", "CN", "1990-12-01"),
        _rec("000001.SZ", "CN", "1991-04-03"),
        _rec("000002.SZ", "CN", "1991-01-29"),
    ]
    ordered = sorted(records, key=index_sort.sort_key)
    assert [r[0] for r in ordered] == ["000004.SZ", "000002.SZ", "000001.SZ"]


def test_empty_date_goes_last_in_group():
    records = [
        _rec("600519.SH", "CN", "2001-08-27"),
        _rec("000001.SZ", "CN", ""),
        _rec("000002.SZ", "CN", "1991-01-29"),
    ]
    ordered = sorted(records, key=index_sort.sort_key)
    assert ordered[-1][0] == "000001.SZ"  # 空日期排到分组末尾


def test_main_writes_sorted_and_idempotent(tmp_path):
    path = tmp_path / "stocks.index.json"
    records = [
        _rec("920000.BJ", "BSE", "2020-12-23"),
        _rec("600519.SH", "CN", "2001-08-27"),
        _rec("000001.SZ", "CN", "1991-04-03"),
    ]
    path.write_text(json.dumps(records), encoding="utf-8")

    assert mod.main(["--index", str(path)]) == 0
    sorted_once = json.loads(path.read_text(encoding="utf-8"))
    assert [r[0] for r in sorted_once] == ["600519.SH", "000001.SZ", "920000.BJ"]
    assert (tmp_path / "stocks.index.json.bak").is_file()

    # 再跑一次应幂等（内容不变）
    import hashlib

    digest = hashlib.md5(path.read_bytes()).hexdigest()
    assert mod.main(["--index", str(path)]) == 0
    assert hashlib.md5(path.read_bytes()).hexdigest() == digest
