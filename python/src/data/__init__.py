# -*- coding: utf-8 -*-
"""
股票数据相关的共享模块（代码/名称映射等）。

- ``stock_mapping``：代码↔名称映射、海外标的英文别名、规范化工具
- ``stock_index_loader``：从前端构建产物/远端缓存加载股票索引（名称/代码映射）
"""

from src.data.stock_mapping import STOCK_NAME_MAP

__all__ = ["STOCK_NAME_MAP"]
