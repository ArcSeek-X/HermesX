# -*- coding: utf-8 -*-
"""
===================================
板块数据接口（申万行业分类 - 层级树形结构）
===================================

职责：
1. GET /api/v1/sector/industry - 行业板块树形数据（一级行业包含二级行业子节点）
2. GET /api/v1/sector/{sector_code}/stocks - 板块成分股列表
3. GET /api/v1/sector/market-indices - 市场指数数据（上证、深证、创业板等）

数据来源：时到量化（shidaotec.com）申万行业分类接口
- 行业结构：https://www.shidaotec.com/api/yuntu/getSwMapScale
- 涨跌幅数据：https://www.shidaotec.com/api/yuntu/getSwMapData?type=1

数据结构（层级 treemap）：
- 一级行业（电子、银行、医药生物等）作为父级容器
- 二级行业（半导体、国有大型银行、化学制药等）作为子块
- 父级颜色 = 子级加权平均涨跌幅
"""

import logging
import time
from typing import Dict, List, Optional

import requests
from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------- 配置 ----------
REQUEST_TIMEOUT = 15
# 缓存 TTL（秒）：5 分钟（涨跌幅实时性要求高）
CACHE_TTL = 300

# 时到量化 API
SHIDAOTEC_SCALE_URL = "https://www.shidaotec.com/api/yuntu/getSwMapScale"
SHIDAOTEC_DATA_URL = "https://www.shidaotec.com/api/yuntu/getSwMapData"
# 个股云图 API
STOCK_MAP_SCALE_URL = "https://www.shidaotec.com/api/yuntu/getMapScale"
STOCK_MAP_DATA_URL = "https://www.shidaotec.com/api/yuntu/getMapData"
# ETF 云图 API
ETF_MAP_SCALE_URL = "https://www.shidaotec.com/api/yuntu/getETFMapScale"
ETF_MAP_DATA_URL = "https://www.shidaotec.com/api/yuntu/getETFMapData"
# 概念云图 API
CONCEPT_MAP_SCALE_URL = "https://www.shidaotec.com/api/yuntu/getThsMapScale"
CONCEPT_MAP_DATA_URL = "https://www.shidaotec.com/api/yuntu/getThsMapData"

# 东方财富市场指数 API（主域名 + 延迟域名 fallback）
EASTMONEY_INDEX_URL = "http://push2.eastmoney.com/api/qt/ulist.np/get"
EASTMONEY_INDEX_URL_DELAY = "http://push2delay.eastmoney.com/api/qt/ulist.np/get"

# 市场指数配置（secid 格式：市场代码.指数代码）
# 1 = 上海，0 = 深圳
MARKET_INDICES = [
    {"secid": "1.000001", "name": "上证指数", "code": "000001"},
    {"secid": "0.399001", "name": "深证成指", "code": "399001"},
    {"secid": "0.399006", "name": "创业板指", "code": "399006"},
    {"secid": "1.000688", "name": "科创50", "code": "000688"},
    {"secid": "1.000681", "name": "科创板指", "code": "000681"},
    {"secid": "1.000016", "name": "上证50", "code": "000016"},
    {"secid": "1.000300", "name": "沪深300", "code": "000300"},
    {"secid": "0.399905", "name": "中证500", "code": "399905"},
    {"secid": "0.932000", "name": "中证2000", "code": "932000"},
]

# ETF 涨跌幅周期映射（type 参数对应不同时间维度）
# 完全对齐参考网站 https://www.shidaotec.com/etfyuntu.html 的 type 映射
# 注意：参考网站没有"今日实时"选项，type=1 返回"-"无数据
ETF_PERIOD_MAP = {
    "yesterday": 2,   # 昨日涨跌幅
    "week": 3,        # 近一周
    "month": 4,       # 近一月
    "quarter": 5,     # 近三月
    "half_year": 6,   # 近半年
    "year": 7,        # 近一年
    "three_year": 8,  # 近三年
    "ytd": 10,        # 今年以来
}

# 概念云图 API
CONCEPT_MAP_SCALE_URL = "https://www.shidaotec.com/api/yuntu/getThsMapScale"
CONCEPT_MAP_DATA_URL = "https://www.shidaotec.com/api/yuntu/getThsMapData"

DEFAULT_HEADERS = {
    "Referer": "https://www.shidaotec.com/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

# ---------- HTTP 会话 ----------
_session = requests.Session()
_session.trust_env = False
_session.proxies = {"http": None, "https": None}
_session.headers.update(DEFAULT_HEADERS)

# ---------- 缓存 ----------
_cache = {
    "scale_data": None,  # 行业结构（名称、市值、涨跌家数）
    "change_data": None,  # 涨跌幅数据（实时）
    "timestamp": 0,
    "ttl": CACHE_TTL,
}
# 历史快照缓存：{time_str: change_data}
_snapshot_cache: Dict[str, Dict] = {}

# ---------- 个股云图缓存 ----------
_stock_cache = {
    "scale_data": None,
    "change_data": None,
    "timestamp": 0,
    "ttl": CACHE_TTL,
}
_stock_snapshot_cache: Dict[str, Dict] = {}

# ---------- ETF 云图缓存 ----------
_etf_cache = {
    "scale_data": None,
    "change_data": {},  # {period: data}
    "timestamp": 0,
    "ttl": CACHE_TTL,
}

# ---------- 概念云图缓存 ----------
_concept_cache = {
    "scale_data": None,
    "change_data": {},  # {period: data}
    "timestamp": 0,
    "ttl": CACHE_TTL,
}

# ---------- 市场指数缓存 ----------
_index_cache = {
    "data": None,
    "timestamp": 0,
    "ttl": 60,  # 指数数据 60 秒缓存
}

# ---------- 市场概览缓存（涨跌家数 + 量能） ----------
# 数据来源：东方财富 push2delay API（全量 A 股实时行情）
# push2delay 每次最多返回 100 条，需分页获取全量 ~5800 条数据
EASTMONEY_MARKET_URL = "http://push2delay.eastmoney.com/api/qt/clist/get"
# A 股全市场筛选条件：沪深主板 + 创业板 + 科创板 + 北交所
A_SHARE_FILTER = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048"

_overview_cache = {
    "data": None,
    "timestamp": 0,
    "ttl": 60,  # 60 秒缓存
}


def _fetch_market_indices() -> Optional[List[Dict]]:
    """获取市场指数数据（东方财富 API，主域名失败则 fallback 到延迟域名）"""
    secids = ",".join([idx["secid"] for idx in MARKET_INDICES])
    # 构建 code → 自定义名称的映射，使用我们定义的名称而非 API 返回的名称
    code_name_map = {idx["code"]: idx["name"] for idx in MARKET_INDICES}

    for url in [EASTMONEY_INDEX_URL, EASTMONEY_INDEX_URL_DELAY]:
        try:
            resp = _session.get(
                url,
                params={
                    "fltt": "2",
                    "fields": "f2,f3,f12,f14",
                    "secids": secids,
                },
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("rc") == 0 and result.get("data") and result["data"].get("diff"):
                items = result["data"]["diff"]
                indices = []
                for item in items:
                    price = item.get("f2", "-")
                    change_pct = item.get("f3", "-")
                    code = item.get("f12", "")
                    # 优先使用自定义名称，fallback 到 API 返回的名称
                    name = code_name_map.get(code, item.get("f14", ""))
                    indices.append({
                        "name": name,
                        "code": code,
                        "price": price if price != "-" else None,
                        "changePercent": change_pct if change_pct != "-" else None,
                    })
                return indices
            logger.warning(f"东方财富指数接口({url})返回异常：{result}")
        except Exception as e:
            logger.error(f"东方财富指数接口({url})异常：{e}", exc_info=True)
    return None


def _get_market_indices_cache() -> Optional[List[Dict]]:
    """获取市场指数缓存，过期则刷新"""
    if _index_cache["data"] is None or (time.time() - _index_cache["timestamp"]) > _index_cache["ttl"]:
        data = _fetch_market_indices()
        if data:
            _index_cache["data"] = data
            _index_cache["timestamp"] = time.time()
    return _index_cache["data"]


def _fetch_market_overview() -> Optional[Dict]:
    """
    获取全市场涨跌家数和量能数据（东方财富 push2delay API）

    数据来源：push2delay.eastmoney.com（东方财富延迟行情接口）
    接口限制：每次最多返回 100 条，需分页获取全量 ~5800 条 A 股数据
    返回字段：
      - riseCount: 上涨家数
      - fallCount: 下跌家数
      - flatCount: 平盘家数
      - totalAmount: 当日成交额（元）
      - volumeRatio: 市场量比（加权平均，相较于昨日同时刻）
    """
    try:
        all_stocks = []
        # 分页获取全量 A 股数据（每页 100 条，最多 60 页）
        for page in range(1, 60):
            resp = _session.get(
                EASTMONEY_MARKET_URL,
                params={
                    "pn": str(page),
                    "pz": "100",
                    "po": "1",
                    "np": "1",
                    "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                    "fltt": "2",
                    "invt": "2",
                    "fid": "f3",
                    "fs": A_SHARE_FILTER,
                    "fields": "f2,f3,f6,f10",  # f2=最新价, f3=涨跌幅, f6=成交额, f10=量比
                },
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            diff = data.get("data", {}).get("diff", [])
            if not diff:
                break
            all_stocks.extend(diff)

        if not all_stocks:
            logger.warning("东方财富全市场接口返回空数据")
            return None

        # 统计涨跌家数
        rise_count = 0
        fall_count = 0
        flat_count = 0
        total_amount = 0.0
        yesterday_amount = 0.0
        # 量比加权平均（权重=成交额）
        weighted_volume_ratio_sum = 0.0
        total_amount_for_ratio = 0.0

        for stock in all_stocks:
            change_pct = stock.get("f3")
            amount = stock.get("f6")
            volume_ratio = stock.get("f10")
            # 跳过停牌/无数据股票（f3 为 "-" 或 None）
            if change_pct is None or change_pct == "-":
                continue
            try:
                change_pct = float(change_pct)
            except (ValueError, TypeError):
                continue
            if change_pct > 0:
                rise_count += 1
            elif change_pct < 0:
                fall_count += 1
            else:
                flat_count += 1
            # 累加成交额（f6 单位：元）
            if amount and amount != "-":
                try:
                    amount_val = float(amount)
                    total_amount += amount_val
                    # 计算量比加权平均
                    if volume_ratio and volume_ratio != "-":
                        try:
                            vr = float(volume_ratio)
                            weighted_volume_ratio_sum += vr * amount_val
                            total_amount_for_ratio += amount_val
                            # 计算昨日成交额：昨日 = 今日 / 量比
                            if vr > 0:
                                yesterday_amount += amount_val / vr
                        except (ValueError, TypeError):
                            pass
                except (ValueError, TypeError):
                    pass

        # 计算市场整体量比（成交额加权平均）
        volume_ratio = None
        if total_amount_for_ratio > 0:
            volume_ratio = round(weighted_volume_ratio_sum / total_amount_for_ratio, 2)

        # 计算放量/缩量金额
        volume_change = total_amount - yesterday_amount

        return {
            "riseCount": rise_count,
            "fallCount": fall_count,
            "flatCount": flat_count,
            "totalAmount": total_amount,
            "volumeRatio": volume_ratio,
            "yesterdayAmount": yesterday_amount,
            "volumeChange": volume_change,
        }
    except Exception as e:
        logger.error(f"东方财富全市场接口异常：{e}", exc_info=True)
        return None


def _get_market_overview_cache() -> Optional[Dict]:
    """获取市场概览缓存，过期则刷新"""
    if _overview_cache["data"] is None or (time.time() - _overview_cache["timestamp"]) > _overview_cache["ttl"]:
        data = _fetch_market_overview()
        if data:
            _overview_cache["data"] = data
            _overview_cache["timestamp"] = time.time()
    return _overview_cache["data"]


def _fetch_scale_data() -> Optional[List[Dict]]:
    """获取行业结构数据（树形结构）"""
    try:
        resp = _session.get(SHIDAOTEC_SCALE_URL, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") == 200:
            return result.get("data")
        logger.warning(f"时到量化 scale 接口返回异常：{result.get('msg')}")
        return None
    except Exception as e:
        logger.error(f"时到量化 scale 接口异常：{e}", exc_info=True)
        return None


def _fetch_change_data(time_param: str = "") -> Optional[Dict]:
    """获取涨跌幅数据（扁平字典：code -> '市值|涨跌幅'）"""
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
        logger.warning(f"时到量化 data 接口返回异常：{result.get('msg')}")
        return None
    except Exception as e:
        logger.error(f"时到量化 data 接口异常：{e}", exc_info=True)
        return None


def _refresh_cache():
    """刷新缓存（实时数据）"""
    scale_data = _fetch_scale_data()
    change_data = _fetch_change_data()

    if scale_data and change_data:
        _cache["scale_data"] = scale_data
        _cache["change_data"] = change_data
        _cache["timestamp"] = time.time()
        logger.info("板块缓存刷新成功")
    else:
        logger.warning(
            f"板块缓存刷新失败：scale={scale_data is not None}, change={change_data is not None}"
        )


def _get_cache() -> Optional[Dict]:
    """获取缓存数据，过期则刷新"""
    if _cache["scale_data"] is None or (time.time() - _cache["timestamp"]) > _cache["ttl"]:
        _refresh_cache()
    return _cache


def _convert_time_format(time_str: str) -> str:
    """
    将前端时间格式转换为 API 格式
    '10:00' -> '1000'
    '09:30' -> '0930'
    """
    return time_str.replace(":", "")


def _get_snapshot_data(time_str: str) -> Optional[Dict]:
    """获取历史快照数据，优先从缓存读取"""
    if time_str in _snapshot_cache:
        return _snapshot_cache[time_str]

    # 转换时间格式
    api_time = _convert_time_format(time_str)
    change_data = _fetch_change_data(time_param=api_time)
    if change_data:
        _snapshot_cache[time_str] = change_data
    return change_data


def _parse_change_value(value: str) -> float:
    """
    解析涨跌幅数据
    格式：'市值|涨跌幅'，如 '579.71|0.17'
    返回涨跌幅百分比
    """
    try:
        if "|" in value:
            parts = value.split("|")
            return float(parts[1])
        return float(value)
    except (ValueError, IndexError):
        return 0.0


def _build_treemap_node(node: Dict, change_data: Dict, level: int = 0) -> Optional[Dict]:
    """
    递归构建 treemap 节点，合并涨跌幅数据

    Args:
        node: 行业树节点（来自 getSwMapScale）
        change_data: 涨跌幅字典 {code: '市值|涨跌幅'}
        level: 当前层级（0=根, 1=一级行业, 2=二级行业）

    Returns:
        treemap 节点字典，或 None（根节点不返回）
    """
    code = node.get("code", "")
    name = node.get("name", "")
    scale = float(node.get("scale", 0) or 0)
    up_count = int(node.get("upCount", 0) or 0)
    down_count = int(node.get("downCount", 0) or 0)

    # 获取涨跌幅
    change_raw = change_data.get(code, "0|0") if change_data else "0|0"
    change_percent = _parse_change_value(change_raw)

    children_raw = node.get("children") or []
    children = []
    for child in children_raw:
        child_node = _build_treemap_node(child, change_data, level + 1)
        if child_node:
            children.append(child_node)

    # 根节点（code="0", name="全部"）不返回，直接返回其 children
    if level == 0:
        return None

    result = {
        "code": code,
        "name": name,
        "value": max(scale, 1),  # ECharts treemap 用 value 决定面积
        "changePercent": round(change_percent, 2),
        "riseCount": up_count,
        "fallCount": down_count,
    }

    if children:
        result["children"] = children

    return result


def _compute_weighted_change(node: Dict) -> float:
    """
    计算节点的加权平均涨跌幅（用于父级颜色）
    权重 = 流通市值（value）
    """
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


@router.get("/industry")
def get_industry_sectors(
    time: str = Query("", description="快照时间，如 '10:00'，空字符串表示实时数据"),
):
    """
    获取行业板块树形数据（申万行业分类）

    返回层级结构：
    - 一级行业（电子、银行、医药生物等）作为父节点
    - 二级行业（半导体、国有大型银行等）作为子节点
    - 父节点颜色 = 子节点加权平均涨跌幅

    参数：
    - time: 快照时间（如 '10:00'），为空则返回实时数据
    """
    cache = _get_cache()
    if not cache or not cache["scale_data"]:
        raise HTTPException(status_code=502, detail="数据获取失败")

    scale_data = cache["scale_data"]

    # 根据 time 参数选择数据源
    if time:
        change_data = _get_snapshot_data(time)
        if not change_data:
            raise HTTPException(status_code=502, detail=f"历史快照数据获取失败：{time}")
    else:
        change_data = cache["change_data"]

    # 构建层级树形数据
    treemap_nodes = []
    for node in scale_data:
        result = _build_treemap_node(node, change_data, level=0)
        # 根节点返回 None，其 children 就是所有一级行业
        if result is None and node.get("children"):
            for child in node["children"]:
                treemap_node = _build_treemap_node(child, change_data, level=1)
                if treemap_node:
                    treemap_nodes.append(treemap_node)

    # 为每个父节点计算加权平均涨跌幅（用于颜色显示）
    for node in treemap_nodes:
        children = node.get("children") or []
        if children:
            node["changePercent"] = _compute_weighted_change(node)

    # 按 changePercent 降序排序（一级行业之间）
    treemap_nodes.sort(key=lambda n: n.get("changePercent", 0), reverse=True)

    return {
        "total": len(treemap_nodes),
        "sectors": treemap_nodes,
        "snapshotTime": time or None,
    }


@router.get("/market-indices")
def get_market_indices():
    """
    获取市场指数数据

    返回主要市场指数的实时行情：
    - 上证指数、深证成指、创业板指、科创50
    - 上证50、沪深300、中证500
    """
    data = _get_market_indices_cache()
    if not data:
        raise HTTPException(status_code=502, detail="市场指数数据获取失败")
    return {"indices": data}


@router.get("/market-overview")
def get_market_overview():
    """
    获取市场概览数据（涨跌家数 + 量能）

    数据来源：东方财富 push2delay API（全量 A 股实时行情）
    返回：
    - riseCount: 上涨家数
    - fallCount: 下跌家数
    - flatCount: 平盘家数
    - totalAmount: 当日成交额（元）
    """
    data = _get_market_overview_cache()
    if not data:
        raise HTTPException(status_code=502, detail="市场概览数据获取失败")
    return data


@router.get("/{sector_code}/stocks")
def get_sector_stocks(
    sector_code: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=500, description="每页数量"),
):
    """
    获取板块成分股列表

    注意：时到量化 API 不提供成分股数据，此接口暂返回空列表。
    如需成分股功能，需要接入其他数据源（如东方财富、新浪等）。
    """
    # TODO: 接入成分股数据源
    logger.info(f"成分股接口调用：sector_code={sector_code}, page={page}, page_size={page_size}")
    return {"total": 0, "stocks": []}


# =============================================================================
# 个股云图接口
# =============================================================================

def _fetch_stock_map_scale() -> Optional[List[Dict]]:
    """获取个股云图结构数据（行业→子行业→个股 三级树）"""
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
        logger.warning(f"时到量化个股 scale 接口返回异常：{result.get('msg')}")
        return None
    except Exception as e:
        logger.error(f"时到量化个股 scale 接口异常：{e}", exc_info=True)
        return None


def _fetch_stock_map_data(time_param: str = "", trade_date: str = "") -> Optional[Dict]:
    """获取个股涨跌幅数据（扁平字典：code -> '价格|涨跌幅'）"""
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
        logger.warning(f"时到量化个股 data 接口返回异常：{result.get('msg')}")
        return None
    except Exception as e:
        logger.error(f"时到量化个股 data 接口异常：{e}", exc_info=True)
        return None


def _refresh_stock_cache():
    """刷新个股云图缓存"""
    scale_data = _fetch_stock_map_scale()
    change_data = _fetch_stock_map_data()

    if scale_data and change_data:
        _stock_cache["scale_data"] = scale_data
        _stock_cache["change_data"] = change_data
        _stock_cache["timestamp"] = time.time()
        logger.info("个股云图缓存刷新成功")
    else:
        logger.warning(
            f"个股云图缓存刷新失败：scale={scale_data is not None}, change={change_data is not None}"
        )


def _get_stock_cache() -> Optional[Dict]:
    """获取个股云图缓存，过期则刷新"""
    if _stock_cache["scale_data"] is None or (time.time() - _stock_cache["timestamp"]) > _stock_cache["ttl"]:
        _refresh_stock_cache()
    return _stock_cache


def _get_stock_snapshot_data(time_str: str) -> Optional[Dict]:
    """获取个股历史快照数据"""
    if time_str in _stock_snapshot_cache:
        return _stock_snapshot_cache[time_str]
    api_time = _convert_time_format(time_str)
    change_data = _fetch_stock_map_data(time_param=api_time)
    if change_data:
        _stock_snapshot_cache[time_str] = change_data
    return change_data


def _build_stock_treemap_node(node: Dict, change_data: Dict) -> Optional[Dict]:
    """
    递归构建个股云图 treemap 节点

    数据结构：
    - Level 0: 根节点（code="0", name="全部"）
    - Level 1: 一级行业（电子、银行等）
    - Level 2: 二级行业（半导体、国有大型银行等）
    - Level 3: 个股（寒武纪、海光信息等，叶子节点）
    """
    code = node.get("code", "")
    name = node.get("name", "")
    scale = float(node.get("scale", 0) or 0)
    up_count = int(node.get("upCount", 0) or 0)
    down_count = int(node.get("downCount", 0) or 0)

    # 获取涨跌幅
    change_raw = change_data.get(code, "0|0") if change_data else "0|0"
    change_percent = _parse_change_value(change_raw)

    children_raw = node.get("children") or []
    children = []
    for child in children_raw:
        child_node = _build_stock_treemap_node(child, change_data)
        if child_node:
            children.append(child_node)

    # 根节点不返回
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


@router.get("/stock-map")
def get_stock_cloud_map(
    time: str = Query("", description="快照时间，如 '10:00'，空字符串表示实时数据"),
):
    """
    获取个股云图数据（三级树：行业→子行业→个股）

    参数：
    - time: 快照时间（如 '10:00'），为空则返回实时数据
    """
    cache = _get_stock_cache()
    if not cache or not cache["scale_data"]:
        raise HTTPException(status_code=502, detail="个股云图数据获取失败")

    scale_data = cache["scale_data"]

    if time:
        change_data = _get_stock_snapshot_data(time)
        if not change_data:
            raise HTTPException(
                status_code=502,
                detail=f"个股历史快照数据获取失败：{time}（该时间点暂无数据）",
            )
    else:
        change_data = cache["change_data"]

    # 构建三级树形数据
    treemap_nodes = []
    for node in scale_data:
        result = _build_stock_treemap_node(node, change_data)
        if result is None and node.get("children"):
            for child in node["children"]:
                treemap_node = _build_stock_treemap_node(child, change_data)
                if treemap_node:
                    treemap_nodes.append(treemap_node)

    # 为每个父节点计算加权平均涨跌幅
    for node in treemap_nodes:
        children = node.get("children") or []
        if children:
            node["changePercent"] = _compute_weighted_change(node)

    # 按 changePercent 降序排序
    treemap_nodes.sort(key=lambda n: n.get("changePercent", 0), reverse=True)

    return {
        "total": len(treemap_nodes),
        "sectors": treemap_nodes,
        "snapshotTime": time or None,
    }


# =============================================================================
# ETF 云图接口
# =============================================================================

def _fetch_etf_map_scale() -> Optional[List[Dict]]:
    """获取 ETF 云图结构数据（扁平列表，code -> scale -> name）"""
    try:
        resp = _session.get(
            ETF_MAP_SCALE_URL,
            params={"etfType": "1"},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") == 200:
            data = result.get("data")
            if data and len(data) > 0:
                root = data[0]
                return root.get("children") or []
        logger.warning(f"时到量化 ETF scale 接口返回异常：{result.get('msg')}")
        return None
    except Exception as e:
        logger.error(f"时到量化 ETF scale 接口异常：{e}", exc_info=True)
        return None


def _fetch_etf_map_data(period: str = "yesterday") -> Optional[Dict]:
    """
    获取 ETF 涨跌幅数据
    period: yesterday/week/month/quarter/half_year/ytd/year/three_year
    """
    type_num = ETF_PERIOD_MAP.get(period, 1)
    try:
        resp = _session.get(
            ETF_MAP_DATA_URL,
            params={"type": str(type_num), "etfType": "1"},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") == 200:
            return result.get("data")
        logger.warning(f"时到量化 ETF data 接口返回异常：{result.get('msg')}")
        return None
    except Exception as e:
        logger.error(f"时到量化 ETF data 接口异常：{e}", exc_info=True)
        return None


def _refresh_etf_cache():
    """刷新 ETF 云图缓存（只刷新 scale，change 按 period 分别缓存）"""
    scale_data = _fetch_etf_map_scale()
    if scale_data:
        _etf_cache["scale_data"] = scale_data
        _etf_cache["timestamp"] = time.time()
        logger.info("ETF 云图 scale 缓存刷新成功")
    else:
        logger.warning("ETF 云图 scale 缓存刷新失败")


def _get_etf_cache() -> Optional[Dict]:
    """获取 ETF 云图缓存，过期则刷新"""
    if _etf_cache["scale_data"] is None or (time.time() - _etf_cache["timestamp"]) > _etf_cache["ttl"]:
        _refresh_etf_cache()
    return _etf_cache


def _get_etf_change_data(period: str) -> Optional[Dict]:
    """获取 ETF 涨跌幅数据（按 period 缓存）"""
    if period in _etf_cache["change_data"]:
        return _etf_cache["change_data"][period]
    change_data = _fetch_etf_map_data(period)
    if change_data:
        _etf_cache["change_data"][period] = change_data
    return change_data


def _build_etf_treemap_node(
    etf_item: Dict,
    change_data: Dict,
    period: str = "today",
) -> Optional[Dict]:
    """构建单个 ETF treemap 节点"""
    code = etf_item.get("code", "")
    name = etf_item.get("name", "")
    scale = float(etf_item.get("scale", 0) or 0)

    # 涨跌幅数据格式：'价格|涨跌幅'
    change_raw = change_data.get(code, "0|0") if change_data else "0|0"
    change_percent = _parse_change_value(change_raw)

    return {
        "code": code,
        "name": name,
        "value": max(scale, 1),
        "changePercent": round(change_percent, 2),
    }


@router.get("/etf-map")
def get_etf_cloud_map(
    period: str = Query("yesterday", description="涨跌幅周期：yesterday/week/month/quarter/half_year/ytd/year/three_year"),
    top_n: int = Query(100, ge=10, le=500, description="选取市值前 N 的 ETF"),
):
    """
    获取 ETF 云图数据（扁平列表，按市值排序）

    参数：
    - period: 涨跌幅周期（yesterday=昨日涨跌幅, week=近一周, month=近一月,
              quarter=近三月, half_year=近半年, ytd=今年以来, year=近一年, three_year=近三年）
    - top_n: 选取市值前 N 的 ETF（默认 100）
    """
    cache = _get_etf_cache()
    if not cache or not cache["scale_data"]:
        raise HTTPException(status_code=502, detail="ETF 云图数据获取失败")

    scale_data = cache["scale_data"]

    # 获取指定周期的涨跌幅数据
    change_data = _get_etf_change_data(period)
    # 外部 API 对部分周期（ytd/year/three_year）可能返回空数据，优雅降级返回空列表
    if not change_data:
        logger.warning(f"ETF 涨跌幅数据为空：{period}，返回空列表")
        return {
            "total": 0,
            "sectors": [],
            "period": period,
            "periodLabel": {
                "yesterday": "昨日涨跌幅",
                "week": "近一周",
                "month": "近一月",
                "quarter": "近三月",
                "half_year": "近半年",
                "ytd": "今年以来",
                "year": "近一年",
                "three_year": "近三年",
            }.get(period, period),
        }

    # 构建 ETF 节点并按市值降序排序
    etf_nodes = []
    for item in scale_data:
        node = _build_etf_treemap_node(item, change_data, period)
        if node:
            etf_nodes.append(node)

    # 按市值（scale）降序排序，取前 top_n
    etf_nodes.sort(key=lambda n: n["value"], reverse=True)
    etf_nodes = etf_nodes[:top_n]

    return {
        "total": len(etf_nodes),
        "sectors": etf_nodes,
        "period": period,
        "periodLabel": {
            "yesterday": "昨日涨跌幅",
            "week": "近一周",
            "month": "近一月",
            "quarter": "近三月",
            "half_year": "近半年",
            "ytd": "今年以来",
            "year": "近一年",
            "three_year": "近三年",
        }.get(period, period),
    }


# =============================================================================
# 概念云图接口
# =============================================================================

def _fetch_concept_map_scale() -> Optional[List[Dict]]:
    """获取概念云图结构数据（扁平化所有子概念）"""
    try:
        resp = _session.get(
            CONCEPT_MAP_SCALE_URL,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") == 200:
            data = result.get("data")
            if data and len(data) > 0:
                root = data[0]
                categories = root.get("children") or []
                # 扁平化：展开所有子概念
                flat_items = []
                for cat in categories:
                    children = cat.get("children") or []
                    for child in children:
                        flat_items.append({
                            "code": child.get("code", ""),
                            "name": child.get("name", ""),
                            "scale": child.get("scale", 0),
                            "category": cat.get("name", ""),
                        })
                return flat_items
        logger.warning(f"时到量化概念 scale 接口返回异常：{result.get('msg')}")
        return None
    except Exception as e:
        logger.error(f"时到量化概念 scale 接口异常：{e}", exc_info=True)
        return None


def _fetch_concept_map_data(period: str = "yesterday") -> Optional[Dict]:
    """
    获取概念涨跌幅数据
    period: yesterday/week/month/quarter/half_year/ytd/year/three_year
    """
    type_num = ETF_PERIOD_MAP.get(period, 1)
    try:
        resp = _session.get(
            CONCEPT_MAP_DATA_URL,
            params={"type": str(type_num)},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") == 200:
            return result.get("data")
        logger.warning(f"时到量化概念 data 接口返回异常：{result.get('msg')}")
        return None
    except Exception as e:
        logger.error(f"时到量化概念 data 接口异常：{e}", exc_info=True)
        return None


def _refresh_concept_cache():
    """刷新概念云图缓存（只刷新 scale，change 按 period 分别缓存）"""
    scale_data = _fetch_concept_map_scale()
    if scale_data:
        _concept_cache["scale_data"] = scale_data
        _concept_cache["timestamp"] = time.time()
        logger.info("概念云图 scale 缓存刷新成功")
    else:
        logger.warning("概念云图 scale 缓存刷新失败")


def _get_concept_cache() -> Optional[Dict]:
    """获取概念云图缓存，过期则刷新"""
    if _concept_cache["scale_data"] is None or (time.time() - _concept_cache["timestamp"]) > _concept_cache["ttl"]:
        _refresh_concept_cache()
    return _concept_cache


def _get_concept_change_data(period: str) -> Optional[Dict]:
    """获取概念涨跌幅数据（按 period 缓存）"""
    if period in _concept_cache["change_data"]:
        return _concept_cache["change_data"][period]
    change_data = _fetch_concept_map_data(period)
    if change_data:
        _concept_cache["change_data"][period] = change_data
    return change_data


def _build_concept_treemap_node(
    concept_item: Dict,
    change_data: Dict,
) -> Optional[Dict]:
    """构建单个概念 treemap 节点"""
    code = concept_item.get("code", "")
    name = concept_item.get("name", "")
    scale = float(concept_item.get("scale", 0) or 0)

    # 涨跌幅数据格式：'市值|涨跌幅'
    change_raw = change_data.get(code, "0|0") if change_data else "0|0"
    change_percent = _parse_change_value(change_raw)

    return {
        "code": code,
        "name": name,
        "value": max(scale, 1),
        "changePercent": round(change_percent, 2),
    }


@router.get("/concept-map")
def get_concept_cloud_map(
    period: str = Query("yesterday", description="涨跌幅周期：yesterday/week/month/quarter/half_year/ytd/year/three_year"),
    top_n: int = Query(100, ge=10, le=500, description="选取市值前 N 的概念"),
):
    """
    获取概念云图数据（扁平列表，按市值排序）

    参数：
    - period: 涨跌幅周期（yesterday=昨日涨跌幅, week=近一周, month=近一月,
              quarter=近三月, half_year=近半年, ytd=今年以来, year=近一年, three_year=近三年）
    - top_n: 选取市值前 N 的概念（默认 100）
    """
    cache = _get_concept_cache()
    if not cache or not cache["scale_data"]:
        raise HTTPException(status_code=502, detail="概念云图数据获取失败")

    scale_data = cache["scale_data"]

    # 获取指定周期的涨跌幅数据
    change_data = _get_concept_change_data(period)
    # 外部 API 对部分周期（ytd/year/three_year）可能返回空数据，优雅降级返回空列表
    if not change_data:
        logger.warning(f"概念涨跌幅数据为空：{period}，返回空列表")
        return {
            "total": 0,
            "sectors": [],
            "period": period,
            "periodLabel": {
                "yesterday": "昨日涨跌幅",
                "week": "近一周",
                "month": "近一月",
                "quarter": "近三月",
                "half_year": "近半年",
                "ytd": "今年以来",
                "year": "近一年",
                "three_year": "近三年",
            }.get(period, period),
        }

    # 构建概念节点并按市值降序排序
    concept_nodes = []
    for item in scale_data:
        node = _build_concept_treemap_node(item, change_data)
        if node:
            concept_nodes.append(node)

    # 按市值（scale）降序排序，取前 top_n
    concept_nodes.sort(key=lambda n: n["value"], reverse=True)
    concept_nodes = concept_nodes[:top_n]

    return {
        "total": len(concept_nodes),
        "sectors": concept_nodes,
        "period": period,
        "periodLabel": {
            "yesterday": "昨日涨跌幅",
            "week": "近一周",
            "month": "近一月",
            "quarter": "近三月",
            "half_year": "近半年",
            "ytd": "今年以来",
            "year": "近一年",
            "three_year": "近三年",
        }.get(period, period),
    }

