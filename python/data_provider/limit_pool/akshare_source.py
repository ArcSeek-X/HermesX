"""AkshareLimitPoolOperations：复用原资源/缓存与既有字段、回退和预算，不复制宿主状态。"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import pandas as pd


@dataclass(frozen=True)
class AkshareLimitPoolOperations:
    """只接入本能力所需窄回调；资源和生命周期继续归原所有者。"""

    use_enforce_realtime_rate_limit: Callable
    use_normalize_limit_time_value: Callable
    use_safe_float: Callable
    use_safe_int: Callable
    use_set_random_user_agent: Callable
    read_logger: Callable[[], Any]
    read_datetime: Callable[[], Any]

    def get_limit_up_pool(
        self,
        date: Optional[str] = None,
        n: int = 20,
    ) -> Optional[List[Dict[str, Any]]]:
        """获取涨停池，优先按连板数和封板时间展示。

        角色：作为 `data_provider/limit_pool/eastmoney_source.py` 的物理后端
        （ADR-001 §4.4「既有文件处置」），不再属于 `BaseFetcher` 能力契约。
        """
        import akshare as ak

        query_date = date or self.read_datetime().now().strftime("%Y%m%d")
        try:
            self.use_set_random_user_agent()
            # 榜单池为单次轻量 GET（与实时行情同级），2~5s 全量爬取休眠会把接口拖到秒级；
            # 请求频率由 emotion 接口层 60s TTL 缓存控制，这里走轻量限速。
            self.use_enforce_realtime_rate_limit()

            self.read_logger().info("[API调用] ak.stock_zt_pool_em(date=%s) 获取涨停池...", query_date)
            df = ak.stock_zt_pool_em(date=query_date)
            if df is None or df.empty:
                return None

            df = df.copy()
            for col in ("连板数", "封板资金", "成交额", "换手率", "涨跌幅"):
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            if "首次封板时间" in df.columns:
                df["首次封板时间"] = df["首次封板时间"].map(self.use_normalize_limit_time_value)
                df["_首次封板时间排序"] = df["首次封板时间"].where(df["首次封板时间"] != "", "999999")
            sort_cols = [col for col in ("连板数", "_首次封板时间排序") if col in df.columns]
            if sort_cols:
                ascending = [False if col == "连板数" else True for col in sort_cols]
                df = df.sort_values(sort_cols, ascending=ascending)

            rows: List[Dict[str, Any]] = []
            for _, row in df.head(n).iterrows():
                rows.append(
                    {
                        "code": str(row.get("代码", "")).strip(),
                        "name": str(row.get("名称", "")).strip(),
                        "change_pct": self.use_safe_float(row.get("涨跌幅")),
                        "price": self.use_safe_float(row.get("最新价")),
                        "amount": self.use_safe_float(row.get("成交额")),
                        "turnover_rate": self.use_safe_float(row.get("换手率")),
                        "seal_amount": self.use_safe_float(row.get("封板资金")),
                        "first_limit_time": str(row.get("首次封板时间", "")).strip(),
                        "last_limit_time": self.use_normalize_limit_time_value(row.get("最后封板时间")),
                        "break_count": self.use_safe_int(row.get("炸板次数")),
                        "limit_stat": str(row.get("涨停统计", "")).strip(),
                        "consecutive_boards": self.use_safe_int(row.get("连板数")),
                        "industry": str(row.get("所属行业", "")).strip(),
                    }
                )
            return rows
        except Exception as e:
            self.read_logger().warning(f"[Akshare] 获取涨停池失败: {e}")
            return None

    def get_limit_down_pool(
        self,
        date: Optional[str] = None,
        n: int = 20,
    ) -> Optional[List[Dict[str, Any]]]:
        """获取跌停池，优先按连续跌停数和封板时间展示。

        字段与涨停池归一为同一 schema（consecutive_boards 表示连续跌停次数）；
        跌停池无「首次封板时间」字段，first_limit_time 以「最后封板时间」充当。

        角色：作为 `data_provider/limit_pool/eastmoney_source.py` 的物理后端
        （ADR-001 §4.4「既有文件处置」），不再属于 `BaseFetcher` 能力契约。
        """
        import akshare as ak

        query_date = date or self.read_datetime().now().strftime("%Y%m%d")
        try:
            self.use_set_random_user_agent()
            # 同涨停池：单次轻量 GET 走轻量限速，频率由接口层 60s TTL 缓存控制
            self.use_enforce_realtime_rate_limit()

            self.read_logger().info("[API调用] ak.stock_zt_pool_dtgc_em(date=%s) 获取跌停池...", query_date)
            df = ak.stock_zt_pool_dtgc_em(date=query_date)
            if df is None or df.empty:
                return None

            df = df.copy()
            for col in ("连续跌停", "封单资金", "成交额", "换手率", "涨跌幅"):
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            if "最后封板时间" in df.columns:
                df["最后封板时间"] = df["最后封板时间"].map(self.use_normalize_limit_time_value)
                df["_封板时间排序"] = df["最后封板时间"].where(df["最后封板时间"] != "", "999999")
            sort_cols = [col for col in ("连续跌停", "_封板时间排序") if col in df.columns]
            if sort_cols:
                ascending = [False if col == "连续跌停" else True for col in sort_cols]
                df = df.sort_values(sort_cols, ascending=ascending)

            rows: List[Dict[str, Any]] = []
            for _, row in df.head(n).iterrows():
                seal_time = str(row.get("最后封板时间", "")).strip()
                rows.append(
                    {
                        "code": str(row.get("代码", "")).strip(),
                        "name": str(row.get("名称", "")).strip(),
                        "change_pct": self.use_safe_float(row.get("涨跌幅")),
                        "price": self.use_safe_float(row.get("最新价")),
                        "amount": self.use_safe_float(row.get("成交额")),
                        "turnover_rate": self.use_safe_float(row.get("换手率")),
                        "seal_amount": self.use_safe_float(row.get("封单资金")),
                        # 跌停池无首次封板时间，统一以最后封板时间充当封板时间
                        "first_limit_time": seal_time,
                        "last_limit_time": seal_time,
                        "break_count": self.use_safe_int(row.get("开板次数")),
                        "limit_stat": "",
                        "consecutive_boards": self.use_safe_int(row.get("连续跌停")),
                        "industry": str(row.get("所属行业", "")).strip(),
                    }
                )
            return rows
        except Exception as e:
            self.read_logger().warning(f"[Akshare] 获取跌停池失败: {e}")
            return None


def normalize_limit_time_value(value: Any) -> str:
    """Normalize AkShare HHMMSS-like seal time values to zero-padded HHMMSS."""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass

    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "none", "null", "-", "--"}:
        return ""

    if ":" in text:
        parts = text.split(":")
        try:
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            second = int(parts[2]) if len(parts) > 2 else 0
            return f"{hour:02d}{minute:02d}{second:02d}"
        except (TypeError, ValueError):
            return text

    try:
        return f"{int(float(text)):06d}"
    except (TypeError, ValueError):
        digits = "".join(ch for ch in text if ch.isdigit())
        return digits.zfill(6) if digits else text
