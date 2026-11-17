"""公共契约提取后，旧导入、捕获、继承及序列化必须保持兼容。"""

import pickle

import pytest

from data_provider import base
from data_provider.common import errors, fetcher_contract
from data_provider.kline.daily_tencent_source import TencentFetcher


@pytest.mark.parametrize("name", ["DataFetchError", "RateLimitError", "DataSourceUnavailableError"])
def test_old_exception_exports_catch_canonical_errors_and_unpickle_legacy_payload(name):
    old_type = getattr(base, name)
    canonical = getattr(errors, name)
    assert old_type is canonical
    assert issubclass(canonical, base.DataFetchError)
    with pytest.raises(old_type, match="upstream failed"):
        raise canonical("upstream failed")
    legacy_payload = f"cdata_provider.base\n{name}\n(Vlegacy failure\ntR.".encode("ascii")
    restored = pickle.loads(legacy_payload)
    assert type(restored) is canonical
    assert str(restored) == "legacy failure"
    assert type(pickle.loads(pickle.dumps(restored))) is canonical


def test_existing_fetcher_inherits_the_single_public_contract():
    assert base.BaseFetcher is fetcher_contract.BaseFetcher
    assert issubclass(TencentFetcher, fetcher_contract.BaseFetcher)
    assert base.STANDARD_COLUMNS is fetcher_contract.STANDARD_COLUMNS
    assert base.summarize_exception is errors.summarize_exception
    assert base.unwrap_exception is errors.unwrap_exception
    assert fetcher_contract.logger.name == "data_provider.base"
