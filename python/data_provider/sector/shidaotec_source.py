# -*- coding: utf-8 -*-
"""
@file: shidaotec_source.py
@description: 板块能力时到量化 source，承接行业/个股/ETF/概念云图相关 HTTP 取数与整形。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = (5, 10)
CACHE_TTL = 300

SHIDAOTEC_SCALE_URL = "https://www.shidaotec.com/api/yuntu/getSwMapScale"
SHIDAOTEC_DATA_URL = "https://www.shidaotec.com/api/yuntu/getSwMapData"
STOCK_MAP_SCALE_URL = "https://www.shidaotec.com/api/yuntu/getMapScale"
STOCK_MAP_DATA_URL = "https://www.shidaotec.com/api/yuntu/getMapData"
ETF_MAP_SCALE_URL = "https://www.shidaotec.com/api/yuntu/getETFMapScale"
ETF_MAP_DATA_URL = "https://www.shidaotec.com/api/yuntu/getETFMapData"
CONCEPT_MAP_SCALE_URL = "https://www.shidaotec.com/api/yuntu/getThsMapScale"
CONCEPT_MAP_DATA_URL = "https://www.shidaotec.com/api/yuntu/getThsMapData"

ETF_PERIOD_MAP = {
    "yesterday": 2,
    "week": 3,
    "month": 4,
    "quarter": 5,
    "half_year": 6,
    "year": 7,
    "three_year": 8,
    "ytd": 10,
}

PERIOD_LABELS = {
    "yesterday": "昨日涨跌幅",
    "week": "近一周",
    "month": "近一月",
    "quarter": "近三月",
    "half_year": "近半年",
    "ytd": "今年以来",
    "year": "近一年",
    "three_year": "近三年",
}

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

_industry_cache = {
    "scale_data": None,
    "change_data": None,
    "timestamp": 0,
    "ttl": CACHE_TTL,
}
_industry_snapshot_cache: Dict[str, Dict] = {}

_stock_cache = {
    "scale_data": None,
    "change_data": None,
    "timestamp": 0,
    "ttl": CACHE_TTL,
}
_stock_snapshot_cache: Dict[str, Dict] = {}

_etf_cache = {
    "scale_data": None,
    "change_data": {},
    "timestamp": 0,
    "ttl": CACHE_TTL,
}

_concept_cache = {
    "scale_data": None,
    "change_data": {},
    "timestamp": 0,
    "ttl": CACHE_TTL,
}


class SnapshotDataUnavailableError(LookupError):
    """指定快照时间无可用数据。"""


def _convert_time_format(time_str: str) -> str:
    """将前端时间格式转换为上游接口格式。"""
    return time_str.replace(":", "")


def _parse_change_value(value: str) -> float:
    """从“价格|涨跌幅”或“市值|涨跌幅”字符串中解析涨跌幅。"""
    try:
        if "|" in value:
            return float(value.split("|")[1])
        return float(value)
    except (ValueError, IndexError):
        return 0.0


def _compute_weighted_change(node: Dict[str, Any]) -> float:
    """按 value 递归计算父节点加权涨跌幅。"""
    children = node.get("children") or []
    if not children:
        return node.get("changePercent", 0)

    total_value = 0
    weighted_sum = 0
    for child in children:
        child_change = _compute_weighted_change(child)
        child_value = child.get("value", 0)
        weighted_sum += child_change * child_value
        total_value += child_value

    if total_value > 0:
        return round(weighted_sum / total_value, 2)
    return 0


def _build_period_label(period: str) -> str:
    """返回周期中文标签。"""
    return PERIOD_LABELS.get(period, period)


def _fetch_industry_scale_data() -> Optional[List[Dict]]:
    """获取行业结构树。"""
    try:
        resp = _session.get(SHIDAOTEC_SCALE_URL, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") == 200:
            return result.get("data")
        logger.warning("时到量化行业 scale 接口返回异常：%s", result.get("msg"))
    except Exception as exc:
        logger.error("时到量化行业 scale 接口异常：%s", exc, exc_info=True)
    return None


def _fetch_industry_change_data(time_param: str = "") -> Optional[Dict]:
    """获取行业涨跌幅字典。"""
    try:
        resp = _session.get(
            SHIDAOTEC_DATA_URL,
            params={"type": "1", "time": time_param, "tradeMonth": ""},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") == 200:
            return result.get("data")
        logger.warning("时到量化行业 data 接口返回异常：%s", result.get("msg"))
    except Exception as exc:
        logger.error("时到量化行业 data 接口异常：%s", exc, exc_info=True)
    return None


def _refresh_industry_cache() -> None:
    """刷新行业实时缓存。"""
    scale_data = _fetch_industry_scale_data()
    change_data = _fetch_industry_change_data()
    if scale_data and change_data:
        _industry_cache["scale_data"] = scale_data
        _industry_cache["change_data"] = change_data
        _industry_cache["timestamp"] = time.time()
        logger.info("行业云图缓存刷新成功")
        return
    logger.warning(
        "行业云图缓存刷新失败：scale=%s, change=%s",
        scale_data is not None,
        change_data is not None,
    )


def _get_industry_cache() -> Optional[Dict]:
    """获取行业缓存，过期则刷新。"""
    if (
        _industry_cache["scale_data"] is None
        or (time.time() - _industry_cache["timestamp"]) > _industry_cache["ttl"]
    ):
        _refresh_industry_cache()
    return _industry_cache


def _get_industry_snapshot_data(time_str: str) -> Optional[Dict]:
    """获取行业历史快照数据。"""
    if time_str in _industry_snapshot_cache:
        return _industry_snapshot_cache[time_str]

    change_data = _fetch_industry_change_data(time_param=_convert_time_format(time_str))
    if change_data:
        _industry_snapshot_cache[time_str] = change_data
    return change_data


def _build_industry_treemap_node(
    node: Dict[str, Any],
    change_data: Dict[str, Any],
    level: int = 0,
) -> Optional[Dict[str, Any]]:
    """递归构建行业 treemap 节点。"""
    code = node.get("code", "")
    name = node.get("name", "")
    scale = float(node.get("scale", 0) or 0)
    up_count = int(node.get("upCount", 0) or 0)
    down_count = int(node.get("downCount", 0) or 0)

    change_raw = change_data.get(code, "0|0") if change_data else "0|0"
    change_percent = _parse_change_value(change_raw)

    children = []
    for child in node.get("children") or []:
        child_node = _build_industry_treemap_node(child, change_data, level + 1)
        if child_node:
            children.append(child_node)

    if level == 0:
        return None

    result = {
        "code": code,
        "name": name,
        "value": max(scale, 1),
        "changePercent": round(change_percent, 2),
        "riseCount": up_count,
        "fallCount": down_count,
    }
    if children:
        result["children"] = children
    return result


def get_industry_treemap(time_str: str = "") -> Optional[Dict[str, Any]]:
    """获取行业云图树。"""
    cache = _get_industry_cache()
    if not cache or not cache["scale_data"]:
        return None

    scale_data = cache["scale_data"]
    if time_str:
        change_data = _get_industry_snapshot_data(time_str)
        if not change_data:
            raise SnapshotDataUnavailableError(f"历史快照数据获取失败：{time_str}")
    else:
        change_data = cache["change_data"]

    treemap_nodes = []
    for node in scale_data:
        result = _build_industry_treemap_node(node, change_data, level=0)
        if result is None and node.get("children"):
            for child in node["children"]:
                treemap_node = _build_industry_treemap_node(child, change_data, level=1)
                if treemap_node:
                    treemap_nodes.append(treemap_node)

    for node in treemap_nodes:
        if node.get("children"):
            node["changePercent"] = _compute_weighted_change(node)

    treemap_nodes.sort(key=lambda item: item.get("changePercent", 0), reverse=True)
    return {
        "total": len(treemap_nodes),
        "sectors": treemap_nodes,
        "snapshotTime": time_str or None,
    }


def get_board_card_list(sector_type: str = "industry", top_n: int = 200) -> Optional[List[Dict[str, Any]]]:
    """将时到量化云图数据投影为板块卡片列表兜底结构。"""
    normalized_type = str(sector_type or "industry").strip().lower()
    if normalized_type == "industry":
        treemap = get_industry_treemap()
    elif normalized_type == "concept":
        treemap = get_concept_treemap(period="yesterday", top_n=top_n)
    else:
        return None

    if not treemap:
        return None

    sectors = treemap.get("sectors") or []
    if not isinstance(sectors, list) or not sectors:
        return None

    boards = []
    for index, item in enumerate(sectors[:top_n], start=1):
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "").strip()
        name = str(item.get("name") or "").strip()
        if not code or not name:
            continue
        boards.append(
            {
                "rank": index,
                "code": code,
                "name": name,
                "changePercent": round(float(item.get("changePercent", 0) or 0), 2),
                # 时到量化行业 value 为真实体量，概念 value 为相对规模；这里统一折算成前端可展示数值。
                "totalMarketCap": _normalize_board_metric(item.get("value")),
                "turnoverRate": 0.0,
                "riseCount": int(item.get("riseCount", 0) or 0),
                "fallCount": int(item.get("fallCount", 0) or 0),
            }
        )
    return boards or None


def _fetch_stock_map_scale() -> Optional[List[Dict]]:
    """获取个股云图结构树。"""
    try:
        resp = _session.get(
            STOCK_MAP_SCALE_URL,
            params={"market": "all"},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") == 200:
            return result.get("data")
        logger.warning("时到量化个股 scale 接口返回异常：%s", result.get("msg"))
    except Exception as exc:
        logger.error("时到量化个股 scale 接口异常：%s", exc, exc_info=True)
    return None


def _fetch_stock_map_data(time_param: str = "", trade_date: str = "") -> Optional[Dict]:
    """获取个股涨跌幅字典。"""
    try:
        resp = _session.get(
            STOCK_MAP_DATA_URL,
            params={"type": "1", "time": time_param, "tradeDate": trade_date},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") == 200:
            return result.get("data")
        logger.warning("时到量化个股 data 接口返回异常：%s", result.get("msg"))
    except Exception as exc:
        logger.error("时到量化个股 data 接口异常：%s", exc, exc_info=True)
    return None


def _refresh_stock_cache() -> None:
    """刷新个股云图缓存。"""
    scale_data = _fetch_stock_map_scale()
    change_data = _fetch_stock_map_data()
    if scale_data and change_data:
        _stock_cache["scale_data"] = scale_data
        _stock_cache["change_data"] = change_data
        _stock_cache["timestamp"] = time.time()
        logger.info("个股云图缓存刷新成功")
        return
    logger.warning(
        "个股云图缓存刷新失败：scale=%s, change=%s",
        scale_data is not None,
        change_data is not None,
    )


def _get_stock_cache() -> Optional[Dict]:
    """获取个股缓存，过期则刷新。"""
    if _stock_cache["scale_data"] is None or (time.time() - _stock_cache["timestamp"]) > _stock_cache["ttl"]:
        _refresh_stock_cache()
    return _stock_cache


def _get_stock_snapshot_data(time_str: str) -> Optional[Dict]:
    """获取个股历史快照数据。"""
    if time_str in _stock_snapshot_cache:
        return _stock_snapshot_cache[time_str]

    change_data = _fetch_stock_map_data(time_param=_convert_time_format(time_str))
    if change_data:
        _stock_snapshot_cache[time_str] = change_data
    return change_data


def _build_stock_treemap_node(node: Dict[str, Any], change_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """递归构建个股 treemap 节点。"""
    code = node.get("code", "")
    name = node.get("name", "")
    scale = float(node.get("scale", 0) or 0)
    up_count = int(node.get("upCount", 0) or 0)
    down_count = int(node.get("downCount", 0) or 0)

    change_raw = change_data.get(code, "0|0") if change_data else "0|0"
    change_percent = _parse_change_value(change_raw)

    children = []
    for child in node.get("children") or []:
        child_node = _build_stock_treemap_node(child, change_data)
        if child_node:
            children.append(child_node)

    if code == "0":
        return None

    result = {
        "code": code,
        "name": name,
        "value": max(scale, 1),
        "changePercent": round(change_percent, 2),
        "riseCount": up_count,
        "fallCount": down_count,
    }
    if children:
        result["children"] = children
    return result


def get_stock_treemap(time_str: str = "") -> Optional[Dict[str, Any]]:
    """获取个股云图树。"""
    cache = _get_stock_cache()
    if not cache or not cache["scale_data"]:
        return None

    scale_data = cache["scale_data"]
    if time_str:
        change_data = _get_stock_snapshot_data(time_str)
        if not change_data:
            raise SnapshotDataUnavailableError(
                f"个股历史快照数据获取失败：{time_str}（该时间点暂无数据）"
            )
    else:
        change_data = cache["change_data"]

    treemap_nodes = []
    for node in scale_data:
        result = _build_stock_treemap_node(node, change_data)
        if result is None and node.get("children"):
            for child in node["children"]:
                treemap_node = _build_stock_treemap_node(child, change_data)
                if treemap_node:
                    treemap_nodes.append(treemap_node)

    for node in treemap_nodes:
        if node.get("children"):
            node["changePercent"] = _compute_weighted_change(node)

    treemap_nodes.sort(key=lambda item: item.get("changePercent", 0), reverse=True)
    return {
        "total": len(treemap_nodes),
        "sectors": treemap_nodes,
        "snapshotTime": time_str or None,
    }


def _fetch_etf_map_scale() -> Optional[List[Dict]]:
    """获取 ETF 云图结构。"""
    try:
        resp = _session.get(
            ETF_MAP_SCALE_URL,
            params={"etfType": "1"},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") == 200:
            data = result.get("data") or []
            if data:
                return data[0].get("children") or []
        logger.warning("时到量化 ETF scale 接口返回异常：%s", result.get("msg"))
    except Exception as exc:
        logger.error("时到量化 ETF scale 接口异常：%s", exc, exc_info=True)
    return None


def _fetch_etf_map_data(period: str = "yesterday") -> Optional[Dict]:
    """获取 ETF 涨跌幅数据。"""
    try:
        resp = _session.get(
            ETF_MAP_DATA_URL,
            params={"type": str(ETF_PERIOD_MAP.get(period, 1)), "etfType": "1"},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") == 200:
            return result.get("data")
        logger.warning("时到量化 ETF data 接口返回异常：%s", result.get("msg"))
    except Exception as exc:
        logger.error("时到量化 ETF data 接口异常：%s", exc, exc_info=True)
    return None


def _refresh_etf_cache() -> None:
    """刷新 ETF scale 缓存。"""
    scale_data = _fetch_etf_map_scale()
    if scale_data:
        _etf_cache["scale_data"] = scale_data
        _etf_cache["timestamp"] = time.time()
        logger.info("ETF 云图 scale 缓存刷新成功")
        return
    logger.warning("ETF 云图 scale 缓存刷新失败")


def _get_etf_cache() -> Optional[Dict]:
    """获取 ETF 缓存，过期则刷新。"""
    if _etf_cache["scale_data"] is None or (time.time() - _etf_cache["timestamp"]) > _etf_cache["ttl"]:
        _refresh_etf_cache()
    return _etf_cache


def _get_etf_change_data(period: str) -> Optional[Dict]:
    """获取 ETF 周期涨跌幅数据。"""
    if period in _etf_cache["change_data"]:
        return _etf_cache["change_data"][period]
    change_data = _fetch_etf_map_data(period)
    if change_data:
        _etf_cache["change_data"][period] = change_data
    return change_data


def _build_flat_treemap_node(item: Dict[str, Any], change_data: Dict[str, Any]) -> Dict[str, Any]:
    """构建 ETF/概念的扁平 treemap 节点。"""
    code = item.get("code", "")
    name = item.get("name", "")
    scale = float(item.get("scale", 0) or 0)
    change_raw = change_data.get(code, "0|0") if change_data else "0|0"
    return {
        "code": code,
        "name": name,
        "value": max(scale, 1),
        "changePercent": round(_parse_change_value(change_raw), 2),
    }


def get_etf_treemap(period: str = "yesterday", top_n: int = 100) -> Optional[Dict[str, Any]]:
    """获取 ETF 云图。"""
    cache = _get_etf_cache()
    if not cache or not cache["scale_data"]:
        return None

    change_data = _get_etf_change_data(period)
    if not change_data:
        logger.warning("ETF 涨跌幅数据为空：%s，返回空列表", period)
        return {
            "total": 0,
            "sectors": [],
            "period": period,
            "periodLabel": _build_period_label(period),
        }

    etf_nodes = [_build_flat_treemap_node(item, change_data) for item in cache["scale_data"]]
    etf_nodes.sort(key=lambda item: item["value"], reverse=True)
    etf_nodes = etf_nodes[:top_n]
    return {
        "total": len(etf_nodes),
        "sectors": etf_nodes,
        "period": period,
        "periodLabel": _build_period_label(period),
    }


def _fetch_concept_map_scale() -> Optional[List[Dict]]:
    """获取概念云图结构并扁平化子概念。"""
    try:
        resp = _session.get(CONCEPT_MAP_SCALE_URL, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") == 200:
            data = result.get("data") or []
            if data:
                categories = data[0].get("children") or []
                flat_items = []
                for category in categories:
                    for child in category.get("children") or []:
                        flat_items.append({
                            "code": child.get("code", ""),
                            "name": child.get("name", ""),
                            "scale": child.get("scale", 0),
                            "category": category.get("name", ""),
                        })
                return flat_items
        logger.warning("时到量化概念 scale 接口返回异常：%s", result.get("msg"))
    except Exception as exc:
        logger.error("时到量化概念 scale 接口异常：%s", exc, exc_info=True)
    return None


def _fetch_concept_map_data(period: str = "yesterday") -> Optional[Dict]:
    """获取概念涨跌幅数据。"""
    try:
        resp = _session.get(
            CONCEPT_MAP_DATA_URL,
            params={"type": str(ETF_PERIOD_MAP.get(period, 1))},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") == 200:
            return result.get("data")
        logger.warning("时到量化概念 data 接口返回异常：%s", result.get("msg"))
    except Exception as exc:
        logger.error("时到量化概念 data 接口异常：%s", exc, exc_info=True)
    return None


def _refresh_concept_cache() -> None:
    """刷新概念 scale 缓存。"""
    scale_data = _fetch_concept_map_scale()
    if scale_data:
        _concept_cache["scale_data"] = scale_data
        _concept_cache["timestamp"] = time.time()
        logger.info("概念云图 scale 缓存刷新成功")
        return
    logger.warning("概念云图 scale 缓存刷新失败")


def _get_concept_cache() -> Optional[Dict]:
    """获取概念缓存，过期则刷新。"""
    if _concept_cache["scale_data"] is None or (time.time() - _concept_cache["timestamp"]) > _concept_cache["ttl"]:
        _refresh_concept_cache()
    return _concept_cache


def _get_concept_change_data(period: str) -> Optional[Dict]:
    """获取概念周期涨跌幅数据。"""
    if period in _concept_cache["change_data"]:
        return _concept_cache["change_data"][period]
    change_data = _fetch_concept_map_data(period)
    if change_data:
        _concept_cache["change_data"][period] = change_data
    return change_data


def get_concept_treemap(period: str = "yesterday", top_n: int = 100) -> Optional[Dict[str, Any]]:
    """获取概念云图。"""
    cache = _get_concept_cache()
    if not cache or not cache["scale_data"]:
        return None

    change_data = _get_concept_change_data(period)
    if not change_data:
        logger.warning("概念涨跌幅数据为空：%s，返回空列表", period)
        return {
            "total": 0,
            "sectors": [],
            "period": period,
            "periodLabel": _build_period_label(period),
        }

    concept_nodes = [_build_flat_treemap_node(item, change_data) for item in cache["scale_data"]]
    concept_nodes.sort(key=lambda item: item["value"], reverse=True)
    concept_nodes = concept_nodes[:top_n]
    return {
        "total": len(concept_nodes),
        "sectors": concept_nodes,
        "period": period,
        "periodLabel": _build_period_label(period),
    }


def _normalize_board_metric(value: Any) -> float:
    """把云图 value 归一成卡片可展示的市值近似值（亿）。"""
    try:
        numeric = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    if numeric > 1e10:
        return round(numeric / 1e8, 2)
    return round(numeric, 2)
