"""Tests for fetcher/fetch_baostock_stock_list_cn.py pure functions.

只覆盖离线可测的转换/过滤/写盘逻辑；真实联网查询由 query_baostock() 承担，
不在单测里调用。
"""

import csv
import importlib
import sys

from tests.support.paths import get_repo_root

FETCHER_DIR = get_repo_root() / "scripts" / "stock_index_catalog" / "fetcher"
if str(FETCHER_DIR) not in sys.path:
    sys.path.insert(0, str(FETCHER_DIR))

mod = importlib.import_module("fetch_baostock_stock_list_cn")


def _record(code, name, ipo_date="2020-01-01", sec_type="1", status="1"):
    return [code, name, ipo_date, "", sec_type, status]


def test_convert_code_maps_sh_and_sz():
    assert mod.convert_code("sh.600519") == ("600519.SH", "600519", "SSE")
    assert mod.convert_code("sz.000001") == ("000001.SZ", "000001", "SZSE")


def test_convert_code_rejects_non_cn_prefixes():
    # 北交所不归本脚本（cn）负责；无后缀/空值也不接受
    assert mod.convert_code("bj.920000") is None
    assert mod.convert_code("920000") is None
    assert mod.convert_code("") is None
    assert mod.convert_code("hk.00700") is None


def test_infer_market_by_code_prefix():
    assert mod.infer_market("688836") == "科创板"
    assert mod.infer_market("301569") == "创业板"
    assert mod.infer_market("000001") == "主板"


def test_build_rows_filters_type_status_and_scope():
    records = [
        _record("sh.600519", "贵州茅台", "2001-08-27"),
        _record("sz.000001", "平安银行", "1991-04-03"),
        _record("sh.000001", "上证指数", sec_type="2"),       # 指数，排除
        _record("sh.600001", "已退市股", status="0"),          # 退市，排除
        _record("bj.920000", "北交所股"),                      # 非沪深，排除
        _record("sh.600002", ""),                             # 空名称，排除
        ["sh.600003"],                                        # 列数不足，排除
    ]

    rows = mod.build_rows(records)

    assert [r["ts_code"] for r in rows] == ["000001.SZ", "600519.SH"]
    assert rows[0]["list_date"] == "1991-04-03"
    assert rows[0]["exchange"] == "SZSE"
    assert rows[0]["list_status"] == "L"
    assert rows[1]["market"] == "主板"


def test_build_rows_deduplicates_and_keeps_first():
    records = [
        _record("sh.600519", "贵州茅台"),
        _record("sh.600519", "贵州茅台重复"),
    ]
    rows = mod.build_rows(records)
    assert len(rows) == 1
    assert rows[0]["name"] == "贵州茅台"


def test_csv_columns_are_tushare_compatible():
    assert mod.CSV_COLUMNS == [
        "ts_code", "symbol", "name", "area", "industry", "fullname", "enname",
        "cnspell", "market", "exchange", "curr_type", "list_status", "list_date",
        "delist_date", "is_hs", "act_name", "act_ent_type",
    ]
    assert mod.OUTPUT_FILENAME == "stock_list_cn.csv"


def test_default_output_dir_is_data_stock_index_catalog():
    expected = get_repo_root() / "data" / "stock_index_catalog"
    assert mod.OUTPUT_DIR.resolve() == expected.resolve()


def test_save_csv_writes_utf8_sig_and_is_readable(tmp_path):
    rows = mod.build_rows([_record("sh.688836", "宇树科技", "2026-08-19")])

    path = mod.save_csv(rows, tmp_path)

    assert path == tmp_path / "stock_list_cn.csv"
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")  # utf-8-sig BOM
    with open(path, encoding="utf-8-sig", newline="") as handle:
        loaded = list(csv.DictReader(handle))
    assert len(loaded) == 1
    assert loaded[0]["ts_code"] == "688836.SH"
    assert loaded[0]["name"] == "宇树科技"
    assert loaded[0]["list_date"] == "2026-08-19"
    assert loaded[0]["market"] == "科创板"


def test_main_writes_csv_without_empty_output(tmp_path):
    records = [
        _record("sh.600519", "贵州茅台", "2001-08-27"),
        _record("sz.000001", "平安银行", "1991-04-03"),
    ]

    from unittest.mock import patch
    with patch.object(mod, "query_baostock", return_value=records):
        assert mod.main(["--output-dir", str(tmp_path)]) == 0

    assert (tmp_path / "stock_list_cn.csv").is_file()
