# -*- coding: utf-8 -*-
"""分析主流程端口的装配（R3-S15b：股票取数端口）。

``StockAnalysisPipeline`` 搬入 ``src/application/analysis/`` 后只依赖
``src.application.analysis.stock_data_port.StockDataPort`` 协议，不再 import
``data_provider``。默认实现
:class:`~src.infrastructure.providers.analysis_stock_data_provider.DataFetcherManagerStockDataPort`
的工厂由本装配在进程入口注册。

与图片渲染端口（未装配回退文本）不同，取数是主流程必需能力：seam 未注册时
``build_stock_data_port()`` 直接抛错，把漏装配暴露在启动期而不是静默返回空数据。
因此本装配必须覆盖全部三条入口链路：``main.py``（CLI）、
``src.bootstrap.api_lifecycle``（API）与 ``tests/conftest.py``（测试会话）。
"""

from __future__ import annotations


def configure_analysis_pipeline_persistence() -> None:
    """装配个股分析主流程的持久化端口工厂（DatabaseManager 适配器）。

    W4.2：``StockAnalysisPipeline`` 不再在构造期 ``get_db()`` 直连 ``src.storage``，
    改为经 ``AnalysisPipelinePersistencePort`` 取得日线读写、基本面快照、新闻情报、
    分析历史与分析上下文能力。注册适配器 **类本身**（零参工厂）而非 eager 实例：
    用例侧每次构造 pipeline 现建一个轻量句柄，内部仍指向 ``DatabaseManager`` 单例，
    因而对 ``DatabaseManager.reset_instance()``（测试切换临时库）保持敏感。

    与取数端口一致，持久化是主流程必需能力：未装配时构造 pipeline 直接报错，
    不做“静默不落库”降级。
    """
    from src.application.analysis.persistence_port import (
        set_analysis_pipeline_persistence_port_factory,
    )
    from src.infrastructure.persistence.repositories.pipeline_persistence_adapter import (
        DatabaseManagerPipelinePersistenceAdapter,
    )

    set_analysis_pipeline_persistence_port_factory(
        DatabaseManagerPipelinePersistenceAdapter
    )


def configure_vision_completion_port() -> None:
    """装配图片识别（Vision）LLM 调用端口（litellm 适配器）。

    W5.5：``image_stock_extractor`` 不再在应用层 ``import litellm`` 发多模态请求，
    改经 ``VisionCompletionPort`` 下发。模型/Key 选择、Prompt、重试退避与结果解析
    仍留在用例层，本装配只负责把**厂商适配器**接上。

    该端口不做 None 降级：图片识别要么可用要么显式报错，因此与取数/持久化端口
    一样必须在三条入口链路装配：``main.py``（CLI）、``src.bootstrap.api_lifecycle``
    （API）与 ``tests/conftest.py``（测试会话）。
    """
    from src.application.analysis.vision_ports import set_vision_completion_port
    from src.infrastructure.generation.vision_litellm import LitellmVisionAdapter

    set_vision_completion_port(LitellmVisionAdapter())


def configure_stock_data_port() -> None:
    """装配个股取数端口工厂（内置 DataFetcherManager 适配器）。

    注册适配器 **类本身**（零参工厂）而非 eager 实例：用例侧默认经
    ``build_stock_data_port()`` 现建，保证“一条流水线一个 ``DataFetcherManager``”
    的既有语义（各实例不共享预热缓存）。进程启动时调用一次，setter 幂等。
    """
    from src.application.analysis.stock_data_port import set_stock_data_port_factory
    from src.infrastructure.providers.analysis_stock_data_provider import (
        DataFetcherManagerStockDataPort,
    )

    set_stock_data_port_factory(DataFetcherManagerStockDataPort)
