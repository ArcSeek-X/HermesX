"""AkshareChipSource：原筹码取数与状态协调；共享规则以 domain 为真源。"""

from dataclasses import dataclass
from typing import Any, Callable, Optional

from src.domain.market.chip_distribution import ChipDistribution


@dataclass(frozen=True)
class AkshareChipSource:
    """显式复用原 SDK、锁、熔断和诊断，不复制宿主资源。"""

    use_enforce_rate_limit: Callable
    use_set_random_user_agent: Callable
    call_is_us_code: Callable
    call_is_hk_code: Callable
    call_is_etf_code: Callable
    call_safe_float: Callable
    read_logger: Callable[[], Any]

    def get_chip_distribution(self, stock_code: str) -> Optional[ChipDistribution]:
        """
        获取筹码分布数据

        数据来源：ak.stock_cyq_em()
        包含：获利比例、平均成本、筹码集中度

        注意：ETF/指数没有筹码分布数据，会直接返回 None

        Args:
            stock_code: 股票代码

        Returns:
            ChipDistribution 对象（最新一天的数据），获取失败返回 None
        """
        import akshare as ak

        # 美股没有筹码分布数据（Akshare 不支持）
        if self.call_is_us_code(stock_code):
            self.read_logger().debug(f"[API跳过] {stock_code} 是美股，无筹码分布数据")
            return None

        # 港股没有筹码分布数据（stock_cyq_em 是 A 股专属接口）
        if self.call_is_hk_code(stock_code):
            self.read_logger().debug(f"[API跳过] {stock_code} 是港股，无筹码分布数据")
            return None

        # ETF/指数没有筹码分布数据
        if self.call_is_etf_code(stock_code):
            self.read_logger().debug(f"[API跳过] {stock_code} 是 ETF/指数，无筹码分布数据")
            return None

        try:
            # 防封禁策略
            self.use_set_random_user_agent()
            self.use_enforce_rate_limit()

            self.read_logger().info(f"[API调用] ak.stock_cyq_em(symbol={stock_code}) 获取筹码分布...")
            import time as _time

            api_start = _time.time()

            df = ak.stock_cyq_em(symbol=stock_code)

            api_elapsed = _time.time() - api_start

            if df.empty:
                self.read_logger().warning(f"[API返回] ak.stock_cyq_em 返回空数据, 耗时 {api_elapsed:.2f}s")
                return None

            self.read_logger().info(f"[API返回] ak.stock_cyq_em 成功: 返回 {len(df)} 天数据, 耗时 {api_elapsed:.2f}s")
            self.read_logger().debug(f"[API返回] 筹码数据列名: {list(df.columns)}")

            # 取最新一天的数据
            latest = df.iloc[-1]

            # 使用 realtime_types.py 中的统一转换函数
            chip = ChipDistribution(
                code=stock_code,
                date=str(latest.get("日期", "")),
                profit_ratio=self.call_safe_float(latest.get("获利比例")),
                avg_cost=self.call_safe_float(latest.get("平均成本")),
                cost_90_low=self.call_safe_float(latest.get("90成本-低")),
                cost_90_high=self.call_safe_float(latest.get("90成本-高")),
                concentration_90=self.call_safe_float(latest.get("90集中度")),
                cost_70_low=self.call_safe_float(latest.get("70成本-低")),
                cost_70_high=self.call_safe_float(latest.get("70成本-高")),
                concentration_70=self.call_safe_float(latest.get("70集中度")),
            )

            self.read_logger().info(
                f"[筹码分布] {stock_code} 日期={chip.date}: 获利比例={chip.profit_ratio:.1%}, "
                f"平均成本={chip.avg_cost}, 90%集中度={chip.concentration_90:.2%}, "
                f"70%集中度={chip.concentration_70:.2%}"
            )
            return chip

        except Exception as e:
            self.read_logger().error(f"[API错误] 获取 {stock_code} 筹码分布失败: {e}")
            return None
