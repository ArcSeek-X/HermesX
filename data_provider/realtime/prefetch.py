"""实时行情预取协调；复用原 Fetcher/缓存/调用锁，不自行持有资源。"""

import logging
from typing import Callable, List

from src.domain.market.stock_codes import normalize_stock_code

logger = logging.getLogger("data_provider.base")


def prefetch_realtime_quotes(
    stock_codes: List[str], *, get_fetcher: Callable, invoke: Callable, get_quote: Callable
) -> int:
    """
    批量预取实时行情数据（在分析开始前调用）

    策略：
    1. 检查优先级中是否包含适合预取的数据源（efinance/akshare_em/tushare/tickflow）
    2. 如果不包含，跳过预取（新浪/腾讯是单股票查询，无需预取）
    3. 如果自选股数量 >= 5 且使用可预取数据源，则预取填充缓存

    这样做的好处：
    - 使用新浪/腾讯时：每只股票独立查询，无全量拉取问题
    - 使用 efinance/东财/Tushare 时：预取一次，后续缓存命中
    - 使用 TickFlow 时：按当前自选股批量预取，避免逐股重复请求

    Args:
        stock_codes: 待分析的股票代码列表

    Returns:
        预取的股票数量（0 表示跳过预取）
    """
    # Normalize all codes
    stock_codes = [normalize_stock_code(c) for c in stock_codes]

    from src.config import get_config

    config = get_config()

    # Issue #455: PREFETCH_REALTIME_QUOTES=false 可禁用预取，避免全市场拉取
    if not getattr(config, "prefetch_realtime_quotes", True):
        logger.debug("[预取] component=realtime_prefetch action=skip reason=disabled")
        return 0

    # 如果实时行情被禁用，跳过预取
    if not config.enable_realtime_quote:
        logger.debug("[预取] component=realtime_prefetch action=skip reason=realtime_quote_disabled")
        return 0

    # 检查优先级中是否包含适合批量预取的数据源
    # efinance/akshare_em/tushare 通过一次调用填充全市场缓存；
    # tickflow 通过 symbols 批量接口预取当前自选股缓存。
    priority = config.realtime_source_priority.lower()
    prefetch_sources = ["efinance", "akshare_em", "tushare", "tickflow"]

    # 如果优先级中前两个都不是可预取数据源，跳过预取
    # 因为新浪/腾讯是单股票查询，不需要预取
    priority_list = [s.strip() for s in priority.split(",")]
    first_prefetch_source_index = None
    for i, source in enumerate(priority_list):
        if source in prefetch_sources:
            first_prefetch_source_index = i
            break

    # 如果没有可预取数据源，或者它排在第 3 位之后，跳过预取
    if first_prefetch_source_index is None or first_prefetch_source_index >= 2:
        logger.info(
            "[预取] component=realtime_prefetch action=skip reason=no_early_prefetch_source priority=%s",
            priority,
        )
        return 0

    # 如果股票数量少于 5 个，不进行批量预取（逐个查询更高效）
    if len(stock_codes) < 5:
        logger.info(
            "[预取] component=realtime_prefetch action=skip reason=small_batch "
            "stock_count=%d threshold=5 prefetch_source=%s",
            len(stock_codes),
            priority_list[first_prefetch_source_index],
        )
        return 0

    prefetch_source = priority_list[first_prefetch_source_index]
    logger.info(
        "[预取] component=realtime_prefetch action=start stock_count=%d prefetch_source=%s first_code=%s",
        len(stock_codes),
        prefetch_source,
        stock_codes[0],
    )

    # TickFlow 使用 symbols 批量接口；其他可预取源通过首次查询触发自身缓存。
    if prefetch_source == "tickflow":
        fetcher = get_fetcher("TickFlowFetcher", capability="realtime_quote")
        if fetcher is None or not hasattr(fetcher, "prefetch_realtime_quotes"):
            logger.info("[prefetch] component=realtime_prefetch action=skip reason=tickflow_unavailable")
            return 0
        try:
            return int(
                invoke(
                    fetcher,
                    "prefetch_realtime_quotes",
                    stock_codes,
                    batch_size=getattr(config, "tickflow_batch_size", 100),
                )
                or 0
            )
        except Exception as exc:
            logger.warning("[TickFlowFetcher] realtime prefetch failed: %s", exc)
            return 0

    try:
        # 用第一只股票触发全量拉取
        first_code = stock_codes[0]
        quote = get_quote(first_code)

        if quote:
            logger.info(
                "[预取] component=realtime_prefetch action=complete status=success "
                "stock_count=%d prefetch_source=%s",
                len(stock_codes),
                prefetch_source,
            )
            return len(stock_codes)
        else:
            logger.warning(
                "[预取] component=realtime_prefetch action=complete status=failed "
                "stock_count=%d prefetch_source=%s fallback=per_stock",
                len(stock_codes),
                prefetch_source,
            )
            return 0

    except Exception as e:
        logger.error(
            "[预取] component=realtime_prefetch action=complete status=error "
            "stock_count=%d prefetch_source=%s error=%s",
            len(stock_codes),
            prefetch_source,
            e,
        )
        return 0
