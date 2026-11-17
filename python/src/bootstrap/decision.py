# -*- coding: utf-8 -*-
"""决策信号用例的装配。

技术信号扫描（signal_scanner）需要两类外部取数端口：日 K 线（信号检测输入）
与涨停池（股票池来源）。二者均复用既有读侧端口的数据源实现
（:class:`~src.infrastructure.providers.kline_provider.DataProviderQuoteProvider` 的
``fetch_kline``、:class:`~src.infrastructure.providers.limit_pool_provider.DataProviderLimitPoolProvider`
的 ``fetch_board``），不新建平行适配器；用例侧只按端口协议调用，不直接依赖
``data_provider``。
"""

from __future__ import annotations


def configure_signal_scanner() -> None:
    """装配技术信号扫描用例的取数默认端口。

    进程启动时调用一次（API lifespan / CLI 入口）；``set_signal_scanner_providers``
    幂等，重复调用只会重新指向同一适配器。未装配时优雅降级：K 线端口缺失 → 单只
    跳过，涨停池端口缺失 → 空池由上层提示，单一取数失败不拖垮整体扫描。
    """
    from src.infrastructure.providers.kline_provider import DataProviderQuoteProvider
    from src.infrastructure.providers.limit_pool_provider import (
        DataProviderLimitPoolProvider,
    )
    from src.application.decision.signal_scanner_service import set_signal_scanner_providers

    set_signal_scanner_providers(
        kline_provider=DataProviderQuoteProvider(),
        limit_pool_provider=DataProviderLimitPoolProvider(),
    )


def configure_decision_repositories() -> None:
    """装配 decision 域四个仓储端口的工厂（进程启动时调用一次）。

    用例侧（``decision_signal_service`` / ``decision_signal_outcome_service`` /
    ``skill_opinion_outcome_service`` / ``skill_opinion_sample_service``）默认经
    ``get_*_repository(db_manager)`` 现建仓储；未装配即 fail-fast。注册的是仓储
    **类本身**（可调用工厂）而非 eager 实例，以适配 ``DatabaseManager.reset_instance()``
    重建后仍能绑定当前管理器（与 PP-1/PP-4 同型）。另装配 decision 域默认分析历史仓储
    工厂（W4.2）：``decision_signal_service`` / ``decision_signal_reassess_service`` 在调用方
    未传句柄时经该 seam 取 ``DatabaseManager.get_instance``，替代此前的 application 侧直连。
    """
    from src.application.decision.ports import (
        set_decision_signal_outcome_repository_factory,
        set_decision_signal_repository_factory,
        set_default_history_repo_factory,
        set_skill_opinion_outcome_repository_factory,
        set_skill_opinion_sample_repository_factory,
    )
    from src.infrastructure.persistence.repositories.decision_signal_outcome_repository import (
        DecisionSignalOutcomeRepository,
    )
    from src.infrastructure.persistence.repositories.decision_signal_repository import (
        DecisionSignalRepository,
    )
    from src.infrastructure.persistence.repositories.skill_opinion_outcome_repository import (
        SkillOpinionOutcomeRepository,
    )
    from src.infrastructure.persistence.repositories.skill_opinion_sample_repository import (
        SkillOpinionSampleRepository,
    )

    set_decision_signal_repository_factory(DecisionSignalRepository)
    set_decision_signal_outcome_repository_factory(DecisionSignalOutcomeRepository)
    set_skill_opinion_outcome_repository_factory(SkillOpinionOutcomeRepository)
    set_skill_opinion_sample_repository_factory(SkillOpinionSampleRepository)

    from src.storage import DatabaseManager

    set_default_history_repo_factory(DatabaseManager.get_instance)
