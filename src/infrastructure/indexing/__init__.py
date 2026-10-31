# -*- coding: utf-8 -*-
"""股票映射与索引加载适配。

承载用例所需的股票代码能力：

- ``stock_code_validator``：自选股用例的代码核验；
- ``stock_code_normalizer``：分析历史个股栏去重所需的代码归一化。

索引数据本身仍由 ``src.data.stock_index_loader`` 读取与缓存，本包只负责把它
（以及仍归 ``data_provider.base`` 的 ``normalize_stock_code``）包装成用例端口。
"""
