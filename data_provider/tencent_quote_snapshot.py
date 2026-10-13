# -*- coding: utf-8 -*-
"""腾讯全市场行情快照。

定位：东方财富全市场快照（ak.stock_zh_a_spot_em）不可用时的回退数据源，
列名与东财快照对齐，可直接喂给尾盘选股（EOD Picker）的基础过滤。

选用腾讯的原因：
- 批量接口 http://qt.gtimg.cn/q=sz000001,sh600519,... 单次可查询多只股票，
  全市场约 5200 只需 ~90 次请求，远低于逐只拉取；
- 字段含 最新价 / 涨跌幅 / 量比 / 换手率 / 流通市值 / 成交额，
  覆盖尾盘选股基础过滤所需的全部指标（新浪全市场快照缺少量比/换手率/流通市值）；
- 休市期间（周末 / 节假日）返回的是最近一个交易日的收盘数据，
  因此尾盘选股在休市日也能以「上一个交易日」为基准运行。
"""
from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

_ENDPOINT = "http://qt.gtimg.cn/q="
_BATCH_SIZE = 60
_MAX_WORKERS = 8
_TIMEOUT = 15
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# 腾讯行情以 "~" 分隔的字段下标
_F_NAME = 1
_F_CODE = 2
_F_PRICE = 3
_F_PREV_CLOSE = 4
_F_OPEN = 5
_F_TIME = 30
_F_CHANGE_PCT = 32
_F_HIGH = 33
_F_LOW = 34
_F_VOLUME = 36       # 手
_F_AMOUNT = 37       # 万元
_F_TURNOVER = 38     # 换手率 %
_F_CIRC_MV = 44      # 流通市值（亿元）
_F_VOLUME_RATIO = 49  # 量比

_ENTRY_RE = re.compile(r'v_([A-Za-z0-9]+)="([^"]*)"')

_COLUMNS = [
    "代码",
    "名称",
    "最新价",
    "涨跌幅",
    "量比",
    "换手率",
    "流通市值",
    "成交额",
    "成交量",
    "昨收",
    "今开",
    "最高",
    "最低",
]


def _stock_index_path() -> Path:
    return Path(__file__).resolve().parent.parent / "apps" / "hrs-web" / "public" / "stocks.index.json"


def _to_tencent_symbol(full_symbol: str, code: str) -> Optional[str]:
    """'000001.SZ' -> 'sz000001'；仅支持沪深 A 股。"""
    suffix = str(full_symbol or "").split(".")[-1].lower()
    if suffix not in ("sh", "sz", "bj"):
        return None
    return f"{suffix}{code}"


def _load_a_share_symbols() -> List[str]:
    """从本地股票索引读取沪深 A 股代码列表（离线、无需网络）。"""
    path = _stock_index_path()
    if not path.exists():
        logger.warning("[腾讯快照] 本地股票索引不存在: %s", path)
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - 防御性兜底
        logger.warning("[腾讯快照] 本地股票索引解析失败: %s", exc)
        return []

    symbols: List[str] = []
    seen = set()
    for item in raw:
        if not isinstance(item, list) or len(item) < 8:
            continue
        if item[6] != "CN" or item[7] != "stock":
            continue
        symbol = _to_tencent_symbol(str(item[0]), str(item[1]))
        if symbol and symbol not in seen:
            seen.add(symbol)
            symbols.append(symbol)
    return symbols


def _to_float(value: Any) -> Optional[float]:
    try:
        text = str(value).strip()
        if not text:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def _parse_entry(fields: List[str]) -> Optional[Dict[str, Any]]:
    """解析单只股票的腾讯行情字段为快照行。"""
    if len(fields) <= _F_VOLUME_RATIO:
        return None

    code = str(fields[_F_CODE]).strip()
    name = str(fields[_F_NAME]).strip()
    price = _to_float(fields[_F_PRICE])
    if not code or not name or price is None or price <= 0:
        return None

    # 成交额：腾讯单位为万元，东财为元，统一成元以保持一致
    amount_wan = _to_float(fields[_F_AMOUNT])
    amount = None if amount_wan is None else amount_wan * 10000

    return {
        "代码": code,
        "名称": name,
        "最新价": price,
        "涨跌幅": _to_float(fields[_F_CHANGE_PCT]),
        "量比": _to_float(fields[_F_VOLUME_RATIO]),
        "换手率": _to_float(fields[_F_TURNOVER]),
        "流通市值": _to_float(fields[_F_CIRC_MV]),
        "成交额": amount,
        "成交量": _to_float(fields[_F_VOLUME]),
        "昨收": _to_float(fields[_F_PREV_CLOSE]),
        "今开": _to_float(fields[_F_OPEN]),
        "最高": _to_float(fields[_F_HIGH]),
        "最低": _to_float(fields[_F_LOW]),
    }


def _fetch_batch(symbols: List[str]) -> List[Dict[str, Any]]:
    """批量查询一批股票的行情（单次 HTTP 请求）。"""
    url = _ENDPOINT + ",".join(symbols)
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": _USER_AGENT, "Referer": "https://gu.qq.com/"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        text = resp.content.decode("gbk", errors="ignore")
    except Exception as exc:
        logger.info("[腾讯快照] 批量行情请求失败(%d只): %s", len(symbols), exc)
        return []

    rows: List[Dict[str, Any]] = []
    for _symbol, payload in _ENTRY_RE.findall(text):
        row = _parse_entry(payload.split("~"))
        if row:
            rows.append(row)
    return rows


def fetch_tencent_market_snapshot(
    batch_size: int = _BATCH_SIZE, max_workers: int = _MAX_WORKERS
) -> Optional[pd.DataFrame]:
    """返回全市场 A 股快照 DataFrame；失败或无数据返回 None。"""
    symbols = _load_a_share_symbols()
    if not symbols:
        return None

    batches = [symbols[i : i + batch_size] for i in range(0, len(symbols), batch_size)]
    rows: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(batches)))) as ex:
        for batch_rows in ex.map(_fetch_batch, batches):
            rows.extend(batch_rows)

    if not rows:
        logger.warning("[腾讯快照] 全市场行情快照为空（共 %d 只待查）", len(symbols))
        return None

    logger.info("[腾讯快照] 全市场行情快照完成: %d/%d 只", len(rows), len(symbols))
    return pd.DataFrame(rows, columns=_COLUMNS)


__all__ = ["fetch_tencent_market_snapshot"]
