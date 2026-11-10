#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 stocks.index.json 按「市场分组 + A股交易所顺序 + 上市日期升序」重新整理。

排序规则（与 README §2.4、``index_sort.py`` 保持一致）：
1. 顶层市场分组顺序：A股（上证 SH → 深圳 SZ → 北交所 BJ）、HK、US、JP、KR。
2. A股内部按交易所：上海(SH) → 深圳(SZ) → 北京(BJ)。
3. 每个市场 / 交易所分组内，按上市日期 ``list_date`` 从早到晚升序；无日期的记录排在分组末尾。

排序逻辑统一由 ``index_sort.py`` 提供（``merge_stock_index_from_csv.py`` 在合并后也会自动调用它），
本脚本是**幂等**的纯重排工具，可在任意时刻把索引规范化，或修复手改 / 历史遗留的乱序。
只调整记录顺序，不改任何字段值；复用与 generate / merge 相同的紧凑排版，
因此重复执行不会改变文件内容（除顺序稳定化外）。

用法：
    python3 scripts/stock_index_catalog/reorder_stock_index.py
    python3 scripts/stock_index_catalog/reorder_stock_index.py --index /path/to/stocks.index.json
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import List, Optional, Sequence

# 让本目录下的 index_sort 可被直接运行或测试导入。
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import index_sort  # noqa: E402

DEFAULT_INDEX = (
    Path(__file__).resolve().parent.parent.parent
    / "apps" / "hrs-web" / "public" / "stocks.index.json"
)


def write_index(path: Path, rows: List[List]) -> None:
    """沿用 generate / merge 的紧凑排版（``[`` + 每条一行 + ``]``）原子写入。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as handle:
        handle.write("[\n")
        for index, item in enumerate(rows):
            json.dump(item, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write(",\n" if index < len(rows) - 1 else "\n")
        handle.write("]\n")
    os.replace(tmp_path, path)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="按市场分组与上市日期重排 stocks.index.json"
    )
    parser.add_argument(
        "--index",
        type=Path,
        default=DEFAULT_INDEX,
        help=f"索引路径（默认：{DEFAULT_INDEX}）",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    path: Path = args.index

    rows = json.load(open(path, encoding="utf-8"))
    original_count = len(rows)

    backup = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, backup)

    rows = index_sort.sort_records(rows)
    write_index(path, rows)

    verified = json.load(open(path, encoding="utf-8"))
    if len(verified) != original_count:
        print("[错误] 写盘后条数不一致", file=sys.stderr)
        return 1

    print(f"✓ 已按规范排序并写盘：{path}")
    print(f"  - 备份：{backup}")
    print(f"  - 记录数：{original_count}（仅调整顺序，字段未变）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
