"""AkshareSectorOperations：复用原资源/缓存与既有字段、回退和预算，不复制宿主状态。"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd


@dataclass(frozen=True)
class AkshareSectorOperations:
    """只接入本能力所需窄回调；资源和生命周期继续归原所有者。"""

    use_enforce_rate_limit: Callable
    use_find_column_containing: Callable
    use_find_first_column: Callable
    use_get_eastmoney_hot_stocks: Callable
    use_get_eastmoney_hot_up_stocks: Callable
    use_get_xueqiu_hot_stocks: Callable
    use_safe_float: Callable
    use_safe_int: Callable
    use_set_random_user_agent: Callable
    read_logger: Callable[[], Any]

    def get_sector_rankings(self, n: int = 5) -> Optional[Tuple[List[Dict], List[Dict]]]:
        """
        获取行业板块涨跌榜

        数据源优先级：
        1. 东财接口 (ak.stock_board_industry_name_em)
        2. 新浪接口 (ak.stock_sector_spot)
        """
        import akshare as ak

        def _get_rank_top_n(df: pd.DataFrame, change_col: str, industry_name: str, n: int) -> Tuple[list, list]:
            """取排行前 N 条记录。"""
            df[change_col] = pd.to_numeric(df[change_col], errors="coerce")
            df = df.dropna(subset=[change_col])

            # 涨幅前n
            top = df.nlargest(n, change_col)
            top_sectors = [{"name": row[industry_name], "change_pct": row[change_col]} for _, row in top.iterrows()]

            bottom = df.nsmallest(n, change_col)
            bottom_sectors = [
                {"name": row[industry_name], "change_pct": row[change_col]} for _, row in bottom.iterrows()
            ]
            return top_sectors, bottom_sectors

        # 优先东财接口
        try:
            self.use_set_random_user_agent()
            self.use_enforce_rate_limit()

            self.read_logger().info("[API调用] ak.stock_board_industry_name_em() 获取板块排行...")
            df = ak.stock_board_industry_name_em()
            if df is not None and not df.empty:
                change_col = "涨跌幅"
                name = "板块名称"
                return _get_rank_top_n(df, change_col, name, n)

        except Exception as e:
            self.read_logger().warning(f"[Akshare] 东财接口获取行业板块排行失败: {e}，尝试新浪接口")

        # 东财失败后，尝试新浪接口
        try:
            self.use_set_random_user_agent()
            self.use_enforce_rate_limit()

            self.read_logger().info("[API调用] ak.stock_sector_spot() 获取行业板块排行(新浪)...")
            df = ak.stock_sector_spot(indicator="行业")
            if df is None or df.empty:
                return None
            change_col = "涨跌幅"
            name = "板块"
            return _get_rank_top_n(df, change_col, name, n)

        except Exception as e:
            self.read_logger().error(f"[Akshare] 新浪接口获取板块排行也失败: {e}")
            return None

    def get_concept_rankings(self, n: int = 5) -> Optional[Tuple[List[Dict], List[Dict]]]:
        """获取概念/题材涨跌榜。"""
        import akshare as ak

        try:
            self.use_set_random_user_agent()
            self.use_enforce_rate_limit()

            self.read_logger().info("[API调用] ak.stock_board_concept_name_em() 获取概念排行...")
            df = ak.stock_board_concept_name_em()
            if df is None or df.empty:
                return None

            change_col = "涨跌幅"
            name_col = "板块名称"
            if change_col not in df.columns or name_col not in df.columns:
                return None

            df = df.copy()
            df[change_col] = pd.to_numeric(df[change_col], errors="coerce")
            df = df.dropna(subset=[change_col])
            top = df.nlargest(n, change_col)
            bottom = df.nsmallest(n, change_col)
            return (
                [{"name": str(row[name_col]), "change_pct": float(row[change_col])} for _, row in top.iterrows()],
                [{"name": str(row[name_col]), "change_pct": float(row[change_col])} for _, row in bottom.iterrows()],
            )
        except Exception as e:
            self.read_logger().warning(f"[Akshare] 获取概念排行失败: {e}")
            return None

    def get_hot_stocks(self, n: int = 10) -> Optional[List[Dict[str, Any]]]:
        """获取人气股榜，按免配置热榜数据源降级。"""
        import akshare as ak

        fetch_attempts = (
            ("东方财富人气榜", lambda top_n: self.use_get_eastmoney_hot_stocks(ak, top_n)),
            ("东方财富飙升榜", lambda top_n: self.use_get_eastmoney_hot_up_stocks(ak, top_n)),
            ("雪球关注榜", lambda top_n: self.use_get_xueqiu_hot_stocks(ak, top_n)),
        )
        last_error = ""
        for source, fetch in fetch_attempts:
            try:
                rows = fetch(n)
                if rows:
                    return rows[:n]
            except Exception as e:
                last_error = f"{source}: {e}"
                self.read_logger().debug("[Akshare] 人气股候选源失败 source=%s: %s", source, e)
        if last_error:
            self.read_logger().warning("[Akshare] 获取人气股全部候选源失败: %s", last_error)
        return None

    def get_eastmoney_hot_stocks(self, ak: Any, n: int = 10) -> Optional[List[Dict[str, Any]]]:
        """获取东方财富人气股榜。"""
        self.use_set_random_user_agent()
        self.use_enforce_rate_limit()

        self.read_logger().info("[API调用] ak.stock_hot_rank_em() 获取东方财富人气股...")
        df = ak.stock_hot_rank_em()
        if df is None or df.empty:
            return None

        rows: List[Dict[str, Any]] = []
        for _, row in df.head(n).iterrows():
            rows.append(
                {
                    "rank": self.use_safe_int(row.get("当前排名")),
                    "code": str(row.get("代码", "")).strip(),
                    "name": str(row.get("股票名称", "")).strip(),
                    "price": self.use_safe_float(row.get("最新价")),
                    "change_pct": self.use_safe_float(row.get("涨跌幅")),
                    "source": "东方财富人气榜",
                }
            )
        return rows

    def get_eastmoney_hot_up_stocks(self, ak: Any, n: int = 10) -> Optional[List[Dict[str, Any]]]:
        """获取东方财富飙升榜。"""
        self.use_set_random_user_agent()
        self.use_enforce_rate_limit()

        self.read_logger().info("[API调用] ak.stock_hot_up_em() 获取东方财富飙升榜...")
        df = ak.stock_hot_up_em()
        if df is None or df.empty:
            return None

        code_col = self.use_find_first_column(df, ("代码", "股票代码"))
        name_col = self.use_find_first_column(df, ("股票名称", "名称", "股票简称"))
        rank_col = self.use_find_first_column(df, ("当前排名", "排名", "序号"))
        price_col = self.use_find_first_column(df, ("最新价", "现价"))
        change_col = self.use_find_column_containing(df, ("涨跌幅",))
        if not code_col or not name_col:
            return None

        rows: List[Dict[str, Any]] = []
        for _, row in df.head(n).iterrows():
            rows.append(
                {
                    "rank": self.use_safe_int(row.get(rank_col)) if rank_col else len(rows) + 1,
                    "code": str(row.get(code_col, "")).strip(),
                    "name": str(row.get(name_col, "")).strip(),
                    "price": self.use_safe_float(row.get(price_col)) if price_col else None,
                    "change_pct": self.use_safe_float(row.get(change_col)) if change_col else None,
                    "source": "东方财富飙升榜",
                }
            )
        return rows

    def get_xueqiu_hot_stocks(self, ak: Any, n: int = 10) -> Optional[List[Dict[str, Any]]]:
        """获取雪球关注榜兜底。该接口较慢，仅在人气榜失败后尝试。"""
        self.use_set_random_user_agent()
        self.use_enforce_rate_limit()

        self.read_logger().info("[API调用] ak.stock_hot_follow_xq() 获取雪球关注榜...")
        df = ak.stock_hot_follow_xq(symbol="最热门")
        if df is None or df.empty:
            return None

        rows: List[Dict[str, Any]] = []
        for idx, (_, row) in enumerate(df.head(n).iterrows(), 1):
            rows.append(
                {
                    "rank": idx,
                    "code": str(row.get("股票代码", "")).strip(),
                    "name": str(row.get("股票简称", "")).strip(),
                    "price": self.use_safe_float(row.get("最新价")),
                    "change_pct": None,
                    "source": "雪球关注榜",
                }
            )
        return rows
