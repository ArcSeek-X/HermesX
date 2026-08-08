# -*- coding: utf-8 -*-
"""
===================================
个股 K 线数据接口
===================================

职责：
1. GET /api/v1/kline/search - 股票搜索（代码/名称/拼音/简拼）
2. GET /api/v1/kline/{stock_code}/kline - K 线数据（多周期）
3. GET /api/v1/kline/{stock_code}/info - 股票实时信息

数据来源：
- K 线数据：新浪财经 API（主）+ 东方财富 API（备用）
- 股票搜索：东方财富搜索 API
- 实时行情：东方财富 push2 API
"""

import logging
import re
import time
from typing import Dict, List, Optional

import requests
from fastapi import APIRouter, HTTPException, Query

from api.v1.schemas.kline import (
    KLinePoint,
    KLineResponse,
    StockInfoResponse,
    StockSearchResponse,
    StockSearchResult,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------- 配置 ----------
REQUEST_TIMEOUT = 15

# 新浪财经 K 线 API（新接口，JSONP，单次上限约 1000 条）
SINA_KLINE_URL = "https://quotes.sina.cn/cn/api/jsonp_v2.php"
# 新浪财经 K 线 API（老接口，纯 JSON，datalen 上限更大，可一次拉全量历史）
SINA_KLINE_URL_LEGACY = "http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"
# 东方财富股票搜索 API
EASTMONEY_SEARCH_URL = "http://searchapi.eastmoney.com/api/suggest/get"
# 东方财富实时行情 API
EASTMONEY_STOCK_URL = "http://push2.eastmoney.com/api/qt/stock/get"
EASTMONEY_STOCK_URL_DELAY = "http://push2delay.eastmoney.com/api/qt/stock/get"
# 东方财富 K 线 API（备用）
EASTMONEY_KLINE_URL = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
EASTMONEY_KLINE_URL_DELAY = "http://push2delay.eastmoney.com/api/qt/stock/kline/get"
# 腾讯财经 K 线 API（备用）
# 注意：必须使用 ifzq 域名，web.ifzq.gtimg.cn 会被腾讯 WAF 拦截（501）
TENCENT_KLINE_URL = "https://ifzq.gtimg.cn/appstock/app/fqkline/get"

# 周期 → 新浪 scale 参数映射
# 新浪 scale 单位是分钟：5=5分钟, 15=15分钟, 30=30分钟, 60=60分钟,
# 120=120分钟, 240=日K(4小时), 1200=周K(5天), 7200=月K(30天), 86400=年K(365天)
# 注意：5d 不复用1分钟，改为复用日K（240），在 _get_kline_data 中单独做聚合
SINA_SCALE_MAP = {
    "1m": 1,       # 分时（1 分钟）
    "5m": 5,       # 5 分钟
    "15m": 15,     # 15 分钟
    "30m": 30,     # 30 分钟
    "60m": 60,     # 60 分钟
    "120m": 120,   # 120 分钟
    "5d": 240,     # 5日K（复用日K数据，本地聚合为每5天1根）
    "daily": 240,  # 日 K（240 分钟 = 4 小时交易日）
    "weekly": 1200,    # 周 K（1200 分钟 = 5 天）
    "monthly": 7200,   # 月 K（7200 分钟 = 30 天）
    "yearly": 86400,   # 年 K（86400 分钟 = 365 天）
}

# 东方财富 klt 周期参数映射（备用）
# 注意：5d 复用日K（101），在 _get_kline_data 中单独做聚合
EASTMONEY_KLT_MAP = {
    "1m": 1, "5m": 5, "15m": 15, "30m": 30, "60m": 60, "120m": 120,
    "5d": 101, "daily": 101, "weekly": 102, "monthly": 103, "yearly": 104,
}

# 各周期默认预加载条数（前端不传 limit 时，后端自动使用合理默认值）
PERIOD_DEFAULT_LIMITS = {
    "1m":    240,    # 分时：当日全部分钟数据
    "5m":    240,    # 5分钟：约5个交易日
    "15m":   200,    # 15分钟：约12个交易日
    "30m":   160,    # 30分钟：约20个交易日
    "60m":   120,    # 60分钟：约30个交易日
    "120m":  100,    # 120分钟：约50个交易日
    "5d":    120,    # 5日K：约2.5年（120根 × 5天 = 600根日K聚合）
    "daily": 250,    # 日K：近1年交易日
    "weekly": 150,   # 周K：约3年
    "monthly": 80,   # 月K：约7年
    "yearly": 40,    # 年K：上市以来全部
}

DEFAULT_HEADERS = {
    "Referer": "http://finance.sina.com.cn/",
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
_kline_cache: Dict[str, Dict] = {}
_info_cache: Dict[str, Dict] = {}
_search_cache: Dict[str, Dict] = {}


def _code_to_sina_symbol(stock_code: str) -> str:
    """
    将股票代码转换为新浪 symbol 格式

    规则：
    - 上海（6 开头）：sh{code}
    - 深圳（0/3 开头）：sz{code}
    - 北京（8/4 开头）：bj{code}
    """
    code = stock_code.strip()
    if code.startswith("6"):
        return f"sh{code}"
    elif code.startswith("0") or code.startswith("3"):
        return f"sz{code}"
    elif code.startswith("8") or code.startswith("4"):
        return f"bj{code}"
    else:
        return f"sz{code}"


def _code_to_secid(stock_code: str) -> str:
    """将股票代码转换为东方财富 secid 格式（1.code = 上海，0.code = 深圳）"""
    code = stock_code.strip()
    if code.startswith("6"):
        return f"1.{code}"
    elif code.startswith("0") or code.startswith("3"):
        return f"0.{code}"
    elif code.startswith("8") or code.startswith("4"):
        return f"0.{code}"
    else:
        return f"0.{code}"


def _is_cache_valid(cache_data: Dict, ttl: int = 60) -> bool:
    """检查缓存是否有效"""
    if not cache_data:
        return False
    return (time.time() - cache_data.get("timestamp", 0)) < ttl


def _resolve_pe_ttm(data: dict) -> Optional[float]:
    """
    解析市盈率(TTM)，带 fallback 逻辑：
    - 优先使用 f115（市盈率TTM）
    - 如果 f115 为 0、None 或 "-"，则 fallback 到 f9（市盈率动态）
    - 如果 f9 也无效，则 fallback 到 f164（市盈率静态）
    - 如果都不有效，返回 None
    """
    f115 = data.get("f115")
    if f115 is not None and f115 != "-" and f115 != 0:
        return f115
    # fallback 到 f9（动态市盈率）
    f9 = data.get("f9")
    if f9 is not None and f9 != "-" and f9 != 0:
        return f9
    # fallback 到 f164（静态市盈率）
    f164 = data.get("f164")
    if f164 is not None and f164 != "-" and f164 != 0:
        return f164
    return None


# ---------- K 线数据获取 ----------


def _fetch_kline_from_sina(stock_code: str, period: str, limit: int) -> Optional[List[Dict]]:
    """从新浪财经获取 K 线数据

    优先使用老接口（money.finance.sina.com.cn，纯 JSON，datalen 可传 10000，
    一次即可覆盖上市以来的全部历史）；老接口异常时降级到新接口
    （quotes.sina.cn，JSONP，单次上限约 1000 条）。
    """
    if period not in SINA_SCALE_MAP:
        return None

    symbol = _code_to_sina_symbol(stock_code)
    scale = SINA_SCALE_MAP[period]

    try:
        # 老接口 datalen 支持 10000（对绝大多数 A 股可覆盖上市以来全部数据）
        # 新接口单次上限约 1000，超限会返回空
        sina_limit = min(limit, 10000)
        items = None

        try:
            resp = _session.get(
                SINA_KLINE_URL_LEGACY,
                params={
                    "symbol": symbol,
                    "scale": scale,
                    "ma": "no",
                    "datalen": sina_limit,
                },
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            parsed = resp.json()
            if isinstance(parsed, list):
                items = parsed
        except Exception as e:
            logger.warning(f"新浪老接口 K 线获取失败：{e}")

        # 老接口失败或格式异常时，降级到新接口（JSONP）
        if not items:
            url = f"{SINA_KLINE_URL}/var%20_{symbol}=/CN_MarketDataService.getKLineData"
            resp = _session.get(
                url,
                params={
                    "symbol": symbol,
                    "scale": scale,
                    "ma": "no",
                    "datalen": min(sina_limit, 1000),
                },
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()

            # 解析 JSONP 响应：var_xxx=([{...},{...}])
            text = resp.text
            match = re.search(r"\((\[.*\])\)", text, re.DOTALL)
            if not match:
                logger.warning(f"新浪 K 线 JSONP 解析失败：{text[:200]}")
                return None
            items = __import__("json").loads(match.group(1))

        if not items:
            return None

        # 转换为统一格式
        kline_data = []
        for item in items:
            volume = float(item.get("volume", 0)) if item.get("volume") else None
            close = float(item.get("close", 0))
            kline_data.append({
                "date": item.get("day", ""),
                "open": float(item.get("open", 0)),
                "close": close,
                "high": float(item.get("high", 0)),
                "low": float(item.get("low", 0)),
                "volume": volume,
                # 新浪不提供成交额，用 volume * close 估算（对均价线精度影响极小）
                "amount": volume * close if volume else None,
                "change_percent": None,  # 下方统一计算
                "turnover_rate": None,
            })

        # 自行计算涨跌幅（当日收盘 vs 前一日收盘）
        for i in range(len(kline_data)):
            if i > 0 and kline_data[i - 1]["close"] and kline_data[i - 1]["close"] > 0:
                prev_close = kline_data[i - 1]["close"]
                cur_close = kline_data[i]["close"]
                kline_data[i]["change_percent"] = round((cur_close - prev_close) / prev_close * 100, 2)

        # 分时数据（1m）：只返回最新一个交易日的分钟数据
        if period == "1m" and kline_data:
            # 获取最新一天的日期
            latest_date = kline_data[-1]["date"].split(" ")[0]
            # 过滤只保留最新一天的数据
            kline_data = [item for item in kline_data if item["date"].startswith(latest_date)]

        return kline_data

    except Exception as e:
        logger.error(f"新浪 K 线获取失败：{e}", exc_info=True)
        return None


def _fetch_kline_from_eastmoney(stock_code: str, period: str, limit: int, fqt: int) -> Optional[List[Dict]]:
    """从东方财富获取 K 线数据（支持分页拉取全量历史数据）

    东方财富 API 的 lmt 参数有服务端上限（约 1000），
    通过 beg 参数从最早日期开始，多次请求拼接获取全量数据。
    """
    if period not in EASTMONEY_KLT_MAP:
        return None

    klt = EASTMONEY_KLT_MAP[period]
    secid = _code_to_secid(stock_code)

    # 单次请求最大条数（保守值，避免服务端截断）
    SINGLE_MAX = 1000
    # 安全上限：最多拉取 10000 条
    total_limit = min(limit, 10000)

    for base_url in [EASTMONEY_KLINE_URL, EASTMONEY_KLINE_URL_DELAY]:
        try:
            all_kline_data = []
            seen_dates = set()
            # 从最早日期开始，逐步向后拉取
            beg = "0"
            end = "20500101"

            for _page in range(20):  # 最多 20 次请求
                resp = _session.get(
                    base_url,
                    params={
                        "secid": secid,
                        "fields1": "f1,f2,f3,f4,f5,f6",
                        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                        "klt": klt,
                        "fqt": fqt,
                        "beg": beg,
                        "end": end,
                        "lmt": SINGLE_MAX,
                        "ut": "fa5fd1943c7b386f172d6893dbbd1d0c",
                    },
                    timeout=REQUEST_TIMEOUT,
                )
                resp.raise_for_status()
                result = resp.json()

                if result.get("rc") != 0 or not result.get("data"):
                    break

                klines = result["data"].get("klines", [])
                if not klines:
                    break

                new_count = 0
                for kline in klines:
                    parts = kline.split(",")
                    if len(parts) < 11:
                        continue
                    date_str = parts[0]
                    if date_str in seen_dates:
                        continue
                    seen_dates.add(date_str)
                    # 东方财富 f56 单位为"手"，×100 转为"股"，与腾讯/新浪统一
                    raw_vol = float(parts[5]) if parts[5] != "-" else None
                    all_kline_data.append({
                        "date": date_str,
                        "open": float(parts[1]),
                        "close": float(parts[2]),
                        "high": float(parts[3]),
                        "low": float(parts[4]),
                        "volume": raw_vol * 100 if raw_vol is not None else None,
                        "amount": float(parts[6]) if parts[6] != "-" else None,
                        "change_percent": float(parts[8]) if parts[8] != "-" else None,
                        "turnover_rate": float(parts[10]) if parts[10] != "-" else None,
                    })
                    new_count += 1

                # 已收集足够数据
                if len(all_kline_data) >= total_limit:
                    break

                # 返回数据不足，说明已到最新日期
                if len(klines) < SINGLE_MAX:
                    break

                # 没有新增数据（可能到达边界）
                if new_count == 0:
                    break

                # 更新 beg 为最后一条数据的下一天，继续拉取
                last_date = klines[-1].split(",")[0]
                # 日期格式 YYYY-MM-DD，去掉横杠后 +1 天
                try:
                    from datetime import datetime, timedelta
                    dt = datetime.strptime(last_date, "%Y-%m-%d")
                    next_day = dt + timedelta(days=1)
                    beg = next_day.strftime("%Y%m%d")
                except ValueError:
                    break

                # 短暂延迟避免触发反爬
                import time
                time.sleep(0.2)

            if all_kline_data:
                # 分时数据（1m）：只返回最新一个交易日的分钟数据
                if period == "1m":
                    latest_date = all_kline_data[-1]["date"].split(" ")[0]
                    all_kline_data = [item for item in all_kline_data if item["date"].startswith(latest_date)]
                # 截断到请求的 limit，保留最新数据（数据为时间升序，取尾部）
                return all_kline_data[-total_limit:]

        except Exception as e:
            logger.warning(f"东方财富 K 线({base_url})失败：{e}")
            continue

    return None


# 腾讯财经周期参数映射
# 注意：5d 复用日K（day），在 _get_kline_data 中单独做聚合
TENCENT_PERIOD_MAP = {
    "1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min",
    "60m": "60min", "120m": "120min",
    "5d": "day", "daily": "day", "weekly": "week", "monthly": "month", "yearly": "year",
}


def _fetch_kline_from_tencent(stock_code: str, period: str, limit: int, fqt: int) -> Optional[List[Dict]]:
    """从腾讯财经获取 K 线数据（支持分段日期拉取全量历史数据）

    腾讯 API 特性：
    - 单次请求上限约 600-640 条
    - 返回数据为倒序（最新在前）
    - 日期范围参数有效，但返回仍为倒序

    策略：从最新日期往回分段拉取，确保优先获取最新数据
    参数格式：{market}{code},{period},{start_date},{end_date},{limit},{fqt}
    """
    if period not in TENCENT_PERIOD_MAP:
        return None

    symbol = _code_to_sina_symbol(stock_code)  # 复用新浪的 symbol 格式（sh/sz/bj）
    tx_period = TENCENT_PERIOD_MAP[period]
    fqt_str = "qfq" if fqt == 1 else ("hfq" if fqt == 2 else "")

    try:
        from datetime import datetime, timedelta

        # 单次请求最大条数（腾讯 API 上限约 640）
        SINGLE_MAX = 600
        total_limit = min(limit, 10000)
        all_items = []
        seen_dates = set()

        # 从最新日期往回分段拉取（每次 2 年）
        # 这样优先获取最新数据，避免旧数据占满配额
        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=730)  # 2 年前

        for _page in range(30):  # 最多 30 次请求
            if start_dt < datetime(2000, 1, 1):
                start_dt = datetime(2000, 1, 1)

            start_str = start_dt.strftime("%Y-%m-%d")
            end_str = end_dt.strftime("%Y-%m-%d")

            param = f"{symbol},{tx_period},{start_str},{end_str},{SINGLE_MAX},{fqt_str}"
            resp = _session.get(
                TENCENT_KLINE_URL,
                params={"param": param},
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            result = resp.json()

            stock_data = result.get("data", {}).get(symbol, {})
            # 腾讯 API 返回的 key 随周期变化：
            # 日K: qfqday/hfqday/day, 周K: qfqweek/hfqweek/week,
            # 月K: qfqmonth/hfqmonth/month, 年K: qfqyear/hfqyear/year
            period_suffix = TENCENT_PERIOD_MAP.get(period, "day")
            # 将 1min/5min 等映射回 day（分钟线用 day key）
            if "min" in period_suffix:
                period_suffix = "day"
            if fqt_str == "qfq":
                day_data = stock_data.get(f"qfq{period_suffix}", stock_data.get(period_suffix, []))
            elif fqt_str == "hfq":
                day_data = stock_data.get(f"hfq{period_suffix}", stock_data.get(period_suffix, []))
            else:
                day_data = stock_data.get(period_suffix, [])

            if not isinstance(day_data, list) or not day_data:
                # 该时间段无数据，继续往前
                end_dt = start_dt - timedelta(days=1)
                start_dt = end_dt - timedelta(days=730)
                if end_dt <= datetime(2000, 1, 1):
                    break
                continue

            new_count = 0
            for item in day_data:
                if not isinstance(item, list) or len(item) < 5:
                    continue
                date_str = item[0]
                if date_str in seen_dates:
                    continue
                seen_dates.add(date_str)
                volume = float(item[5]) if len(item) > 5 and item[5] else None
                close = float(item[2])
                all_items.append({
                    "date": date_str,
                    "open": float(item[1]),
                    "close": close,
                    "high": float(item[3]),
                    "low": float(item[4]),
                    "volume": volume,
                    # 腾讯不提供成交额，用 volume * close 估算（对均价线精度影响极小）
                    "amount": volume * close if volume else None,
                    "change_percent": None,
                    "turnover_rate": None,
                })
                new_count += 1

            # 已收集足够数据
            if len(all_items) >= total_limit:
                break

            # 该时间段数据不足，继续往前
            end_dt = start_dt - timedelta(days=1)
            start_dt = end_dt - timedelta(days=730)
            if end_dt <= datetime(2000, 1, 1):
                break

            # 短暂延迟避免触发反爬
            time.sleep(0.2)

        if all_items:
            # 按日期升序排序，取最新的 total_limit 条
            all_items.sort(key=lambda x: x["date"])
            result = all_items[-total_limit:]
            # 自行计算涨跌幅（当日收盘 vs 前一日收盘）
            for i in range(len(result)):
                if i > 0 and result[i-1]["close"] and result[i-1]["close"] > 0:
                    prev_close = result[i-1]["close"]
                    cur_close = result[i]["close"]
                    result[i]["change_percent"] = round((cur_close - prev_close)/prev_close * 100, 2)
            # 分时数据（1m）：只返回最新一个交易日的分钟数据
            if period == "1m" and result:
                latest_date = result[-1]["date"].split(" ")[0]
                result = [item for item in result if item["date"].startswith(latest_date)]
            return result

        return None

    except Exception as e:
        logger.warning(f"腾讯 K 线获取失败：{e}")
        return None


def _aggregate_5d_kline(daily_data: list) -> list:
    """
    将日K数据聚合为5日K线

    规则：
    - 每5个交易日合成1根K线
    - 开盘价：第1天的开盘价
    - 收盘价：第5天的收盘价
    - 最高价：5天中的最高价
    - 最低价：5天中的最低价
    - 成交量：5天成交量之和
    - 成交额：5天成交额之和
    - 涨跌幅：使用最后一天的涨跌幅
    - 换手率：5天换手率之和
    """
    result = []
    for i in range(0, len(daily_data), 5):
        chunk = daily_data[i:i + 5]
        if not chunk:
            continue

        aggregated = {
            "date": chunk[-1]["date"],  # 使用最后一天日期
            "open": chunk[0]["open"],
            "close": chunk[-1]["close"],
            "high": max(d["high"] for d in chunk),
            "low": min(d["low"] for d in chunk),
            "volume": sum(d["volume"] or 0 for d in chunk),
            "amount": sum(d["amount"] or 0 for d in chunk),
            "change_percent": chunk[-1].get("change_percent"),
            "turnover_rate": sum(d.get("turnover_rate") or 0 for d in chunk),
        }
        result.append(aggregated)

    return result


def _aggregate_yearly_kline(daily_data: list) -> list:
    """
    将日K数据聚合为年K线

    规则：
    - 按自然年分组，每年合成1根K线
    - 开盘价：该年第一个交易日的开盘价
    - 收盘价：该年最后一个交易日的收盘价
    - 最高价：该年所有交易日中的最高价
    - 最低价：该年所有交易日中的最低价
    - 成交量：该年成交量之和
    - 成交额：该年成交额之和
    - 涨跌幅：使用该年最后一天的涨跌幅
    - 换手率：该年换手率之和
    - 日期：该年最后一个交易日的日期
      - 历史年：约为 12-31（实际为年末最后一个交易日）
      - 当年：截止到当前交易日
    """
    from collections import OrderedDict
    yearly_groups: dict = OrderedDict()

    for item in daily_data:
        # 日期格式："2025-07-28" 或 "2025-07-28 09:35:00"
        date_str = item["date"]
        year = date_str[:4]  # "2025"
        if year not in yearly_groups:
            yearly_groups[year] = []
        yearly_groups[year].append(item)

    result = []
    for year, chunk in yearly_groups.items():
        if not chunk:
            continue

        aggregated = {
            "date": chunk[-1]["date"],  # 该年最后一个交易日日期
            "open": chunk[0]["open"],   # 该年第一个交易日开盘价
            "close": chunk[-1]["close"], # 该年最后一个交易日收盘价
            "high": max(d["high"] for d in chunk),
            "low": min(d["low"] for d in chunk),
            "volume": sum(d["volume"] or 0 for d in chunk),
            "amount": sum(d["amount"] or 0 for d in chunk),
            "change_percent": chunk[-1].get("change_percent"),
            "turnover_rate": sum(d.get("turnover_rate") or 0 for d in chunk),
        }
        result.append(aggregated)

    return result


def _get_kline_data(stock_code: str, period: str, limit: int, fqt: int) -> tuple:
    """
    获取 K 线数据（东方财富 → 腾讯 → 新浪，三级降级）

    策略：
    - 5日K：获取日K数据 → 本地聚合为每5天1根
    - 年K：获取日K数据 → 本地聚合为每年1根（历史年≈12-31，当年≈当前交易日）
    - 日K/周K/月K：东方财富 → 腾讯 → 新浪
      （东方财富提供真实成交额和换手率，优先使用）
    - 分钟线：新浪 → 腾讯 → 东方财富

    Returns:
        (stock_name, kline_data_list)
    """
    # 5日K：使用日K数据聚合
    if period == "5d":
        # 需要更多日K数据来聚合（limit根5日K × 5天 = limit*5根日K）
        fetch_limit = max(limit * 5, 600)
        stock_name, daily_data = _get_kline_data(stock_code, "daily", fetch_limit, fqt)
        if daily_data:
            return stock_name, _aggregate_5d_kline(daily_data)
        return None, []

    # 年K：使用日K数据聚合（第三方API对年K支持不佳，腾讯只返回当天数据）
    if period == "yearly":
        # 拉取全量日K数据来聚合（每年约250个交易日，40根年K需要约10000根日K）
        stock_name, daily_data = _get_kline_data(stock_code, "daily", 10000, fqt)
        if daily_data:
            return stock_name, _aggregate_yearly_kline(daily_data)
        return None, []

    # 日K/周K/月K
    if period in ("daily", "weekly", "monthly"):
        # 统一优先级：东方财富 → 腾讯 → 新浪
        # 东方财富提供真实成交额(amount)和换手率(turnover_rate)，优先使用
        # 腾讯提供成交量(volume)和复权价格，作为备选
        # 新浪作为最终降级
        kline_data = _fetch_kline_from_eastmoney(stock_code, period, limit, fqt)
        if kline_data:
            stock_name = _get_stock_name_from_cache(stock_code)
            return stock_name, kline_data
        kline_data = _fetch_kline_from_tencent(stock_code, period, limit, fqt)
        if kline_data:
            stock_name = _get_stock_name_from_cache(stock_code)
            return stock_name, kline_data
        kline_data = _fetch_kline_from_sina(stock_code, period, limit)
        if kline_data:
            stock_name = _get_stock_name_from_cache(stock_code)
            return stock_name, kline_data
    else:
        # 分钟线：新浪 → 腾讯 → 东方财富
        kline_data = _fetch_kline_from_sina(stock_code, period, limit)
        if kline_data:
            stock_name = _get_stock_name_from_cache(stock_code)
            return stock_name, kline_data
        # 新浪失败，降级到腾讯
        kline_data = _fetch_kline_from_tencent(stock_code, period, limit, fqt)
        if kline_data:
            stock_name = _get_stock_name_from_cache(stock_code)
            return stock_name, kline_data
        # 腾讯失败，降级到东方财富
        kline_data = _fetch_kline_from_eastmoney(stock_code, period, limit, fqt)
        if kline_data:
            stock_name = _get_stock_name_from_cache(stock_code)
            return stock_name, kline_data

    return None, []


def _get_stock_name_from_cache(stock_code: str) -> Optional[str]:
    """从搜索缓存中获取股票名称"""
    for key, val in _search_cache.items():
        if val and isinstance(val, dict):
            for item in val.get("items", []):
                if item.get("code") == stock_code:
                    return item.get("name")
    return None


# ---------- 辅助函数 ----------


def _fetch_prev_close(stock_code: str) -> Optional[float]:
    """获取昨收价（用于分时图计算涨跌幅百分比）"""
    secid = _code_to_secid(stock_code)
    for url in [EASTMONEY_STOCK_URL, EASTMONEY_STOCK_URL_DELAY]:
        try:
            resp = _session.get(
                url,
                params={
                    "secid": secid,
                    "fields": "f43,f170",
                    "ut": "fa5fd1943c7b386f172d6893dbbd1d0c",
                },
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("rc") != 0 or not result.get("data"):
                continue
            data = result["data"]
            current_price = data.get("f43")
            change_percent = data.get("f170")
            if current_price and current_price != "-" and change_percent and change_percent != 0:
                current_price = current_price / 100
                change_percent = change_percent / 100
                return current_price / (1 + change_percent / 100)
        except Exception:
            continue
    return None


# ---------- API 接口 ----------


@router.get("/search", response_model=StockSearchResponse)
def search_stocks(q: str = Query(..., min_length=1, description="搜索关键词（代码/名称/拼音/简拼）")):
    """
    股票搜索接口

    支持股票代码、名称、拼音全拼、拼音简拼搜索
    """
    cache_key = q.lower().strip()

    # 检查缓存
    if cache_key in _search_cache and _is_cache_valid(_search_cache[cache_key], ttl=300):
        return StockSearchResponse(results=_search_cache[cache_key]["results"])

    try:
        resp = _session.get(
            EASTMONEY_SEARCH_URL,
            params={
                "input": q,
                "type": 14,
                "token": "D43BF722C8E33BDC906FB84D85E326E8",
                "count": 10,
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        result = resp.json()

        results = []
        items = []
        if result.get("QuotationCodeTable") and result["QuotationCodeTable"].get("Data"):
            for item in result["QuotationCodeTable"]["Data"]:
                code = item.get("Code", "")
                name = item.get("Name", "")
                market = item.get("MktNum", "")

                if market == "0":
                    market_name = "SZ"
                elif market == "1":
                    market_name = "SH"
                elif market == "0.8":
                    market_name = "BJ"
                else:
                    market_name = market

                secid = f"{market}.{code}" if market in ["0", "1"] else code

                results.append(StockSearchResult(code=code, name=name, market=market_name, secid=secid))
                items.append({"code": code, "name": name, "market": market_name, "secid": secid})

        # 缓存结果（同时保存 items 供后续获取名称用）
        _search_cache[cache_key] = {
            "results": results,
            "items": items,
            "timestamp": time.time(),
        }

        return StockSearchResponse(results=results)

    except Exception as e:
        logger.error(f"股票搜索失败：{e}", exc_info=True)
        raise HTTPException(status_code=502, detail="股票搜索数据获取失败")


@router.get("/{stock_code}/kline", response_model=KLineResponse)
def get_kline(
    stock_code: str,
    period: str = Query("daily", description="K 线周期", pattern="^(1m|5m|15m|30m|60m|120m|5d|daily|weekly|monthly|yearly)$"),
    limit: Optional[int] = Query(None, ge=1, le=10000, description="数据条数（不传则使用周期默认值）"),
    fqt: int = Query(1, ge=0, le=2, description="复权方式：0=不复权，1=前复权，2=后复权"),
    before_date: Optional[str] = Query(None, description="分页加载：返回此日期之前的数据"),
):
    """
    获取 K 线数据

    数据源优先级：
    - 日K/周K/月K/年K/5日K：东方财富 → 腾讯 → 新浪
    - 分钟线：新浪 → 腾讯 → 东方财富

    limit 参数：不传则使用周期默认值（见 PERIOD_DEFAULT_LIMITS）
    before_date 参数：用于分页加载，返回该日期之前的数据
    """
    # 如果前端未传 limit，使用周期默认值
    if limit is None:
        limit = PERIOD_DEFAULT_LIMITS.get(period, 250)

    cache_key = f"{stock_code}_{period}_{limit}_{fqt}_{before_date or ''}"

    # 检查缓存
    if cache_key in _kline_cache and _is_cache_valid(_kline_cache[cache_key], ttl=60):
        return _kline_cache[cache_key]["data"]

    stock_name, kline_data = _get_kline_data(stock_code, period, limit, fqt)

    if not kline_data:
        raise HTTPException(status_code=404, detail="K 线数据获取失败")

    # 分页加载：before_date 过滤
    if before_date and kline_data:
        # kline_data 已按日期升序排列
        # 保留 before_date 之前的数据，取最后 limit 条
        kline_data = [item for item in kline_data if item["date"] < before_date]
        kline_data = kline_data[-limit:]

    # 内部 volume 统一为"股"，转为"手"（÷100）供前端显示
    # 前端 formatVolume 假设 volume 单位为"手"，vol/10000 → 万手
    for item in kline_data:
        if item.get("volume") is not None:
            item["volume"] = item["volume"] / 100

    secid = _code_to_secid(stock_code)

    # 分时数据：获取昨收价（用于前端计算涨跌幅百分比）
    prev_close = None
    if period == "1m":
        try:
            prev_close = _fetch_prev_close(stock_code)
        except Exception as e:
            logger.warning(f"获取昨收价失败：{e}")

    response = KLineResponse(
        stock_code=stock_code,
        stock_name=stock_name,
        period=period,
        secid=secid,
        prev_close=prev_close,
        data=[KLinePoint(**item) for item in kline_data],
    )

    # 缓存结果
    _kline_cache[cache_key] = {
        "data": response,
        "timestamp": time.time(),
    }

    return response


@router.get("/{stock_code}/info", response_model=StockInfoResponse)
def get_stock_info(stock_code: str):
    """获取股票实时信息"""
    cache_key = stock_code

    # 检查缓存
    if cache_key in _info_cache and _is_cache_valid(_info_cache[cache_key], ttl=30):
        return _info_cache[cache_key]["data"]

    secid = _code_to_secid(stock_code)

    for url in [EASTMONEY_STOCK_URL, EASTMONEY_STOCK_URL_DELAY]:
        try:
            resp = _session.get(
                url,
                params={
                    "secid": secid,
                    "fields": "f9,f43,f44,f45,f46,f47,f48,f50,f51,f52,f55,f57,f58,f60,f115,f116,f117,f162,f164,f167,f168,f170",
                    "ut": "fa5fd1943c7b386f172d6893dbbd1d0c",
                },
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            result = resp.json()

            if result.get("rc") != 0 or not result.get("data"):
                continue

            data = result["data"]

            # 价格字段除以 100
            price_fields = ["f43", "f44", "f45", "f46"]
            for field in price_fields:
                if data.get(field) and data[field] != "-":
                    data[field] = data[field] / 100

            # 比率字段除以 100：f9=市盈率(动态), f115=市盈率(TTM), f162=市盈率(动态), f164=市盈率(静态), f167=市净率, f168=换手率, f170=涨跌幅
            # 注意：使用 is not None 而非 truthy 检查，因为 API 可能返回 0（有效值），0 在 Python 中是 falsy
            ratio_fields = ["f9", "f115", "f162", "f164", "f167", "f168", "f170"]
            for field in ratio_fields:
                if data.get(field) is not None and data[field] != "-":
                    data[field] = data[field] / 100

            change_percent = data.get("f170")

            # 昨收价：优先使用 API 返回的 f60，其次通过计算得到
            prev_close_raw = data.get("f60")
            if prev_close_raw and prev_close_raw != "-":
                prev_close = prev_close_raw / 100
            else:
                prev_close = None

            change = None
            current_price = data.get("f43")
            if current_price and current_price != "-":
                if prev_close and prev_close != 0:
                    change = current_price - prev_close

            # f47=成交量（手），×100 转为股，与 KLine schema 保持一致
            volume_raw = data.get("f47")
            volume = volume_raw * 100 if volume_raw and volume_raw != "-" else None

            # 振幅 = (最高 - 最低) / 昨收 × 100%
            amplitude = None
            high_val = data.get("f44") if data.get("f44") and data["f44"] != "-" else None
            low_val = data.get("f45") if data.get("f45") and data["f45"] != "-" else None
            if high_val is not None and low_val is not None and prev_close and prev_close != 0:
                amplitude = round((high_val - low_val) / prev_close * 100, 2)

            response = StockInfoResponse(
                stock_code=stock_code,
                stock_name=data.get("f58"),
                current_price=current_price if current_price and current_price != "-" else 0,
                change=change,
                change_percent=change_percent if change_percent and change_percent != "-" else None,
                open=data.get("f46") if data.get("f46") and data["f46"] != "-" else None,
                prev_close=prev_close,
                high=high_val,
                low=low_val,
                volume=volume,
                amount=data.get("f48") if data.get("f48") and data["f48"] != "-" else None,
                turnover_rate=data.get("f168") if data.get("f168") and data["f168"] != "-" else None,
                amplitude=amplitude,
                pe_ratio_ttm=_resolve_pe_ttm(data),
                total_market_cap=data.get("f116") if data.get("f116") and data["f116"] != "-" else None,
            )

            _info_cache[cache_key] = {
                "data": response,
                "timestamp": time.time(),
            }

            return response

        except Exception as e:
            logger.warning(f"股票信息({url})失败：{e}")
            continue

    raise HTTPException(status_code=502, detail="股票信息获取失败")
