# -*- coding: utf-8 -*-
"""Shared production port wiring; framework runtime remains unmodified."""

import pytest


@pytest.fixture(scope="session", autouse=True)
def _configure_notification_send_port():
    """为整个测试会话注册内置通知发送端口与图片渲染端口工厂，对齐生产入口。

    R2-B5 后 ``NotificationService`` 的默认内置组合适配器改由 bootstrap seam 注 册，
    application 不再直接构造它；R3-S11 后 Markdown 转图片同样经 ``ImageRenderPort``
    seam 注入（实现已下沉 ``src.infrastructure.reporting.img_render``）。测试进程的
    等价入口即本 conftest。未注册会让零参构造的默认端口为 ``None``：发送链断裂、
    图片转换为文本回退，与本片前的可见行为不一致。会话级注册一次，与生产恒装 配一致。
    """
    from src.bootstrap.notification import (
        configure_image_render_port,
        configure_notification_send_port,
    )

    configure_notification_send_port()
    configure_image_render_port()


@pytest.fixture(scope="session", autouse=True)
def _configure_stock_data_port():
    """为整个测试会话注册个股取数端口工厂，对齐生产入口。

    R3-S15b 后 ``StockAnalysisPipeline`` 搬入 application 层，不再直接构造
    ``DataFetcherManager``，取数改经 ``StockDataPort`` seam 注入。该端口**无 None
    降级**（取数是主流程必需能力），未注册时构造 pipeline 直接抛错，因此测试进程
    必须与 CLI / API 一样完成装配。会话级注册一次，与生产恒装配一致。

    W4.2 起同一入口另装配个股分析持久化端口（``AnalysisPipelinePersistencePort``），
    两者都是 pipeline 构造期必需能力，缺一组即报错。W5.5 起同批装配图片识别的
    Vision 调用端口（``VisionCompletionPort``），未装配时识别接口显式报错。
    """
    from src.bootstrap.analysis import (
        configure_analysis_pipeline_persistence,
        configure_stock_data_port,
        configure_vision_completion_port,
    )

    configure_stock_data_port()
    configure_analysis_pipeline_persistence()
    configure_vision_completion_port()
