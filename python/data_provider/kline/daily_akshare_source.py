"""AkShare 分析日线协议与标准化；共享节流和超时由旧 Fetcher 提供。"""


from dataclasses import dataclass
import logging
from typing import Callable, List, Tuple

import pandas as pd

from data_provider.common.errors import DataFetchError, RateLimitError
from data_provider.common.fetcher_contract import STANDARD_COLUMNS

logger = logging.getLogger("data_provider.akshare_fetcher")


@dataclass(frozen=True)
class AkshareDailySource:
    """保留各渠道原有 UA/节流差异，不复制 SDK、锁、超时或状态。"""

    set_user_agent: Callable[[], None]
    rate_limit: Callable[[], None]
    call_with_timeout: Callable[..., pd.DataFrame]
    history_timeout: Callable[[], float]
    to_symbol: Callable[[str], str]

    def fetch_stock_data(
        self, stock_code: str, start_date: str, end_date: str,
        *, channels: List[Tuple[Callable, str]],
    ) -> pd.DataFrame:
        """
        获取普通 A 股历史数据

        策略：
        1. 优先尝试东方财富接口 (ak.stock_zh_a_hist)
        2. 失败后尝试新浪财经接口 (ak.stock_zh_a_daily)
        3. 最后尝试腾讯财经接口 (ak.stock_zh_a_hist_tx)
        """
        # 尝试列表
        methods = channels

        last_error = None

        for fetch_method, source_name in methods:
            try:
                logger.info(f"[数据源] 尝试使用 {source_name} 获取 {stock_code}...")
                df = fetch_method(stock_code, start_date, end_date)

                if df is not None and not df.empty:
                    logger.info(f"[数据源] {source_name} 获取成功")
                    return df
            except Exception as e:
                last_error = e
                logger.warning(f"[数据源] {source_name} 获取失败: {e}")
                # 继续尝试下一个

        # 所有都失败
        raise DataFetchError(f"Akshare 所有渠道获取失败: {last_error}")


    def fetch_stock_data_em(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取普通 A 股历史数据 (东方财富)
        数据来源：ak.stock_zh_a_hist()
        """
        import akshare as ak

        # 防封禁策略 1: 随机 User-Agent
        self.set_user_agent()

        # 防封禁策略 2: 强制休眠
        self.rate_limit()

        logger.info(f"[API调用] ak.stock_zh_a_hist(symbol={stock_code}, ...)")

        try:
            import time as _time
            api_start = _time.time()

            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust="qfq"
            )

            api_elapsed = _time.time() - api_start

            if df is not None and not df.empty:
                logger.info(f"[API返回] ak.stock_zh_a_hist 成功: {len(df)} 行, 耗时 {api_elapsed:.2f}s")
                return df
            else:
                logger.warning(f"[API返回] ak.stock_zh_a_hist 返回空数据")
                return pd.DataFrame()

        except Exception as e:
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['banned', 'blocked', '频率', 'rate', '限制']):
                raise RateLimitError(f"Akshare(EM) 可能被限流: {e}") from e
            raise e


    def fetch_stock_data_sina(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取普通 A 股历史数据 (新浪财经)
        数据来源：ak.stock_zh_a_daily()
        """
        import akshare as ak

        # 转换代码格式：sh600000, sz000001, bj920748
        symbol = self.to_symbol(stock_code)

        self.rate_limit()

        try:
            df = self.call_with_timeout(
                ak.stock_zh_a_daily,
                symbol=symbol,
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust="qfq",
                timeout=self.history_timeout(),
                call_name="ak.stock_zh_a_daily",
            )

            # 标准化新浪数据列名
            # 新浪返回：date, open, high, low, close, volume, amount, outstanding_share, turnover
            if df is not None and not df.empty:
                # 确保日期列存在
                if 'date' in df.columns:
                    df = df.rename(columns={'date': '日期'})

                # 映射其他列以匹配 _normalize_data 的期望
                # _normalize_data 期望：日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额
                rename_map = {
                    'open': '开盘', 'high': '最高', 'low': '最低',
                    'close': '收盘', 'volume': '成交量', 'amount': '成交额'
                }
                df = df.rename(columns=rename_map)

                # 计算涨跌幅（新浪接口可能不返回）
                if '收盘' in df.columns:
                    df['涨跌幅'] = df['收盘'].pct_change() * 100
                    df['涨跌幅'] = df['涨跌幅'].fillna(0)

                return df
            return pd.DataFrame()

        except Exception as e:
            raise e


    def fetch_stock_data_tx(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取普通 A 股历史数据 (腾讯财经)
        数据来源：ak.stock_zh_a_hist_tx()
        """
        import akshare as ak

        # 转换代码格式：sh600000, sz000001, bj920748
        symbol = self.to_symbol(stock_code)

        self.rate_limit()

        try:
            df = self.call_with_timeout(
                ak.stock_zh_a_hist_tx,
                symbol=symbol,
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust="qfq",
                timeout=self.history_timeout(),
                call_name="ak.stock_zh_a_hist_tx",
            )

            # 标准化腾讯数据列名
            # 腾讯返回：date, open, close, high, low, volume, amount
            if df is not None and not df.empty:
                rename_map = {
                    'date': '日期', 'open': '开盘', 'high': '最高',
                    'low': '最低', 'close': '收盘', 'volume': '成交量',
                    'amount': '成交额'
                }
                df = df.rename(columns=rename_map)

                # 腾讯数据通常包含 '涨跌幅'，如果没有则计算
                if 'pct_chg' in df.columns:
                    df = df.rename(columns={'pct_chg': '涨跌幅'})
                elif '收盘' in df.columns:
                    df['涨跌幅'] = df['收盘'].pct_change() * 100
                    df['涨跌幅'] = df['涨跌幅'].fillna(0)

                return df
            return pd.DataFrame()

        except Exception as e:
            raise e


    def fetch_etf_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取 ETF 基金历史数据

        数据来源：ak.fund_etf_hist_em()

        Args:
            stock_code: ETF 代码，如 '512400', '159883'
            start_date: 开始日期，格式 'YYYY-MM-DD'
            end_date: 结束日期，格式 'YYYY-MM-DD'

        Returns:
            ETF 历史数据 DataFrame
        """
        import akshare as ak

        # 防封禁策略 1: 随机 User-Agent
        self.set_user_agent()

        # 防封禁策略 2: 强制休眠
        self.rate_limit()

        logger.info(f"[API调用] ak.fund_etf_hist_em(symbol={stock_code}, period=daily, "
                   f"start_date={start_date.replace('-', '')}, end_date={end_date.replace('-', '')}, adjust=qfq)")

        try:
            import time as _time
            api_start = _time.time()

            # 调用 akshare 获取 ETF 日线数据
            df = ak.fund_etf_hist_em(
                symbol=stock_code,
                period="daily",
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust="qfq"  # 前复权
            )

            api_elapsed = _time.time() - api_start

            # 记录返回数据摘要
            if df is not None and not df.empty:
                logger.info(f"[API返回] ak.fund_etf_hist_em 成功: 返回 {len(df)} 行数据, 耗时 {api_elapsed:.2f}s")
                logger.info(f"[API返回] 列名: {list(df.columns)}")
                logger.info(f"[API返回] 日期范围: {df['日期'].iloc[0]} ~ {df['日期'].iloc[-1]}")
                logger.debug(f"[API返回] 最新3条数据:\n{df.tail(3).to_string()}")
            else:
                logger.warning(f"[API返回] ak.fund_etf_hist_em 返回空数据, 耗时 {api_elapsed:.2f}s")

            return df

        except Exception as e:
            error_msg = str(e).lower()

            # 检测反爬封禁
            if any(keyword in error_msg for keyword in ['banned', 'blocked', '频率', 'rate', '限制']):
                logger.warning(f"检测到可能被封禁: {e}")
                raise RateLimitError(f"Akshare 可能被限流: {e}") from e

            raise DataFetchError(f"Akshare 获取 ETF 数据失败: {e}") from e


    def fetch_hk_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取港股历史数据

        数据来源：ak.stock_hk_hist()

        Args:
            stock_code: 港股代码，如 '00700', '01810'
            start_date: 开始日期，格式 'YYYY-MM-DD'
            end_date: 结束日期，格式 'YYYY-MM-DD'

        Returns:
            港股历史数据 DataFrame
        """
        import akshare as ak

        # 防封禁策略 1: 随机 User-Agent
        self.set_user_agent()

        # 防封禁策略 2: 强制休眠
        self.rate_limit()

        # 确保代码格式正确（5位数字）
        code = stock_code.lower().replace('hk', '').zfill(5)

        logger.info(f"[API调用] ak.stock_hk_hist(symbol={code}, period=daily, "
                   f"start_date={start_date.replace('-', '')}, end_date={end_date.replace('-', '')}, adjust=qfq)")

        try:
            import time as _time
            api_start = _time.time()

            # 调用 akshare 获取港股日线数据
            df = ak.stock_hk_hist(
                symbol=code,
                period="daily",
                start_date=start_date.replace('-', ''),
                end_date=end_date.replace('-', ''),
                adjust="qfq"  # 前复权
            )

            api_elapsed = _time.time() - api_start

            # 记录返回数据摘要
            if df is not None and not df.empty:
                logger.info(f"[API返回] ak.stock_hk_hist 成功: 返回 {len(df)} 行数据, 耗时 {api_elapsed:.2f}s")
                logger.info(f"[API返回] 列名: {list(df.columns)}")
                logger.info(f"[API返回] 日期范围: {df['日期'].iloc[0]} ~ {df['日期'].iloc[-1]}")
                logger.debug(f"[API返回] 最新3条数据:\n{df.tail(3).to_string()}")
            else:
                logger.warning(f"[API返回] ak.stock_hk_hist 返回空数据, 耗时 {api_elapsed:.2f}s")

            return df

        except Exception as e:
            error_msg = str(e).lower()

            # 检测反爬封禁
            if any(keyword in error_msg for keyword in ['banned', 'blocked', '频率', 'rate', '限制']):
                logger.warning(f"检测到可能被封禁: {e}")
                raise RateLimitError(f"Akshare 可能被限流: {e}") from e

            raise DataFetchError(f"Akshare 获取港股数据失败: {e}") from e


    @staticmethod
    def normalize_data( df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        """
        标准化 Akshare 数据

        Akshare 返回的列名（中文）：
        日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率

        需要映射到标准列名：
        date, open, high, low, close, volume, amount, pct_chg
        """
        df = df.copy()

        # 列名映射（Akshare 中文列名 -> 标准英文列名）
        column_mapping = {
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交额': 'amount',
            '涨跌幅': 'pct_chg',
        }

        # 重命名列
        df = df.rename(columns=column_mapping)

        # 添加股票代码列
        df['code'] = stock_code

        # 只保留需要的列
        keep_cols = ['code'] + STANDARD_COLUMNS
        existing_cols = [col for col in keep_cols if col in df.columns]
        df = df[existing_cols]

        return df



@dataclass(frozen=True)
class AkshareDailyRouting:
    """原能力实现；不接收整个 Fetcher，不拥有第二份客户端或缓存。"""

    use_enforce_rate_limit: Callable
    use_fetch_etf_data: Callable
    use_fetch_hk_data: Callable
    use_fetch_stock_data: Callable
    use_set_random_user_agent: Callable
    read_global_logger: Callable
    read_global_is_us_code: Callable
    read_global_is_hk_code: Callable
    read_global_is_etf_code: Callable

    def _fetch_raw_data(
        self, stock_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """
        从 Akshare 获取原始数据

        根据代码类型自动选择 API：
        - 美股：不支持，抛出异常由 YfinanceFetcher 处理（Issue #311）
        - 港股：使用 ak.stock_hk_hist()
        - ETF 基金：使用 ak.fund_etf_hist_em()
        - 普通 A 股：使用 ak.stock_zh_a_hist()

        流程：
        1. 判断代码类型（美股/港股/ETF/A股）
        2. 设置随机 User-Agent
        3. 执行速率限制（随机休眠）
        4. 调用对应的 akshare API
        5. 处理返回数据
        """
        if self.read_global_is_us_code()(stock_code):
            raise DataFetchError(
                f"AkshareFetcher 不支持美股 {stock_code}，请使用 YfinanceFetcher 获取正确的复权价格"
            )
        elif self.read_global_is_hk_code()(stock_code):
            return self.use_fetch_hk_data(stock_code, start_date, end_date)
        elif self.read_global_is_etf_code()(stock_code):
            return self.use_fetch_etf_data(stock_code, start_date, end_date)
        else:
            return self.use_fetch_stock_data(stock_code, start_date, end_date)

    def _fetch_us_data(
        self, stock_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """
        获取美股历史数据

        数据来源：ak.stock_us_daily()（新浪财经接口）

        Args:
            stock_code: 美股代码，如 'AMD', 'AAPL', 'TSLA'
            start_date: 开始日期，格式 'YYYY-MM-DD'
            end_date: 结束日期，格式 'YYYY-MM-DD'

        Returns:
            美股历史数据 DataFrame
        """
        import akshare as ak

        self.use_set_random_user_agent()
        self.use_enforce_rate_limit()
        symbol = stock_code.strip().upper()
        self.read_global_logger().info(
            f"[API调用] ak.stock_us_daily(symbol={symbol}, adjust=qfq)"
        )
        try:
            import time as _time

            api_start = _time.time()
            df = ak.stock_us_daily(symbol=symbol, adjust="qfq")
            api_elapsed = _time.time() - api_start
            if df is not None and (not df.empty):
                self.read_global_logger().info(
                    f"[API返回] ak.stock_us_daily 成功: 返回 {len(df)} 行数据, 耗时 {api_elapsed:.2f}s"
                )
                self.read_global_logger().info(f"[API返回] 列名: {list(df.columns)}")
                df["date"] = pd.to_datetime(df["date"])
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)
                df = df[(df["date"] >= start_dt) & (df["date"] <= end_dt)]
                if not df.empty:
                    self.read_global_logger().info(
                        f"[API返回] 过滤后日期范围: {df['date'].iloc[0].strftime('%Y-%m-%d')} ~ {df['date'].iloc[-1].strftime('%Y-%m-%d')}"
                    )
                    self.read_global_logger().debug(
                        f"[API返回] 最新3条数据:\n{df.tail(3).to_string()}"
                    )
                else:
                    self.read_global_logger().warning(
                        f"[API返回] 过滤后数据为空，日期范围 {start_date} ~ {end_date} 无数据"
                    )
                rename_map = {
                    "date": "日期",
                    "open": "开盘",
                    "high": "最高",
                    "low": "最低",
                    "close": "收盘",
                    "volume": "成交量",
                }
                df = df.rename(columns=rename_map)
                if "收盘" in df.columns:
                    df["涨跌幅"] = df["收盘"].pct_change() * 100
                    df["涨跌幅"] = df["涨跌幅"].fillna(0)
                if "成交量" in df.columns and "收盘" in df.columns:
                    df["成交额"] = df["成交量"] * df["收盘"]
                else:
                    df["成交额"] = 0
                return df
            else:
                self.read_global_logger().warning(
                    f"[API返回] ak.stock_us_daily 返回空数据, 耗时 {api_elapsed:.2f}s"
                )
                return pd.DataFrame()
        except Exception as e:
            error_msg = str(e).lower()
            if any(
                (
                    keyword in error_msg
                    for keyword in ["banned", "blocked", "频率", "rate", "限制"]
                )
            ):
                self.read_global_logger().warning(f"检测到可能被封禁: {e}")
                raise RateLimitError(f"Akshare 可能被限流: {e}") from e
            raise DataFetchError(f"Akshare 获取美股数据失败: {e}") from e
