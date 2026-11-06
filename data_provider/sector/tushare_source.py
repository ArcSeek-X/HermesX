"""TushareSectorOperations：复用原资源/缓存与既有字段、回退和预算，不复制宿主状态。"""

from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple

import pandas as pd


@dataclass(frozen=True)
class TushareSectorOperations:
    """只接入本能力所需窄回调；资源和生命周期继续归原所有者。"""

    use_call_api_with_rate_limit: Callable
    use_get_trade_time: Callable
    read_logger: Callable[[], Any]

    def get_sector_rankings(self, n: int = 5) -> Optional[Tuple[list, list]]:
        """
        获取行业板块涨跌榜 (Tushare Pro)

        数据源优先级：
        1. 同花顺接口 (ts.pro_api().moneyflow_ind_ths)
        2. 东财接口 (ts.pro_api().moneyflow_ind_dc)
        注意：每个接口的行业分类和板块定义不同，会导致结果两者不一致
        """

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

        # 15:30之后才有当天数据
        start_date = self.use_get_trade_time(early_time="00:00", late_time="15:30")
        if not start_date:
            return None

        # 优先同花顺接口
        self.read_logger().info("[Tushare] ts.pro_api().moneyflow_ind_ths 获取板块排行(同花顺)...")
        try:
            df = self.use_call_api_with_rate_limit("moneyflow_ind_ths", trade_date=start_date)
            if df is not None and not df.empty:
                change_col = "pct_change"
                name = "industry"
                if change_col in df.columns:
                    return _get_rank_top_n(df, change_col, name, n)
        except Exception as e:
            self.read_logger().warning(f"[Tushare] 获取同花顺行业板块涨跌榜失败: {e} 尝试东财接口")

        # 同花顺接口失败，降级尝试东财接口
        self.read_logger().info("[Tushare] ts.pro_api().moneyflow_ind_dc 获取板块排行(东财)...")
        try:
            df = self.use_call_api_with_rate_limit("moneyflow_ind_dc", trade_date=start_date)
            if df is not None and not df.empty:
                df = df[df["content_type"] == "行业"]  # 过滤出行业板块
                change_col = "pct_change"
                name = "name"
                if change_col in df.columns:
                    return _get_rank_top_n(df, change_col, name, n)
        except Exception as e:
            self.read_logger().warning(f"[Tushare] 获取东财行业板块涨跌榜失败: {e}")
            return None

        # 获取为空或者接口调用失败，返回 None
        return None
