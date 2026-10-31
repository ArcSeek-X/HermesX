# -*- coding: utf-8 -*-
"""单票分时（当日）取数服务。

职责：
1. 统一对外提供「单只股票最近一个交易日的分时明细」能力，供尾盘选股分时强度过滤、
   个股 K 线页、自选股列表分时缩略图等场景复用，避免各处重复对接上游分时接口。
2. 数据源为东方财富 trends2（与参考项目 stock-sdk ``quotes.timeline`` 同源同语义），
   均价线为数据源返回的真实 VWAP（f58），不本地推导。
3. 抓取策略「直连温和为主 + 桥接回退」：
   - 直连 ``trends2/get``（JSON 端点；SSE 端点 ``trends2/sse`` 已被东财持续断连、
     不可用），带全局节流（≈3 req/s）+ 多组 CDN 主机轮换 + 温和退避，避免突发并发
     触发 push2his 限流导致级联取空；
   - 直连失败回退 stock-sdk 桥接（同一东财数据，SDK 自带限速/主机轮换/重试）。
4. 输出 KLinePoint 形态（date/open/close/high/low/volume/amount），date 已标准化为
   ``YYYY-MM-DD HH:mm:ss``，前端 KLineChart / KLineView 可直接解析渲染。

节流与并发约束：上游对 push2his 高并发限流严格（实测 16 并发会触发 IP 临时封禁），
调用方应使用有界并发（建议 ≤4），本模块的全局节流会进一步把请求间隔收敛到 ≈3 req/s。
"""
from __future__ import annotations

import logging
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

from src.application.quote.ports import IntradayTimelineBridgePort

logger = logging.getLogger(__name__)

# stock-sdk 桥接回退端口（best-effort fallback）：与 S2c name_to_code_resolver 同型，
# 未装配时优雅降级为“仅直连”，不抛异常、不拖垮主路（与既有“桥接不可用→空”语义一致）。
_bridge_port: Optional[IntradayTimelineBridgePort] = None


def set_timeline_bridge_port(port: Optional[IntradayTimelineBridgePort]) -> None:
    """装配 stock-sdk 桥接回退端口（幂等）；传 None 保持既有指向，避免部分装配互相覆盖。"""
    global _bridge_port
    if port is not None:
        _bridge_port = port


def _get_bridge_port() -> Optional[IntradayTimelineBridgePort]:
    return _bridge_port


# 东财分时 trends2：必须走 JSON 端点 /get（SSE 端点 /sse 已被东财持续断连、不可用）
_TRENDS_URL = "https://push2his.eastmoney.com/api/qt/stock/trends2/get"
_TRENDS_URLS = (
    _TRENDS_URL,
    "https://33.push2his.eastmoney.com/api/qt/stock/trends2/get",
    "https://63.push2his.eastmoney.com/api/qt/stock/trends2/get",
    "https://7.push2his.eastmoney.com/api/qt/stock/trends2/get",
)
_TRENDS_TIMEOUT = (5, 10)
_TRENDS_RETRIES = 4
# 全局节流：相邻两次 trends2 请求的最小间隔（秒），≈3 req/s，与 stock-sdk 默认限速一致
_TRENDS_MIN_INTERVAL = 0.35
# 单次失败后的退避基数（秒）：第 n 次重试前睡 _TRENDS_BACKOFF * n，避免雪上加霜
_TRENDS_BACKOFF = 1.0
_TRENDS_GATE_LOCK = threading.Lock()
_TRENDS_NEXT_TS = 0.0

_SESSION = requests.Session()
_SESSION.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
    }
)


def _safe_float(value: Any) -> Optional[float]:
    """安全转 float：None / 非数值 / NaN 一律返回 None（不依赖 pandas）。"""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if f == f else None  # f != f 即 NaN


def _round(value: Any, nd: int = 3) -> Optional[float]:
    v = _safe_float(value)
    return None if v is None else round(v, nd)


def _code_to_secid(code: str) -> str:
    """'603019' / '603019.SH' -> 东财 secid（沪市 1.xxxx，深市/北交 0.xxxx）。"""
    pure = str(code).split(".")[0].strip()
    return f"{'1' if pure.startswith('6') else '0'}.{pure}"


def _trends_throttle() -> None:
    """全局节流：跨线程保证 trends2 请求间隔不小于 _TRENDS_MIN_INTERVAL。

    调用方以线程池并发拉分时，若无节流，突发并发会触发东财 push2his 限流，一旦被限流
    所有候选一起取空 → 0 结果。用「预约下一时隙」放行：锁内只算时间、锁外睡，避免长时间
    持锁串行化。
    """
    global _TRENDS_NEXT_TS
    with _TRENDS_GATE_LOCK:
        now = time.monotonic()
        start = now if now > _TRENDS_NEXT_TS else _TRENDS_NEXT_TS
        _TRENDS_NEXT_TS = start + _TRENDS_MIN_INTERVAL
    delay = start - time.monotonic()
    if delay > 0:
        time.sleep(delay)


def _normalize_trend_date(date_str: str) -> str:
    """东财 trends2 时间串标准化：'YYYYMMDD HH:mm' 或 'YYYY-MM-DD HH:mm(:ss)'

    东财 trends2 返回的 f51 时间字段为 ``YYYYMMDD HH:mm``（无连字符），前端 KLineView
    的 parseTimelineTime 期望 ``YYYY-MM-DD HH:mm:ss``；统一在本层补齐连字符与秒，避免
    分时图因时间格式不识别而被过滤为空。
    """
    s = str(date_str).strip()
    # YYYYMMDD HH:mm(:ss) -> YYYY-MM-DD HH:mm:ss
    m = re.match(r"^(\d{4})(\d{2})(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?$", s)
    if m:
        y, mo, d, h, mi, sec = m.groups()
        return f"{y}-{mo}-{d} {h}:{mi}:{sec or '00'}"
    # YYYY-MM-DD HH:mm(:ss) -> 统一补齐秒
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?$", s)
    if m:
        y, mo, d, h, mi, sec = m.groups()
        return f"{y}-{mo}-{d} {h}:{mi}:{sec or '00'}"
    return s


def _parse_trends_payload(inner: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Optional[float], str]:
    """trends2 data → (分钟点列表, 昨收, 名称)；无 trends 返回空列表。

    每点含 date/open/close/high/low/volume/amount/avg_price；均价取数据源真实 VWAP(f58)，
    不本地推导。date 已标准化为 ``YYYY-MM-DD HH:mm:ss``，可直接给前端 KLineView 解析。
    """
    trends = inner.get("trends") or []
    if not trends:
        return [], None, ""
    points: List[Dict[str, Any]] = []
    for line in trends:
        parts = str(line).split(",")
        if len(parts) < 8:
            continue
        # f51 时间, f52 开, f53 收, f54 高, f55 低, f56 量(手), f57 额(元), f58 均价(元)
        vol_shou = _safe_float(parts[5])
        points.append(
            {
                "date": _normalize_trend_date(parts[0]),
                "open": _safe_float(parts[1]),
                "close": _safe_float(parts[2]),
                "high": _safe_float(parts[3]),
                "low": _safe_float(parts[4]),
                # 手 -> 股：与 amount(元) 同单位，保证 amount/volume = 真实均价
                "volume": vol_shou * 100.0 if vol_shou is not None else None,
                "amount": _safe_float(parts[6]),
                "avg_price": _safe_float(parts[7]),
            }
        )
    return points, _safe_float(inner.get("preClose")), str(inner.get("name") or "")


def _fetch_trends_direct(code: str) -> Tuple[List[Dict[str, Any]], Optional[float], str]:
    """直连东财 trends2 /get（温和节流 + 多 CDN 主机轮换 + 退避）拉分时。"""
    params = {
        "secid": _code_to_secid(code),
        "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
        "ndays": "1",
        "iscr": "0",
    }
    headers = {"Referer": "https://quote.eastmoney.com/"}
    last_exc: Optional[Exception] = None
    for attempt in range(_TRENDS_RETRIES):
        url = _TRENDS_URLS[attempt % len(_TRENDS_URLS)]
        _trends_throttle()
        try:
            resp = _SESSION.get(url, params=params, timeout=_TRENDS_TIMEOUT, headers=headers)
            resp.raise_for_status()
            points, pre_close, name = _parse_trends_payload(resp.json().get("data") or {})
            if points:
                return points, pre_close, name
        except Exception as e:  # pragma: no cover - 网络 / 限流兜底
            last_exc = e
        if attempt < _TRENDS_RETRIES - 1:
            time.sleep(_TRENDS_BACKOFF * (attempt + 1))
    if last_exc is not None:
        logger.debug("[Timeline] 分时直连失败 %s: %s", code, last_exc)
    return [], None, ""


def _fetch_trends_via_bridge(code: str) -> Tuple[List[Dict[str, Any]], Optional[float], str]:
    """直连失败时回退 stock-sdk 桥接（同一东财 trends2 数据，SDK 自带限速/主机轮换/重试）。

    stock-sdk 分时为 tick 线（price/avgPrice，无 OHLC），故回退路径的 open/high/low 退化为
    price、volume/amount 为累计值。
    """
    port = _get_bridge_port()
    if port is None:
        # 桥接端口未装配：与“桥接不可用”一致优雅降级（直连仍是主路径）
        return [], None, ""
    try:
        data = port.fetch_timeline(code=code)
    except Exception as exc:  # pragma: no cover - 桥接未启用 / Node 缺失等
        logger.debug("[Timeline] 分时桥接回退不可用 %s: %s", code, exc)
        return [], None, ""
    if not data:
        return [], None, ""

    points: List[Dict[str, Any]] = []
    for t in data.get("points") or []:
        price = _safe_float(t.get("close"))
        if price is None:
            continue
        points.append(
            {
                "date": _normalize_trend_date(str(t.get("date") or "")),
                "open": _safe_float(t.get("open")) if t.get("open") is not None else price,
                "close": price,
                "high": _safe_float(t.get("high")) if t.get("high") is not None else price,
                "low": _safe_float(t.get("low")) if t.get("low") is not None else price,
                "volume": _safe_float(t.get("volume")),
                "amount": _safe_float(t.get("amount")),
                "avg_price": _safe_float(t.get("avg_price")),
            }
        )
    if not points:
        return [], None, ""
    return points, _safe_float(data.get("preClose")), str(data.get("name") or "")


def fetch_intraday_trends(code: str) -> Tuple[List[Dict[str, Any]], Optional[float], str]:
    """拉取最近一个交易日分时，返回 (分钟点列表, 昨收, 名称)。

    策略「直连温和为主 + 桥接回退」：先直连东财 trends2 /get（温和节流避免限流），
    直连失败再回退 stock-sdk 桥接（同一东财数据）。休市日两者均返回最近一个已收盘
    交易日的全天分时。
    """
    points, pre_close, name = _fetch_trends_direct(code)
    if points:
        return points, pre_close, name
    return _fetch_trends_via_bridge(code)


def build_timeline_points(bars: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    将分钟 bar 转为 KLinePoint 形态的分时点，供前端 KLineChart / KLineView 直接渲染。

    字段：date(YYYY-MM-DD HH:mm(:ss))、open、close、high、low、volume、amount。
    前端 KLineChart / KLineView 内部会用累计 amount/volume 复算均价线（VWAP）。
    """
    points: List[Dict[str, Any]] = []
    for b in bars:
        close = _safe_float(b.get("close"))
        if close is None:
            continue
        points.append(
            {
                "date": str(b.get("date") or ""),
                "open": _round(b.get("open")) if b.get("open") is not None else close,
                "close": round(close, 3),
                "high": _round(b.get("high")) if b.get("high") is not None else close,
                "low": _round(b.get("low")) if b.get("low") is not None else close,
                "volume": _safe_float(b.get("volume")),
                "amount": _safe_float(b.get("amount")),
            }
        )
    return points


def fetch_intraday_timeline(code: str, limit: int = 240) -> Dict[str, Any]:
    """返回单只股票的完整分时明细（KLinePoint 形态，供前端分时图渲染）。

    limit 参数仅为兼容既有 API 契约保留（trends2 一次返回全天分时）。

    Args:
        code: 股票代码（支持 600519 / 600519.SH 形式）
        limit: 兼容参数，当前不影响返回点数

    Returns:
        {"code", "name", "prev_close", "points"}；points 为 KLinePoint 形态列表
        （date/open/close/high/low/volume/amount），拉取失败时 points 为空列表。
    """
    points, prev_close, name = fetch_intraday_trends(code)
    return {
        "code": code,
        "name": name,
        "prev_close": prev_close,
        "points": build_timeline_points(points),
    }


__all__ = [
    "build_timeline_points",
    "fetch_intraday_timeline",
    "fetch_intraday_trends",
]
