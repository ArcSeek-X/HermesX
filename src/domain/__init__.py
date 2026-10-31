# -*- coding: utf-8 -*-
"""领域层：纯业务规则与业务数据模型。

不依赖任何框架 / ORM / 存储 / 外部层（守卫规则禁止
``fastapi``/``sqlalchemy``/``data_provider``/``src.services``/``src.core``/
``src.storage``/``src.config``/``src.repositories``/``src.infrastructure``/``api``/``bot``），
只承载可被应用层与基础设施层共同引用的业务概念与记录形状。
"""
