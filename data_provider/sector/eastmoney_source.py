# -*- coding: utf-8 -*-
"""
@file: eastmoney_source.py
@description: 板块能力东财 source，承接东财板块排行与市场总览相关 HTTP 取数。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

import requests

from data_provider.runtime.fetchers.akshare import AkshareFetcher
from data_provider.sector.source_contract import SectorDataSource, SectorRankingRequest, SectorRankingResult

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = (5, 10)
FUND_FLOW_MAX_RETRIES = 3
FUND_FLOW_MAX_WORKERS = 5

EASTMONEY_INDEX_URL = "http://push2.eastmoney.com/api/qt/ulist.np/get"
EASTMONEY_INDEX_URL_DELAY = "http://push2delay.eastmoney.com/api/qt/ulist.np/get"
EASTMONEY_MARKET_URL = "http://push2delay.eastmoney.com/api/qt/clist/get"
EASTMONEY_NORTHBOUND_URL = "https://push2.eastmoney.com/api/qt/kamt/get"
EASTMONEY_FFLOW_DAYKLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
EASTMONEY_SECTOR_FLOW_RANK_URL = "http://push2delay.eastmoney.com/api/qt/clist/get"
EASTMONEY_SECTOR_FLOW_KLINE_URL = "http://push2his.eastmoney.com/api/qt/stock/fflow/kline/get"
EASTMONEY_SECTOR_FLOW_KLINE_URL_DELAY = "http://push2delay.eastmoney.com/api/qt/stock/fflow/kline/get"
EASTMONEY_BOARD_LIST_URL = "http://push2.eastmoney.com/api/qt/clist/get"
EASTMONEY_BOARD_LIST_URL_DELAY = "http://push2delay.eastmoney.com/api/qt/clist/get"

A_SHARE_FILTER = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048"

MARKET_INDICES = [
    {"secid": "1.000001", "name": "上证指数", "code": "000001"},
    {"secid": "0.399001", "name": "深证成指", "code": "399001"},
    {"secid": "0.399006", "name": "创业板指", "code": "399006"},
    {"secid": "1.000681", "name": "科创板指", "code": "000681"},
    {"secid": "1.000016", "name": "上证50", "code": "000016"},
    {"secid": "1.000300", "name": "沪深300", "code": "000300"},
    {"secid": "0.399905", "name": "中证500", "code": "399905"},
    {"secid": "0.399303", "name": "国证2000", "code": "399303"},
    {"secid": "1.000688", "name": "科创50", "code": "000688"},
    {"secid": "0.899050", "name": "北证50", "code": "899050"},
]
MARKET_INDICES_US = [
    {"secid": "100.DJIA", "name": "道琼斯", "code": "DJIA"},
    {"secid": "100.SPX", "name": "标普500", "code": "SPX"},
    {"secid": "100.NDX", "name": "纳斯达克", "code": "NDX"},
    {"secid": "100.NDX100", "name": "纳斯达克100", "code": "NDX100"},
    {"secid": "251.HXC", "name": "纳指金龙中国", "code": "HXC"},
    {"secid": "251.SOX", "name": "费城半导体指数", "code": "SOX"},
]
MARKET_INDICES_JP_KR = [
    {"secid": "100.N225", "name": "日经指数", "code": "N225"},
    {"secid": "100.KS11", "name": "韩国KOSPI", "code": "KS11"},
]

DEFAULT_HEADERS = {
    "Referer": "https://www.shidaotec.com/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

_session = requests.Session()
_session.trust_env = False
_session.proxies = {"http": None, "https": None}
_session.headers.update(DEFAULT_HEADERS)

_INDEX_CACHE: Dict[str, Dict] = {}
_OVERVIEW_CACHE = {
    "data": None,
    "timestamp": 0,
    "ttl": 60,
}
_FLOW_CACHE = {
    "northbound": None,
    "market_fund_flow": None,
    "timestamp": 0,
    "ttl": 60,
}
_BOARD_LIST_CACHE = {
    "data": {},
    "timestamp": 0,
    "ttl": 60,
}
_FUND_FLOW_HISTORY_CACHE: Dict[str, Dict] = {}


class EastMoneySectorSource(SectorDataSource):
    """复用 AkshareFetcher.get_sector_rankings 的东财板块 source。"""

    source_id = "eastmoney"

    def __init__(self) -> None:
        """构造板块数据源（东财）。"""
        self.fetcher = AkshareFetcher()

    def fetch(self, request: SectorRankingRequest) -> Optional[SectorRankingResult]:
        """获取东财板块涨跌排行。"""
        limit = max(int(request.limit), 1)
        ranking_type = str(request.ranking_type or "sector").strip().lower()
        if ranking_type == "concept":
            rankings = self.fetcher.get_concept_rankings(limit)
        else:
            rankings = self.fetcher.get_sector_rankings(limit)
        if not rankings:
            return None

        top_sectors, bottom_sectors = rankings
        return SectorRankingResult(
            top_sectors=top_sectors or [],
            bottom_sectors=bottom_sectors or [],
            source=self.source_id,
            metadata={"limit": limit, "ranking_type": ranking_type},
        )


def fetch_market_indices(market: str = "a") -> Optional[List[Dict]]:
    return _market_card_indices().fetch_market_indices(market)


def get_cached_market_indices(market: str = "a") -> Optional[List[Dict]]:
    return _market_card_indices().get_cached_market_indices(market)


def fetch_market_overview() -> Optional[Dict]:
    return _market_card_statistics().fetch_market_overview()


def get_cached_market_overview() -> Optional[Dict]:
    return _market_card_statistics().get_cached_market_overview()


def fetch_northbound_flow() -> Optional[Dict]:
    return _market_card_statistics().fetch_northbound_flow()


def get_cached_northbound_flow() -> Optional[Dict]:
    return _market_card_statistics().get_cached_northbound_flow()


def fetch_market_fund_flow() -> Optional[Dict]:
    return _market_card_statistics().fetch_market_fund_flow()


def get_cached_market_fund_flow() -> Optional[Dict]:
    return _market_card_statistics().get_cached_market_fund_flow()


def fetch_sector_fund_flow_rank(
    sector_type: str = "industry",
    top_n: int = 10,
    max_retries: int = 2,
) -> Optional[List[Dict]]:
    """获取板块资金流排行。"""
    fs_param = "m:90+t:2" if sector_type == "industry" else "m:90+t:3"
    for attempt in range(max_retries):
        try:
            resp = _session.get(
                EASTMONEY_SECTOR_FLOW_RANK_URL,
                params={
                    "pn": "1",
                    "pz": str(max(top_n, 200)),
                    "po": "1",
                    "np": "1",
                    "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                    "fltt": "2",
                    "invt": "2",
                    "fid": "f62",
                    "fs": fs_param,
                    "fields": "f12,f14,f62",
                },
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            diff = resp.json().get("data", {}).get("diff", [])
            if not diff:
                logger.warning("板块资金流排行返回空数据：sector_type=%s", sector_type)
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return None
            return [
                {
                    "code": item.get("f12", ""),
                    "name": item.get("f14", ""),
                    "latest": _yuan_to_yi(item.get("f62")) if item.get("f62") not in (None, "-") else None,
                }
                for item in diff
            ]
        except Exception as exc:
            logger.error("板块资金流排行接口异常（attempt %s/%s）：%s", attempt + 1, max_retries, exc)
            if attempt < max_retries - 1:
                time.sleep(1)
    return None


def fetch_sector_fund_flow_kline(sector_code: str, limit: int = 30) -> Optional[List[Dict]]:
    """获取单个板块的资金流日线。"""
    params = {
        "secid": f"90.{sector_code}",
        "klt": "101",
        "lmt": str(limit),
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fields1": "f1,f2,f3,f7",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
    }
    for url in [EASTMONEY_SECTOR_FLOW_KLINE_URL, EASTMONEY_SECTOR_FLOW_KLINE_URL_DELAY]:
        try:
            resp = _session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            result = resp.json()
            if result.get("rc") != 0:
                logger.warning("板块 %s 资金流接口返回 rc=%s：%s", sector_code, result.get("rc"), url)
                continue
            klines = result.get("data", {}).get("klines", [])
            if not klines:
                logger.warning("板块 %s 资金流日线数据为空：%s", sector_code, url)
                continue
            parsed = []
            for line in klines:
                parts = line.split(",")
                if len(parts) < 2:
                    continue
                try:
                    main_flow = float(parts[1]) if parts[1] != "-" else None
                except (TypeError, ValueError):
                    main_flow = None
                parsed.append({"date": parts[0], "mainFlow": main_flow})
            return parsed
        except Exception as exc:
            logger.warning("板块 %s 资金流接口异常（%s）：%s", sector_code, url, exc)
    logger.error("板块 %s 资金流所有接口均失败", sector_code)
    return None


def fetch_sector_fund_flow_kline_with_retry(
    sector_code: str,
    limit: int = 30,
    max_retries: int = FUND_FLOW_MAX_RETRIES,
) -> Optional[List[Dict]]:
    """带重试获取板块资金流日线。"""
    for attempt in range(max_retries):
        result = fetch_sector_fund_flow_kline(sector_code, limit)
        if result:
            return result
        if attempt < max_retries - 1:
            time.sleep(1.5)
    return None


def get_sector_fund_flow_history_data(
    sector_type: str = "industry",
    limit: int = 30,
    top_n: int = 10,
    sector_codes: Optional[List[str]] = None,
) -> Optional[Dict]:
    """获取板块资金流历史序列并做短时缓存。"""
    specified_codes = [code.strip() for code in (sector_codes or []) if code and code.strip()]
    codes_key = ",".join(specified_codes) if specified_codes else f"top{top_n}"
    cache_key = f"{sector_type}_{limit}_{codes_key}"
    cached = _FUND_FLOW_HISTORY_CACHE.get(cache_key)
    if cached and (time.time() - cached.get("timestamp", 0)) < 300:
        return cached["data"]

    if specified_codes:
        all_sectors = fetch_sector_fund_flow_rank(sector_type, 200)
        if not all_sectors:
            return None
        code_map = {sector["code"]: sector for sector in all_sectors}
        rank_sectors = [code_map[code] for code in specified_codes if code in code_map]
        if not rank_sectors:
            raise LookupError("specified sector codes not found")
    else:
        rank_sectors = fetch_sector_fund_flow_rank(sector_type, top_n)
        if not rank_sectors:
            return None

    all_dates = set()
    sector_histories: List[Dict] = []

    def _fetch_one(sector: Dict) -> Optional[Dict]:
        """拉取单个板块数据。"""
        klines = fetch_sector_fund_flow_kline_with_retry(sector["code"], limit)
        if not klines:
            return None
        for kline in klines:
            all_dates.add(kline["date"])
        return {
            "code": sector["code"],
            "name": sector["name"],
            "latest": sector["latest"],
            "klines": {kline["date"]: kline["mainFlow"] for kline in klines},
        }

    with ThreadPoolExecutor(max_workers=FUND_FLOW_MAX_WORKERS) as executor:
        futures = {executor.submit(_fetch_one, sector): sector for sector in rank_sectors}
        for future in as_completed(futures):
            result = future.result()
            if result:
                sector_histories.append(result)

    sorted_dates = sorted(all_dates)
    color_palette = [
        "#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de",
        "#3ba272", "#fc8452", "#9a60b4", "#ea7ccc", "#d48265",
        "#c23531", "#2f4554", "#61a0a8", "#d48265", "#749f83",
    ]

    sectors_result = []
    for idx, sector in enumerate(sector_histories):
        series = []
        for current_date in sorted_dates:
            raw = sector["klines"].get(current_date)
            series.append(_yuan_to_yi(raw) if raw is not None else None)
        sectors_result.append({
            "code": sector["code"],
            "name": sector["name"],
            "series": series,
            "latest": sector["latest"],
            "color": color_palette[idx % len(color_palette)],
        })

    result_data = {
        "dates": sorted_dates,
        "sectors": sectors_result,
    }
    _FUND_FLOW_HISTORY_CACHE[cache_key] = {
        "data": result_data,
        "timestamp": time.time(),
    }
    return result_data


def fetch_board_list(sector_type: str = "industry", max_retries: int = 2) -> Optional[List[Dict]]:
    """获取行业或概念板块列表。"""
    fs_param = "m:90+t:2" if sector_type == "industry" else "m:90+t:3"
    page_size = 100
    max_pages = 5
    for attempt in range(max_retries):
        for url in [EASTMONEY_BOARD_LIST_URL, EASTMONEY_BOARD_LIST_URL_DELAY]:
            try:
                boards = []
                for page in range(1, max_pages + 1):
                    resp = _session.get(
                        url,
                        params={
                            "pn": str(page),
                            "pz": str(page_size),
                            "po": "1",
                            "np": "1",
                            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                            "fltt": "2",
                            "invt": "2",
                            "fid": "f3",
                            "fs": fs_param,
                            "fields": "f12,f14,f3,f20,f8,f104,f105",
                        },
                        timeout=REQUEST_TIMEOUT,
                    )
                    resp.raise_for_status()
                    diff = resp.json().get("data", {}).get("diff", [])
                    if not diff:
                        break
                    for item in diff:
                        boards.append({
                            "code": item.get("f12", ""),
                            "name": item.get("f14", ""),
                            "changePercent": round(float(item.get("f3") or 0.0), 2),
                            "totalMarketCap": round(float(item.get("f20") or 0.0) / 1e8, 2),
                            "turnoverRate": round(float(item.get("f8") or 0.0), 2),
                            "riseCount": int(item.get("f104") or 0),
                            "fallCount": int(item.get("f105") or 0),
                        })
                    if len(diff) < page_size:
                        break
                if not boards:
                    logger.warning("板块列表返回空数据：url=%s sector_type=%s", url, sector_type)
                    continue
                for idx, board in enumerate(boards, start=1):
                    board["rank"] = idx
                return boards
            except Exception as exc:
                logger.error("fetch_board_list 第 %s 次尝试(%s)失败：%s", attempt + 1, url, exc)
        if attempt < max_retries - 1:
            time.sleep(1)
    return None


def get_cached_board_list(sector_type: str = "industry") -> Optional[List[Dict]]:
    """获取带缓存的板块列表。"""
    if (
        sector_type not in _BOARD_LIST_CACHE["data"]
        or (time.time() - _BOARD_LIST_CACHE["timestamp"]) > _BOARD_LIST_CACHE["ttl"]
    ):
        boards = fetch_board_list(sector_type)
        if not boards:
            return None
        _BOARD_LIST_CACHE["data"][sector_type] = boards
        _BOARD_LIST_CACHE["timestamp"] = time.time()
    return _BOARD_LIST_CACHE["data"][sector_type]


def _get_limit_ratio(code: str, name: str) -> float:
    """按代码与名称判断涨跌幅限制。"""
    if code.startswith(("300", "301", "302", "688", "689")):
        return 20.0
    if code.startswith(("43", "83", "87", "920")):
        return 30.0
    if "ST" in name.upper():
        return 5.0
    return 10.0


def _yuan_to_yi(value: Optional[float]) -> Optional[float]:
    """元转换为亿。"""
    if value is None:
        return None
    return round(value / 1e8, 2)


def _market_card_indices():
    """显式接线原模块运行资源，不复制缓存或提前创建桥接客户端。"""
    from data_provider.market.indices import EastmoneyCardIndices

    return EastmoneyCardIndices(
        call_fetch_market_indices=lambda *args, **kwargs: fetch_market_indices(
            *args, **kwargs
        ),
        read_eastmoney_index_url=lambda: EASTMONEY_INDEX_URL,
        read_eastmoney_index_url_delay=lambda: EASTMONEY_INDEX_URL_DELAY,
        read_market_indices=lambda: MARKET_INDICES,
        read_market_indices_jp_kr=lambda: MARKET_INDICES_JP_KR,
        read_market_indices_us=lambda: MARKET_INDICES_US,
        read_request_timeout=lambda: REQUEST_TIMEOUT,
        read_index_cache=lambda: _INDEX_CACHE,
        read_session=lambda: _session,
        read_logger=lambda: logger,
        read_time=lambda: time,
    )


def _market_card_statistics():
    """显式接线原模块运行资源，不复制缓存或提前创建桥接客户端。"""
    from data_provider.market.statistics import EastmoneyCardStatistics

    return EastmoneyCardStatistics(
        call_get_limit_ratio=lambda *args, **kwargs: _get_limit_ratio(*args, **kwargs),
        call_fetch_market_fund_flow=lambda *args, **kwargs: fetch_market_fund_flow(
            *args, **kwargs
        ),
        call_fetch_market_overview=lambda *args, **kwargs: fetch_market_overview(
            *args, **kwargs
        ),
        call_fetch_northbound_flow=lambda *args, **kwargs: fetch_northbound_flow(
            *args, **kwargs
        ),
        read_a_share_filter=lambda: A_SHARE_FILTER,
        read_eastmoney_fflow_daykline_url=lambda: EASTMONEY_FFLOW_DAYKLINE_URL,
        read_eastmoney_index_url=lambda: EASTMONEY_INDEX_URL,
        read_eastmoney_index_url_delay=lambda: EASTMONEY_INDEX_URL_DELAY,
        read_eastmoney_market_url=lambda: EASTMONEY_MARKET_URL,
        read_eastmoney_northbound_url=lambda: EASTMONEY_NORTHBOUND_URL,
        read_request_timeout=lambda: REQUEST_TIMEOUT,
        read_flow_cache=lambda: _FLOW_CACHE,
        read_overview_cache=lambda: _OVERVIEW_CACHE,
        read_session=lambda: _session,
        read_logger=lambda: logger,
        read_time=lambda: time,
    )
