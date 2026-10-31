# -*- coding: utf-8 -*-
"""报告/渲染类基础设施适配层（飞书文档、Markdown 渲染等）。

按 `ARCHITECTURE_TARGET.md` §4 归位：对外部文档/渲染服务与 Markdown 渲染等
非业务 IO 放此包。本 ``__init__`` 不做 eager 聚合，避免不必要的导入耦合与循环。
"""
