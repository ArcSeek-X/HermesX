# -*- coding: utf-8 -*-
"""持久化仓储：按业务域承载 SQL 读写，`storage.py` 只做装配与薄委托。

目录约定：

- ``_common``：跨域复用的纯函数（日期 / NaN / JSON / 原始结果展开），零依赖。
- ``market_data_repo``：``stock_daily`` 读写与分析上下文组装。
- ``intelligence_repo``：``news_intel`` / ``fundamental_snapshot`` 读写。
- ``analysis_history_repo``：``analysis_history`` 与依赖它的派生数据。
- ``conversation_repo``：对话消息、滚动摘要与 provider 轨迹。
- ``llm_usage_repo``：``llm_usage`` 追加与聚合。
- ``watchlist_repo``：自选股分类/条目读写，实现 ``application/watchlist`` 的端口。

每个仓储在构造时接收已装配的 ``DatabaseManager``（``self._db``），连接、会话与
写事务重试都由宿主提供，仓储自身**不建引擎**，也不直接 ``session.commit()``；
需要写入时统一调用宿主的 ``_run_write_transaction`` 由其提交并重试。业务代码不直接
构造仓储：应用用例经 ``src/application/*/ports.py`` 的端口消费，bootstrap 负责注册
实现（PP-1~PP-6 已把原 ``src/repositories`` 全部收拢到本包）。

迁移状态：P2-B2b 已把 ``DatabaseManager`` 的业务查询/写入方法全部迁入本包，
``src/storage.py`` 只保留单例装配、会话入口、schema 兼容委托与同名薄委托。
P3 起新增的纵向用例仓储（如 ``watchlist_repo``）只用 ``Protocol`` 端口描述能力，
不再以 ``DatabaseManager`` 的同名方法为契约。
"""
