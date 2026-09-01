# -*- coding: utf-8 -*-
"""
===================================
板块数据接口（申万行业分类 - 层级树形结构）
===================================

职责：
1. GET /api/v1/sector/industry - 行业板块树形数据（一级行业包含二级行业子节点）
2. GET /api/v1/sector/{sector_code}/stocks - 板块成分股列表
3. GET /api/v1/sector/market-indices - 市场指数数据（上证、深证、创业板等）
4. GET /api/v1/sector/market-overview - 市场概览（涨跌家数、成交额、涨跌停家数、量能）
5. GET /api/v1/sector/northbound-flow - 北向资金（沪深港通）净流入
6. GET /api/v1/sector/market-fund-flow - 大盘主力资金净流入

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
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

import requests
from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------- 配置 ----------
# 连接超时 5s，读取超时 10s（东财接口偶发慢响应）
REQUEST_TIMEOUT = (5, 10)
# 缓存 TTL（秒）：5 分钟（涨跌幅实时性要求高）
CACHE_TTL = 300
# 并发线程数（获取板块资金流历史）
FUND_FLOW_MAX_WORKERS = 5

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
    {"secid": "1.000681", "name": "科创板指", "code": "000681"},
    {"secid": "1.000016", "name": "上证50", "code": "000016"},
    {"secid": "1.000300", "name": "沪深300", "code": "000300"},
    {"secid": "0.399905", "name": "中证500", "code": "399905"},
    {"secid": "0.399303", "name": "国证2000", "code": "399303"},
    {"secid": "1.000688", "name": "科创50", "code": "000688"},
    {"secid": "0.899050", "name": "北证50", "code": "899050"},
]

# 欧美股主要指数配置。
# secid 前缀规则（东方财富行情）：
#   - 美股主要指数（道琼斯/标普/纳斯达克/纳指100）使用 100. 前缀；
#   - 中国金龙指数、费城半导体等美股行业/概念指数在东财「美股」板块使用 251. 前缀
#     （对应 quote.eastmoney.com/gb/zsXXX.html 的 unify/r/251.xxx 路由）。
# 纳指金融100、纳指互联网东财未单独收录行情页，先以 251. 前缀尝试，
# 若接口无返回则前端 IndexCard 优雅降级显示 --（不影响其余卡片）。
MARKET_INDICES_US = [
    {"secid": "100.DJIA", "name": "道琼斯", "code": "DJIA"},
    {"secid": "100.SPX", "name": "标普500", "code": "SPX"},
    {"secid": "100.NDX", "name": "纳斯达克", "code": "NDX"},
    {"secid": "100.NDX100", "name": "纳斯达克100", "code": "NDX100"},
    {"secid": "251.HXC", "name": "纳指金龙中国", "code": "HXC"},
    {"secid": "251.SOX", "name": "费城半导体指数", "code": "SOX"},
]

# 日韩主要指数配置（secid 前缀 100，对应东财全球指数 unify/r/100.xxx 路由）。
# 韩国综指即 KOSPI（韩国综合股价指数），与 KOSDAQ（韩国创业板）并列展示。
MARKET_INDICES_JP_KR = [
    {"secid": "100.N225", "name": "日经指数", "code": "N225"},
    {"secid": "100.KS11", "name": "韩国KOSPI", "code": "KS11"},
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

# ---------- 市场指数缓存（按市场分别缓存：{'a': {...}, 'us': {...}}） ----------
_index_cache: Dict[str, Dict] = {}

# ---------- 市场概览缓存（涨跌家数 + 量能） ----------
# 数据来源：东方财富 push2delay API（全量 A 股实时行情）
# push2delay 每次最多返回 100 条，需分页获取全量 ~5800 条数据
EASTMONEY_MARKET_URL = "http://push2delay.eastmoney.com/api/qt/clist/get"
# A 股全市场筛选条件：沪深主板 + 创业板 + 科创板 + 北交所
A_SHARE_FILTER = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048"

# 北向资金（沪深港通）实时资金接口
# 注意：自 2024-08 起北向资金实时数据停止盘中披露，接口可能返回空数据
EASTMONEY_NORTHBOUND_URL = "https://push2.eastmoney.com/api/qt/kamt/get"

# 大盘资金流日线接口（上证指数，用于大盘主力净流入与占比）
EASTMONEY_FFLOW_DAYKLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"

_overview_cache = {
    "data": None,
    "timestamp": 0,
    "ttl": 60,  # 60 秒缓存
}

# ---------- 北向资金 / 大盘主力缓存（60 秒） ----------
_flow_cache = {
    "northbound": None,
    "market_fund_flow": None,
    "timestamp": 0,
    "ttl": 60,
}

# ---------- 板块列表缓存（60 秒，按板块类型分别缓存） ----------
_board_list_cache = {
    "data": {},  # {"industry": [...], "concept": [...]}
    "timestamp": 0,
    "ttl": 60,
}


def _fetch_market_indices(market: str = "a") -> Optional[List[Dict]]:
    """获取市场指数数据（东方财富 API，主域名失败则 fallback 到延迟域名）。

    market: 'a' 返回 A 股主要指数，'us' 返回欧美股主要指数。
    """
    if market == "us":
        indices_cfg = MARKET_INDICES_US
    elif market == "jp-kr":
        indices_cfg = MARKET_INDICES_JP_KR
    else:
        indices_cfg = MARKET_INDICES
    secids = ",".join([idx["secid"] for idx in indices_cfg])
    # 构建 code → 自定义名称的映射，使用我们定义的名称而非 API 返回的名称
    code_name_map = {idx["code"]: idx["name"] for idx in indices_cfg}

    for url in [EASTMONEY_INDEX_URL, EASTMONEY_INDEX_URL_DELAY]:
        try:
            resp = _session.get(
                url,
                params={
                    "fltt": "2",
                    # f15=最高 f16=最低 f18=昨收 用于派生指数振幅（指数无成交额，海外指数 f6 为空）
                    "fields": "f2,f3,f4,f5,f6,f12,f14,f15,f16,f18",
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
                    change = item.get("f4", "-")  # 涨跌点数
                    amount = item.get("f6", "-")  # 成交额（元，海外指数通常为空）
                    # 成交额无效（空标记或 0）时置 None，前端据此降级显示振幅而非「成交 0.00亿」
                    amount_val = amount
                    if amount_val in ("-", "", 0, "0", "0.0", "0.00", None):
                        amount_val = None
                    else:
                        try:
                            amount_val = float(amount_val)
                            if amount_val <= 0:
                                amount_val = None
                        except (TypeError, ValueError):
                            amount_val = None
                    high = item.get("f15", "-")  # 当日最高
                    low = item.get("f16", "-")  # 当日最低
                    pre_close = item.get("f18", "-")  # 昨收
                    code = item.get("f12", "")
                    # 优先使用自定义名称，fallback 到 API 返回的名称
                    name = code_name_map.get(code, item.get("f14", ""))
                    indices.append({
                        "name": name,
                        "code": code,
                        "price": price if price != "-" else None,
                        "changePercent": change_pct if change_pct != "-" else None,
                        "change": change if change != "-" else None,
                        "amount": amount_val,
                        "high": high if high != "-" else None,
                        "low": low if low != "-" else None,
                        "preClose": pre_close if pre_close != "-" else None,
                    })
                return indices
            logger.warning(f"东方财富指数接口({url})返回异常：{result}")
        except Exception as e:
            logger.error(f"东方财富指数接口({url})异常：{e}", exc_info=True)
    return None


def _get_market_indices_cache(market: str = "a") -> Optional[List[Dict]]:
    """获取市场指数缓存，过期则刷新（按市场分别缓存）。"""
    cache = _index_cache.setdefault(market, {"data": None, "timestamp": 0, "ttl": 60})
    if cache["data"] is None or (time.time() - cache["timestamp"]) > cache["ttl"]:
        data = _fetch_market_indices(market)
        if data:
            cache["data"] = data
            cache["timestamp"] = time.time()
    return cache["data"]


# ---------------------------------------------------------------------------
# 昨日全市场成交额（元）
#
# 背景：东方财富历史日线接口（push2his / kline）在当前网络被代理拦截，
# 且运行环境未配置 TUSHARE_TOKEN，无法直接拿到「昨日全市场成交额」。
# 当前 totalAmount（今日全市场成交额）来自东方财富 push2delay 全市场快照，
# 因此「昨日成交额」也需保持「全市场」口径，才能正确计算放量/缩量。
#
# 解决方案：直连腾讯证券个股日线接口（proxy.finance.qq.com，该域名当前可用），
# 对全 A 股票并发拉取「前一交易日」成交额（amount，单位万元）并求和，
def _fetch_market_overview() -> Optional[Dict]:
    """
    获取全市场涨跌家数和量能数据（东方财富 push2delay API）

    数据来源：push2delay.eastmoney.com（东方财富延迟行情接口）
    接口限制：每次最多返回 100 条，需分页获取全量 ~5800 条 A 股数据
    返回字段：
      - riseCount: 上涨家数
      - fallCount: 下跌家数
      - flatCount: 平盘家数
      - totalAmount: 当日成交额（元，东方财富全市场快照）
      - volumeRatio: 市场量比（加权平均，相较于过去 5 日同时刻）
      - limitUpCount: 涨停家数（按板块涨跌幅限制精确判断）
      - limitDownCount: 跌停家数
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
                    # f2=最新价, f3=涨跌幅, f5=成交量 (手), f6=成交额 (元),
                    # f10=量比, f12=代码, f14=名称, f17=昨量 (手)
                    "fields": "f2,f3,f5,f6,f10,f12,f14,f17",
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
        limit_up_count = 0
        limit_down_count = 0
        total_amount = 0.0
        # 量比加权平均（权重=成交额）
        weighted_volume_ratio_sum = 0.0
        total_amount_for_ratio = 0.0

        for stock in all_stocks:
            change_pct = stock.get("f3")
            amount = stock.get("f6")
            volume = stock.get("f5")  # 今日成交量（手）
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
            # 涨跌停判断（按板块涨跌幅限制，容差 0.1% 覆盖涨停价四舍五入误差）
            limit_ratio = _get_limit_ratio(str(stock.get("f12", "")), str(stock.get("f14", "")))
            if change_pct >= limit_ratio - 0.1:
                limit_up_count += 1
            elif change_pct <= -(limit_ratio - 0.1):
                limit_down_count += 1
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
                        except (ValueError, TypeError):
                            pass
                except (ValueError, TypeError):
                    pass

        # 计算市场整体量比（成交额加权平均）
        volume_ratio = None
        if total_amount_for_ratio > 0:
            volume_ratio = round(weighted_volume_ratio_sum / total_amount_for_ratio, 2)

        return {
            "riseCount": rise_count,
            "fallCount": fall_count,
            "flatCount": flat_count,
            "totalAmount": total_amount,
            "volumeRatio": volume_ratio,
            "limitUpCount": limit_up_count,
            "limitDownCount": limit_down_count,
        }
    except Exception as e:
        logger.error(f"东方财富全市场接口异常：{e}", exc_info=True)
        return None


def _get_limit_ratio(code: str, name: str) -> float:
    """获取个股涨跌幅限制（%）：创业板/科创板 20%，北交所 30%，主板 ST 5%，其余 10%

    注：新股上市首日、退市整理期无涨跌幅限制，此处按常规交易规则近似判断。
    """
    if code.startswith(("300", "301", "302", "688", "689")):
        return 20.0
    if code.startswith(("43", "83", "87", "920")):
        return 30.0
    if "ST" in name.upper():
        return 5.0
    return 10.0


def _get_market_overview_cache() -> Optional[Dict]:
    """获取市场概览缓存，过期则刷新"""
    if _overview_cache["data"] is None or (time.time() - _overview_cache["timestamp"]) > _overview_cache["ttl"]:
        data = _fetch_market_overview()
        if data:
            _overview_cache["data"] = data
            _overview_cache["timestamp"] = time.time()
    return _overview_cache["data"]


def _fetch_northbound_flow() -> Optional[Dict]:
    """获取北向资金（沪深港通）净流入数据（东方财富 kamt 接口）

    返回：
      - netInflow: 北向资金净流入（元），字段缺失/接口空数据时为 None
      - name: 数据名称
    注意：自 2024-08 起北向资金实时数据停止盘中披露，接口可能返回空数据，
    此时返回 netInflow=None，前端展示占位符而非报错。
    """
    try:
        resp = _session.get(
            EASTMONEY_NORTHBOUND_URL,
            params={
                "fields1": "f1,f2,f3,f4",
                "fields2": "f51,f52,f53,f54,f55,f56",
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        result = resp.json()
        data = result.get("data") or {}
        # 北向：hk2sh=沪股通（港→沪），hk2sz=深股通（港→深）
        # dayNetAmtIn=当日净买入（单位：万元）；2024-08 后北向净流入停披露，返回 0
        net_inflow_wan = 0.0
        found = False
        for item_key in ("hk2sh", "hk2sz"):
            item = data.get(item_key) or {}
            raw = item.get("dayNetAmtIn")
            if raw is None or raw == "-":
                continue
            try:
                net_inflow_wan += float(raw)
                found = True
            except (ValueError, TypeError):
                continue
        # 北向两个通道净买入均为 0：视为停披露（而非真实零流入），返回 None
        if not found or net_inflow_wan == 0:
            logger.warning("北向资金接口返回空数据（2024-08 后可能停披露）")
            return {"netInflow": None, "name": "北向资金", "date": None}
        return {
            "netInflow": round(net_inflow_wan * 1e4, 2),  # 万元 → 元
            "name": "北向资金",
            "date": data.get("hk2sh", {}).get("date2"),
        }
    except Exception as e:
        logger.error(f"北向资金接口异常：{e}", exc_info=True)
        return None


def _get_northbound_flow_cache() -> Optional[Dict]:
    """获取北向资金缓存，过期则刷新"""
    if _flow_cache["northbound"] is None or (time.time() - _flow_cache["timestamp"]) > _flow_cache["ttl"]:
        data = _fetch_northbound_flow()
        if data:
            _flow_cache["northbound"] = data
            _flow_cache["timestamp"] = time.time()
    return _flow_cache["northbound"]


def _fetch_market_fund_flow() -> Optional[Dict]:
    """获取大盘主力资金净流入（东方财富大盘资金流日线接口）

    数据来源：push2his.eastmoney.com/api/qt/stock/fflow/daykline/get（上证指数，日线）
    klines 行格式（fields2）：f51=日期, f52=主力净流入(元), f57=主力净流入占比(%), f62=收盘价
    返回：
      - mainNetInflow: 主力净流入（元）
      - mainNetInflowPercent: 主力净流入占比（%）
      - date: 数据日期（最近一个交易日）
    注：该接口为日线，盘中展示的是最近交易日收盘数据；失败时 fallback 到 ulist 实时接口（无占比）。
    """
    # 主接口：大盘资金流日线（含主力占比与日期）
    try:
        resp = _session.get(
            EASTMONEY_FFLOW_DAYKLINE_URL,
            params={
                "lmt": "1",
                "klt": "101",
                "secid": "1.000001",
                "fields1": "f1,f2,f3,f7",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        result = resp.json()
        klines = result.get("data", {}).get("klines") or []
        if klines:
            items = klines[-1].split(",")
            # f51=日期, f52=主力净流入, f57=主力净流入占比
            net_inflow = float(items[1]) if items[1] not in ("", "-") else None
            percent = float(items[6]) if items[6] not in ("", "-") else None
            return {
                "mainNetInflow": round(net_inflow, 2) if net_inflow is not None else None,
                "mainNetInflowPercent": round(percent, 2) if percent is not None else None,
                "date": items[0] or None,
            }
        logger.warning(f"大盘资金流日线接口返回空数据：{result}")
    except Exception as e:
        logger.error(f"大盘资金流日线接口异常：{e}", exc_info=True)

    # fallback：ulist 实时接口（无占比/日期）
    for url in [EASTMONEY_INDEX_URL, EASTMONEY_INDEX_URL_DELAY]:
        try:
            resp = _session.get(
                url,
                params={
                    "fltt": "2",
                    # f62=主力净流入(元)
                    "fields": "f2,f3,f12,f14,f62",
                    "secids": "1.000001,0.399001",
                },
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("rc") == 0 and result.get("data") and result["data"].get("diff"):
                items = result["data"]["diff"]
                net_inflow = 0.0
                for item in items:
                    raw_flow = item.get("f62", "-")
                    if raw_flow not in (None, "-"):
                        try:
                            net_inflow += float(raw_flow)
                        except (ValueError, TypeError):
                            pass
                return {
                    "mainNetInflow": round(net_inflow, 2) if net_inflow else None,
                    "mainNetInflowPercent": None,
                    "date": None,
                }
            logger.warning(f"东方财富主力资金接口({url})返回异常：{result}")
        except Exception as e:
            logger.error(f"东方财富主力资金接口({url})异常：{e}", exc_info=True)
    return None


def _get_market_fund_flow_cache() -> Optional[Dict]:
    """获取大盘主力缓存，过期则刷新"""
    if _flow_cache["market_fund_flow"] is None or (time.time() - _flow_cache["timestamp"]) > _flow_cache["ttl"]:
        data = _fetch_market_fund_flow()
        if data:
            _flow_cache["market_fund_flow"] = data
            _flow_cache["timestamp"] = time.time()
    return _flow_cache["market_fund_flow"]


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
def get_market_indices(market: str = Query("a", description="市场类型：a=A股，us=欧美股，jp-kr=日韩")):
    """
    获取市场指数数据

    返回主要市场指数的实时行情：
    - market=a：上证指数、深证成指、创业板指、科创50、上证50、沪深300、中证500 等
    - market=us：道琼斯、标普500、纳斯达克、纳斯达克100、纳指金龙中国、纳指金融100、纳指互联网、费城半导体
    - market=jp-kr：日经指数、韩国综指(KOSPI)、韩国KOSDAQ
    """
    if market not in ("a", "us", "jp-kr"):
        raise HTTPException(status_code=400, detail="market 仅支持 a、us 或 jp-kr")
    data = _get_market_indices_cache(market)
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


@router.get("/northbound-flow")
def get_northbound_flow():
    """
    获取北向资金（沪深港通）净流入数据

    数据来源：东方财富 kamt 接口
    注意：自 2024-08 起北向资金实时数据停止盘中披露，接口可能返回空数据，
    此时返回 netInflow=None（200），由前端展示占位符，不抛错。
    """
    data = _get_northbound_flow_cache()
    if not data:
        return {"netInflow": None, "name": "北向资金"}
    return data


@router.get("/market-fund-flow")
def get_market_fund_flow():
    """
    获取大盘主力资金净流入

    数据来源：东方财富 ulist 实时接口（上证指数 + 深证成指主力净流入汇总）
    返回：mainNetInflow（元）、mainNetInflowPercent（%）、date（实时接口为 None）
    """
    data = _get_market_fund_flow_cache()
    if not data:
        return {"mainNetInflow": None, "mainNetInflowPercent": None, "date": None}
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
# 板块资金流历史接口
# =============================================================================

# 东方财富板块资金流 API
EASTMONEY_SECTOR_FLOW_RANK_URL = "http://push2delay.eastmoney.com/api/qt/clist/get"
EASTMONEY_SECTOR_FLOW_KLINE_URL = "http://push2his.eastmoney.com/api/qt/stock/fflow/kline/get"
EASTMONEY_SECTOR_FLOW_KLINE_URL_DELAY = "http://push2delay.eastmoney.com/api/qt/stock/fflow/kline/get"

# 板块资金流历史缓存
_fund_flow_cache: Dict[str, Dict] = {}


def _yuan_to_yi(value: Optional[float]) -> Optional[float]:
    """元 → 亿，保留 2 位小数"""
    if value is None:
        return None
    return round(value / 1e8, 2)


def _fetch_sector_fund_flow_rank(
    sector_type: str = "industry",
    top_n: int = 10,
    max_retries: int = 2,
) -> Optional[List[Dict]]:
    """
    获取板块资金流排行（当日主力净流入降序）

    接口：push2delay.eastmoney.com/api/qt/clist/get
    参数：
    - m:90+t:2 行业板块，m:90+t:3 概念板块
    - fs=m:90+t:2 或 m:90+t:3
    - fid=f62 按主力净流入排序
    - po=1 降序
    """
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
            result = resp.json()
            diff = result.get("data", {}).get("diff", [])
            if not diff:
                logger.warning(f"板块资金流排行返回空数据：sector_type={sector_type}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                return None
            sectors = []
            for item in diff:
                code = item.get("f12", "")
                name = item.get("f14", "")
                main_flow = item.get("f62")
                sectors.append({
                    "code": code,
                    "name": name,
                    "latest": _yuan_to_yi(main_flow) if main_flow and main_flow != "-" else None,
                })
            return sectors
        except Exception as e:
            logger.error(f"板块资金流排行接口异常（attempt {attempt + 1}/{max_retries}）：{e}")
            if attempt < max_retries - 1:
                time.sleep(1)
    return None


def _fetch_sector_fund_flow_kline(
    sector_code: str,
    limit: int = 30,
) -> Optional[List[Dict]]:
    """
    获取单个板块的日线资金流历史序列

    接口：push2his（主）/ push2delay（备）
    参数：
    - secid=90.{BK代码}
    - klt=101 日线
    - lmt=limit 返回天数

    返回 klines 格式：["日期,主力,小单,中单,大单,超大单", ...]
    单位：元
    """
    kline_urls = [
        EASTMONEY_SECTOR_FLOW_KLINE_URL,
        EASTMONEY_SECTOR_FLOW_KLINE_URL_DELAY,
    ]
    params = {
        "secid": f"90.{sector_code}",
        "klt": "101",
        "lmt": str(limit),
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fields1": "f1,f2,f3,f7",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
    }
    for url in kline_urls:
        try:
            resp = _session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            result = resp.json()
            if result.get("rc") != 0:
                logger.warning(f"板块 {sector_code} 资金流接口返回 rc={result.get('rc')}：{url}")
                continue
            klines = result.get("data", {}).get("klines", [])
            if not klines:
                logger.warning(f"板块 {sector_code} 资金流日线数据为空：{url}")
                continue
            parsed = []
            for line in klines:
                parts = line.split(",")
                if len(parts) >= 2:
                    date = parts[0]
                    try:
                        main_flow = float(parts[1]) if parts[1] != "-" else None
                    except (ValueError, TypeError):
                        main_flow = None
                    parsed.append({"date": date, "mainFlow": main_flow})
            return parsed
        except Exception as e:
            logger.warning(f"板块 {sector_code} 资金流接口异常（{url}）：{e}")
            continue
    logger.error(f"板块 {sector_code} 资金流所有接口均失败")
    return None


def _fetch_sector_fund_flow_kline_with_retry(
    sector_code: str,
    limit: int = 30,
    max_retries: int = 3,
) -> Optional[List[Dict]]:
    """带重试的板块资金流日线获取（push2his 存在间歇性网络抖动）"""
    for attempt in range(max_retries):
        result = _fetch_sector_fund_flow_kline(sector_code, limit)
        if result:
            return result
        if attempt < max_retries - 1:
            time.sleep(1.5)
    return None


@router.get("/fund-flow-history")
def get_sector_fund_flow_history(
    sector_type: str = Query("industry", description="板块类型：industry / concept"),
    limit: int = Query(30, ge=5, le=100, description="返回天数"),
    top_n: int = Query(10, ge=1, le=30, description="资金流排名前 N 的板块"),
    sector_codes: Optional[str] = Query(None, description="指定板块代码，逗号分隔，如 BK0475,BK0717"),
):
    """
    获取板块资金流历史序列（日线）

    数据来源：东方财富 push2delay（排行）+ push2his（日线资金流）
    返回：
    - dates: 日期数组
    - sectors: 各板块资金流序列（主力净流入，单位亿，保留2位小数）
    """
    # 解析指定板块代码
    specified_codes = [c.strip() for c in sector_codes.split(",") if c.strip()] if sector_codes else None

    # 缓存 key
    codes_key = ",".join(specified_codes) if specified_codes else f"top{top_n}"
    cache_key = f"{sector_type}_{limit}_{codes_key}"
    cached = _fund_flow_cache.get(cache_key)
    if cached and (time.time() - cached.get("timestamp", 0)) < 300:
        return cached["data"]

    # 1. 确定目标板块列表
    if specified_codes:
        # 使用指定板块代码，需要获取名称
        all_sectors = _fetch_sector_fund_flow_rank(sector_type, 200)
        if not all_sectors:
            raise HTTPException(status_code=502, detail="板块资金流排行数据获取失败")
        code_map = {s["code"]: s for s in all_sectors}
        rank_sectors = []
        for code in specified_codes:
            if code in code_map:
                rank_sectors.append(code_map[code])
        if not rank_sectors:
            raise HTTPException(status_code=404, detail="指定的板块代码未找到")
    else:
        # 按当日主力净流入降序，取 TOP N
        rank_sectors = _fetch_sector_fund_flow_rank(sector_type, top_n)
        if not rank_sectors:
            raise HTTPException(status_code=502, detail="板块资金流排行数据获取失败")

    # 2. 并发获取每个板块的日线资金流历史
    all_dates: set = set()
    sector_histories: List[Dict] = []

    def _fetch_one(sector: Dict) -> Optional[Dict]:
        klines = _fetch_sector_fund_flow_kline_with_retry(sector["code"], limit)
        if not klines:
            return None
        for k in klines:
            all_dates.add(k["date"])
        return {
            "code": sector["code"],
            "name": sector["name"],
            "latest": sector["latest"],
            "klines": {k["date"]: k["mainFlow"] for k in klines},
        }

    with ThreadPoolExecutor(max_workers=FUND_FLOW_MAX_WORKERS) as executor:
        futures = {executor.submit(_fetch_one, s): s for s in rank_sectors}
        for future in as_completed(futures):
            result = future.result()
            if result:
                sector_histories.append(result)

    # 3. 日期排序
    sorted_dates = sorted(all_dates)

    # 4. 折线配色（高区分度色板，不再按涨跌分色）
    color_palette = [
        "#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de",
        "#3ba272", "#fc8452", "#9a60b4", "#ea7ccc", "#d48265",
        "#c23531", "#2f4554", "#61a0a8", "#d48265", "#749f83",
    ]

    # 5. 构建返回数据
    sectors_result = []
    for idx, s in enumerate(sector_histories):
        series = []
        for d in sorted_dates:
            raw = s["klines"].get(d)
            series.append(_yuan_to_yi(raw) if raw is not None else None)
        sectors_result.append({
            "code": s["code"],
            "name": s["name"],
            "series": series,
            "latest": s["latest"],
            "color": color_palette[idx % len(color_palette)],
        })

    result_data = {
        "dates": sorted_dates,
        "sectors": sectors_result,
    }

    # 缓存 5 分钟
    _fund_flow_cache[cache_key] = {
        "data": result_data,
        "timestamp": time.time(),
    }

    return result_data


@router.get("/fund-flow-sectors")
def get_sector_fund_flow_sector_list(
    sector_type: str = Query("industry", description="板块类型：industry / concept"),
):
    """
    获取板块资金流可选板块列表（用于前端多选下拉框）

    返回所有行业/概念板块的代码和名称，按当日主力净流入降序排列。
    """
    all_sectors = _fetch_sector_fund_flow_rank(sector_type, 200)
    if not all_sectors:
        raise HTTPException(status_code=502, detail="板块列表获取失败")
    return {
        "sectors": [{"code": s["code"], "name": s["name"]} for s in all_sectors],
    }


# =============================================================================
# 板块卡片列表接口
# =============================================================================

EASTMONEY_BOARD_LIST_URL = "http://push2.eastmoney.com/api/qt/clist/get"
# 延迟镜像域名：push2 主站偶发不可达时兜底（与指数接口的 delay 备选一致）
EASTMONEY_BOARD_LIST_URL_DELAY = "http://push2delay.eastmoney.com/api/qt/clist/get"


def _fetch_board_list(
    sector_type: str = "industry",
    max_retries: int = 2,
) -> Optional[List[Dict]]:
    """
    获取板块列表数据（行业/概念），包含涨跌幅、总市值、换手率、涨跌家数等字段。

    接口：push2.eastmoney.com/api/qt/clist/get（主），push2delay（延迟镜像备选）
    参数：
    - fs=m:90+t:2 行业板块，m:90+t:3 概念板块
    - fields=f12,f14,f3,f20,f8,f104,f105
      f12=代码, f14=名称, f3=涨跌幅(%), f20=总市值(元),
      f8=换手率(%), f104=上涨家数, f105=下跌家数
    - fid=f3 按涨跌幅排序
    - po=1 降序
    """
    fs_param = "m:90+t:2" if sector_type == "industry" else "m:90+t:3"
    # delay 镜像单次最多返回 100 条，统一按每页 100 条分页抓取（最多 5 页 = 500 条）
    page_size = 100
    max_pages = 5
    for attempt in range(max_retries):
        # 主域名失败则 fallback 到延迟域名（与指数接口模式一致）
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
                    result = resp.json()
                    diff = result.get("data", {}).get("diff", [])
                    if not diff:
                        break  # 本页为空，数据已取完

                    for item in diff:
                        code = item.get("f12", "")
                        name = item.get("f14", "")
                        change_percent_raw = item.get("f3")
                        total_market_cap_raw = item.get("f20")
                        turnover_rate_raw = item.get("f8")
                        rise_count = item.get("f104", 0)
                        fall_count = item.get("f105", 0)

                        # 涨跌幅：百分比值，保留2位小数
                        change_percent = round(float(change_percent_raw), 2) if change_percent_raw is not None else 0.0
                        # 总市值：元 → 亿，保留2位小数
                        total_market_cap = round(float(total_market_cap_raw) / 1e8, 2) if total_market_cap_raw is not None else 0.0
                        # 换手率：百分比值，保留2位小数
                        turnover_rate = round(float(turnover_rate_raw), 2) if turnover_rate_raw is not None else 0.0

                        boards.append({
                            "code": code,
                            "name": name,
                            "changePercent": change_percent,
                            "totalMarketCap": total_market_cap,
                            "turnoverRate": turnover_rate,
                            "riseCount": int(rise_count) if rise_count is not None else 0,
                            "fallCount": int(fall_count) if fall_count is not None else 0,
                        })
                    if len(diff) < page_size:
                        break  # 不足一页，说明已到最后一页

                if not boards:
                    logger.warning(f"板块列表返回空数据：url={url} sector_type={sector_type}")
                    continue

                # 按返回顺序补排名（1 起）
                for idx, board in enumerate(boards, start=1):
                    board["rank"] = idx
                return boards

            except Exception as e:
                logger.error(f"_fetch_board_list 第 {attempt + 1} 次尝试({url})失败：{e}")
        if attempt < max_retries - 1:
            time.sleep(1)
    return None


@router.get("/board-list")
def get_board_list(
    sector_type: str = Query("industry", description="板块类型：industry / concept"),
):
    """
    获取板块卡片列表数据

    返回行业或概念板块的完整信息，包括：
    - 排名、代码、名称
    - 涨跌幅、总市值（亿）、换手率（%)
    - 上涨家数、下跌家数

    注意：领涨股票信息需要额外调用成分股接口，本接口暂不包含。

    数据走 60 秒缓存：上游接口偶发不可达时，命中缓存仍可正常返回，
    避免页面频繁 502；缓存过期后上游仍不可达时才返回 502。
    """
    cache = _board_list_cache
    if (
        sector_type not in cache["data"]
        or (time.time() - cache["timestamp"]) > cache["ttl"]
    ):
        boards = _fetch_board_list(sector_type)
        if not boards:
            raise HTTPException(status_code=502, detail="板块列表获取失败")
        cache["data"][sector_type] = boards
        cache["timestamp"] = time.time()
    boards = cache["data"][sector_type]
    return {
        "sectorType": sector_type,
        "total": len(boards),
        "boards": boards,
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

