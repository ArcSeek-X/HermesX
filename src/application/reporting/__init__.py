# -*- coding: utf-8 -*-
"""报告渲染用例（Jinja2 模板报告引擎）。

按 ``ARCHITECTURE_TARGET.md`` §4.1，报告渲染件落 ``application/reporting/``
（目标注记"按内容生成与具体渲染依赖拆分"属 P4 报告收敛优化，非守卫阻断，
同 T3 image_stock_extractor 先例：本片整体直搬、不宣称拆分完成）。本包按
业务能力逐片收纳自 ``src/services/`` 下沉的实现，消费方直接子模块 import
（不在此重复导出，避免 eager 聚合引入循环依赖，与 ``application/history``、
``application/analysis``、``application/intelligence`` 先例一致）。
"""
