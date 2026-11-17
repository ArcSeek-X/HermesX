# -*- coding: utf-8 -*-
"""
@file: akshare_source.py
@description: 实时行情 akshare source，复用既有 AkshareFetcher 实时行情通道。
@author: Lensgcx (GaoCangxiong)
"""

from __future__ import annotations
from typing import Optional, List
from data_provider.realtime.source_contract import RealtimeSource
from data_provider.realtime.types import UnifiedRealtimeQuote
from dataclasses import dataclass
import logging
from typing import Any, Callable, Tuple
import pandas as pd
import requests
from data_provider.realtime.types import (
    RealtimeSource as QuoteSource,
    safe_float,
    safe_int,
)


class AkshareRealtimeSource(RealtimeSource):
    """复用 AkshareFetcher 的实时行情 source。

    `market_source` 指定 akshare 的行情通道（`tencent` / `sina` / `em`）；
    `source_id` 允许以「通道」为粒度注册到 Manager，使注册 id 与
    `REALTIME_SOURCE_PRIORITY` 配置词表（`tencent` / `akshare_sina` /
    `akshare_em`）保持一致。
    """

    source_id = "akshare"

    def __init__(
        self, market_source: str = "em", source_id: Optional[str] = None
    ) -> None:
        """构造实时行情数据源（AkShare）。"""
        from data_provider.runtime.fetchers.akshare import AkshareFetcher

        self.market_source = market_source
        self.fetcher = AkshareFetcher()
        if source_id:
            self.source_id = source_id

    def fetch(self, request: str) -> Optional[UnifiedRealtimeQuote]:
        """通过既有 AkshareFetcher 获取实时行情。"""
        return self.fetcher.get_realtime_quote(request, source=self.market_source)


# 原 Fetcher 与能力入口共用取数实现；回调读取原缓存与请求状态。


logger = logging.getLogger("data_provider.akshare_fetcher")


@dataclass(frozen=True)
class AkshareRealtimeOperations:
    """按实时通道接入原宿主资源，不持有另一个 Fetcher 或复制缓存。"""

    hk_quote: Callable
    etf_quote: Callable
    sina_quote: Callable
    tencent_quote: Callable
    em_quote: Callable
    set_random_user_agent: Callable
    enforce_rate_limit: Callable
    enforce_realtime_rate_limit: Callable
    get_realtime_circuit_breaker: Callable
    is_us_code: Callable
    is_hk_code: Callable
    is_etf_code: Callable
    build_realtime_failure_message: Callable
    classify_realtime_http_error: Callable
    to_sina_tx_symbol: Callable
    normalize_tencent_volume: Callable
    parse_tencent_amount: Callable
    stock_cache: Callable[[], Any]
    etf_cache: Callable[[], Any]
    hk_cache: Callable[[], Any]
    hk_cache_lock: Callable[[], Any]
    sina_endpoint: Callable[[], Any]
    tencent_endpoint: Callable[[], Any]
    user_agents: Callable[[], Any]
    clock: Callable[[], Any]
    transport: Callable[[], Any]
    randomizer: Callable[[], Any]

    def get_realtime_quote(
        self, stock_code: str, source: str = "em"
    ) -> Optional[UnifiedRealtimeQuote]:
        """
        获取实时行情数据（支持多数据源）

        数据源优先级（可配置）：
        1. em: 东方财富（akshare ak.stock_zh_a_spot_em）- 数据最全，含量比/PE/PB/市值等
        2. sina: 新浪财经（akshare ak.stock_zh_a_spot）- 轻量级，基本行情
        3. tencent: 腾讯直连接口 - 单股票查询，负载小

        Args:
            stock_code: 股票/ETF代码
            source: 数据源类型，可选 "em", "sina", "tencent"

        Returns:
            UnifiedRealtimeQuote 对象，获取失败返回 None
        """
        circuit_breaker = self.get_realtime_circuit_breaker()

        # 根据代码类型选择不同的获取方法
        if self.is_us_code(stock_code):
            # 美股不使用 Akshare，由 YfinanceFetcher 处理
            logger.debug(f"[API跳过] {stock_code} 是美股，Akshare 不支持美股实时行情")
            return None
        elif self.is_hk_code(stock_code):
            return self.hk_quote(stock_code)
        elif self.is_etf_code(stock_code):
            source_key = "akshare_etf"
            if not circuit_breaker.is_available(source_key):
                logger.info(f"[熔断] 数据源 {source_key} 处于熔断状态，跳过")
                return None
            return self.etf_quote(stock_code)
        else:
            source_key = f"akshare_{source}"
            if not circuit_breaker.is_available(source_key):
                logger.info(f"[熔断] 数据源 {source_key} 处于熔断状态，跳过")
                return None
            # 普通 A 股：根据 source 选择数据源
            if source == "sina":
                return self.sina_quote(stock_code)
            elif source == "tencent":
                return self.tencent_quote(stock_code)
            else:
                return self.em_quote(stock_code)

    def get_stock_realtime_quote_em(
        self, stock_code: str
    ) -> Optional[UnifiedRealtimeQuote]:
        """
        获取普通 A 股实时行情数据（东方财富数据源）

        数据来源：ak.stock_zh_a_spot_em()
        优点：数据最全，含量比、换手率、市盈率、市净率、总市值、流通市值等
        缺点：全量拉取，数据量大，容易超时/限流
        """
        import akshare as ak

        circuit_breaker = self.get_realtime_circuit_breaker()
        source_key = "akshare_em"

        try:
            # 检查缓存
            current_time = self.clock().time()
            if (
                self.stock_cache()["data"] is not None
                and current_time - self.stock_cache()["timestamp"]
                < self.stock_cache()["ttl"]
            ):
                df = self.stock_cache()["data"]
                cache_age = int(current_time - self.stock_cache()["timestamp"])
                logger.debug(
                    f"[缓存命中] A股实时行情(东财) - 缓存年龄 {cache_age}s/{self.stock_cache()['ttl']}s"
                )
            else:
                # 触发全量刷新
                logger.info(f"[缓存未命中] 触发全量刷新 A股实时行情(东财)")
                last_error: Optional[Exception] = None
                df = None
                for attempt in range(1, 3):
                    try:
                        # 防封禁策略
                        self.set_random_user_agent()
                        self.enforce_rate_limit()

                        logger.info(
                            f"[API调用] ak.stock_zh_a_spot_em() 获取A股实时行情... (attempt {attempt}/2)"
                        )
                        import time as _time

                        api_start = _time.time()

                        df = ak.stock_zh_a_spot_em()

                        api_elapsed = _time.time() - api_start
                        logger.info(
                            f"[API返回] ak.stock_zh_a_spot_em 成功: 返回 {len(df)} 只股票, 耗时 {api_elapsed:.2f}s"
                        )
                        circuit_breaker.record_success(source_key)
                        break
                    except Exception as e:
                        last_error = e
                        logger.info(
                            f"[API错误] ak.stock_zh_a_spot_em 获取失败 (attempt {attempt}/2): {e}"
                        )
                        self.clock().sleep(min(2**attempt, 5))

                # 更新缓存：成功缓存数据；失败也缓存空数据，避免同一轮任务对同一接口反复请求
                if df is None:
                    logger.info(
                        f"[API错误] ak.stock_zh_a_spot_em 最终失败: {last_error}"
                    )
                    circuit_breaker.record_failure(source_key, str(last_error))
                    df = pd.DataFrame()
                self.stock_cache()["data"] = df
                self.stock_cache()["timestamp"] = current_time
                logger.info(
                    f"[缓存更新] A股实时行情(东财) 缓存已刷新，TTL={self.stock_cache()['ttl']}s"
                )

            if df is None or df.empty:
                logger.info(f"[实时行情] A股实时行情数据为空，跳过 {stock_code}")
                return None

            # 查找指定股票
            row = df[df["代码"] == stock_code]
            if row.empty:
                logger.info(f"[API返回] 未找到股票 {stock_code} 的实时行情")
                return None

            row = row.iloc[0]

            # 使用 realtime_types.py 中的统一转换函数
            quote = UnifiedRealtimeQuote(
                code=stock_code,
                name=str(row.get("名称", "")),
                source=QuoteSource.AKSHARE_EM,
                price=safe_float(row.get("最新价")),
                change_pct=safe_float(row.get("涨跌幅")),
                change_amount=safe_float(row.get("涨跌额")),
                volume=safe_int(row.get("成交量")),
                amount=safe_float(row.get("成交额")),
                volume_ratio=safe_float(row.get("量比")),
                turnover_rate=safe_float(row.get("换手率")),
                amplitude=safe_float(row.get("振幅")),
                open_price=safe_float(row.get("今开")),
                high=safe_float(row.get("最高")),
                low=safe_float(row.get("最低")),
                pe_ratio=safe_float(row.get("市盈率-动态")),
                pb_ratio=safe_float(row.get("市净率")),
                total_mv=safe_float(row.get("总市值")),
                circ_mv=safe_float(row.get("流通市值")),
                change_60d=safe_float(row.get("60日涨跌幅")),
                high_52w=safe_float(row.get("52周最高")),
                low_52w=safe_float(row.get("52周最低")),
            )

            logger.info(
                f"[实时行情-东财] {stock_code} {quote.name}: 价格={quote.price}, 涨跌={quote.change_pct}%, "
                f"量比={quote.volume_ratio}, 换手率={quote.turnover_rate}%"
            )
            return quote

        except Exception as e:
            logger.info(f"[API错误] 获取 {stock_code} 实时行情(东财)失败: {e}")
            circuit_breaker.record_failure(source_key, str(e))
            return None

    def get_realtime_quote_snapshot(self) -> Optional["pd.DataFrame"]:
        """
        返回全市场 A 股实时快照 DataFrame（东方财富 ak.stock_zh_a_spot_em()）。

        列含：代码、名称、最新价、涨跌幅、涨跌额、成交量、成交额、量比、换手率、
        振幅、今开、最高、最低、市盈率-动态、市净率、总市值、流通市值等。
        复用模块级 _realtime_cache 缓存（TTL 1200s），避免重复全量拉取。
        返回 None 表示数据源异常或为空（可能为非交易日 / 数据源限流）。

        用途：尾盘选股（EOD Picker）第一阶段全市场基础过滤。
        """
        try:
            # 借助内部全量拉取逻辑填充 / 复用模块级缓存，再直接读取缓存整表
            self.em_quote("__eod_snapshot__")
            df = self.stock_cache().get("data")
            if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                return None
            return df
        except Exception as e:  # pragma: no cover - 防御性兜底
            logger.info(f"[实时行情] 获取全市场快照失败: {e}")
            return None

    def get_stock_realtime_quote_sina(
        self, stock_code: str
    ) -> Optional[UnifiedRealtimeQuote]:
        """
        获取普通 A 股实时行情数据（新浪财经数据源）

        数据来源：新浪财经接口（直连，单股票查询）
        优点：单股票查询，负载小，速度快
        缺点：数据字段较少，无量比/PE/PB等

        接口格式：http://hq.sinajs.cn/list=sh600519,sz000001
        """
        circuit_breaker = self.get_realtime_circuit_breaker()
        source_key = "akshare_sina"
        symbol = self.to_sina_tx_symbol(stock_code)
        url = f"http://{self.sina_endpoint()}={symbol}"
        api_start = self.clock().time()

        try:
            headers = {
                "Referer": "http://finance.sina.com.cn",
                "User-Agent": self.randomizer().choice(self.user_agents()),
            }

            logger.info(
                f"[API调用] 新浪财经接口获取 {stock_code} 实时行情: endpoint={self.sina_endpoint()}, symbol={symbol}"
            )

            self.enforce_realtime_rate_limit()
            response = self.transport().get(url, headers=headers, timeout=10)
            response.encoding = "gbk"
            api_elapsed = self.clock().time() - api_start

            if response.status_code != 200:
                failure_message = self.build_realtime_failure_message(
                    source_name="新浪",
                    endpoint=self.sina_endpoint(),
                    stock_code=stock_code,
                    symbol=symbol,
                    category="http_status",
                    detail=f"HTTP {response.status_code}",
                    elapsed=api_elapsed,
                    error_type="HTTPStatus",
                )
                logger.info(failure_message)
                circuit_breaker.record_failure(source_key, failure_message)
                return None

            # 解析数据：var hq_str_sh600519="贵州茅台,1866.000,1870.000,..."
            content = response.text.strip()
            if '=""' in content or not content:
                failure_message = self.build_realtime_failure_message(
                    source_name="新浪",
                    endpoint=self.sina_endpoint(),
                    stock_code=stock_code,
                    symbol=symbol,
                    category="empty_response",
                    detail="empty quote payload",
                    elapsed=api_elapsed,
                    error_type="EmptyResponse",
                )
                logger.info(failure_message)
                circuit_breaker.record_failure(source_key, failure_message)
                return None

            # 提取引号内的数据
            data_start = content.find('"')
            data_end = content.rfind('"')
            if data_start == -1 or data_end == -1:
                failure_message = self.build_realtime_failure_message(
                    source_name="新浪",
                    endpoint=self.sina_endpoint(),
                    stock_code=stock_code,
                    symbol=symbol,
                    category="malformed_payload",
                    detail="quote payload missing quotes",
                    elapsed=api_elapsed,
                    error_type="MalformedPayload",
                )
                logger.info(failure_message)
                circuit_breaker.record_failure(source_key, failure_message)
                return None

            data_str = content[data_start + 1 : data_end]
            fields = data_str.split(",")

            if len(fields) < 32:
                failure_message = self.build_realtime_failure_message(
                    source_name="新浪",
                    endpoint=self.sina_endpoint(),
                    stock_code=stock_code,
                    symbol=symbol,
                    category="insufficient_fields",
                    detail=f"field_count={len(fields)}",
                    elapsed=api_elapsed,
                    error_type="InsufficientFields",
                )
                logger.info(failure_message)
                circuit_breaker.record_failure(source_key, failure_message)
                return None

            circuit_breaker.record_success(source_key)

            # 新浪数据字段顺序：
            # 0:名称 1:今开 2:昨收 3:最新价 4:最高 5:最低 6:买一价 7:卖一价
            # 8:成交量(股) 9:成交额(元) ... 30:日期 31:时间
            # 使用 realtime_types.py 中的统一转换函数
            price = safe_float(fields[3])
            pre_close = safe_float(fields[2])
            change_pct = None
            change_amount = None
            if price and pre_close and pre_close > 0:
                change_amount = price - pre_close
                change_pct = (change_amount / pre_close) * 100

            quote = UnifiedRealtimeQuote(
                code=stock_code,
                name=fields[0],
                source=QuoteSource.AKSHARE_SINA,
                price=price,
                change_pct=change_pct,
                change_amount=change_amount,
                volume=safe_int(fields[8]),  # 成交量（股）
                amount=safe_float(fields[9]),  # 成交额（元）
                open_price=safe_float(fields[1]),
                high=safe_float(fields[4]),
                low=safe_float(fields[5]),
                pre_close=pre_close,
            )

            logger.info(
                f"[实时行情-新浪] {stock_code} {quote.name}: endpoint={self.sina_endpoint()}, "
                f"价格={quote.price}, 涨跌={quote.change_pct}, 成交量={quote.volume}, elapsed={api_elapsed:.2f}s"
            )
            return quote

        except Exception as e:
            api_elapsed = self.clock().time() - api_start
            category, detail = self.classify_realtime_http_error(e)
            failure_message = self.build_realtime_failure_message(
                source_name="新浪",
                endpoint=self.sina_endpoint(),
                stock_code=stock_code,
                symbol=symbol,
                category=category,
                detail=detail,
                elapsed=api_elapsed,
                error_type=type(e).__name__,
            )
            logger.info(failure_message)
            circuit_breaker.record_failure(source_key, failure_message)
            return None

    def get_stock_realtime_quote_tencent(
        self, stock_code: str
    ) -> Optional[UnifiedRealtimeQuote]:
        """
        获取普通 A 股实时行情数据（腾讯财经数据源）

        数据来源：腾讯财经接口（直连，单股票查询）
        优点：单股票查询，负载小，包含换手率
        缺点：无量比/PE/PB等估值数据

        接口格式：http://qt.gtimg.cn/q=sh600519,sz000001
        """
        circuit_breaker = self.get_realtime_circuit_breaker()
        source_key = "akshare_tencent"
        symbol = self.to_sina_tx_symbol(stock_code)
        url = f"http://{self.tencent_endpoint()}={symbol}"
        api_start = self.clock().time()

        try:
            headers = {
                "Referer": "http://finance.qq.com",
                "User-Agent": self.randomizer().choice(self.user_agents()),
            }

            logger.info(
                f"[API调用] 腾讯财经接口获取 {stock_code} 实时行情: endpoint={self.tencent_endpoint()}, symbol={symbol}"
            )

            self.enforce_realtime_rate_limit()
            response = self.transport().get(url, headers=headers, timeout=10)
            response.encoding = "gbk"
            api_elapsed = self.clock().time() - api_start

            if response.status_code != 200:
                failure_message = self.build_realtime_failure_message(
                    source_name="腾讯",
                    endpoint=self.tencent_endpoint(),
                    stock_code=stock_code,
                    symbol=symbol,
                    category="http_status",
                    detail=f"HTTP {response.status_code}",
                    elapsed=api_elapsed,
                    error_type="HTTPStatus",
                )
                logger.info(failure_message)
                circuit_breaker.record_failure(source_key, failure_message)
                return None

            content = response.text.strip()
            if '=""' in content or not content:
                failure_message = self.build_realtime_failure_message(
                    source_name="腾讯",
                    endpoint=self.tencent_endpoint(),
                    stock_code=stock_code,
                    symbol=symbol,
                    category="empty_response",
                    detail="empty quote payload",
                    elapsed=api_elapsed,
                    error_type="EmptyResponse",
                )
                logger.info(failure_message)
                circuit_breaker.record_failure(source_key, failure_message)
                return None

            # 提取数据
            data_start = content.find('"')
            data_end = content.rfind('"')
            if data_start == -1 or data_end == -1:
                failure_message = self.build_realtime_failure_message(
                    source_name="腾讯",
                    endpoint=self.tencent_endpoint(),
                    stock_code=stock_code,
                    symbol=symbol,
                    category="malformed_payload",
                    detail="quote payload missing quotes",
                    elapsed=api_elapsed,
                    error_type="MalformedPayload",
                )
                logger.info(failure_message)
                circuit_breaker.record_failure(source_key, failure_message)
                return None

            data_str = content[data_start + 1 : data_end]
            fields = data_str.split("~")

            if len(fields) < 45:
                failure_message = self.build_realtime_failure_message(
                    source_name="腾讯",
                    endpoint=self.tencent_endpoint(),
                    stock_code=stock_code,
                    symbol=symbol,
                    category="insufficient_fields",
                    detail=f"field_count={len(fields)}",
                    elapsed=api_elapsed,
                    error_type="InsufficientFields",
                )
                logger.info(failure_message)
                circuit_breaker.record_failure(source_key, failure_message)
                return None

            circuit_breaker.record_success(source_key)

            # 腾讯数据字段顺序（完整）：
            # 1:名称 2:代码 3:最新价 4:昨收 5:今开 6:成交量 7:外盘 8:内盘
            # 9-28:买卖五档 30:时间戳 31:涨跌额 32:涨跌幅(%) 33:最高 34:最低 35:收盘/成交量/成交额
            # 36:成交量(口径随 payload 变化) 37:成交额(万) 38:换手率(%) 39:市盈率 43:振幅(%)
            # 44:流通市值(亿) 45:总市值(亿) 46:市净率 47:涨停价 48:跌停价 49:量比
            # 使用 realtime_types.py 中的统一转换函数
            amount = self.parse_tencent_amount(fields)
            quote = UnifiedRealtimeQuote(
                code=stock_code,
                name=fields[1] if len(fields) > 1 else "",
                source=QuoteSource.TENCENT,
                price=safe_float(fields[3]),
                change_pct=safe_float(fields[32]),
                change_amount=safe_float(fields[31]) if len(fields) > 31 else None,
                volume=self.normalize_tencent_volume(fields),
                amount=amount,
                open_price=safe_float(fields[5]),
                high=(
                    safe_float(fields[33]) if len(fields) > 33 else None
                ),  # 修正：字段 33 是最高价
                low=(
                    safe_float(fields[34]) if len(fields) > 34 else None
                ),  # 修正：字段 34 是最低价
                pre_close=safe_float(fields[4]),
                turnover_rate=safe_float(fields[38]) if len(fields) > 38 else None,
                amplitude=safe_float(fields[43]) if len(fields) > 43 else None,
                volume_ratio=(
                    safe_float(fields[49]) if len(fields) > 49 else None
                ),  # 量比
                pe_ratio=safe_float(fields[39]) if len(fields) > 39 else None,  # 市盈率
                pb_ratio=safe_float(fields[46]) if len(fields) > 46 else None,  # 市净率
                circ_mv=(
                    safe_float(fields[44]) * 100000000
                    if len(fields) > 44 and fields[44]
                    else None
                ),  # 流通市值(亿->元)
                total_mv=(
                    safe_float(fields[45]) * 100000000
                    if len(fields) > 45 and fields[45]
                    else None
                ),  # 总市值(亿->元)
            )

            logger.info(
                f"[实时行情-腾讯] {stock_code} {quote.name}: endpoint={self.tencent_endpoint()}, "
                f"价格={quote.price}, 涨跌={quote.change_pct}%, 量比={quote.volume_ratio}, "
                f"换手率={quote.turnover_rate}%, elapsed={api_elapsed:.2f}s"
            )
            return quote

        except Exception as e:
            api_elapsed = self.clock().time() - api_start
            category, detail = self.classify_realtime_http_error(e)
            failure_message = self.build_realtime_failure_message(
                source_name="腾讯",
                endpoint=self.tencent_endpoint(),
                stock_code=stock_code,
                symbol=symbol,
                category=category,
                detail=detail,
                elapsed=api_elapsed,
                error_type=type(e).__name__,
            )
            logger.info(failure_message)
            circuit_breaker.record_failure(source_key, failure_message)
            return None

    def get_etf_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        """
        获取 ETF 基金实时行情数据

        数据来源：ak.fund_etf_spot_em()
        包含：最新价、涨跌幅、成交量、成交额、换手率等

        Args:
            stock_code: ETF 代码

        Returns:
            UnifiedRealtimeQuote 对象，获取失败返回 None
        """
        import akshare as ak

        circuit_breaker = self.get_realtime_circuit_breaker()
        source_key = "akshare_etf"

        try:
            # 检查缓存
            current_time = self.clock().time()
            if (
                self.etf_cache()["data"] is not None
                and current_time - self.etf_cache()["timestamp"]
                < self.etf_cache()["ttl"]
            ):
                df = self.etf_cache()["data"]
                logger.debug(f"[缓存命中] 使用缓存的ETF实时行情数据")
            else:
                last_error: Optional[Exception] = None
                df = None
                for attempt in range(1, 3):
                    try:
                        # 防封禁策略
                        self.set_random_user_agent()
                        self.enforce_rate_limit()

                        logger.info(
                            f"[API调用] ak.fund_etf_spot_em() 获取ETF实时行情... (attempt {attempt}/2)"
                        )
                        import time as _time

                        api_start = _time.time()

                        df = ak.fund_etf_spot_em()

                        api_elapsed = _time.time() - api_start
                        logger.info(
                            f"[API返回] ak.fund_etf_spot_em 成功: 返回 {len(df)} 只ETF, 耗时 {api_elapsed:.2f}s"
                        )
                        circuit_breaker.record_success(source_key)
                        break
                    except Exception as e:
                        last_error = e
                        logger.info(
                            f"[API错误] ak.fund_etf_spot_em 获取失败 (attempt {attempt}/2): {e}"
                        )
                        self.clock().sleep(min(2**attempt, 5))

                if df is None:
                    logger.info(f"[API错误] ak.fund_etf_spot_em 最终失败: {last_error}")
                    circuit_breaker.record_failure(source_key, str(last_error))
                    df = pd.DataFrame()
                self.etf_cache()["data"] = df
                self.etf_cache()["timestamp"] = current_time

            if df is None or df.empty:
                logger.info(f"[实时行情] ETF实时行情数据为空，跳过 {stock_code}")
                return None

            # 查找指定 ETF
            row = df[df["代码"] == stock_code]
            if row.empty:
                logger.info(f"[API返回] 未找到 ETF {stock_code} 的实时行情")
                return None

            row = row.iloc[0]

            # 使用 realtime_types.py 中的统一转换函数
            # ETF 行情数据构建
            quote = UnifiedRealtimeQuote(
                code=stock_code,
                name=str(row.get("名称", "")),
                source=QuoteSource.AKSHARE_EM,
                price=safe_float(row.get("最新价")),
                change_pct=safe_float(row.get("涨跌幅")),
                change_amount=safe_float(row.get("涨跌额")),
                volume=safe_int(row.get("成交量")),
                amount=safe_float(row.get("成交额")),
                volume_ratio=safe_float(row.get("量比")),
                turnover_rate=safe_float(row.get("换手率")),
                amplitude=safe_float(row.get("振幅")),
                open_price=safe_float(row.get("开盘价")),
                high=safe_float(row.get("最高价")),
                low=safe_float(row.get("最低价")),
                total_mv=safe_float(row.get("总市值")),
                circ_mv=safe_float(row.get("流通市值")),
                high_52w=safe_float(row.get("52周最高")),
                low_52w=safe_float(row.get("52周最低")),
            )

            logger.info(
                f"[ETF实时行情] {stock_code} {quote.name}: 价格={quote.price}, 涨跌={quote.change_pct}%, "
                f"换手率={quote.turnover_rate}%"
            )
            return quote

        except Exception as e:
            logger.info(f"[API错误] 获取 ETF {stock_code} 实时行情失败: {e}")
            circuit_breaker.record_failure(source_key, str(e))
            return None

    def get_hk_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        """
        获取港股实时行情数据

        主数据源：ak.stock_hk_spot_em()（东方财富）
        备用数据源：ak.stock_hk_spot()（新浪）
        包含：最新价、涨跌幅、成交量、成交额等

        Args:
            stock_code: 港股代码

        Returns:
            UnifiedRealtimeQuote 对象，获取失败返回 None
        """
        import akshare as ak

        circuit_breaker = self.get_realtime_circuit_breaker()
        em_key = "akshare_hk_em"
        sina_key = "akshare_hk_sina"

        # 确保代码格式正确（5位数字）
        raw_code = stock_code.strip().lower()
        if raw_code.endswith(".hk"):
            raw_code = raw_code[:-3]
        if raw_code.startswith("hk"):
            raw_code = raw_code[2:]
        code = raw_code.zfill(5)

        def build_em_quote(df: pd.DataFrame) -> Optional[UnifiedRealtimeQuote]:
            """构造东财行情数据对象。"""
            if df.empty:
                logger.info(f"[API返回] 港股实时行情数据为空 (stock_hk_spot_em)")
                return None

            row = df[df["代码"] == code]
            if row.empty:
                logger.info(
                    f"[API返回] 未找到港股 {code} 的实时行情 (stock_hk_spot_em)"
                )
                return None

            row = row.iloc[0]
            quote = UnifiedRealtimeQuote(
                code=stock_code,
                name=str(row.get("名称", "")),
                source=QuoteSource.AKSHARE_EM,
                price=safe_float(row.get("最新价")),
                change_pct=safe_float(row.get("涨跌幅")),
                change_amount=safe_float(row.get("涨跌额")),
                volume=safe_int(row.get("成交量")),
                amount=safe_float(row.get("成交额")),
                volume_ratio=safe_float(row.get("量比")),
                turnover_rate=safe_float(row.get("换手率")),
                amplitude=safe_float(row.get("振幅")),
                pe_ratio=safe_float(row.get("市盈率")),
                pb_ratio=safe_float(row.get("市净率")),
                total_mv=safe_float(row.get("总市值")),
                circ_mv=safe_float(row.get("流通市值")),
                high_52w=safe_float(row.get("52周最高")),
                low_52w=safe_float(row.get("52周最低")),
            )
            logger.info(
                f"[港股实时行情] {stock_code} {quote.name}: 价格={quote.price}, "
                f"涨跌={quote.change_pct}%, 换手率={quote.turnover_rate}%"
            )
            return quote

        def read_cached_em_quote() -> Tuple[bool, Optional[UnifiedRealtimeQuote]]:
            """读取缓存的东财行情。"""
            current_time = self.clock().time()
            cache_data = self.hk_cache()["data"]
            cache_age = current_time - self.hk_cache()["timestamp"]
            if self.hk_cache().get(
                "last_result"
            ) == "failure" and cache_age < self.hk_cache().get("failure_ttl", 0):
                logger.debug(
                    f"[缓存命中] 港股实时行情(东财) - 复用最近失败结果 "
                    f"{int(cache_age)}s/{self.hk_cache().get('failure_ttl', 0)}s"
                )
                return True, None

            if cache_data is None or cache_age >= self.hk_cache()["ttl"]:
                return False, None

            logger.debug(
                f"[缓存命中] 港股实时行情(东财) - 缓存年龄 "
                f"{int(cache_age)}s/{self.hk_cache()['ttl']}s"
            )
            try:
                return True, build_em_quote(cache_data)
            except Exception as e:
                logger.warning(
                    f"[缓存错误] 港股实时行情缓存无法解析: {e}，"
                    "尝试 stock_hk_spot 备用接口"
                )
                return True, None

        cache_hit, quote = read_cached_em_quote()
        if quote is not None:
            return quote

        # --- 主数据源：东方财富 ---
        if not cache_hit:
            # 组合快照会并发查询多个 symbol；锁内二次检查保证同一进程仅一次冷拉取。
            with self.hk_cache_lock():
                cache_hit, quote = read_cached_em_quote()
                if quote is not None:
                    return quote

                if circuit_breaker.is_available(em_key) and not cache_hit:
                    try:
                        # 仅在真正发起网络请求前执行防封禁策略；热缓存命中不等待。
                        self.set_random_user_agent()
                        self.enforce_rate_limit()

                        logger.info(
                            f"[API调用] ak.stock_hk_spot_em() 获取港股实时行情..."
                        )
                        import time as _time

                        api_start = _time.time()

                        df = ak.stock_hk_spot_em()

                        api_elapsed = _time.time() - api_start
                        logger.info(
                            f"[API返回] ak.stock_hk_spot_em 成功: 返回 {len(df)} 只港股, "
                            f"耗时 {api_elapsed:.2f}s"
                        )

                        if not isinstance(df, pd.DataFrame):
                            raise TypeError("stock_hk_spot_em 未返回 DataFrame")
                        if "代码" not in df.columns:
                            raise KeyError("stock_hk_spot_em 返回结果缺少 代码 列")
                        if df.empty:
                            raise ValueError("stock_hk_spot_em 返回空市场快照")

                        self.hk_cache()["data"] = df
                        self.hk_cache()["timestamp"] = self.clock().time()
                        self.hk_cache()["last_result"] = "success"
                        logger.info(
                            f"[缓存更新] 港股实时行情(东财) 缓存已刷新，"
                            f"TTL={self.hk_cache()['ttl']}s"
                        )

                        quote = build_em_quote(df)
                        circuit_breaker.record_success(em_key)
                        if quote is not None:
                            return quote

                    except Exception as e:
                        self.hk_cache()["data"] = None
                        self.hk_cache()["timestamp"] = self.clock().time()
                        self.hk_cache()["last_result"] = "failure"
                        logger.warning(
                            f"[API错误] ak.stock_hk_spot_em 获取港股 {stock_code} "
                            f"失败: {e}，尝试 stock_hk_spot 备用接口"
                        )
                        circuit_breaker.record_failure(em_key, str(e))
                elif not cache_hit:
                    logger.info(
                        f"[熔断] 数据源 {em_key} 处于熔断状态，尝试使用备用链路"
                    )

        # --- 备用数据源：新浪 ---
        if not circuit_breaker.is_available(sina_key):
            logger.info(f"[熔断] 数据源 {sina_key} 处于熔断状态，跳过备用链路")
            return None

        try:
            self.set_random_user_agent()
            self.enforce_rate_limit()

            logger.info(f"[API调用] ak.stock_hk_spot() 获取港股实时行情（备用）...")
            import time as _time

            api_start = _time.time()

            df_spot = ak.stock_hk_spot()

            api_elapsed = _time.time() - api_start
            logger.info(
                f"[API返回] ak.stock_hk_spot 成功: 返回 {len(df_spot)} 只港股, 耗时 {api_elapsed:.2f}s"
            )

            row = df_spot[df_spot["代码"] == code]
            if row.empty:
                logger.info(f"[API返回] 未找到港股 {code} 的实时行情 (stock_hk_spot)")
                return None

            row = row.iloc[0]
            quote = UnifiedRealtimeQuote(
                code=stock_code,
                name=str(row.get("名称", "")),
                source=QuoteSource.AKSHARE_EM,
                price=safe_float(row.get("最新价")),
                change_pct=safe_float(row.get("涨跌幅")),
                change_amount=safe_float(row.get("涨跌额")),
                volume=safe_int(row.get("成交量")),
                amount=safe_float(row.get("成交额")),
            )
            circuit_breaker.record_success(sina_key)
            logger.info(
                f"[港股实时行情-备用] {stock_code} {quote.name}: 价格={quote.price}, 涨跌={quote.change_pct}%"
            )
            return quote

        except Exception as e:
            logger.info(f"[API错误] ak.stock_hk_spot 备用接口也失败: {e}")
            circuit_breaker.record_failure(sina_key, str(e))
            return None


def _normalize_tencent_volume(fields: List[str]) -> Optional[int]:
    """
    将腾讯实时行情成交量归一为股。

    腾讯返回内容对字段 6 的公开说明和实际返回不完全一致。优先使用
    换手率、价格、流通市值交叉校验，在原值和旧的“手转股”结果中选择
    更接近的一方。若无法交叉校验，则保留旧的“手转股”兜底逻辑，避免
    传统腾讯返回内容回归为原成交量的 1/100。
    """
    if len(fields) <= 6 or not fields[6]:
        return None

    raw_volume = safe_int(fields[6])
    if raw_volume is None:
        return None

    price = safe_float(fields[3]) if len(fields) > 3 else None
    turnover_rate = safe_float(fields[38]) if len(fields) > 38 else None
    circ_mv_yi = safe_float(fields[44]) if len(fields) > 44 and fields[44] else None
    circ_mv = circ_mv_yi * 100000000 if circ_mv_yi is not None else None

    if price and price > 0 and turnover_rate and turnover_rate > 0 and circ_mv and circ_mv > 0:
        expected_volume = (circ_mv / price) * (turnover_rate / 100)
        if expected_volume > 0:
            raw_delta = abs(raw_volume - expected_volume)
            hand_to_share_volume = raw_volume * 100
            hand_delta = abs(hand_to_share_volume - expected_volume)
            return raw_volume if raw_delta <= hand_delta else hand_to_share_volume

    return raw_volume * 100


def _parse_tencent_amount(fields: List[str]) -> Optional[float]:
    """
    解析腾讯实时行情成交额，单位为元。

    观测到的返回内容中，字段 35 包含更精确的“价格/成交量/成交额”
    三元组。字段 37 是旧的“万元”口径兜底字段。
    """
    if len(fields) > 35 and fields[35]:
        parts = fields[35].split("/")
        if len(parts) >= 3:
            precise_amount = safe_float(parts[2])
            if precise_amount is not None:
                return precise_amount

    amount_wan = safe_float(fields[37]) if len(fields) > 37 and fields[37] else None
    return amount_wan * 10000 if amount_wan is not None else None


def _classify_realtime_http_error(exc: Exception) -> Tuple[str, str]:
    """
    Classify Sina/Tencent realtime quote failures into stable categories.
    """
    detail = str(exc).strip() or type(exc).__name__
    lowered = detail.lower()

    remote_disconnect_keywords = (
        "remotedisconnected",
        "remote end closed connection without response",
        "connection aborted",
        "connection broken",
        "protocolerror",
        "chunkedencodingerror",
    )
    timeout_keywords = (
        "timeout",
        "timed out",
        "readtimeout",
        "connecttimeout",
    )
    rate_limit_keywords = (
        "banned",
        "blocked",
        "频率",
        "rate limit",
        "too many requests",
        "429",
        "限制",
        "forbidden",
        "403",
    )

    if any(keyword in lowered for keyword in remote_disconnect_keywords):
        return "remote_disconnect", detail
    if isinstance(exc, (TimeoutError, requests.exceptions.Timeout)) or any(
        keyword in lowered for keyword in timeout_keywords
    ):
        return "timeout", detail
    if any(keyword in lowered for keyword in rate_limit_keywords):
        return "rate_limit_or_anti_bot", detail
    if isinstance(exc, requests.exceptions.RequestException):
        return "request_error", detail
    return "unknown_request_error", detail


def _build_realtime_failure_message(
    source_name: str,
    endpoint: str,
    stock_code: str,
    symbol: str,
    category: str,
    detail: str,
    elapsed: float,
    error_type: str,
) -> str:
    """构造实时行情获取失败提示。"""
    return (
        f"{source_name} 实时行情接口失败: endpoint={endpoint}, stock_code={stock_code}, "
        f"symbol={symbol}, category={category}, error_type={error_type}, "
        f"elapsed={elapsed:.2f}s, detail={detail}"
    )
