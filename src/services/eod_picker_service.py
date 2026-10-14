# -*- coding: utf-8 -*-
"""
尾盘选股法（EOD Picker）服务层。

设计要点：
- 两阶段筛选：
  1) 基础过滤：直接对全市场实时快照按 流通市值 / 量比 / 当日涨幅 / 换手率 /
     排除 ST 进行向量化过滤，极快。快照优先直连东方财富 clist
     （push2.eastmoney.com，按页大小 500 顺序翻页、无随机休眠，字段与
     ak.stock_zh_a_spot_em 同源），失败依次回退腾讯批量行情、东财
     ak.stock_zh_a_spot_em；各源流通市值单位不同（元 / 亿元），统一归一化到
     亿元后再过滤。
  2) 分时强度过滤：对候选逐只拉取当日分时（东财 trends2，与参考项目
     stock-sdk quotes.timeline 同源同语义，均价线为数据源返回的真实 VWAP），
     计算「分时强度」（价格 >= 均价线的采样点占比），仅保留强度达标的股票。
- 分时强度 = Σ(price >= avg_price) / N * 100%，衡量股价在均价线上方运行的时长占比，
  是尾盘选股（一日持股）的核心指标。
- 分时点输出为 KLinePoint 形态（date/open/close/high/low/volume/amount），
  可直接喂给前端的 KLineChart（period='1m'）渲染价格线 + 均价线 + 昨收基准线。
- 有界并发：阶段 2 用线程池并发拉取分时，受 DEFAULT_CONCURRENCY 限制。
- 进度回调：通过 update_progress(progress:int, message:str) 上报阶段与各阶段百分比。
"""
from __future__ import annotations

import datetime
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# 默认筛选条件（单位：流通市值=亿元，涨幅/换手率=%，量比=倍，强度=%）
DEFAULT_FILTERS: Dict[str, Any] = {
    "circ_mv_min": 50.0,        # 流通市值下限（亿元）
    "circ_mv_max": 200.0,       # 流通市值上限（亿元），None 表示不限
    "volume_ratio_min": 1.2,    # 量比下限
    "change_pct_min": 3.0,      # 当日涨幅下限（%）
    "change_pct_max": 5.0,      # 当日涨幅上限（%）
    "turnover_rate_min": 5.0,   # 换手率下限（%）
    "turnover_rate_max": 10.0,  # 换手率上限（%）
    "exclude_st": True,         # 过滤 ST / *ST
    "strength_min": 80.0,       # 分时强度下限（%）
    "limit": 240,               # 分钟线数量
}

# 阶段 2 并发上限（与参考项目 DEFAULT_SCAN_CONCURRENCY 一致；东财 push2his 对突发
# 高并发限流严格——实测 16 并发会触发 IP 临时封禁，4 并发为安全值）
DEFAULT_CONCURRENCY = 4

# 结果分时图下采样点数（避免一次返回几十只 × 240 点的巨型 payload，详细数据走 /timeline 懒加载）
TIMELINE_DOWNSAMPLE = 48


# --------------------------------------------------------------------------- #
# 工具函数
# --------------------------------------------------------------------------- #
def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        f = float(value)
        return f if pd.notna(f) else None
    except (TypeError, ValueError):
        return None


def _round(value: Any, nd: int = 3) -> Optional[float]:
    v = _safe_float(value)
    return None if v is None else round(v, nd)


def _downsample(points: List[Dict[str, Any]], n: int) -> List[Dict[str, Any]]:
    if len(points) <= n:
        return points
    step = len(points) / n
    return [points[int(i * step)] for i in range(n)]


def _normalize_cmv(series: "pd.Series") -> "pd.Series":
    """将流通市值统一归一化到「亿元」。

    东财快照(akshare)流通市值为「元」，腾讯回退快照为「亿元」；以量级自动判定并
    归一化，避免单位不统一导致基础过滤把绝大多数股票误杀（结果数 3 vs 5 的根因）。
    """
    s = pd.to_numeric(series, errors="coerce")
    if s.notna().any() and s.max() > 1e6:
        s = s / 1e8
    return s


# --------------------------------------------------------------------------- #
# 数据源接入（懒加载，避免循环依赖与重量级 import）
# --------------------------------------------------------------------------- #
_SESSION = requests.Session()
_SESSION.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        )
    }
)

_fetcher: Any = None
_fetcher_lock = threading.Lock()


def _get_fetcher() -> Any:
    """复用 AkshareFetcher 的单例（共享其模块级全市场快照缓存）。"""
    global _fetcher
    if _fetcher is None:
        with _fetcher_lock:
            if _fetcher is None:
                from data_provider.akshare_fetcher import AkshareFetcher

                _fetcher = AkshareFetcher()
    return _fetcher


def get_realtime_quote_snapshot() -> Optional[pd.DataFrame]:
    """全市场快照：优先直连东方财富 clist，依次回退腾讯批量行情、东财 akshare。

    优先级（单源失败即降级到下一源，任一非空即返回）：
    1. 东财 clist 直连（push2.eastmoney.com，按页大小 500 顺序翻页、无随机限速），
       字段与 akshare ak.stock_zh_a_spot_em 同源，覆盖基础过滤全部指标；
    2. 腾讯批量行情（qt.gtimg.cn，每批 60 只、8 并发）无随机限速，秒级返回；
    3. 东财 ak.stock_zh_a_spot_em（AkshareFetcher，单次调用含 2~5s 随机限速），
       作为高覆盖回退（含全部 A 股、不依赖本地股票索引）。
    """
    try:
        from data_provider.eastmoney_quote_snapshot import fetch_eastmoney_market_snapshot

        em = fetch_eastmoney_market_snapshot()
        if em is not None and not (hasattr(em, "empty") and em.empty):
            logger.info("[EOD] 使用东财 clist 直连全市场快照: %d 只", len(em))
            return em
    except Exception as exc:  # pragma: no cover - 防御性兜底
        logger.warning("[EOD] 东财 clist 直连快照获取失败，回退腾讯: %s", exc)

    try:
        from data_provider.tencent_quote_snapshot import fetch_tencent_market_snapshot

        tencent = fetch_tencent_market_snapshot()
        if tencent is not None and not (hasattr(tencent, "empty") and tencent.empty):
            logger.info("[EOD] 使用腾讯全市场快照: %d 只", len(tencent))
            return tencent
    except Exception as exc:  # pragma: no cover - 防御性兜底
        logger.warning("[EOD] 腾讯全市场快照获取失败，回退东财 akshare: %s", exc)

    df = _get_fetcher().get_realtime_quote_snapshot()
    if df is not None and not (hasattr(df, "empty") and df.empty):
        return df
    return None


# 东财分时 trends2：必须走 JSON 端点 /get。SSE 端点 /sse 已被东财持续断连
# （RemoteDisconnected，实测多次无一成功），若用它作 stage-2 数据源，每只候选都会
# 取不到分时、被静默淘汰，最终 0 结果（这正是尾盘选股「参照对象有结果、本项没有」
# 的根因）。改用与 stock-sdk getTodayTimeline 同源的 /get，并做多组 CDN 主机轮换 +
# 指数退避，避免单主机被限流即整体失败。
_TRENDS_URL = "https://push2his.eastmoney.com/api/qt/stock/trends2/get"
_TRENDS_URLS = (
    _TRENDS_URL,
    "https://33.push2his.eastmoney.com/api/qt/stock/trends2/get",
    "https://63.push2his.eastmoney.com/api/qt/stock/trends2/get",
    "https://7.push2his.eastmoney.com/api/qt/stock/trends2/get",
)
_TRENDS_TIMEOUT = (5, 10)
_TRENDS_RETRIES = 4


def _code_to_secid(code: str) -> str:
    """'603019' / '603019.SH' -> 东财 secid（沪市 1.xxxx，深市/北交 0.xxxx）。"""
    pure = str(code).split(".")[0].strip()
    return f"{'1' if pure.startswith('6') else '0'}.{pure}"


def _fetch_intraday_trends(code: str) -> Tuple[List[Dict[str, Any]], Optional[float], str]:
    """拉取最近一个交易日分时（东财 trends2 /get），返回 (分钟点列表, 昨收, 名称)。

    与参考项目 stock-sdk getTodayTimeline 同源同实现：均走 JSON 端点
    ``trends2/get``（SSE 端点 ``trends2/sse`` 已被东财断连、不可用）。每点含
    date/open/close/high/low/volume/amount/avg_price，均价线直接采用数据源返回
    的真实 VWAP（f58），不再用 volume*close 推导（sina 1m 源无真实成交额，会污染
    强度口径），也不经 K 线 Manager 多源回退（避免 StockDB/新浪缺数据或限流导致
    候选被静默丢弃）。多组 CDN 主机轮换 + 指数退避抵御 push2his 对单主机/高频的
    限流。休市日自动返回最近一个已收盘交易日的全天分时。
    """
    params = {
        "secid": _code_to_secid(code),
        "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
        "ndays": "1",
        "iscr": "0",
    }
    headers = {"Referer": "https://quote.eastmoney.com/"}
    inner: Dict[str, Any] = {}
    last_exc: Optional[Exception] = None
    for attempt in range(_TRENDS_RETRIES):
        url = _TRENDS_URLS[attempt % len(_TRENDS_URLS)]
        try:
            resp = _SESSION.get(url, params=params, timeout=_TRENDS_TIMEOUT, headers=headers)
            resp.raise_for_status()
            inner = resp.json().get("data") or {}
            if inner:
                break
        except Exception as e:  # pragma: no cover - 网络 / 限流兜底
            last_exc = e
            if attempt < _TRENDS_RETRIES - 1:
                time.sleep(0.5 * (attempt + 1))
    if not inner:
        if last_exc is not None:
            logger.debug("[EOD] 分时获取失败 %s: %s", code, last_exc)
        return [], None, ""

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
                "date": parts[0],
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


# --------------------------------------------------------------------------- #
# 指标计算
# --------------------------------------------------------------------------- #
def compute_strength_trends(points: List[Dict[str, Any]]) -> float:
    """
    分时强度 = 现价 >= 数据源均价线（avg_price）的采样点占比 × 100%。

    与参考项目 calculateTimelineStrength 完全同口径：逐点比较现价与数据源
    返回的真实均价线，而非本地自算 VWAP（避免分钟源成交额缺失时口径漂移）。
    """
    count = 0
    above = 0
    for p in points:
        price = _safe_float(p.get("close"))
        avg = _safe_float(p.get("avg_price"))
        if price is None or avg is None:
            continue
        count += 1
        if price >= avg:
            above += 1
    return (above / count * 100.0) if count else 0.0


def build_timeline_points(bars: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    将分钟 bar 转为 KLinePoint 形态的分时点，供前端 KLineChart(period='1m') 直接渲染。

    字段：date(YYYY-MM-DD HH:mm(:ss))、open、close、high、low、volume、amount。
    KLineChart 内部会用累计 amount/volume 复算均价线（VWAP），与本服务强度口径一致。
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


# --------------------------------------------------------------------------- #
# 阶段 1：全市场基础过滤
# --------------------------------------------------------------------------- #
def _basic_filter(df: pd.DataFrame, filt: Dict[str, Any]) -> pd.DataFrame:
    d = df.copy()
    for col in ("涨跌幅", "量比", "换手率", "流通市值"):
        if col in d.columns:
            d[col] = pd.to_numeric(d[col], errors="coerce")

    mask = pd.Series(True, index=d.index)
    # 涨幅与量比为必填项
    mask &= d["涨跌幅"].notna() & d["量比"].notna()
    # 当日涨幅区间（上限为 None 表示不限制）
    mask &= d["涨跌幅"] >= float(filt["change_pct_min"])
    if filt.get("change_pct_max") is not None:
        mask &= d["涨跌幅"] <= float(filt["change_pct_max"])
    # 量比下限
    mask &= d["量比"] >= float(filt["volume_ratio_min"])
    # 换手率区间（上限为 None 表示不限制）
    if "换手率" in d.columns:
        tr = d["换手率"]
        mask &= tr.notna() & (tr >= float(filt["turnover_rate_min"]))
        if filt.get("turnover_rate_max") is not None:
            mask &= tr <= float(filt["turnover_rate_max"])
    # 流通市值区间（自动归一化到亿元，兼容东财「元」/腾讯「亿元」两种口径）
    if "流通市值" in d.columns:
        cmv = _normalize_cmv(d["流通市值"])
        d["_cmv_yi"] = cmv
        mask &= cmv.notna() & (cmv >= float(filt["circ_mv_min"]))
        if filt.get("circ_mv_max") is not None:
            mask &= cmv <= float(filt["circ_mv_max"])
    # 排除 ST / *ST
    if filt.get("exclude_st"):
        name = d["名称"].astype(str).str.upper()
        mask &= ~name.str.contains("ST", na=False)

    return d[mask]


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def get_eod_picker_defaults() -> Dict[str, Any]:
    """返回默认筛选条件（前端「恢复默认」按钮的数据源）。"""
    return dict(DEFAULT_FILTERS)


# --------------------------------------------------------------------------- #
# 基准交易日
# --------------------------------------------------------------------------- #
_TRADE_DATE_CACHE: Dict[str, Any] = {}


def _load_trade_calendar() -> set:
    """加载 A 股交易日历（新浪源）；失败返回空集合（回退到「跳过周末」判断）。"""
    try:
        import akshare as ak

        df = ak.tool_trade_date_hist_sina()
        return set(pd.to_datetime(df["trade_date"]).dt.date)
    except Exception as exc:  # pragma: no cover - 防御性兜底
        logger.warning("[EOD] 交易日历获取失败，回退到工作日判断: %s", exc)
        return set()


def resolve_trade_date() -> Tuple[datetime.date, bool]:
    """
    返回尾盘选股的基准交易日 (date, 是否就是今天)。

    尾盘选股本质是「以收盘数据为基准」，休市（周末 / 节假日）时应回退到
    最近的已收盘交易日，而不是因为当天不开市就报错。
    """
    today = datetime.date.today()
    if _TRADE_DATE_CACHE.get("today") == today:
        return _TRADE_DATE_CACHE["target"], _TRADE_DATE_CACHE["is_today"]

    calendar = _load_trade_calendar()
    target = today
    if calendar:
        # 最多回溯 30 天，避免日历异常时死循环
        for _ in range(30):
            if target in calendar:
                break
            target -= datetime.timedelta(days=1)
    else:
        while target.weekday() >= 5:
            target -= datetime.timedelta(days=1)

    is_today = target == today
    _TRADE_DATE_CACHE.update({"today": today, "target": target, "is_today": is_today})
    return target, is_today


def _build_result(
    stocks: List[Dict[str, Any]],
    filt: Dict[str, Any],
    total_scanned: int,
    stage2_total: int,
    trade_date: Optional[datetime.date] = None,
) -> Dict[str, Any]:
    return {
        "filters": filt,
        "total_scanned": total_scanned,
        "candidate_count": stage2_total,
        "match_count": len(stocks),
        "stocks": stocks,
        "trade_date": trade_date.isoformat() if trade_date else None,
        "generated_at": datetime.datetime.now().isoformat(),
    }


def run_eod_picker(
    filters: Optional[Dict[str, Any]] = None,
    *,
    update_progress: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, Any]:
    """
    执行尾盘选股全流程。

    Args:
        filters: 用户筛选条件（与 DEFAULT_FILTERS 同键集合，缺省用默认）。
        update_progress: 进度回调 (progress:int[0..100], message:str) -> None。
    Returns:
        结果字典（见 _build_result）。
    Raises:
        RuntimeError: 全市场快照与其回退数据源均不可用（数据源异常）。
    """
    filt = dict(DEFAULT_FILTERS)
    if filters:
        filt.update({k: v for k, v in filters.items() if k in DEFAULT_FILTERS})
    update = update_progress or (lambda p, m: None)

    # 阶段 0：确定基准交易日（休市时回退到上一个已收盘交易日）
    trade_date, _is_today = resolve_trade_date()

    # 阶段 1：全市场快照 + 基础过滤
    update(5, f"获取全市场行情快照（基准 {trade_date:%Y-%m-%d}）")
    df = get_realtime_quote_snapshot()
    if df is None or (hasattr(df, "empty") and df.empty):
        raise RuntimeError(
            f"无法获取全市场行情快照（基准交易日 {trade_date:%Y-%m-%d}）："
            "数据源暂不可用，请稍后重试"
        )

    update(15, "按基础条件过滤全市场")
    candidates = _basic_filter(df, filt)
    stage2_total = len(candidates)
    if stage2_total == 0:
        update(100, "未匹配到符合基础条件的股票")
        return _build_result(
            [], filt, total_scanned=len(df), stage2_total=0, trade_date=trade_date
        )

    update(30, f"基础过滤完成：{stage2_total} 只候选，开始计算分时强度")
    logger.debug(
        "[EOD] 阶段1候选 %d 只: %s",
        stage2_total,
        ",".join(candidates["代码"].astype(str).tolist()),
    )

    # 阶段 2：逐只分时强度过滤（有界并发）
    results: List[Dict[str, Any]] = []
    lock = threading.Lock()
    done = 0
    workers = max(1, min(DEFAULT_CONCURRENCY, stage2_total))

    def worker(row: "pd.Series") -> Optional[Dict[str, Any]]:
        code = str(row.get("代码", ""))
        name = str(row.get("名称", ""))
        points, prev_close, _name = _fetch_intraday_trends(code)
        if not points:
            return None
        strength = compute_strength_trends(points)
        if strength < float(filt["strength_min"]):
            return None
        display = build_timeline_points(points)
        return {
            "code": code,
            "name": name,
            "price": _round(row.get("最新价")),
            "change_pct": _round(row.get("涨跌幅")),
            "circ_mv": _round(row.get("_cmv_yi")),
            "volume_ratio": _round(row.get("量比")),
            "turnover_rate": _round(row.get("换手率")),
            "amount": _round(row.get("成交额")),
            "strength": round(strength, 2),
            "prev_close": _round(prev_close),
            "timeline": _downsample(display, TIMELINE_DOWNSAMPLE),
        }

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(worker, row) for _, row in candidates.iterrows()]
        for fut in as_completed(futures):
            res = fut.result()
            with lock:
                done += 1
                pct = 30 + int(60 * done / stage2_total)
                update(pct, f"分时强度计算 {done}/{stage2_total}")
            if res:
                results.append(res)

    results.sort(key=lambda x: x["strength"], reverse=True)
    update(95, f"筛选完成，命中 {len(results)} 只")
    return _build_result(
        results,
        filt,
        total_scanned=len(df),
        stage2_total=stage2_total,
        trade_date=trade_date,
    )


def fetch_intraday_timeline(
    code: str, limit: int = 240
) -> Dict[str, Any]:
    """返回单只股票的完整分时明细（KLinePoint 形态，供前端分时图懒加载 / 放大查看）。

    limit 参数仅为兼容既有 API 契约保留（trends2 一次返回全天分时）。
    """
    points, prev_close, name = _fetch_intraday_trends(code)
    return {
        "code": code,
        "name": name,
        "prev_close": prev_close,
        "points": build_timeline_points(points),
    }


__all__ = [
    "DEFAULT_FILTERS",
    "get_eod_picker_defaults",
    "run_eod_picker",
    "resolve_trade_date",
    "fetch_intraday_timeline",
    "compute_strength_trends",
    "build_timeline_points",
    "get_realtime_quote_snapshot",
]
