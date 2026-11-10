#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 baostock 抓取沪深 A 股列表，生成 ``data/stock_index_catalog/stock_list_cn.csv``。

定位
----
``fetcher/`` 下的数据源之一。产物与 Tushare 抓取器的沪深部分
（``fetch_tushare_stock_list_all.py`` -> ``stock_list_cn.csv``）**列名完全同构**，
因此可被 ``generate_index_from_csv.py`` 直接消费，无需改动生成器。

为什么范围是 ``cn``
--------------------
命名遵循 ``fetch + 数据源 + stock_list + 范围``；``cn`` = 沪深（``.SH`` / ``.SZ``）。
baostock 不收录北交所（``.BJ`` / ``920xxx``），北交所由 ``stock_list_bse.csv`` 负责，
本脚本不会产出该文件。

数据源
------
``baostock.query_stock_basic()``：免费、无需 token、需要联网。

- 返回字段：``code, code_name, ipoDate, outDate, type, status``
- 过滤 ``type=1``（股票）且 ``status=1``（正常上市）→ 沪深 A 股
  （实测只含 ``60`` / ``68`` / ``00`` / ``30`` 号码段，无 B 股、指数、退市股）
- ``ipoDate`` 即**真实上市日期**，格式 ``YYYY-MM-DD``，可直接写入 ``list_date``

输出
----
    data/stock_index_catalog/stock_list_cn.csv   （utf-8-sig，列名与 Tushare CSV 一致）

日期格式：baostock 的 ``ipoDate`` 是 ``YYYY-MM-DD``，Tushare 的 ``list_date``
是 ``YYYYMMDD``。CSV 各自保留源格式，但生成器 / 合并器在写索引第 11 列
``listDate`` 时会统一规范化为 ``YYYY-MM-DD``（前端 ``stockIndex.ts`` 约定），
因此本脚本的产物**可以与 Tushare 产出的其它 CSV 自由混用**。

用法
----
    python3 scripts/stock_index_catalog/fetcher/fetch_baostock_stock_list_cn.py
    python3 scripts/stock_index_catalog/fetcher/fetch_baostock_stock_list_cn.py --output-dir /tmp/stock_csv

依赖
----
    pip install baostock

注意：本脚本**未登记到** ``refresh_stock_index.py`` 的 ``FETCHER_SCRIPTS``。
原因是它只覆盖沪深，而 ``refresh`` 的 ``--fetch-source`` 是整条索引链路的全局源，
直接接入会牵连港/美/日/韩数据。请单独运行本脚本生成 CSV 后：补齐其它市场 CSV
走 ``generate_index_from_csv.py`` 全量重建；只有沪深这一份时改走
``merge_stock_index_from_csv.py`` 增量合并，不要直接全量重建。
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

# fetcher/ -> stock_index_catalog/ -> scripts/ -> 仓库根
# 与 generate_index_from_csv.py 的默认读取目录保持一致，改动时需同步两边。
OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "stock_index_catalog"
OUTPUT_FILENAME = "stock_list_cn.csv"

# 与 fetch_tushare_stock_list_all.py 的 stock_basic fields 完全一致，保证 CSV 可互换。
CSV_COLUMNS = [
    "ts_code", "symbol", "name", "area", "industry", "fullname", "enname",
    "cnspell", "market", "exchange", "curr_type", "list_status", "list_date",
    "delist_date", "is_hs", "act_name", "act_ent_type",
]

# baostock code 前缀 -> (ts_code 后缀, Tushare exchange)
EXCHANGE_PREFIX = {
    "sh": ("SH", "SSE"),
    "sz": ("SZ", "SZSE"),
}


def convert_code(code: str) -> Optional[Tuple[str, str, str]]:
    """把 baostock 的 ``sh.600519`` 转成 ``(600519.SH, 600519, SSE)``。

    非 ``sh.`` / ``sz.`` 前缀返回 None——这是保证范围严格为沪深（cn）的关键，
    避免把北交所或其它证券类型写进本文件。
    """
    raw = (code or "").strip().lower()
    if "." not in raw:
        return None

    prefix, symbol = raw.split(".", 1)
    if prefix not in EXCHANGE_PREFIX or not symbol:
        return None

    suffix, exchange = EXCHANGE_PREFIX[prefix]
    return f"{symbol}.{suffix}", symbol, exchange


def infer_market(symbol: str) -> str:
    """按号码段推断 Tushare ``market`` 列（生成器不消费，仅用于 CSV 可读性）。"""
    if symbol.startswith("688"):
        return "科创板"
    if symbol.startswith(("300", "301")):
        return "创业板"
    return "主板"


def build_rows(records: Iterable[Sequence[str]]) -> List[Dict[str, str]]:
    """把 baostock 查询结果过滤并映射成 Tushare 同构的 CSV 行。

    每行来自 ``rs.get_row_data()``：
    ``[code, code_name, ipoDate, outDate, type, status]``
    """
    rows: List[Dict[str, str]] = []
    seen = set()

    for record in records:
        if len(record) < 6:
            continue

        code, code_name, ipo_date, _out_date, sec_type, status = record[:6]
        # type=1 股票；status=1 正常上市（排除退市/暂停）
        if (sec_type or "").strip() != "1" or (status or "").strip() != "1":
            continue

        converted = convert_code(code)
        if converted is None:
            continue
        ts_code, symbol, exchange = converted

        if not (code_name or "").strip() or ts_code in seen:
            continue
        seen.add(ts_code)

        row = {column: "" for column in CSV_COLUMNS}
        row.update({
            "ts_code": ts_code,
            "symbol": symbol,
            "name": (code_name or "").strip(),
            "market": infer_market(symbol),
            "exchange": exchange,
            "list_status": "L",
            # 真实上市日期，YYYY-MM-DD；生成器统一规范化后写入索引第 11 列 listDate
            "list_date": (ipo_date or "").strip(),
        })
        rows.append(row)

    rows.sort(key=lambda item: item["ts_code"])
    return rows


def query_baostock() -> Optional[List[Sequence[str]]]:
    """登录 baostock 并拉取证券基础信息；失败返回 None。"""
    try:
        import baostock as bs
    except ImportError:
        print("[错误] 未安装 baostock，请先执行：pip install baostock", file=sys.stderr)
        return None

    login = bs.login()
    if getattr(login, "error_code", "1") != "0":
        print(f"[错误] baostock 登录失败：{getattr(login, 'error_msg', 'unknown')}", file=sys.stderr)
        return None

    try:
        result = bs.query_stock_basic()
        if getattr(result, "error_code", "1") != "0":
            print(f"[错误] query_stock_basic 失败：{getattr(result, 'error_msg', 'unknown')}", file=sys.stderr)
            return None

        records: List[Sequence[str]] = []
        while result.error_code == "0" and result.next():
            records.append(result.get_row_data())
        return records
    except Exception as exc:
        print(f"[错误] 读取 baostock 数据失败：{exc}", file=sys.stderr)
        return None
    finally:
        bs.logout()


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
        description="从 baostock 抓取沪深 A 股列表，生成 stock_list_cn.csv"
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

    print("\n[1/2] 正在从 baostock 获取证券基础信息...")
    records = query_baostock()
    if records is None:
        return 1
    print(f"✓ 原始数据：{len(records)} 条")

    rows = build_rows(records)
    if not rows:
        print("[错误] 过滤后没有沪深 A 股数据，未写出文件", file=sys.stderr)
        return 1

    print("\n[2/2] 正在写出 CSV...")
    output_path = save_csv(rows, args.output_dir)
    exchanges: Dict[str, int] = {}
    for row in rows:
        exchanges[row["exchange"]] = exchanges.get(row["exchange"], 0) + 1
    print(f"✓ 已写出 {len(rows)} 只沪深 A 股 -> {output_path}")
    for exchange, count in sorted(exchanges.items()):
        print(f"  - {exchange}: {count} 只")
    print(f"  - 含上市日期：{sum(1 for r in rows if r['list_date'])} 只")
    return 0


if __name__ == "__main__":
    sys.exit(main())
