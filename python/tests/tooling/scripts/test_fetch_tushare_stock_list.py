# -*- coding: utf-8 -*-
"""Tests for scripts/stock_index_catalog/fetcher/fetch_tushare_stock_list_all A-share rt_k fix flow.
测试获取Tusharestock列表相关功能测试
"""

from __future__ import annotations

import importlib
import sys
import types
from unittest.mock import MagicMock, patch

import pandas as pd

from tests.support.paths import get_repo_root

ROOT = get_repo_root()
SCRIPTS_DIR = ROOT / "scripts" / "stock_index_catalog" / "fetcher"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

if "dotenv" not in sys.modules:
    dotenv_stub = types.ModuleType("dotenv")
    dotenv_stub.load_dotenv = lambda *args, **kwargs: None
    # conftest 的 autouse fixture 会触发 src.config.settings 导入 dotenv_values；
    # 桩需提供该函数，否则同进程收集其它测试模块时报 ImportError。
    dotenv_stub.dotenv_values = lambda *args, **kwargs: {}
    sys.modules["dotenv"] = dotenv_stub

if "tushare" not in sys.modules:
    tushare_stub = types.ModuleType("tushare")
    tushare_stub.pro_api = lambda *args, **kwargs: MagicMock()
    sys.modules["tushare"] = tushare_stub

fetch_tushare_stock_list_all = importlib.import_module("fetch_tushare_stock_list_all")


def test_should_fix_a_stock_name_matches_status_prefixes():
    assert fetch_tushare_stock_list_all.should_fix_a_stock_name("XD西藏药")
    assert fetch_tushare_stock_list_all.should_fix_a_stock_name("XR浦东建")
    assert fetch_tushare_stock_list_all.should_fix_a_stock_name("DR罗曼股")
    assert fetch_tushare_stock_list_all.should_fix_a_stock_name("N惠康")
    assert fetch_tushare_stock_list_all.should_fix_a_stock_name("C天海")
    assert not fetch_tushare_stock_list_all.should_fix_a_stock_name("平安银行")
    assert not fetch_tushare_stock_list_all.should_fix_a_stock_name("ST罗顿")
    assert not fetch_tushare_stock_list_all.should_fix_a_stock_name("*ST铖昌")


def test_fix_a_stock_names_with_rt_k_replaces_candidate_names():
    api = MagicMock()
    source_df = pd.DataFrame(
        {
            "ts_code": ["000001.SZ", "600848.SH", "300001.SZ"],
            "name": ["XD西藏药", "平安银行", "N惠康"],
        }
    )

    with patch.object(
        fetch_tushare_stock_list_all,
        "fetch_rt_k_names",
        return_value={"000001.SZ": "西藏药", "300001.SZ": "惠康"},
    ) as fetch_rt_k_names:
        fixed_df = fetch_tushare_stock_list_all.fix_a_stock_names_with_rt_k(api, source_df)

    assert fixed_df.loc[fixed_df["ts_code"] == "000001.SZ", "name"].iloc[0] == "西藏药"
    assert fixed_df.loc[fixed_df["ts_code"] == "600848.SH", "name"].iloc[0] == "平安银行"
    assert fixed_df.loc[fixed_df["ts_code"] == "300001.SZ", "name"].iloc[0] == "惠康"
    fetch_rt_k_names.assert_called_once_with(api, ["000001.SZ", "300001.SZ"])


def test_fetch_rt_k_names_batches_and_collects_results():
    api = MagicMock()
    api.rt_k.return_value = pd.DataFrame(
        {
            "ts_code": ["000001.SZ", "300001.SZ"],
            "name": ["西藏药", "惠康"],
            "close": [1.0, 2.0],
            "pre_close": [1.0, 2.0],
            "trade_time": ["10:00:00", "10:00:00"],
        }
    )

    with patch.object(fetch_tushare_stock_list_all, "random_sleep") as random_sleep:
        name_map = fetch_tushare_stock_list_all.fetch_rt_k_names(api, ["000001.SZ", "300001.SZ"])

    assert name_map == {"000001.SZ": "西藏药", "300001.SZ": "惠康"}
    api.rt_k.assert_called_once_with(
        ts_code="000001.SZ,300001.SZ",
        fields="ts_code,name,close,pre_close,trade_time",
    )
    random_sleep.assert_not_called()


def test_main_default_flow_writes_split_a_stock_files():
    api = MagicMock()
    a_df = pd.DataFrame({"ts_code": ["000001.SZ"], "name": ["平安银行"]})
    hk_df = pd.DataFrame({"ts_code": ["00001.HK"], "name": ["长和"]})
    us_df = pd.DataFrame({"ts_code": ["AAPL"], "name": ["苹果"]})
    expected_cn, expected_bse = fetch_tushare_stock_list_all.split_a_stock_list(a_df)

    with (
        patch.object(fetch_tushare_stock_list_all, "get_tushare_api", return_value=api),
        patch.object(fetch_tushare_stock_list_all, "fetch_a_stock_list", return_value=a_df) as fetch_a,
        patch.object(fetch_tushare_stock_list_all, "save_to_csv") as save_to_csv,
        patch.object(fetch_tushare_stock_list_all, "fetch_hk_stock_list", return_value=hk_df) as fetch_hk,
        patch.object(fetch_tushare_stock_list_all, "fetch_us_stock_list", return_value=us_df) as fetch_us,
        patch.object(fetch_tushare_stock_list_all, "generate_data_documentation") as generate_doc,
        patch.object(fetch_tushare_stock_list_all, "random_sleep") as random_sleep,
        patch.object(fetch_tushare_stock_list_all, "fix_a_stock_names_with_rt_k") as fix_a_stock_names,
    ):
        exit_code = fetch_tushare_stock_list_all.main([])

    assert exit_code == 0
    fetch_a.assert_called_once_with(api)

    saved = {call.args[1]: call.args[0] for call in save_to_csv.call_args_list}
    assert set(saved) == {
        "stock_list_cn.csv", "stock_list_bse.csv", "stock_list_hk.csv", "stock_list_us.csv"
    }
    pd.testing.assert_frame_equal(saved["stock_list_cn.csv"], expected_cn)
    pd.testing.assert_frame_equal(saved["stock_list_bse.csv"], expected_bse)

    fetch_hk.assert_called_once_with(api)
    fetch_us.assert_called_once_with(api)
    fix_a_stock_names.assert_not_called()

    generate_doc.assert_called_once()
    doc = generate_doc.call_args
    pd.testing.assert_frame_equal(doc.args[0], expected_cn)
    pd.testing.assert_frame_equal(doc.args[1], expected_bse)
    assert doc.args[2] is hk_df
    assert doc.args[3] is us_df
    assert doc.kwargs == {"cn_title": "A股沪深列表"}
    assert random_sleep.call_count == 2


def test_main_a_rk_flow_only_fixes_cn_and_keeps_bse_raw():
    api = MagicMock()
    a_df = pd.DataFrame({
        "ts_code": ["000001.SZ", "920000.BJ"],
        "name": ["XD西藏药", "XD北交股"],
    })
    fixed_df = pd.DataFrame({"ts_code": ["000001.SZ"], "name": ["西藏药"]})
    hk_df = pd.DataFrame({"ts_code": ["00001.HK"], "name": ["长和"]})
    us_df = pd.DataFrame({"ts_code": ["AAPL"], "name": ["苹果"]})
    expected_cn, expected_bse = fetch_tushare_stock_list_all.split_a_stock_list(a_df)

    with (
        patch.object(fetch_tushare_stock_list_all, "get_tushare_api", return_value=api),
        patch.object(fetch_tushare_stock_list_all, "fetch_a_stock_list", return_value=a_df) as fetch_a,
        patch.object(fetch_tushare_stock_list_all, "fix_a_stock_names_with_rt_k", return_value=fixed_df) as fix_a_stock_names,
        patch.object(fetch_tushare_stock_list_all, "save_to_csv") as save_to_csv,
        patch.object(fetch_tushare_stock_list_all, "fetch_hk_stock_list", return_value=hk_df) as fetch_hk,
        patch.object(fetch_tushare_stock_list_all, "fetch_us_stock_list", return_value=us_df) as fetch_us,
        patch.object(fetch_tushare_stock_list_all, "generate_data_documentation") as generate_doc,
        patch.object(fetch_tushare_stock_list_all, "random_sleep") as random_sleep,
    ):
        exit_code = fetch_tushare_stock_list_all.main(["--a-rk"])

    assert exit_code == 0
    fetch_a.assert_called_once_with(api)

    # rt_k 只收到沪深数据，不含北交所。
    fix_a_stock_names.assert_called_once()
    fix_call = fix_a_stock_names.call_args
    assert fix_call.args[0] is api
    pd.testing.assert_frame_equal(fix_call.args[1], expected_cn)
    assert "920000.BJ" not in fix_call.args[1]["ts_code"].tolist()

    saved = {call.args[1]: call.args[0] for call in save_to_csv.call_args_list}
    pd.testing.assert_frame_equal(saved["stock_list_cn.csv"], fixed_df)
    pd.testing.assert_frame_equal(saved["stock_list_bse.csv"], expected_bse)
    cn_save_call = next(
        call for call in save_to_csv.call_args_list if call.args[1] == "stock_list_cn.csv"
    )
    assert cn_save_call.args[2] == "A股沪深"

    fetch_hk.assert_called_once_with(api)
    fetch_us.assert_called_once_with(api)
    generate_doc.assert_called_once()
    doc = generate_doc.call_args
    pd.testing.assert_frame_equal(doc.args[0], fixed_df)
    pd.testing.assert_frame_equal(doc.args[1], expected_bse)
    assert doc.kwargs == {"cn_title": "A股沪深列表（修正后）"}
    assert random_sleep.call_count == 2


def test_split_a_stock_list_separates_bse_and_keeps_all_columns():
    df = pd.DataFrame({
        "ts_code": ["000001.SZ", "600519.SH", "920000.BJ", "920305.BJ"],
        "name": ["平安银行", "贵州茅台", "安徽凤凰", "纬达光电"],
        "list_date": ["19910403", "20010827", "20201223", "20221227"],
    })

    cn_df, bse_df = fetch_tushare_stock_list_all.split_a_stock_list(df)

    assert cn_df["ts_code"].tolist() == ["000001.SZ", "600519.SH"]
    assert bse_df["ts_code"].tolist() == ["920000.BJ", "920305.BJ"]
    assert list(cn_df.columns) == list(df.columns)
    assert list(bse_df.columns) == list(df.columns)


def test_split_a_stock_list_routes_unknown_suffix_to_cn_with_warning(capsys):
    df = pd.DataFrame({"ts_code": ["WEIRD.XY", "920000.BJ"], "name": ["x", "y"]})

    cn_df, bse_df = fetch_tushare_stock_list_all.split_a_stock_list(df)

    assert "WEIRD.XY" in cn_df["ts_code"].tolist()
    assert bse_df["ts_code"].tolist() == ["920000.BJ"]
    assert "警告" in capsys.readouterr().out


def test_split_a_stock_list_handles_empty_input():
    cn_df, bse_df = fetch_tushare_stock_list_all.split_a_stock_list(None)
    assert len(cn_df) == 0 and len(bse_df) == 0
