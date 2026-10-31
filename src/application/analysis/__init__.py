# -*- coding: utf-8 -*-
"""个股分析应用层用例包。

分层说明：本包持有“分析用例编排”的目标职责——`analysis_service`（T1 自
`src/services/` 迁入，分析请求编排与响应组装）、`analyzer_service`（对
CLI/WebUI/Bot 的分析入口薄封装）、`analysis_context_builder`（分析上下文包
构建）、`eod_picker_service`（T5b 快照端口化后迁入）、`alphasift_service`
（T5e §4.3 拆分整改后迁入，外部调用经 `alphasift_ports.AlphaSiftRuntimePort`
端口绑定 infrastructure 适配器）、`image_stock_extractor`（T3 迁入；W5.5 起多模态
调用经 `vision_ports.VisionCompletionPort` 下沉 `infrastructure/generation/vision_litellm`，
本包只保留输入校验、模型/Key 选择、Prompt、重试与结果解析）、`pipeline`（R3-S15b 自
`src/core/` 迁入的主流程编排，
取数经 `stock_data_port.StockDataPort` 端口）。各件均无对外部取数/驱动的直接依赖
（数据访问经 `src/application/*/ports.py` 的端口、端口化适配器与 bootstrap 装配）。

导入约定：与 `application/quote`/`application/portfolio` 一致，本包 __init__
**不做 eager 顶层聚合**——`analysis_service` 依赖链
（ports→bootstrap→storage→config）较重，聚合导入曾在 S2d 触发 config→application
循环导入，消费方统一经子模块全路径导入（如
`from src.application.analysis.analysis_service import AnalysisService`）。
"""
