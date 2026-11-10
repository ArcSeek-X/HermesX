#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 akshare 抓取北交所(BSE)股票列表，生成 ``data/stock_index_catalog/stock_list_bse.csv``。

定位
----
``fetcher/`` 下的数据源之一。产物与 ``fetch_tushare_stock_list_all.py`` 拆出的
``stock_list_bse.csv`` **列名完全同构**，因此可被 ``generate_index_from_csv.py`` /
``merge_stock_index_from_csv.py`` 直接消费，无需改动生成器。

为什么范围是 ``bse``
--------------------
命名遵循 ``fetch + 数据源 + stock_list + 范围``；``bse`` = 北交所（``.BJ``）。
北交所代码段（``920xxx`` / ``8xxxxx`` / ``43xxxx`` / ``83xxxx`` / ``87xxxx``）统一
加 ``.BJ`` 后缀，生成器 ``determine_market()`` 据此识别为 BSE 市场。

数据源
------
``akshare.stock_info_bj_name_code()``：免费、无需 token、需要联网。

- 返回字段（中文）：``证券代码、证券简称、总股本、流通股本、上市日期、所属行业、地区、报告日期``
- 每行即为一只北交所上市公司（实测约 350+ 只）

输出
----
    data/stock_index_catalog/stock_list_bse.csv   （utf-8-sig，列名与 Tushare CSV 一致）

日期格式：akshare 的 ``上市日期`` 是 ``YYYY-MM-DD``；生成器 / 合并器写索引第 11 列
``listDate`` 时会统一规范化为 ``YYYY-MM-DD``（前端 ``stockIndex.ts`` 约定），与 baostock
的沪深产物一致，可与 Tushare 产出的其它 CSV 自由混用。

用法
----
    python3 scripts/stock_index_catalog/fetcher/fetch_akshare_stock_list_bse.py
    python3 scripts/stock_index_catalog/fetcher/fetch_akshare_stock_list_bse.py --output-dir /tmp/stock_csv

依赖
----
    pip install akshare

注意：本脚本**未登记到** ``refresh_stock_index.py`` 的 ``FETCHER_SCRIPTS``（只覆盖北交所）。
它生成的就是 ``stock_list_bse.csv`` —— 与 ``fetch_tushare_stock_list_all.py`` 拆出的同名文件
是「可互换的数据源」，二者取其一即可；单独运行本脚本会**覆盖**该文件。``refresh`` 的
``--fetch-source`` 是整条索引链路的全局源，直接接入会牵连沪深 / 港 / 美 / 日 / 韩数据，故不登记。
"""

import argparse
import csv
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence

# fetcher/ -> stock_index_catalog/ -> scripts/ -> 仓库根
# 与 generate_index_from_csv.py 的默认读取目录保持一致，改动时需同步两边。
OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "stock_index_catalog"
OUTPUT_FILENAME = "stock_list_bse.csv"

# 与 fetch_tushare_stock_list_all.py 的 stock_basic fields 完全一致，保证 CSV 可互换。
CSV_COLUMNS = [
    "ts_code", "symbol", "name", "area", "industry", "fullname", "enname",
    "cnspell", "market", "exchange", "curr_type", "list_status", "list_date",
    "delist_date", "is_hs", "act_name", "act_ent_type",
]


def normalize_date(value) -> str:
    """把 akshare 的上市日期统一为 ``YYYY-MM-DD``。

    已是目标格式、空值（含 ``NaT`` / ``nan``）或无法解析的值原样返回 / 置空，
    不丢数据。合法 ``YYYYMMDD`` 也会被转换成 ``YYYY-MM-DD``。
    """
    if value is None:
        return ""
    text = str(value).strip()
    if text in ("", "NaT", "nan", "None"):
        return ""
    if re.fullmatch(r"\d{8}", text):
        try:
            return datetime.strptime(text, "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            return text
    return text


def build_rows(df) -> List[Dict[str, str]]:
    """把 akshare 的北交所 DataFrame 映射成 Tushare 同构的 CSV 行。

    每行来自 ``stock_info_bj_name_code()`` 的结果，列名为中文：
    ``证券代码、证券简称、总股本、流通股本、上市日期、所属行业、地区、报告日期``。
    """
    rows: List[Dict[str, str]] = []
    seen = set()

    for _, record in df.iterrows():
        code = str(record.get("证券代码", "")).strip()
        name = str(record.get("证券简称", "")).strip()
        # 代码必须是 6 位纯数字（北交所号码段），否则跳过
        if not code or not name or not code.isdigit():
            continue

        ts_code = f"{code}.BJ"
        if ts_code in seen:
            continue
        seen.add(ts_code)

        row = {column: "" for column in CSV_COLUMNS}
        row.update({
            "ts_code": ts_code,
            "symbol": code,
            "name": name,
            "area": str(record.get("地区", "")).strip(),
            "industry": str(record.get("所属行业", "")).strip(),
            "market": "北交所",
            "exchange": "BSE",
            "list_status": "L",
            # 真实上市日期（YYYY-MM-DD），生成器统一规范化后写入索引第 11 列 listDate
            "list_date": normalize_date(record.get("上市日期")),
        })
        rows.append(row)

    rows.sort(key=lambda item: item["ts_code"])
    return rows


def query_akshare():
    """调用 akshare 拉取北交所列表；失败返回 None。"""
    try:
        import akshare as ak
    except ImportError:
        print("[错误] 未安装 akshare，请先执行：pip install akshare", file=sys.stderr)
        return None

    try:
        df = ak.stock_info_bj_name_code()
    except Exception as exc:  # noqa: BLE001 - 真实联网失败需向用户暴露
        print(f"[错误] akshare 获取北交所列表失败：{exc}", file=sys.stderr)
        return None

    if df is None or len(df) == 0:
        print("[错误] akshare 返回空数据，未写出文件", file=sys.stderr)
        return None
    return df


def save_csv(rows: List[Dict[str, str]], output_dir: Path) -> Path:
    """以 utf-8-sig 写出 CSV（与生成器的 DictReader 编码一致）。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / OUTPUT_FILENAME
    with open(output_path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="从 akshare 抓取北交所股票列表，生成 stock_list_bse.csv"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help=f"输出目录（默认：{OUTPUT_DIR}）",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)

    print("\n[1/2] 正在从 akshare 获取北交所股票列表...")
    df = query_akshare()
    if df is None:
        return 1
    print(f"✓ 原始数据：{len(df)} 条")

    rows = build_rows(df)
    if not rows:
        print("[错误] 过滤后没有北交所数据，未写出文件", file=sys.stderr)
        return 1

    print("\n[2/2] 正在写出 CSV...")
    output_path = save_csv(rows, args.output_dir)
    print(f"✓ 已写出 {len(rows)} 只北交所股票 -> {output_path}")
    print(f"  - 含上市日期：{sum(1 for r in rows if r['list_date'])} 只")
    return 0


if __name__ == "__main__":
    sys.exit(main())
