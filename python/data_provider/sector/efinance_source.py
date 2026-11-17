"""EfinanceSectorOperations：复用原资源/缓存与既有字段、回退和预算，不复制宿主状态。"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd
from concurrent.futures import TimeoutError as FuturesTimeoutError


@dataclass(frozen=True)
class EfinanceSectorOperations:
    """只接入本能力所需窄回调；资源和生命周期继续归原所有者。"""

    use_enforce_rate_limit: Callable
    use_set_random_user_agent: Callable
    call_ef_call_with_timeout: Callable
    read_logger: Callable[[], Any]
    read_ef_call_timeout: Callable[[], Any]

    def get_sector_rankings(self, n: int = 5) -> Optional[Tuple[List[Dict], List[Dict]]]:
        """
        获取板块涨跌榜 (efinance)
        """
        import efinance as ef

        try:
            self.use_set_random_user_agent()
            self.use_enforce_rate_limit()

            self.read_logger().info("[API调用] ef.stock.get_realtime_quotes(['行业板块']) 获取板块行情...")
            df = self.call_ef_call_with_timeout(ef.stock.get_realtime_quotes, ["行业板块"])
            if df is None or df.empty:
                self.read_logger().warning("[efinance] 板块行情数据为空")
                return None

            change_col = "涨跌幅" if "涨跌幅" in df.columns else "pct_chg"
            name_col = "股票名称" if "股票名称" in df.columns else "name"
            if change_col not in df.columns or name_col not in df.columns:
                return None

            df[change_col] = pd.to_numeric(df[change_col], errors="coerce")
            df = df.dropna(subset=[change_col])
            top = df.nlargest(n, change_col)
            bottom = df.nsmallest(n, change_col)

            top_sectors = [
                {"name": str(row[name_col]), "change_pct": float(row[change_col])} for _, row in top.iterrows()
            ]
            bottom_sectors = [
                {"name": str(row[name_col]), "change_pct": float(row[change_col])} for _, row in bottom.iterrows()
            ]
            return top_sectors, bottom_sectors
        except Exception as e:
            self.read_logger().error(f"[efinance] 获取板块排行失败: {e}")
            return None

    def get_belong_board(self, stock_code: str) -> Optional[pd.DataFrame]:
        """
        获取股票所属板块

        数据来源：ef.stock.get_belong_board()

        Args:
            stock_code: 股票代码

        Returns:
            所属板块 DataFrame，获取失败返回 None
        """
        import efinance as ef

        try:
            # 防封禁策略
            self.use_set_random_user_agent()
            self.use_enforce_rate_limit()

            self.read_logger().info(f"[API调用] ef.stock.get_belong_board(stock_code={stock_code}) 获取所属板块...")
            import time as _time

            api_start = _time.time()

            df = self.call_ef_call_with_timeout(ef.stock.get_belong_board, stock_code)

            api_elapsed = _time.time() - api_start

            if df is not None and not df.empty:
                self.read_logger().info(
                    f"[API返回] ef.stock.get_belong_board 成功: 返回 {len(df)} 个板块, 耗时 {api_elapsed:.2f}s"
                )
                return df
            else:
                self.read_logger().warning(f"[API返回] 未获取到 {stock_code} 的板块信息")
                return None

        except FuturesTimeoutError:
            self.read_logger().warning(
                f"[超时] ef.stock.get_belong_board({stock_code}) 超过 {self.read_ef_call_timeout()}s，跳过"
            )
            return None
        except Exception as e:
            self.read_logger().error(f"[API错误] 获取 {stock_code} 所属板块失败: {e}")
            return None
