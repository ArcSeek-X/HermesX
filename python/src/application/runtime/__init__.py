# -*- coding: utf-8 -*-
"""运行时用例（任务队列、调度、运行流与后端/模型状态诊断）。

按 ``ARCHITECTURE_TARGET.md`` §3 的业务域划分，运行期编排与状态探测类用例落在
``application/runtime/``。本包按业务能力逐片收纳自 ``src/services/`` 下沉的实现，
消费方直接子模块 import（不在此重复导出，以保持单一 import 面、与
``application/history`` 先例一致）。
"""
