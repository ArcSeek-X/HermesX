"""ChipCoordination：原筹码取数与状态协调；共享规则以 domain 为真源。"""

from dataclasses import dataclass
from typing import Any, Callable, Optional

from src.domain.market.chip_distribution import ChipDistribution  # noqa: F401
import numpy as np
from src.domain.analysis.chip_rules import has_usable_chip_metrics


def _coerce_chip_metric(value: Any) -> Optional[float]:
    """将筹码指标值安全转换为数值。"""
    try:
        if value is None:
            return None
        numeric = float(value)
        if np.isnan(numeric):
            return None
        return numeric
    except (TypeError, ValueError):
        return None


def _is_meaningful_chip_distribution(chip: Any) -> bool:
    """Validate that a provider returned usable core chip metrics."""
    if chip is None:
        return False
    avg_cost = _coerce_chip_metric(getattr(chip, "avg_cost", None))
    concentration_90 = _coerce_chip_metric(getattr(chip, "concentration_90", None))
    concentration_70 = _coerce_chip_metric(getattr(chip, "concentration_70", None))
    return has_usable_chip_metrics(avg_cost, concentration_90, concentration_70)


@dataclass(frozen=True)
class ChipCoordination:
    """显式复用原 SDK、锁、熔断和诊断，不复制宿主资源。"""

    use_call_fetcher_method: Callable
    use_get_fetchers_snapshot: Callable
    call_normalize_stock_code: Callable
    call_record_provider_run: Callable
    call_record_provider_run_started: Callable
    call_summarize_exception: Callable
    call_is_meaningful_chip_distribution: Callable
    read_logger: Callable[[], Any]
    read_time: Callable[[], Any]

    def get_chip_distribution(self, stock_code: str):
        """
        获取筹码分布数据（带熔断和多数据源降级）

        策略：
        1. 检查配置开关
        2. 检查熔断器状态
        3. 依次尝试多个数据源：数据源优先级与获取daily的数据优先级一致
        4. 所有数据源失败则返回 None（降级兜底）

        Args:
            stock_code: 股票代码

        Returns:
            ChipDistribution 对象，失败则返回 None
        """
        # Normalize code (strip SH/SZ prefix etc.)
        stock_code = self.call_normalize_stock_code(stock_code)

        from data_provider.common.health import get_chip_circuit_breaker
        from src.config import get_config

        config = get_config()

        # 如果筹码分布功能被禁用，直接返回 None
        if not config.enable_chip_distribution:
            self.read_logger().debug(f"[筹码分布] 功能已禁用，跳过 {stock_code}")
            return None

        circuit_breaker = get_chip_circuit_breaker()

        candidate_fetchers = []
        # 直接遍历管理器已经按 priority 排好序的数据源列表
        for fetcher in self.use_get_fetchers_snapshot():
            # 只处理实现了筹码分布逻辑的数据源
            if not hasattr(fetcher, "get_chip_distribution"):
                continue

            fetcher_name = fetcher.name
            # 动态生成熔断器的 key，例如 "TushareFetcher" -> "tushare_chip"
            source_key = f"{fetcher_name.replace('Fetcher', '').lower()}_chip"

            # 检查熔断器状态
            if not circuit_breaker.is_available(source_key):
                self.read_logger().debug(f"[熔断] {fetcher_name} 筹码接口处于熔断状态，尝试下一个")
                continue

            candidate_fetchers.append((fetcher, fetcher_name, source_key))

        for index, (fetcher, fetcher_name, source_key) in enumerate(candidate_fetchers):
            fallback_to = candidate_fetchers[index + 1][1] if index + 1 < len(candidate_fetchers) else None
            attempt_start = self.read_time().time()
            try:
                self.call_record_provider_run_started(
                    data_type="chip",
                    provider=fetcher_name,
                    operation="get_chip_distribution",
                )
                chip = self.use_call_fetcher_method(fetcher, "get_chip_distribution", stock_code)
                latency_ms = int((self.read_time().time() - attempt_start) * 1000)
                if self.call_is_meaningful_chip_distribution(chip):
                    self.call_record_provider_run(
                        data_type="chip",
                        provider=fetcher_name,
                        operation="get_chip_distribution",
                        success=True,
                        latency_ms=latency_ms,
                        record_count=1,
                    )
                    circuit_breaker.record_success(source_key)
                    self.read_logger().info(f"[筹码分布] {stock_code} 成功获取 (来源: {fetcher_name})")
                    return chip
                else:
                    self.call_record_provider_run(
                        data_type="chip",
                        provider=fetcher_name,
                        operation="get_chip_distribution",
                        success=False,
                        latency_ms=latency_ms,
                        error_type="empty",
                        error_message="empty or incomplete chip distribution",
                        fallback_to=fallback_to,
                        record_count=0,
                    )
                    if chip is not None:
                        self.read_logger().warning(
                            "[筹码分布] %s 返回字段不完整或占位值，继续尝试下一个数据源",
                            fetcher_name,
                        )
                    # 空结果或占位结果：释放 HALF_OPEN 探测名额，避免卡死
                    circuit_breaker.record_inconclusive(source_key)
            except Exception as e:
                error_type, error_reason = self.call_summarize_exception(e)
                self.call_record_provider_run(
                    data_type="chip",
                    provider=fetcher_name,
                    operation="get_chip_distribution",
                    success=False,
                    latency_ms=int((self.read_time().time() - attempt_start) * 1000),
                    error_type=error_type,
                    error_message=error_reason,
                    fallback_to=fallback_to,
                )
                self.read_logger().warning(f"[筹码分布] {fetcher_name} 获取 {stock_code} 失败: {e}")
                circuit_breaker.record_failure(source_key, str(e))
                continue

        self.read_logger().warning(f"[筹码分布] {stock_code} 所有数据源均失败")
        return None
