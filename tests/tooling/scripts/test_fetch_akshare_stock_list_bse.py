"""Tests for fetcher/fetch_akshare_stock_list_bse.py pure functions.

只覆盖离线可测的映射 / 过滤 / 写盘逻辑；真实联网查询由 query_akshare() 承担，
不在单测里调用（用 unittest.mock.patch 替换）。
"""

import csv
import importlib
import sys

from tests.support.paths import get_repo_root

FETCHER_DIR = get_repo_root() / "scripts" / "stock_index_catalog" / "fetcher"
if str(FETCHER_DIR) not in sys.path:
    sys.path.insert(0, str(FETCHER_DIR))

mod = importlib.import_module("fetch_akshare_stock_list_bse")

EXPECTED_COLUMNS = [
    "ts_code", "symbol", "name", "area", "industry", "fullname", "enname",
    "cnspell", "market", "exchange", "curr_type", "list_status", "list_date",
    "delist_date", "is_hs", "act_name", "act_ent_type",
]


def _dataframe(rows):
    """用与 akshare 一致的列名构造测试 DataFrame。"""
    import pandas as pd

    return pd.DataFrame(rows, columns=[
        "证券代码", "证券简称", "总股本", "流通股本", "上市日期", "所属行业", "地区", "报告日期",
    ])


def test_csv_columns_are_tushare_compatible():
    assert mod.CSV_COLUMNS == EXPECTED_COLUMNS
    assert mod.OUTPUT_FILENAME == "stock_list_bse.csv"


def test_default_output_dir_is_data_stock_index_catalog():
    expected = get_repo_root() / "data" / "stock_index_catalog"
    assert mod.OUTPUT_DIR.resolve() == expected.resolve()


def test_normalize_date_preserves_and_converts():
    assert mod.normalize_date("2020-12-23") == "2020-12-23"
    assert mod.normalize_date("20201223") == "2020-12-23"
    assert mod.normalize_date("") == ""
    assert mod.normalize_date("NaT") == ""
    assert mod.normalize_date("20260230") == "20260230"  # 非法日期不猜测


def test_build_rows_maps_bj_and_filters():
    df = _dataframe([
        ["920000", "安徽凤凰", 1, 1, "2020-12-23", "汽车制造业", "安徽省", "2026-11-10"],
        ["830799", "价值在线", 1, 1, "2015-01-01", "", "", "2026-11-10"],
        ["920000", "安徽凤凰重复", 1, 1, "2020-12-23", "", "", "2026-11-10"],  # 重复，跳过
        ["", "空代码", 1, 1, "2020-12-23", "", "", "2026-11-10"],            # 空代码，跳过
        ["ABC", "非数字", 1, 1, "2020-12-23", "", "", "2026-11-10"],          # 非数字，跳过
        ["430047", "诺思兰德", 1, 1, "NaT", "", "", "2026-11-10"],           # NaT -> 空
    ])

    rows = mod.build_rows(df)

    assert [r["ts_code"] for r in rows] == ["430047.BJ", "830799.BJ", "920000.BJ"]
    assert rows[0]["name"] == "诺思兰德"
    assert rows[0]["list_date"] == ""  # NaT 被清空
    assert rows[1]["list_date"] == "2015-01-01"
    assert rows[2]["list_date"] == "2020-12-23"
    assert all(r["exchange"] == "BSE" for r in rows)
    assert all(r["market"] == "北交所" for r in rows)
    assert all(r["list_status"] == "L" for r in rows)
    assert rows[2]["area"] == "安徽省"
    assert rows[2]["industry"] == "汽车制造业"


def test_save_csv_writes_utf8_sig_and_is_readable(tmp_path):
    df = _dataframe([["920000", "安徽凤凰", 1, 1, "2020-12-23", "汽车制造业", "安徽省", "2026-11-10"]])
    rows = mod.build_rows(df)

    path = mod.save_csv(rows, tmp_path)

    assert path == tmp_path / "stock_list_bse.csv"
    assert path.read_bytes().startswith(b"\xef\xbb\xbf")  # utf-8-sig BOM
    with open(path, encoding="utf-8-sig", newline="") as handle:
        loaded = list(csv.DictReader(handle))
    assert len(loaded) == 1
    assert loaded[0]["ts_code"] == "920000.BJ"
    assert loaded[0]["name"] == "安徽凤凰"
    assert loaded[0]["list_date"] == "2020-12-23"
    assert loaded[0]["exchange"] == "BSE"


def test_main_writes_csv_without_empty_output(tmp_path):
    df = _dataframe([
        ["920000", "安徽凤凰", 1, 1, "2020-12-23", "汽车制造业", "安徽省", "2026-11-10"],
        ["830799", "价值在线", 1, 1, "2015-01-01", "", "", "2026-11-10"],
    ])

    from unittest.mock import patch

    with patch.object(mod, "query_akshare", return_value=df):
        assert mod.main(["--output-dir", str(tmp_path)]) == 0

    assert (tmp_path / "stock_list_bse.csv").is_file()
