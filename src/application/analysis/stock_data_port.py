# -*- coding: utf-8 -*-
"""个股分析主流程的取数端口契约（R3-S15b）。

``StockAnalysisPipeline`` 历史上在构造期直接 ``DataFetcherManager()``，随编排层搬入
``src/application/analysis/`` 后，这行 import 会命中 application 层“不得依赖具体数据源包”
的守卫。本模块把“取数能力”收敛为显式端口：流水线只依赖 :class:`StockDataPort` 协议，
具体实现由 ``src/infrastructure/providers/analysis_stock_data_provider.py`` 承接，并经
``src/bootstrap/analysis.py`` 的 ``configure_stock_data_port()`` 工厂 seam 注入。

设计约束（对齐 R2-B3 / R3-S11 既有端口模式）：

- 方法面即 pipeline 实测调用点去重后的 10 个方法，不新增、不遗漏；名称均为公开名
  （无 ``_`` 前缀），对 ``forbid_private_members`` 零命中。
- 保持结构化（Protocol / 鸭子类型），不引入 ABC 继承链。
- 排行榜类能力（``get_concept_rankings`` / ``get_sector_rankings`` 等）由
  ``MarketHotspotService`` 以 ``getattr`` 动态探测后调用，属可选能力，不进入本协议的必选面；
  适配器以 ``__getattr__`` 透传，缺失时保留原有 ``AttributeError`` 语义（探测即得 ``None``）。
- 与 ``ImageRenderPort``（未装配回退文本）不同，取数是主流程必需能力：未装配时 **显式报错**，
  不静默降级为空数据，避免把“漏装配”伪装成“数据源无数据”。
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple, runtime_checkable


@runtime_checkable
class StockDataPort(Protocol):
    """个股分析主流程所需的取数能力（按 pipeline 真实调用点去重）。"""

    def get_stock_name(
        self, stock_code: str, allow_realtime: bool = True
    ) -> Optional[str]: ...

    def get_daily_data(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        days: int = 30,
    ) -> Tuple[Any, str]: ...

    def get_realtime_quote(
        self, stock_code: str, *, log_final_failure: bool = True
    ) -> Any: ...

    def get_chip_distribution(self, stock_code: str) -> Any: ...

    def get_fundamental_context(
        self, stock_code: str, budget_seconds: Optional[float] = None
    ) -> Dict[str, Any]: ...

    def build_failed_fundamental_context(
        self, stock_code: str, reason: str
    ) -> Dict[str, Any]: ...

    def get_belong_boards(self, stock_code: str) -> List[Dict[str, Any]]: ...

    def prefetch_daily_klines(self, stock_codes: List[str], days: int = 30) -> int: ...

    def prefetch_realtime_quotes(self, stock_codes: List[str]) -> int: ...

    def prefetch_stock_names(
        self, stock_codes: List[str], use_bulk: bool = False
    ) -> None: ...


# —— 取数端口的 bootstrap seam（R3-S15b）——
#
# application 不得 import ``data_provider``；编排层需要的默认取数实现改由下面这对 hook 取得：
# 具体工厂（infra 的 ``DataFetcherManagerStockDataPort``）由入口（``main.py`` /
# ``api_lifecycle`` / 测试 conftest）经 ``src.bootstrap.configure_stock_data_port()`` 注册。
# 与图片渲染端口不同，这里不做 None 降级：未注册时直接抛错，把漏装配暴露在启动期。
_stock_data_port_factory: Optional[Callable[[], "StockDataPort"]] = None


def set_stock_data_port_factory(
    factory: Optional[Callable[[], "StockDataPort"]],
) -> None:
    """注册默认取数端口工厂（入口装配用，幂等；传 None 可重置）。"""
    global _stock_data_port_factory
    _stock_data_port_factory = factory


def build_stock_data_port() -> "StockDataPort":
    """构造默认取数端口；未装配时抛错（不静默降级为空数据）。"""
    if _stock_data_port_factory is None:
        raise RuntimeError(
            "StockDataPort 未装配：请在启动链路调用 "
            "src.bootstrap.analysis.configure_stock_data_port()（CLI 见 main.py，API 见 "
            "src.bootstrap.api_lifecycle，测试见 tests/conftest.py）"
        )
    return _stock_data_port_factory()
