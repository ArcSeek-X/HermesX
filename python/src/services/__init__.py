# -*- coding: utf-8 -*-
"""
===================================
服务层模块初始化
===================================

职责：
1. 声明可导出的服务类（延迟导入，避免启动时拉入 LLM 等重依赖）
2. 兼容面：`src/services/` 已无具体实现（全部下沉 `src/application/`），
   本模块仅保留 `get_task_service` 惰性映射，供外部脚本/历史调用方过渡。
   全仓 0 个生产调用方（`bot/commands/analyze.py` 已直接 import
   `src.application.runtime.task_service`），删除属对外契约变更，故按
   “保留兼容面”处理；新增代码请勿再从这里导入。

使用方式：
    直接从子模块导入，例如:
    from src.application.quote.stock_code_utils import normalize_stock_code_for_input
"""


def __getattr__(name: str):
    """延迟导入：仅在通过 src.services.X 访问时才加载对应实现模块。"""
    _lazy_map = {
        "get_task_service": "src.application.runtime.task_service",
    }
    if name in _lazy_map:
        import importlib
        module = importlib.import_module(_lazy_map[name])
        return getattr(module, name)
    raise AttributeError(f"module 'src.services' has no attribute {name!r}")


__all__ = [
    "get_task_service",
]
