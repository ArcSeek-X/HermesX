"""公开兼容面：类型与规则复用唯一实现，不持有资源或能力算法。"""

from data_provider.common.errors import (  # noqa: F401
    DataFetchError, RateLimitError, DataSourceUnavailableError,
    unwrap_exception, summarize_exception,
)
from data_provider.common.fetcher_contract import BaseFetcher, STANDARD_COLUMNS  # noqa: F401
from data_provider.runtime.manager import DataFetcherManager  # noqa: F401
from src.domain.market.stock_codes import (  # noqa: F401
    canonical_stock_code, normalize_stock_code, is_bse_code,
    is_st_stock, is_kc_cy_stock,
)
