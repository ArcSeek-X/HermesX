"""Efinance 实时请求与载荷适配；SDK、缓存和请求状态由原宿主维护。"""

from dataclasses import dataclass
import logging
from typing import Any, Callable, Optional, Dict
from concurrent.futures import TimeoutError as FuturesTimeoutError
import pandas as pd

from data_provider.realtime.types import UnifiedRealtimeQuote, RealtimeSource, safe_float, safe_int

logger = logging.getLogger("data_provider.efinance_fetcher")


@dataclass(frozen=True)
class EfinanceRealtimeOperations:
    """显式绑定所需能力，不新建宿主、缓存、SDK 或熔断实例。"""

    use_get_etf_realtime_quote: Callable
    use_enforce_rate_limit: Callable
    use_set_random_user_agent: Callable
    call_is_etf_code: Callable
    call_get_realtime_circuit_breaker: Callable
    call_ef_call_with_timeout: Callable
    read_ef_call_timeout: Callable[[], Any]
    read_realtime_cache: Callable[[], Any]
    read_etf_realtime_cache: Callable[[], Any]
    read_time: Callable[[], Any]

    def get_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        """
        获取实时行情数据

        数据来源：ef.stock.get_realtime_quotes()
        ETF 数据源：ef.stock.get_realtime_quotes(['ETF'])

        Args:
            stock_code: 股票代码

        Returns:
            UnifiedRealtimeQuote 对象，获取失败返回 None
        """
        # ETF 需要单独请求 ETF 实时行情接口
        if self.call_is_etf_code(stock_code):
            return self.use_get_etf_realtime_quote(stock_code)

        import efinance as ef

        circuit_breaker = self.call_get_realtime_circuit_breaker()
        source_key = "efinance"

        # 检查熔断器状态
        if not circuit_breaker.is_available(source_key):
            logger.info(f"[熔断] 数据源 {source_key} 处于熔断状态，跳过")
            return None

        try:
            # 检查缓存
            current_time = self.read_time().time()
            if (
                self.read_realtime_cache()["data"] is not None
                and current_time - self.read_realtime_cache()["timestamp"] < self.read_realtime_cache()["ttl"]
            ):
                df = self.read_realtime_cache()["data"]
                cache_age = int(current_time - self.read_realtime_cache()["timestamp"])
                logger.debug(
                    f"[缓存命中] 实时行情(efinance) - 缓存年龄 {cache_age}s/{self.read_realtime_cache()['ttl']}s"
                )
            else:
                # 触发全量刷新
                logger.info(f"[缓存未命中] 触发全量刷新 实时行情(efinance)")
                # 防封禁策略
                self.use_set_random_user_agent()
                self.use_enforce_rate_limit()

                logger.info(f"[API调用] ef.stock.get_realtime_quotes() 获取实时行情...")
                import time as _time

                api_start = _time.time()

                # efinance 的实时行情 API (with timeout to avoid indefinite hangs)
                df = self.call_ef_call_with_timeout(ef.stock.get_realtime_quotes)

                api_elapsed = _time.time() - api_start
                logger.info(
                    f"[API返回] ef.stock.get_realtime_quotes 成功: 返回 {len(df)} 只股票, 耗时 {api_elapsed:.2f}s"
                )
                circuit_breaker.record_success(source_key)

                # 更新缓存
                self.read_realtime_cache()["data"] = df
                self.read_realtime_cache()["timestamp"] = current_time
                logger.info(f"[缓存更新] 实时行情(efinance) 缓存已刷新，TTL={self.read_realtime_cache()['ttl']}s")

            # 查找指定股票
            # efinance 返回的列名可能是 '股票代码' 或 'code'
            code_col = "股票代码" if "股票代码" in df.columns else "code"
            row = df[df[code_col] == stock_code]
            if row.empty:
                logger.info(f"[API返回] 未找到股票 {stock_code} 的实时行情")
                return None

            row = row.iloc[0]

            # 使用 realtime_types.py 中的统一转换函数
            # 获取列名（可能是中文或英文）
            name_col = "股票名称" if "股票名称" in df.columns else "name"
            price_col = "最新价" if "最新价" in df.columns else "price"
            pct_col = "涨跌幅" if "涨跌幅" in df.columns else "pct_chg"
            chg_col = "涨跌额" if "涨跌额" in df.columns else "change"
            vol_col = "成交量" if "成交量" in df.columns else "volume"
            amt_col = "成交额" if "成交额" in df.columns else "amount"
            turn_col = "换手率" if "换手率" in df.columns else "turnover_rate"
            amp_col = "振幅" if "振幅" in df.columns else "amplitude"
            high_col = "最高" if "最高" in df.columns else "high"
            low_col = "最低" if "最低" in df.columns else "low"
            open_col = "开盘" if "开盘" in df.columns else "open"
            # efinance 也返回量比、市盈率、市值等字段
            vol_ratio_col = "量比" if "量比" in df.columns else "volume_ratio"
            pe_col = "市盈率" if "市盈率" in df.columns else "pe_ratio"
            total_mv_col = "总市值" if "总市值" in df.columns else "total_mv"
            circ_mv_col = "流通市值" if "流通市值" in df.columns else "circ_mv"

            quote = UnifiedRealtimeQuote(
                code=stock_code,
                name=str(row.get(name_col, "")),
                source=RealtimeSource.EFINANCE,
                price=safe_float(row.get(price_col)),
                change_pct=safe_float(row.get(pct_col)),
                change_amount=safe_float(row.get(chg_col)),
                volume=safe_int(row.get(vol_col)),
                amount=safe_float(row.get(amt_col)),
                turnover_rate=safe_float(row.get(turn_col)),
                amplitude=safe_float(row.get(amp_col)),
                high=safe_float(row.get(high_col)),
                low=safe_float(row.get(low_col)),
                open_price=safe_float(row.get(open_col)),
                volume_ratio=safe_float(row.get(vol_ratio_col)),  # 量比
                pe_ratio=safe_float(row.get(pe_col)),  # 市盈率
                total_mv=safe_float(row.get(total_mv_col)),  # 总市值
                circ_mv=safe_float(row.get(circ_mv_col)),  # 流通市值
            )

            logger.info(
                f"[实时行情-efinance] {stock_code} {quote.name}: 价格={quote.price}, 涨跌={quote.change_pct}%, "
                f"量比={quote.volume_ratio}, 换手率={quote.turnover_rate}%"
            )
            return quote

        except FuturesTimeoutError:
            logger.info(f"[超时] ef.stock.get_realtime_quotes() 超过 {self.read_ef_call_timeout()}s，跳过 {stock_code}")
            circuit_breaker.record_failure(source_key, "timeout")
            return None
        except Exception as e:
            logger.info(f"[API错误] 获取 {stock_code} 实时行情(efinance)失败: {e}")
            circuit_breaker.record_failure(source_key, str(e))
            return None

    def get_etf_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        """
        获取 ETF 实时行情

        efinance 默认实时接口仅返回股票数据，ETF 需要显式传入 ['ETF']。
        """
        import efinance as ef

        circuit_breaker = self.call_get_realtime_circuit_breaker()
        source_key = "efinance_etf"

        if not circuit_breaker.is_available(source_key):
            logger.info(f"[熔断] 数据源 {source_key} 处于熔断状态，跳过")
            return None

        try:
            current_time = self.read_time().time()
            if (
                self.read_etf_realtime_cache()["data"] is not None
                and current_time - self.read_etf_realtime_cache()["timestamp"] < self.read_etf_realtime_cache()["ttl"]
            ):
                df = self.read_etf_realtime_cache()["data"]
                cache_age = int(current_time - self.read_etf_realtime_cache()["timestamp"])
                logger.debug(
                    f"[缓存命中] ETF实时行情(efinance) - 缓存年龄 {cache_age}s/{self.read_etf_realtime_cache()['ttl']}s"
                )
            else:
                self.use_set_random_user_agent()
                self.use_enforce_rate_limit()

                logger.info("[API调用] ef.stock.get_realtime_quotes(['ETF']) 获取ETF实时行情...")
                import time as _time

                api_start = _time.time()
                df = self.call_ef_call_with_timeout(ef.stock.get_realtime_quotes, ["ETF"])
                api_elapsed = _time.time() - api_start

                if df is not None and not df.empty:
                    logger.info(f"[API返回] ETF 实时行情成功: {len(df)} 条, 耗时 {api_elapsed:.2f}s")
                    circuit_breaker.record_success(source_key)
                else:
                    logger.info(f"[API返回] ETF 实时行情为空, 耗时 {api_elapsed:.2f}s")
                    df = pd.DataFrame()

                self.read_etf_realtime_cache()["data"] = df
                self.read_etf_realtime_cache()["timestamp"] = current_time

            if df is None or df.empty:
                logger.info(f"[实时行情] ETF实时行情数据为空(efinance)，跳过 {stock_code}")
                return None

            code_col = "股票代码" if "股票代码" in df.columns else "code"
            code_series = df[code_col].astype(str).str.zfill(6)
            target_code = str(stock_code).strip().zfill(6)
            row = df[code_series == target_code]
            if row.empty:
                logger.info(f"[API返回] 未找到 ETF {stock_code} 的实时行情(efinance)")
                return None

            row = row.iloc[0]
            name_col = "股票名称" if "股票名称" in df.columns else "name"
            price_col = "最新价" if "最新价" in df.columns else "price"
            pct_col = "涨跌幅" if "涨跌幅" in df.columns else "pct_chg"
            chg_col = "涨跌额" if "涨跌额" in df.columns else "change"
            vol_col = "成交量" if "成交量" in df.columns else "volume"
            amt_col = "成交额" if "成交额" in df.columns else "amount"
            turn_col = "换手率" if "换手率" in df.columns else "turnover_rate"
            amp_col = "振幅" if "振幅" in df.columns else "amplitude"
            high_col = "最高" if "最高" in df.columns else "high"
            low_col = "最低" if "最低" in df.columns else "low"
            open_col = "开盘" if "开盘" in df.columns else "open"

            quote = UnifiedRealtimeQuote(
                code=target_code,
                name=str(row.get(name_col, "")),
                source=RealtimeSource.EFINANCE,
                price=safe_float(row.get(price_col)),
                change_pct=safe_float(row.get(pct_col)),
                change_amount=safe_float(row.get(chg_col)),
                volume=safe_int(row.get(vol_col)),
                amount=safe_float(row.get(amt_col)),
                turnover_rate=safe_float(row.get(turn_col)),
                amplitude=safe_float(row.get(amp_col)),
                high=safe_float(row.get(high_col)),
                low=safe_float(row.get(low_col)),
                open_price=safe_float(row.get(open_col)),
            )

            logger.info(
                f"[ETF实时行情-efinance] {target_code} {quote.name}: "
                f"价格={quote.price}, 涨跌={quote.change_pct}%, 换手率={quote.turnover_rate}%"
            )
            return quote
        except Exception as e:
            logger.info(f"[API错误] 获取 ETF {stock_code} 实时行情(efinance)失败: {e}")
            circuit_breaker.record_failure(source_key, str(e))
            return None


@dataclass
class EfinanceRealtimeQuote:
    """
    实时行情数据（来自 efinance）- 向后兼容别名
    
    新代码建议使用 UnifiedRealtimeQuote
    """
    code: str
    name: str = ""
    price: float = 0.0           # 最新价
    change_pct: float = 0.0      # 涨跌幅(%)
    change_amount: float = 0.0   # 涨跌额
    
    # 量价指标
    volume: int = 0              # 成交量
    amount: float = 0.0          # 成交额
    turnover_rate: float = 0.0   # 换手率(%)
    amplitude: float = 0.0       # 振幅(%)
    
    # 价格区间
    high: float = 0.0            # 最高价
    low: float = 0.0             # 最低价
    open_price: float = 0.0      # 开盘价
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'code': self.code,
            'name': self.name,
            'price': self.price,
            'change_pct': self.change_pct,
            'change_amount': self.change_amount,
            'volume': self.volume,
            'amount': self.amount,
            'turnover_rate': self.turnover_rate,
            'amplitude': self.amplitude,
            'high': self.high,
            'low': self.low,
            'open': self.open_price,
        }
