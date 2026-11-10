"""Tests for scripts/stock_index_catalog/merge_stock_index_from_csv.py.

用 tmp_path 造小索引与 CSV，验证增量合并语义（只加不删、只补缺省、幂等）。
"""

import importlib
import json
import sys

from tests.support.paths import get_repo_root

SCRIPTS_DIR = get_repo_root() / "scripts" / "stock_index_catalog"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

mod = importlib.import_module("merge_stock_index_from_csv")

CN_CSV_HEADER = "ts_code,symbol,name,list_date\n"


def _write_csv(path, lines):
    path.write_text(CN_CSV_HEADER + "".join(lines), encoding="utf-8-sig")
    return path


def _write_csv_with_header(path, header, lines):
    path.write_text(header + "".join(lines), encoding="utf-8-sig")
    return path


def _row(code, market, list_date=""):
    return [code, code, "名称", "mingcheng", "mc", [], market, "stock", True, 100, list_date]


def _write_index(path):
    rows = [
        ["000001.SZ", "000001", "平安银行", "pinganyinhang", "payh", ["平银"], "CN", "stock", True, 100],
        ["00700.HK", "00700", "腾讯控股", "tengxunkonggu", "txkg", [], "HK", "stock", True, 100],
        ["AAPL", "AAPL", "苹果", "pingguo", "pg", [], "US", "stock", True, 100],
    ]
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("[\n")
        for index, row in enumerate(rows):
            json.dump(row, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write(",\n" if index < len(rows) - 1 else "\n")
        handle.write("]\n")
    return path


def _read_index(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def test_dry_run_reports_without_writing(tmp_path, capsys):
    index = _write_index(tmp_path / "stocks.index.json")
    csv_path = _write_csv(tmp_path / "cn.csv", ["600519.SH,600519,贵州茅台,2001-08-27\n"])
    before = index.read_bytes()

    assert mod.main(["--cn", str(csv_path), "--index", str(index), "--dry-run"]) == 0
    out = capsys.readouterr().out

    assert "新增 1 条" in out
    assert "合并后总数：4 条" in out
    assert "[dry-run] 未写盘" in out
    assert index.read_bytes() == before


def test_merge_adds_entries_pads_columns_and_keeps_other_markets(tmp_path):
    index = _write_index(tmp_path / "stocks.index.json")
    csv_path = _write_csv(
        tmp_path / "cn.csv",
        [
            "000001.SZ,000001,平安银行,1991-04-03\n",  # 已存在 -> 补 listDate
            "600519.SH,600519,贵州茅台,2001-08-27\n",  # 新增
        ],
    )

    assert mod.main(["--cn", str(csv_path), "--index", str(index)]) == 0
    rows = _read_index(index)

    assert len(rows) == 4  # 只增不删，HK / US 保留
    assert all(len(row) == mod.INDEX_COLUMNS for row in rows)
    # 合并后按规范排序：CN 内 SH(600519) 在 SZ(000001) 前，再 HK、US。
    assert [row[0] for row in rows] == [
        "600519.SH", "000001.SZ", "00700.HK", "AAPL",
    ]
    by_code = {row[0]: row for row in rows}
    assert by_code["000001.SZ"][10] == "1991-04-03"
    assert by_code["600519.SH"][2] == "贵州茅台"
    assert by_code["600519.SH"][6] == "CN"
    assert by_code["600519.SH"][10] == "2001-08-27"
    assert by_code["00700.HK"][10] == ""  # 未传 --hk，只补空列
    assert by_code["AAPL"][2] == "苹果"  # 非空字段未被覆盖


def test_merge_does_not_overwrite_non_empty_values(tmp_path):
    index = _write_index(tmp_path / "stocks.index.json")
    csv_path = _write_csv(tmp_path / "cn.csv", ["000001.SZ,000001,改名后的名称,1991-04-03\n"])

    assert mod.main(["--cn", str(csv_path), "--index", str(index)]) == 0
    by_code = {row[0]: row for row in _read_index(index)}

    assert by_code["000001.SZ"][2] == "平安银行"  # 名称非空，不覆盖
    assert by_code["000001.SZ"][10] == "1991-04-03"  # 缺失列补齐


def test_update_existing_overwrites_when_requested(tmp_path):
    index = _write_index(tmp_path / "stocks.index.json")
    csv_path = _write_csv(tmp_path / "cn.csv", ["000001.SZ,000001,改名后的名称,1991-04-03\n"])

    assert mod.main(
        ["--cn", str(csv_path), "--index", str(index), "--update-existing"]
    ) == 0
    by_code = {row[0]: row for row in _read_index(index)}

    assert by_code["000001.SZ"][2] == "改名后的名称"


def test_merge_is_idempotent(tmp_path):
    index = _write_index(tmp_path / "stocks.index.json")
    csv_path = _write_csv(tmp_path / "cn.csv", ["600519.SH,600519,贵州茅台,2001-08-27\n"])
    args = ["--cn", str(csv_path), "--index", str(index)]

    assert mod.main(args) == 0
    first = index.read_bytes()
    assert mod.main(args) == 0
    assert index.read_bytes() == first  # 第二次不重复追加、不产生变化
    assert len(_read_index(index)) == 4


def test_only_selected_markets_are_read(tmp_path, capsys):
    index = _write_index(tmp_path / "stocks.index.json")
    cn_csv = _write_csv(tmp_path / "cn.csv", ["600519.SH,600519,贵州茅台,2001-08-27\n"])
    # 故意不创建 bse.csv：若脚本误读会报错
    assert mod.main(["--cn", str(cn_csv), "--index", str(index), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "CN" in out
    assert "BSE" not in out


def test_no_market_argument_returns_error(tmp_path, capsys):
    index = _write_index(tmp_path / "stocks.index.json")
    assert mod.main(["--index", str(index)]) == 2
    assert "至少指定一个市场参数" in capsys.readouterr().err


def test_missing_csv_returns_error(tmp_path, capsys):
    index = _write_index(tmp_path / "stocks.index.json")
    assert mod.main(["--cn", str(tmp_path / "nope.csv"), "--index", str(index)]) == 1
    assert "CSV 不存在" in capsys.readouterr().err


def test_new_entries_are_inserted_into_each_market_segment(tmp_path, capsys):
    index = _write_index(tmp_path / "stocks.index.json")
    cn = _write_csv(tmp_path / "cn.csv", ["600519.SH,600519,贵州茅台,20010827\n"])
    hk = _write_csv(tmp_path / "hk.csv", ["00005.HK,00005,汇丰控股,19750401\n"])
    us = _write_csv_with_header(
        tmp_path / "us.csv",
        "ts_code,name,enname,list_date\n",
        ["TSLA,特斯拉,TESLA INC,20100629\n"],
    )

    assert mod.main(
        ["--cn", str(cn), "--hk", str(hk), "--us", str(us), "--index", str(index)]
    ) == 0
    rows = _read_index(index)

    assert [row[0] for row in rows] == [
        "600519.SH", "000001.SZ", "00005.HK", "00700.HK", "TSLA", "AAPL",
    ]
    by_code = {row[0]: row for row in rows}
    # 三个来源的 YYYYMMDD 都规范化为 YYYY-MM-DD。
    assert by_code["600519.SH"][10] == "2001-08-27"
    assert by_code["00005.HK"][10] == "1975-04-01"
    assert by_code["TSLA"][10] == "2010-06-29"
    assert by_code["000001.SZ"][10] == ""  # 未传 CSV 的现有条目只补空列
    assert "已按规范重排" in capsys.readouterr().out


def test_existing_compact_list_date_is_normalized(tmp_path, capsys):
    index = tmp_path / "stocks.index.json"
    with open(index, "w", encoding="utf-8") as handle:
        json.dump([_row("000001.SZ", "CN", "19910403")], handle, ensure_ascii=False)

    csv_path = _write_csv(
        tmp_path / "cn.csv", ["000001.SZ,000001,平安银行,19910403\n"]
    )
    assert mod.main(["--cn", str(csv_path), "--index", str(index)]) == 0
    result = _read_index(index)

    assert result[0][10] == "1991-04-03"
    assert result[0][2] == "名称"  # 非空字段未被覆盖
    assert "规范化 listDate：1 条" in capsys.readouterr().out


def test_insertion_anchors_use_last_occurrence_in_interleaved_markets():
    rows = [
        _row("C1", "CN"), _row("B1", "BSE"), _row("C2", "CN"),
        _row("H1", "HK"), _row("U1", "US"),
    ]
    anchors = mod.insertion_anchors(rows, ["CN", "BSE", "HK", "US", "JP"])

    assert anchors["CN"] == 3  # 最后一次 CN 在下标 2
    assert anchors["BSE"] == 2
    assert anchors["HK"] == 4
    assert anchors["US"] == 5
    assert anchors["JP"] == 5  # JP 不存在 -> 退到前一个存在市场 US


def test_insert_additions_by_market_keeps_existing_order():
    rows = [_row("C1", "CN"), _row("H1", "HK"), _row("U1", "US")]
    additions = [_row("U2", "US"), _row("C2", "CN"), _row("H2", "HK")]

    result, anchors = mod.insert_additions_by_market(rows, additions)

    assert [row[0] for row in result] == ["C1", "C2", "H1", "H2", "U1", "U2"]
    assert anchors == {"CN": 1, "HK": 2, "US": 3}
    assert [row[0] for row in rows] == ["C1", "H1", "U1"]  # 入参不被修改


def test_market_missing_from_index_uses_neighbor_anchor(tmp_path):
    index = tmp_path / "stocks.index.json"
    with open(index, "w", encoding="utf-8") as handle:
        json.dump([_row("C1", "CN"), _row("U1", "US")], handle, ensure_ascii=False)

    hk = _write_csv(tmp_path / "hk.csv", ["00005.HK,00005,汇丰控股,1975-04-01\n"])
    assert mod.main(["--hk", str(hk), "--index", str(index)]) == 0

    assert [row[0] for row in _read_index(index)] == ["C1", "00005.HK", "U1"]


def test_no_additions_returns_same_rows():
    rows = [_row("C1", "CN"), _row("H1", "HK")]
    result, anchors = mod.insert_additions_by_market(rows, [])
    assert [row[0] for row in result] == ["C1", "H1"]
    assert anchors == {}


def test_default_csv_paths():
    assert mod.default_csv_path("cn").name == "stock_list_cn.csv"
    assert mod.default_csv_path("bse").name == "stock_list_bse.csv"
    assert mod.default_csv_path("jp").parent.name == "static_markets"
    assert mod.default_csv_path("kr").name == "stock_list_kr.csv"
    assert mod.resolve_csv("cn", None).name == "stock_list_cn.csv"
    assert mod.resolve_csv("cn", "/tmp/custom.csv").name == "custom.csv"
