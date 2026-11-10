#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把指定市场的股票 CSV **增量合并**到前端搜索索引 ``stocks.index.json``。

与 generate_index_from_csv.py 的区别
------------------------------------
- ``generate_index_from_csv.py`` 是「重建」：按市场读取全部 CSV，全量覆盖写索引；
  缺哪份 CSV 就丢哪个市场（当前只跑 baostock 会把 31678 条砍到 5284 条）。
- 本脚本是「打补丁」：保留现有索引的每一条记录，只做两件事：
    1. **加条目**：CSV 有、索引没有的 ``canonicalCode`` → 生成完整 11 列记录，
       按市场插入到所属分段末尾，不追加到数组最末尾；
    2. **补字段缺省值**：现有记录不足 11 列、或某些列为空 → 用 CSV 数据补齐；
       非空字段一律保留，不覆盖（除非显式给 ``--update-existing``）。

写入索引前会把 ``listDate`` 统一规范化为 ``YYYY-MM-DD``：Tushare CSV 的
``YYYYMMDD`` 与 baostock CSV 的 ``YYYY-MM-DD`` 可以混用，索引只输出后者。

因此只传 ``--cn`` 也能安全更新，不会让 HK / US / JP / KR 缩水。

用法
----
    # 只合并沪深（CSV 用默认路径），先看报告
    python3 scripts/stock_index_catalog/merge_stock_index_from_csv.py --cn --dry-run

    # 多个市场 + 自定义 CSV 路径，实际写盘
    python3 scripts/stock_index_catalog/merge_stock_index_from_csv.py \\
        --cn data/stock_index_catalog/stock_list_cn.csv --bse --jp

    # 写盘并同步其它索引副本
    python3 scripts/stock_index_catalog/merge_stock_index_from_csv.py --cn --sync-copies

参数
----
    ``--cn / --bse / --hk / --us / --jp / --kr``
        不带值时使用该市场的默认 CSV 路径；带值时使用指定文件。
        默认路径：
          - CN/BSE/HK/US -> ``data/stock_index_catalog/stock_list_<market>.csv``
          - JP/KR       -> ``scripts/stock_index_catalog/static_markets/stock_list_<market>.csv``
    ``--index PATH``       目标索引，默认 ``apps/hrs-web/public/stocks.index.json``
    ``--dry-run``          只打印合并报告，不写盘
    ``--sync-copies``      写盘后同步到其余索引副本（仅覆盖已存在的副本）
    ``--update-existing``  允许用 CSV 覆盖已有非空字段（默认关闭，只补缺省）

CSV 必需列
----------
- CN / BSE / HK / JP / KR：``ts_code``、``name``（``symbol`` 可选）
- US：``ts_code``、``enname``（生成器的美股分支读 ``enname``）
- 可选列：``aliases``、``list_date``、``delist_date`` 等；``list_date`` 统一为
  ``YYYY-MM-DD`` 后写入第 11 列（``YYYYMMDD`` 会自动转换）。

字段顺序严格遵循 ``stockIndexSchema.ts`` 的 11 列约定；新增记录由生成器的
``parse_stock_row`` / ``build_stock_index`` / ``compress_index`` 产出，保证格式一致。
市场分段顺序与生成器的 ``load_tushare_data`` 一致：CN → BSE → HK → US → JP → KR。
"""

import argparse
import csv
import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_index_from_csv as g  # noqa: E402
import index_sort  # noqa: E402  # 合并后按规范排序（与 reorder 共用同一套规则）

# stockIndexSchema.ts 的列数（末列为 listDate）
INDEX_COLUMNS = 11
MARKET_COLUMN = 6
LIST_DATE_COLUMN = 10

# 与 generate_index_from_csv.load_tushare_data 的 market_files 顺序一致。
# 现有索引里 CN/BSE、JP/KR 存在交错段，按市场分段插入时以此顺序为准。
MARKET_ORDER = ("CN", "BSE", "HK", "US", "JP", "KR")

DEFAULT_INDEX = REPO_ROOT / "apps" / "hrs-web" / "public" / "stocks.index.json"
SEED_DIR = SCRIPT_DIR / "static_markets"

# 参数名 -> (索引里的 market 值, 默认 CSV 文件名)
MARKETS: Dict[str, Tuple[str, str]] = {
    "cn": ("CN", "stock_list_cn.csv"),
    "bse": ("BSE", "stock_list_bse.csv"),
    "hk": ("HK", "stock_list_hk.csv"),
    "us": ("US", "stock_list_us.csv"),
    "jp": ("JP", "stock_list_jp.csv"),
    "kr": ("KR", "stock_list_kr.csv"),
}

# refresh_stock_index.py 只同步 dist-web 一份，这里列出其余副本供 --sync-copies 使用。
# 注意：data/cache 是运行时远程缓存（被 src/data/stock_index_loader 优先读取），保留；
# src/data/cache 是历史遗留、无任何代码读取，已从同步列表移除。
COPY_TARGETS = [
    "dist-web/static/stocks.index.json",
    "dist-desktop/frontend/static/stocks.index.json",
    "data/cache/stocks.index.json",
    "apps/hrs-desktop/dist/mac-arm64/HermesX.app/Contents/Resources/frontend/static/stocks.index.json",
]

# argparse: 未指定市场时值为 None；只给开关不带路径时取此哨兵值。
USE_DEFAULT = "__DEFAULT__"


def market_order_index(market: str) -> int:
    """返回市场在分段顺序中的下标；未知市场排在最后。"""
    try:
        return MARKET_ORDER.index(market)
    except ValueError:
        return len(MARKET_ORDER)


def insertion_anchors(existing_rows: List[List], markets: Iterable[str]) -> Dict[str, int]:
    """为每个市场计算新增条目的插入位置（下标）。

    锚点 = 该市场在现有数组中**最后一次出现**位置 + 1。用「最后一次」而非
    「首次」，是因为旧版单份 A 股 CSV 按代码排序，索引里 CN/BSE 交错 178 段、
    JP/KR 也有交错；这样新增条目仍落在本市场块内，不会被堆到数组最末尾。

    现有数组里没有该市场时，退到 ``MARKET_ORDER`` 中前一个存在市场的锚点；
    前面也没有则插到数组开头。
    """
    last_pos: Dict[str, int] = {}
    for position, row in enumerate(existing_rows):
        market = row[MARKET_COLUMN] if len(row) > MARKET_COLUMN else ""
        last_pos[market] = position + 1

    anchors: Dict[str, int] = {}
    for market in markets:
        if market in last_pos:
            anchors[market] = last_pos[market]
            continue
        order = market_order_index(market)
        anchors[market] = next(
            (last_pos[candidate] for candidate in reversed(MARKET_ORDER[:order])
             if candidate in last_pos),
            0,
        )
    return anchors


def insert_additions_by_market(
    existing_rows: List[List], additions: List[List]
) -> Tuple[List[List], Dict[str, int]]:
    """把新增条目按市场分段插入，返回最终记录与各市场插入位置。

    从锚点大的位置往前插，避免先插入的条目影响后续下标；锚点相同时按
    ``MARKET_ORDER`` 逆序插入，保证同位置的多段仍符合市场顺序。
    """
    buckets: Dict[str, List[List]] = {}
    for row in additions:
        buckets.setdefault(row[MARKET_COLUMN], []).append(row)

    if not buckets:
        return list(existing_rows), {}

    anchors = insertion_anchors(existing_rows, buckets.keys())
    result = list(existing_rows)
    for market in sorted(
        buckets,
        key=lambda name: (-anchors[name], -market_order_index(name)),
    ):
        result[anchors[market]:anchors[market]] = buckets[market]
    return result, anchors


def default_csv_path(market_key: str) -> Path:
    """返回某市场的默认 CSV 路径。JP/KR 来自静态种子目录。"""
    _, filename = MARKETS[market_key]
    if market_key in ("jp", "kr"):
        return SEED_DIR / filename
    return g.DEFAULT_DATA_DIR / filename


def resolve_csv(market_key: str, value: Optional[str]) -> Path:
    """把命令行值解析成实际的 CSV 路径。"""
    if value and value != USE_DEFAULT:
        return Path(value).expanduser()
    return default_csv_path(market_key)


def load_market_rows(market_key: str, csv_path: Path) -> Tuple[Dict[str, List], int, int]:
    """读单个市场的 CSV，转成 ``{canonicalCode: 11列元组}``。

    Returns:
        (按代码索引的记录, 解析成功条数, 跳过条数)
    """
    market_name = MARKETS[market_key][0]
    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV 不存在：{csv_path}")

    parsed = []
    skipped = 0
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as handle:
        for raw in csv.DictReader(handle):
            # DictReader 在列数不足时给 None，统一清洗成字符串，避免 .strip() 崩溃。
            row = {
                key: (value.strip() if isinstance(value, str) else ("" if value is None else str(value)))
                for key, value in raw.items()
                if key is not None
            }
            item = g.parse_stock_row(row, preferred_market=market_name)
            if item is None:
                skipped += 1
                continue
            parsed.append(item)

    compressed = g.compress_index(g.build_stock_index(parsed))
    return {record[0]: record for record in compressed}, len(parsed), skipped


def merge_rows(
    existing_rows: List[List],
    market_rows: Dict[str, Dict[str, List]],
    update_existing: bool = False,
) -> Tuple[List[List], int, int, int, Dict[str, Dict[str, int]]]:
    """增量合并。

    - 先把所有现有记录补齐到 ``INDEX_COLUMNS`` 列（缺失位补空串），并把
      ``listDate`` 统一规范化为 ``YYYY-MM-DD``（格式修正，不算覆盖数据）。
    - CSV 中已存在的代码：只填「缺失或为空」的列；``update_existing`` 为真时才覆盖非空值。
    - CSV 中不存在于索引的代码：生成完整 11 列记录，按市场插入所属分段末尾。

    Returns:
        (最终记录, 填补空字段数, 覆盖非空字段数, 规范化日期数, 各市场统计)
    """
    normalized = 0
    for row in existing_rows:
        while len(row) < INDEX_COLUMNS:
            row.append("")
        canonical = g.normalize_list_date(row[LIST_DATE_COLUMN])
        if canonical != row[LIST_DATE_COLUMN]:
            row[LIST_DATE_COLUMN] = canonical
            normalized += 1

    existing_by_code = {row[0]: row for row in existing_rows}
    additions: List[List] = []
    filled = 0
    updated = 0
    stats: Dict[str, Dict[str, int]] = {}

    for market_key, rows_by_code in market_rows.items():
        new_count = 0
        existing_count = 0
        for code, new_row in rows_by_code.items():
            current = existing_by_code.get(code)
            if current is None:
                additions.append(new_row)
                existing_by_code[code] = new_row
                new_count += 1
                continue

            existing_count += 1
            for column in range(INDEX_COLUMNS):
                current_value = current[column] if column < len(current) else ""
                new_value = new_row[column] if column < len(new_row) else ""
                if new_value in (None, ""):
                    continue

                is_empty = current_value is None or current_value == ""
                if is_empty:
                    current[column] = new_value
                    filled += 1
                elif update_existing and new_value != current_value:
                    current[column] = new_value
                    updated += 1

        stats[market_key] = {"new": new_count, "existing": existing_count}

    final_rows, anchors = insert_additions_by_market(existing_rows, additions)
    for market_key, counts in stats.items():
        counts["anchor"] = anchors.get(MARKETS[market_key][0], 0)

    return final_rows, filled, updated, normalized, stats


def write_index(path: Path, rows: List[List]) -> None:
    """沿用生成器的紧凑排版（``[`` + 每条一行 + ``]``）原子写入。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as handle:
        handle.write("[\n")
        for index, item in enumerate(rows):
            json.dump(item, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write(",\n" if index < len(rows) - 1 else "\n")
        handle.write("]\n")
    os.replace(tmp_path, path)


def sync_copies(source: Path) -> List[Path]:
    """把写好的索引同步到其余已存在的副本。"""
    synced = []
    for relative in COPY_TARGETS:
        target = REPO_ROOT / relative
        if target.is_file() and target.resolve() != source.resolve():
            shutil.copyfile(source, target)
            synced.append(target)
    return synced


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="按市场把 CSV 增量合并到 stocks.index.json（加条目 / 补字段缺省值）"
    )
    for key, (market_name, filename) in MARKETS.items():
        parser.add_argument(
            f"--{key}",
            nargs="?",
            const=USE_DEFAULT,
            default=None,
            metavar="CSV",
            help=f"合并 {market_name} 市场；不带值则用默认 {filename}",
        )
    parser.add_argument(
        "--index",
        default=str(DEFAULT_INDEX),
        help=f"目标索引文件（默认：{DEFAULT_INDEX}）",
    )
    parser.add_argument("--dry-run", action="store_true", help="只打印合并报告，不写盘")
    parser.add_argument("--sync-copies", action="store_true", help="写盘后同步其余索引副本")
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="允许用 CSV 覆盖已有非空字段（默认只补缺省值）",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    selected = {key: getattr(args, key) for key in MARKETS if getattr(args, key) is not None}
    if not selected:
        print("[错误] 至少指定一个市场参数（--cn / --bse / --hk / --us / --jp / --kr）", file=sys.stderr)
        return 2

    if not g.require_pypinyin():
        return 1

    index_path = Path(args.index).expanduser()
    if not index_path.is_file():
        print(f"[错误] 索引文件不存在：{index_path}", file=sys.stderr)
        return 1

    with open(index_path, "r", encoding="utf-8") as handle:
        existing = json.load(handle)
    if not isinstance(existing, list):
        print("[错误] 索引文件不是数组格式", file=sys.stderr)
        return 1

    original_columns = dict(Counter(len(row) for row in existing))
    print(f"目标索引：{index_path}")
    print(f"  现有 {len(existing)} 条，列数分布 {original_columns}")

    print("\n读取市场 CSV：")
    market_rows: Dict[str, Dict[str, List]] = {}
    for key, value in selected.items():
        csv_path = resolve_csv(key, value)
        try:
            rows_by_code, parsed_count, skipped = load_market_rows(key, csv_path)
        except (FileNotFoundError, OSError) as exc:
            print(f"[错误] {key.upper()}: {exc}", file=sys.stderr)
            return 1
        market_rows[key] = rows_by_code
        print(
            f"  {key.upper():<4} <- {csv_path}  "
            f"({parsed_count} 条解析成功，{skipped} 条跳过)"
        )

    rows = [list(row) for row in existing]
    final_rows, filled, updated, normalized, stats = merge_rows(
        rows, market_rows, args.update_existing
    )

    print("\n合并报告：")
    for key, counts in stats.items():
        print(
            f"  {key.upper():<4} 新增 {counts['new']} 条 / "
            f"已存在 {counts['existing']} 条"
        )
    padded = sum(1 for row in existing if len(row) < INDEX_COLUMNS)
    print(f"  补齐到 {INDEX_COLUMNS} 列：{padded} 条记录（其余已符合）")
    print(f"  填补空字段：{filled} 处；覆盖非空字段：{updated} 处")
    print(f"  规范化 listDate：{normalized} 条（YYYYMMDD → YYYY-MM-DD）")
    print(f"  新增条目：{len(final_rows) - len(existing)} 条")
    print(f"  合并后总数：{len(final_rows)} 条")

    if args.dry_run:
        print("\n[dry-run] 未写盘（排序将在写盘时应用）")
        return 0

    # 合并后按规范排序：新条目自动落入正确位置（市场分组 → 交易所 → 上市日期升序），
    # 已有记录若因补日期而需重排也会被一并纠正。
    final_rows = index_sort.sort_records(final_rows)

    backup = index_path.with_suffix(index_path.suffix + ".bak")
    shutil.copy2(index_path, backup)
    write_index(index_path, final_rows)
    print(f"  排序：已按规范重排（市场分组 → A股交易所 → 上市日期升序）")
    print(f"\n已备份：{backup}")
    print(f"已写入：{index_path}")

    with open(index_path, "r", encoding="utf-8") as handle:
        verified = json.load(handle)
    if len(verified) != len(final_rows):
        print("[错误] 写盘后校验失败", file=sys.stderr)
        return 1
    print(f"校验通过：{len(verified)} 条")

    if args.sync_copies:
        synced = sync_copies(index_path)
        print(f"已同步 {len(synced)} 份副本：")
        for path in synced:
            print(f"  - {path}")
    else:
        print("提示：未加 --sync-copies，其余索引副本仍是旧数据。")

    return 0


if __name__ == "__main__":
    sys.exit(main())
