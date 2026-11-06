"""Root compatibility exports stay lazy and retain identity across replacement scopes."""

import importlib
import subprocess
import sys
from unittest.mock import patch

from tests.support.paths import get_repo_root


def test_package_import_does_not_load_vendor_modules_or_pandas():
    result = subprocess.run([sys.executable, "-c", "\n".join([
        "import sys, data_provider",
        "assert 'pandas' not in sys.modules",
        "assert 'data_provider.runtime.fetchers.akshare' not in sys.modules",
        "assert set(data_provider.__all__) <= set(dir(data_provider))",
    ])], cwd=get_repo_root(), capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr


def test_lazy_export_reflects_scoped_module_replacement():
    import data_provider
    module = importlib.import_module("data_provider.runtime.fetchers.akshare")
    original = module.AkshareFetcher
    replacement = object()
    with patch.object(module, "AkshareFetcher", replacement):
        assert data_provider.AkshareFetcher is replacement
    assert data_provider.AkshareFetcher is original


def test_index_helper_and_package_share_domain_mapping():
    import data_provider
    from data_provider.common import symbols
    from src.domain.market import us_index_symbols
    assert symbols.US_INDEX_MAPPING is us_index_symbols.US_INDEX_MAPPING
    assert symbols.get_us_index_yf_symbol("spx") == us_index_symbols.US_INDEX_MAPPING["SPX"]

    assert data_provider.US_INDEX_MAPPING is us_index_symbols.US_INDEX_MAPPING
    assert data_provider.is_us_index_code is us_index_symbols.is_us_index_code
    assert data_provider.is_us_stock_code is us_index_symbols.is_us_stock_code
    assert data_provider.get_us_index_yf_symbol is symbols.get_us_index_yf_symbol


def test_low_level_symbol_imports_do_not_load_runtime_manager():
    result = subprocess.run([sys.executable, "-c", "\n".join([
        "import sys",
        "import data_provider.common.normalize",
        "import data_provider.common.symbols",
        "import data_provider.clients.stocksdk.bridge",
        "assert 'data_provider.base' not in sys.modules",
        "assert 'data_provider.runtime.manager' not in sys.modules",
    ])], cwd=get_repo_root(), capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
