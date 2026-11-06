"""各源股票清单及内部分页缓存加载；不承担代码搜索或索引持久化。"""

from typing import Dict

from dataclasses import dataclass
from typing import Any, Callable, Optional

import pandas as pd


@dataclass(frozen=True)
class TushareCatalog:
    """读取原宿主资源与扩展点，不新建缓存或 SDK。"""

    use_check_rate_limit: Callable
    read_api: Callable[[], Any]
    read_stock_name_cache: Callable[[], Any]
    write_stock_name_cache: Callable[[Any], None]
    has_stock_name_cache: Callable[[], bool]
    log: Callable[[], Any]

    def get_stock_list(self) -> Optional[pd.DataFrame]:
        """
        获取股票列表

        使用 Tushare 的 stock_basic 接口获取 A 股列表（不含港股）。

        Returns:
            包含 code, name, industry, area, market 列的 DataFrame，失败返回 None
        """
        if self.read_api() is None:
            self.log().warning("Tushare API 未初始化，无法获取股票列表")
            return None

        try:
            self.use_check_rate_limit()

            df = self.read_api().stock_basic(exchange="", list_status="L", fields="ts_code,name,industry,area,market")

            if df is None or df.empty:
                return None

            df = df.copy()
            df["code"] = df["ts_code"].astype(str).str.split(".").str[0]

            if not self.has_stock_name_cache():
                self.write_stock_name_cache({})
            for _, row in df.iterrows():
                self.read_stock_name_cache()[row["code"]] = row["name"]

            self.log().info(f"Tushare 获取股票列表成功: {len(df)} 条")
            return df[["code", "name", "industry", "area", "market"]]

        except Exception as e:
            self.log().warning(f"Tushare 获取股票列表失败: {e}")

        return None


@dataclass(frozen=True)
class BaostockCatalog:
    """读取原宿主资源与扩展点，不新建缓存或 SDK。"""

    use_baostock_session: Callable
    read_stock_name_cache: Callable[[], Any]
    write_stock_name_cache: Callable[[Any], None]
    has_stock_name_cache: Callable[[], bool]
    log: Callable[[], Any]

    def get_stock_list(self) -> Optional[pd.DataFrame]:
        """
        获取股票列表

        使用 Baostock 的 query_stock_basic 接口获取全部股票列表

        Returns:
            包含 code, name 列的 DataFrame，失败返回 None
        """
        try:
            with self.use_baostock_session() as bs:
                # 查询所有股票基本信息
                rs = bs.query_stock_basic()

                if rs.error_code == "0":
                    data_list = []
                    while rs.next():
                        data_list.append(rs.get_row_data())

                    if data_list:
                        df = pd.DataFrame(data_list, columns=rs.fields)

                        # 转换代码格式（去除 sh. 或 sz. 前缀）
                        df["code"] = df["code"].apply(lambda x: x.split(".")[1] if "." in x else x)
                        df = df.rename(columns={"code_name": "name"})

                        # 更新缓存
                        if not self.has_stock_name_cache():
                            self.write_stock_name_cache({})
                        for _, row in df.iterrows():
                            self.read_stock_name_cache()[row["code"]] = row["name"]

                        self.log().info(f"Baostock 获取股票列表成功: {len(df)} 条")
                        return df[["code", "name"]]

        except Exception as e:
            self.log().warning(f"Baostock 获取股票列表失败: {e}")

        return None


@dataclass(frozen=True)
class TickflowCatalog:
    """读取原宿主资源与扩展点，不新建缓存或 SDK。"""

    use_extract_universe_entries: Callable
    use_get_client: Callable
    use_is_cn_equity_symbol: Callable
    use_is_universe_permission_error: Callable
    call_normalize_stock_code: Callable
    current_cn_universe_id: Callable[[], Any]
    log: Callable[[], Any]

    def get_stock_list(self) -> pd.DataFrame:
        """获取 TickFlow 标的池列表。"""
        client = self.use_get_client()
        if client is None:
            return pd.DataFrame(columns=["code", "name", "industry", "area", "market"])

        try:
            universe = client.universes.get(self.current_cn_universe_id())
            entries = self.use_extract_universe_entries(universe)
        except Exception as exc:
            if self.use_is_universe_permission_error(exc):
                self.log().info("[TickFlowFetcher] universe list is not available for current plan")
                return pd.DataFrame(columns=["code", "name", "industry", "area", "market"])
            self.log().warning("[TickFlowFetcher] stock universe lookup failed: %s", exc)
            return pd.DataFrame(columns=["code", "name", "industry", "area", "market"])

        rows = []
        for entry in entries:
            symbol = entry["symbol"]
            if not self.use_is_cn_equity_symbol(symbol):
                continue
            rows.append(
                {
                    "code": self.call_normalize_stock_code(symbol),
                    "name": entry.get("name", ""),
                    "industry": "",
                    "area": "",
                    "market": symbol.rsplit(".", 1)[-1],
                }
            )
        return pd.DataFrame(rows, columns=["code", "name", "industry", "area", "market"])


@dataclass(frozen=True)
class PytdxCatalog:
    """读取原宿主资源与扩展点，不新建缓存或 SDK。"""

    read_security_list_page_size: Callable[[], Any]
    read_stock_list_cache: Callable[[], Any]
    write_stock_list_cache: Callable[[Any], None]
    log: Callable[[], Any]

    def build_stock_list_cache(self, api) -> None:
        """
        Build a full stock code -> name cache from paginated security lists.
        """
        self.write_stock_list_cache({})

        for market in (0, 1):
            start = 0
            while True:
                stocks = api.get_security_list(market, start) or []
                for stock in stocks:
                    code = stock.get("code")
                    name = stock.get("name")
                    if code and name:
                        self.read_stock_list_cache()[code] = name

                if len(stocks) < self.read_security_list_page_size():
                    break

                start += self.read_security_list_page_size()


@dataclass(frozen=True)
class EfinanceBaseInfo:
    """原能力实现；不接收整个 Fetcher，不拥有第二份客户端或缓存。"""

    use_enforce_rate_limit: Callable
    use_set_random_user_agent: Callable
    read_global_logger: Callable
    read_global_ef_call_with_timeout: Callable

    def get_base_info(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        获取股票基本信息

        数据来源：ef.stock.get_base_info()
        包含：市盈率、市净率、所处行业、总市值、流通市值、ROE、净利率等

        Args:
            stock_code: 股票代码

        Returns:
            包含基本信息的字典，获取失败返回 None
        """
        import efinance as ef

        try:
            self.use_set_random_user_agent()
            self.use_enforce_rate_limit()
            self.read_global_logger().info(
                f"[API调用] ef.stock.get_base_info(stock_codes={stock_code}) 获取基本信息..."
            )
            import time as _time

            api_start = _time.time()
            info = self.read_global_ef_call_with_timeout()(
                ef.stock.get_base_info, stock_code
            )
            api_elapsed = _time.time() - api_start
            self.read_global_logger().info(
                f"[API返回] ef.stock.get_base_info 成功, 耗时 {api_elapsed:.2f}s"
            )
            if info is None:
                self.read_global_logger().warning(
                    f"[API返回] 未获取到 {stock_code} 的基本信息"
                )
                return None
            if isinstance(info, pd.Series):
                return info.to_dict()
            elif isinstance(info, pd.DataFrame):
                if not info.empty:
                    return info.iloc[0].to_dict()
            return None
        except Exception as e:
            self.read_global_logger().error(
                f"[API错误] 获取 {stock_code} 基本信息失败: {e}"
            )
            return None
