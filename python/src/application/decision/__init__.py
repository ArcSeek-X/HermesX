# -*- coding: utf-8 -*-
"""决策信号用例（信号生成/提取/结果评估/复评/扫描与技能观点样本）。

按 ``ARCHITECTURE_TARGET.md`` §3 的业务域划分，决策信号类用例落在
``application/decision/``。本包按业务能力逐片收纳自 ``src/services/`` 下沉的实现，
消费方直接子模块 import（不在此重复导出，以保持单一 import 面、与
``application/history`` 先例一致）。
"""
