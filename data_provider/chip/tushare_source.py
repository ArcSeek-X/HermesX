"""TushareChipSource：原筹码取数与状态协调；共享规则以 domain 为真源。"""

from dataclasses import dataclass
from typing import Any, Callable, Optional

from src.domain.market.chip_distribution import ChipDistribution


@dataclass(frozen=True)
class TushareChipSource:
    """显式复用原 SDK、锁、熔断和诊断，不复制宿主资源。"""

    use_call_api_with_rate_limit: Callable
    use_convert_stock_code: Callable
    use_compute_cyq_metrics: Callable
    use_get_trade_time: Callable
    call_is_us_code: Callable
    call_is_etf_code: Callable
    call_is_hk_market: Callable
    read_logger: Callable[[], Any]
    read_datetime: Callable[[], Any]

    def get_chip_distribution(self, stock_code: str) -> Optional[ChipDistribution]:
        """
        获取筹码分布数据

        数据来源：ts.pro_api().cyq_chips()
        包含：获利比例、平均成本、筹码集中度

        注意：ETF/指数没有筹码分布数据，会直接返回 None；港股不支持，直接返回 None。
        5000积分以下每天访问15次,每小时访问5次

        Args:
            stock_code: 股票代码

        Returns:
            ChipDistribution 对象（最新交易日的数据），获取失败返回 None

        """
        if self.call_is_us_code(stock_code):
            self.read_logger().warning(f"[Tushare] TushareFetcher 不支持美股 {stock_code} 的筹码分布")
            return None

        if self.call_is_etf_code(stock_code):
            self.read_logger().warning(f"[Tushare] TushareFetcher 不支持 ETF {stock_code} 的筹码分布")
            return None

        if self.call_is_hk_market(stock_code):
            self.read_logger().warning(f"[Tushare] TushareFetcher 不支持港股 {stock_code} 的筹码分布")
            return None

        try:
            # 19点之后才有当天数据
            start_date = self.use_get_trade_time(early_time="00:00", late_time="19:00")
            if not start_date:
                return None

            ts_code = self.use_convert_stock_code(stock_code)

            df = self.use_call_api_with_rate_limit(
                "cyq_chips",
                ts_code=ts_code,
                start_date=start_date,
                end_date=start_date,
            )
            if df is not None and not df.empty:
                daily_df = self.use_call_api_with_rate_limit(
                    "daily",
                    ts_code=ts_code,
                    start_date=start_date,
                    end_date=start_date,
                )
                if daily_df is None or daily_df.empty:
                    return None
                current_price = daily_df.iloc[0]["close"]
                metrics = self.use_compute_cyq_metrics(df, current_price)

                chip = ChipDistribution(
                    code=stock_code,
                    date=self.read_datetime().strptime(start_date, "%Y%m%d").strftime("%Y-%m-%d"),
                    profit_ratio=metrics["获利比例"],
                    avg_cost=metrics["平均成本"],
                    cost_90_low=metrics["90成本-低"],
                    cost_90_high=metrics["90成本-高"],
                    concentration_90=metrics["90集中度"],
                    cost_70_low=metrics["70成本-低"],
                    cost_70_high=metrics["70成本-高"],
                    concentration_70=metrics["70集中度"],
                )

                self.read_logger().info(
                    f"[筹码分布] {stock_code} 日期={chip.date}: 获利比例={chip.profit_ratio:.1%}, "
                    f"平均成本={chip.avg_cost}, 90%集中度={chip.concentration_90:.2%}, "
                    f"70%集中度={chip.concentration_70:.2%}"
                )
                return chip

        except Exception as e:
            self.read_logger().warning(f"[Tushare] 获取筹码分布失败 {stock_code}: {e}")
            return None
