# -*- coding: utf-8 -*-
"""情报与舆情用例（资讯聚合、社交舆情 sentiment）。

按 ``ARCHITECTURE_TARGET.md`` §3 的业务域划分，外部情报聚合类用例落在
``application/intelligence/``。本包按业务能力逐片收纳自 ``src/services/``
下沉的实现，消费方直接子模块 import（不在此重复导出，避免 eager 聚合
引入 config→application 循环依赖，与 ``application/history``、
``application/analysis`` 先例一致）。
"""
