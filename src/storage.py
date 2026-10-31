# -*- coding: utf-8 -*-
"""
===================================
自选股智能分析系统 - 数据库管理器
===================================

覆盖 A股 / 港股 / 美股 / 日股 / 韩股 / 台股，不限于单一市场。

职责（本模块在 P2-B 之后只保留这三件事）：
1. 装配数据库访问（引擎与会话由 ``persistence.session`` 提供）
2. 委托 schema 兼容升级（实现见 ``persistence.schema_compat``）
3. 单例生命周期与模块级 ``persist_llm_usage`` 入口

模型已迁出本模块：表结构按业务域放在 ``src.infrastructure.persistence.models``，
唯一 ``Base`` 与 UTC 时间归一化在 ``src.infrastructure.persistence.base``。
引擎、Session 工厂与写事务重试在 ``src.infrastructure.persistence.session``，
启动期 schema 兼容升级在 ``src.infrastructure.persistence.schema_compat``。
业务查询与写入在 ``src.infrastructure.persistence.repositories``，本模块只保留
同名薄委托（含测试直接引用的 ``_parse_sniper_value`` 等静态辅助）。
本模块不再定义模型、不再创建 Base，也不再直接建引擎或写 ``ALTER TABLE``。

关于数据库后端：
- 当前 ``Config.get_db_url()`` 固定返回 SQLite，实际运行只使用 SQLite；
- 代码中保留的少量 ``_is_sqlite_engine`` 分支（如锁重试、``ON CONFLICT`` 语法）
  属于兼容铺垫，**不等于已支持其它后端**；切换前需先补齐这些分支的替代实现。

分层约定：
- 本模块只做「连接管理 + schema 兼容 + 通用存取原语」，不包含业务编排；
- 领域规则请放在 ``src/domain/`` 与 ``src/application/``；持久化随 ``persistence.repositories``
  下沉，本模块不再承载仓储实现。

存储约定（修改本文件时务必遵守）：

1. **时间统一为 UTC naive**：所有 ``DateTime`` 列存储不带时区信息的 UTC 时间。
   写入前用 ``base.to_utc_naive_datetime`` 归一化，避免「东八区时间被当成 UTC」
   与「同一字段混存带时区/不带时区」两类问题。
2. **金额与比率**：金额统一为元，涨跌幅统一为百分比数值（1.5 表示 1.5%），
   不做「小数/百分数」混用。
3. **股票代码**：统一为纯代码字符串（如 ``600519``、``hk00700``、``AAPL``），
   不带交易所后缀；跨市场代码在业务层做等价归一化，不在存储层隐式转换。
4. **JSON 列**：以 ``Text`` 存储 JSON 字符串，读取方负责解析；模型只保证可存，
   不保证结构，结构契约由对应 schema 定义。
5. **软删除与保留期**：多数流水表不物理删除，改由保留期任务按时间清理。

Schema 迁移：
- ``CURRENT_SCHEMA_VERSION`` 为基线版本标记（记录在 ``schema_migrations`` 表）；
- 基线之后的增量变更通过幂等的「补列 / 补索引」函数完成（实现见
  ``persistence.schema_compat``），启动时按固定顺序调用，失败仅告警不阻断，
  保证老库可平滑升级；本模块只保留同名 ``_ensure_*`` 薄委托供既有调用方使用。

后续（P2-C）：原 ``src/repositories/`` 的仓储已全部下沉 ``persistence.repositories``
（P3/P4 持久化收口 PP-1~PP-7），下游调用方经 ``src/application/*/ports.py`` 端口与
bootstrap 装配消费；本模块与仓储之间只保留 ``DatabaseManager`` 的会话/事务入口。
"""

import atexit
from contextlib import contextmanager
import logging
import threading
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple, Callable, TypeVar, Union, TYPE_CHECKING

import pandas as pd
from sqlalchemy.orm import Session

from src.config import get_config
from src.infrastructure.persistence import schema_compat
from src.infrastructure.persistence.base import Base
from src.infrastructure.persistence.session import (
    DatabaseSession,
    dispose_engine,
)
from src.infrastructure.persistence.models.agent import (
    _LLM_PROMPT_CACHE_TELEMETRY_COLUMNS,
    _LLM_PROMPT_CACHE_TELEMETRY_DISABLED_ATTR,
    _LLM_USAGE_INTEGER_TELEMETRY_COLUMNS,
    _LLM_USAGE_TELEMETRY_COLUMN_SQL,
)
from src.infrastructure.persistence.models.analysis import AnalysisHistory
from src.infrastructure.persistence.models.intelligence import NewsIntel
from src.infrastructure.persistence.models.market_data import StockDaily
from src.infrastructure.persistence.repositories._common import (
    build_raw_result,
    safe_json_dumps,
)
from src.infrastructure.persistence.repositories.analysis_history_repo import (
    AnalysisHistoryRepository,
)
from src.infrastructure.persistence.repositories.conversation_repo import ConversationRepository
from src.infrastructure.persistence.repositories.intelligence_repo import NewsIntelRepository
from src.infrastructure.persistence.repositories.llm_usage_repo import LLMUsageRepository
from src.infrastructure.persistence.repositories.market_data_repo import MarketDataRepository
from src.utils.sniper_points import extract_sniper_points, parse_sniper_value

if TYPE_CHECKING:  # noqa: F401  仅用于类型注解，避免运行期引入循环依赖
    from src.domain.search import SearchResponse

logger = logging.getLogger(__name__)
T = TypeVar("T")


class _DatabaseManagerMeta(type):
    """Serialize DatabaseManager construction across __new__ and __init__."""

    def __call__(cls, *args, **kwargs):
        with cls._init_lock:
            return super().__call__(*args, **kwargs)


class DatabaseManager(metaclass=_DatabaseManagerMeta):
    """
    数据库管理器 - 单例模式
    
    职责：
    1. 管理数据库连接池
    2. 提供 Session 上下文管理
    3. 封装数据存取操作

    单例语义：
    - 通过元类 + ``__new__`` 保证进程内唯一实例；``__init__`` 用 ``_initialized``
      做幂等保护，重复构造不会重建引擎（但仍可用 :meth:`reset_instance` 主动释放）；
    - 引擎与 Session 工厂在多线程下共享，写入通过锁与重试保证串行安全。

    并发与重试：
    - SQLite 在并发写入时可能抛 ``database is locked``，写入统一走
      :meth:`_run_write_transaction`（有限重试 + 退避），业务代码不要直接
      开 session 写库，以免绕过重试导致随机失败；
    - 读取使用 :meth:`get_session` 上下文管理器，用完即还连接池。

    Schema 迁移：
    - 初始化时会建表并记录基线版本；基线之后的增量变更由 ``_ensure_*`` 系列
      幂等函数补齐（补列 / 补索引 / 重建表），失败仅记录日志不阻断启动，
      保证老库升级后仍可运行。
    """
    
    _instance: Optional['DatabaseManager'] = None
    _init_lock = threading.RLock()
    _initialized: bool = False
    
    def __new__(cls, *args, **kwargs):
        """返回进程内唯一实例；首次构造时标记为未初始化。"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_url: Optional[str] = None):
        """
        初始化数据库管理器（幂等）。

        重复构造时直接返回，不会重建引擎；需要切换数据库请先调用
        :meth:`reset_instance`。

        装配职责只保留三步：读配置 -> 建会话（引擎/PRAGMA/Session 工厂都在
        :class:`~src.infrastructure.persistence.session.DatabaseSession` 里）
        -> ``create_all`` 后委托 :func:`schema_compat.apply_startup_migrations`。

        Args:
            db_url: 数据库连接 URL（可选，默认从配置读取）
        """
        if getattr(self, '_initialized', False):
            return

        # 仓储只持有本实例引用，不持有引擎；在初始化 try 之前装配，保证
        # 初始化失败后调用业务方法仍会得到"未正确初始化"而不是 AttributeError。
        self._market_data_repo = MarketDataRepository(self)
        self._news_intel_repo = NewsIntelRepository(self)
        self._analysis_history_repo = AnalysisHistoryRepository(self)
        self._conversation_repo = ConversationRepository(self)
        self._llm_usage_repo = LLMUsageRepository(self)

        created_session: Optional[DatabaseSession] = None

        try:
            config = get_config()
            if db_url is None:
                db_url = config.get_db_url()

            self._db_url = db_url
            self._sqlite_wal_enabled = config.sqlite_wal_enabled
            self._sqlite_busy_timeout_ms = config.sqlite_busy_timeout_ms
            self._sqlite_write_retry_max = config.sqlite_write_retry_max
            self._sqlite_write_retry_base_delay = config.sqlite_write_retry_base_delay

            created_session = DatabaseSession(
                db_url,
                sqlite_busy_timeout_ms=self._sqlite_busy_timeout_ms,
                sqlite_wal_enabled=self._sqlite_wal_enabled,
                sqlite_write_retry_max=self._sqlite_write_retry_max,
                sqlite_write_retry_base_delay=self._sqlite_write_retry_base_delay,
            )
            self._session = created_session

            # 兼容别名：既有业务方法与外部调用方（含两个 repo）直接读这些属性。
            # 它们只是引用，不复制状态；真正的事实源是 ``self._session``。
            self._engine = created_session.engine
            self._SessionLocal = created_session.session_factory
            self._is_sqlite_engine = created_session.is_sqlite
            self._sqlite_file_db = created_session.is_file_sqlite

            # 创建所有表（依赖 models 包已在导入期完成注册）
            Base.metadata.create_all(self._engine)
            schema_compat.apply_startup_migrations(created_session)

            self._initialized = True
            logger.info(f"数据库初始化完成: {db_url}")

            # 注册退出钩子，确保程序退出时关闭数据库连接
            atexit.register(dispose_engine, self._engine)
        except Exception:
            self._initialized = False
            if created_session is not None:
                try:
                    created_session.dispose()
                except Exception as cleanup_exc:
                    logger.warning("数据库初始化失败后的引擎清理也失败: %s", cleanup_exc)
            self._engine = None
            self._SessionLocal = None
            self._session = None
            self.__class__._instance = None
            raise

    # ------------------------------------------------------------------
    # schema 兼容升级：实现已迁至 ``persistence.schema_compat``
    #
    # 这里保留同名实例方法，是因为既有测试与运维脚本会直接调用
    # ``db._ensure_xxx()`` 观察升级结果；方法体只做委托，不含任何逻辑。
    # 新增补列 / 补索引请写到 schema_compat，不要在本文件里重新长出来。
    # ------------------------------------------------------------------

    def _ensure_schema_migration_record(self) -> None:
        schema_compat.ensure_schema_migration_record(self._session)

    def _ensure_decision_signal_profile_schema(self) -> None:
        schema_compat.ensure_decision_signal_profile_schema(self._session)

    def _ensure_decision_signal_profile_indexes(self) -> None:
        schema_compat.ensure_decision_signal_profile_indexes(self._session)

    def _backfill_decision_signal_profile_from_metadata(self) -> None:
        schema_compat.backfill_decision_signal_profile_from_metadata(self._session)

    def _ensure_intelligence_items_unique_index(self) -> None:
        schema_compat.ensure_intelligence_items_unique_index(self._session)

    def _rebuild_intelligence_items_table(self) -> None:
        schema_compat.rebuild_intelligence_items_table(self._session)

    def _ensure_intelligence_items_scoped_unique_index_once(self) -> None:
        schema_compat.ensure_intelligence_items_scoped_unique_index_once(self._session)

    def _list_sqlite_unique_indexes(self, table_name: str):
        return schema_compat.list_sqlite_unique_indexes(self._session, table_name)

    def _ensure_llm_usage_telemetry_columns(self) -> None:
        schema_compat.ensure_llm_usage_telemetry_columns(self._session)

    def _ensure_intelligence_item_scope_values(self) -> None:
        schema_compat.ensure_intelligence_item_scope_values(self._session)

    def _ensure_intelligence_item_importance_column(self) -> None:
        schema_compat.ensure_intelligence_item_importance_column(self._session)

    def _ensure_intelligence_item_importance_indexes(self) -> None:
        schema_compat.ensure_intelligence_item_importance_indexes(self._session)

    def _ensure_live_news_importance_rescaled(self) -> None:
        schema_compat.ensure_live_news_importance_rescaled(self._session)

    def _is_duplicate_column_error(self, exc: Exception, column: str) -> bool:
        return schema_compat.is_duplicate_column_error(self._session, exc, column)

    @classmethod
    def get_instance(cls) -> 'DatabaseManager':
        """获取单例实例"""
        with cls._init_lock:
            if cls._instance is None:
                cls()
            return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """重置单例（用于测试）"""
        with cls._init_lock:
            if cls._instance is not None:
                session_holder = getattr(cls._instance, '_session', None)
                if session_holder is not None:
                    session_holder.dispose()
                elif getattr(cls._instance, '_engine', None) is not None:
                    cls._instance._engine.dispose()
                cls._instance._initialized = False
                cls._instance = None

    @classmethod
    def _cleanup_engine(cls, engine) -> None:
        """清理数据库引擎（atexit 钩子）。实现见 ``persistence.session``。"""
        dispose_engine(engine)

    def _run_write_transaction(
        self,
        operation_name: str,
        write_operation: Callable[[Session], T],
    ) -> T:
        """执行写入事务，并在 SQLite 锁冲突时自动重试。

        实现见 ``persistence.session.DatabaseSession.write_transaction``；本方法保留
        同名入口，是因为 ``persistence.repositories`` 与既有测试直接调用它。业务代码仍应
        走这里，不要自己开 session 写库，否则会绕过锁重试。
        """
        return self._session.write_transaction(operation_name, write_operation)


    def get_session(self) -> Session:
        """
        获取数据库 Session

        使用示例:
            with db.get_session() as session:
                # 执行查询
                session.commit()  # 如果需要
        """
        if not getattr(self, '_initialized', False) or self._session is None:
            raise RuntimeError(
                "DatabaseManager 未正确初始化。"
                "请确保通过 DatabaseManager.get_instance() 获取实例。"
            )
        return self._session.create_session()

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        with self._session.session_scope() as session:
            yield session
    
    def has_today_data(self, code: str, target_date: Optional[date] = None) -> bool:
        """
        检查是否已有指定日期的数据
        
        用于断点续传逻辑：如果已有数据则跳过网络请求
        
        Args:
            code: 股票代码
            target_date: 目标日期（默认今天）
            
        Returns:
            是否存在数据
        """
        return self._market_data_repo.has_today_data(code, target_date)
    
    def get_latest_data(
        self, 
        code: str, 
        days: int = 2
    ) -> List[StockDaily]:
        """
        获取最近 N 天的数据
        
        用于计算"相比昨日"的变化
        
        Args:
            code: 股票代码
            days: 获取天数
            
        Returns:
            StockDaily 对象列表（按日期降序）
        """
        return self._market_data_repo.get_latest_data(code, days)

    def save_news_intel(
        self,
        code: str,
        name: str,
        dimension: str,
        query: str,
        response: 'SearchResponse',
        query_context: Optional[Dict[str, str]] = None
    ) -> int:
        """
        保存新闻情报到数据库

        去重策略：
        - 优先按 URL 去重（唯一约束）
        - URL 缺失时按 title + source + published_date 进行软去重

        关联策略：
        - query_context 记录用户查询信息（平台、用户、会话、原始指令等）
        """
        return self._news_intel_repo.save_news_intel(code, name, dimension, query, response, query_context)

    def save_fundamental_snapshot(
        self,
        query_id: str,
        code: str,
        payload: Optional[Dict[str, Any]],
        source_chain: Optional[Any] = None,
        coverage: Optional[Any] = None,
    ) -> int:
        """
        保存基本面快照（P0 write-only）。失败不抛异常，返回写入条数 0/1。
        """
        return self._news_intel_repo.save_fundamental_snapshot(query_id, code, payload, source_chain, coverage)

    def get_latest_fundamental_snapshot(
        self,
        query_id: str,
        code: str,
    ) -> Optional[Dict[str, Any]]:
        """
        获取指定 query_id + code 的最新基本面快照 payload。

        读取失败或不存在时返回 None（fail-open）。
        """
        return self._news_intel_repo.get_latest_fundamental_snapshot(query_id, code)

    def get_recent_news(self, code: str, days: int = 7, limit: int = 20) -> List[NewsIntel]:
        """
        获取指定股票最近 N 天的新闻情报
        """
        return self._news_intel_repo.get_recent_news(code, days, limit)

    def get_news_intel_by_query_id(self, query_id: str, limit: int = 20) -> List[NewsIntel]:
        """
        根据 query_id 获取新闻情报列表

        Args:
            query_id: 分析记录唯一标识
            limit: 返回数量限制

        Returns:
            NewsIntel 列表（按发布时间或抓取时间倒序）
        """
        return self._news_intel_repo.get_news_intel_by_query_id(query_id, limit)

    def save_analysis_history(
        self,
        result: Any,
        query_id: str,
        report_type: str,
        news_content: Optional[str],
        context_snapshot: Optional[Dict[str, Any]] = None,
        save_snapshot: bool = True
    ) -> int:
        """
        保存分析结果历史记录。

        Returns:
            新保存的 AnalysisHistory.id；保存失败返回 0。
        """
        return self._analysis_history_repo.save_analysis_history(
            result, query_id, report_type, news_content, context_snapshot, save_snapshot
        )

    def update_analysis_history_diagnostics(
        self,
        *,
        query_id: str,
        code: Optional[str] = None,
        diagnostics: Optional[Dict[str, Any]] = None,
        notification_runs: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        """
        更新已保存分析历史的运行诊断快照。

        通知结果通常在分析历史落库后才产生，因此这里仅补写
        context_snapshot.diagnostics，不改变报告正文或其它历史字段。
        """
        return self._analysis_history_repo.update_analysis_history_diagnostics(
            query_id=query_id,
            code=code,
            diagnostics=diagnostics,
            notification_runs=notification_runs,
        )

    def get_analysis_history(
        self,
        code: Optional[str] = None,
        query_id: Optional[str] = None,
        days: int = 30,
        limit: int = 50,
        exclude_query_id: Optional[str] = None,
    ) -> List[AnalysisHistory]:
        """
        Query analysis history records.

        Notes:
        - If query_id is provided, perform exact lookup and ignore days window.
        - If query_id is not provided, apply days-based time filtering.
        - exclude_query_id: exclude records with this query_id (for history comparison).
        """
        return self._analysis_history_repo.get_analysis_history(
            code, query_id, days, limit, exclude_query_id=exclude_query_id
        )

    def get_latest_analysis_history_id(
        self,
        *,
        query_id: str,
        code: str,
        report_type: str,
    ) -> Optional[int]:
        """Return the latest matching history id for read-only lookups.

        P2 automatic DecisionSignal extraction receives the freshly saved id
        directly from ``save_analysis_history()`` and does not use this helper.
        """
        return self._analysis_history_repo.get_latest_analysis_history_id(
            query_id=query_id, code=code, report_type=report_type
        )
    
    def get_analysis_history_paginated(
        self,
        code: Optional[Union[str, List[str]]] = None,
        report_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        offset: int = 0,
        limit: int = 20
    ) -> Tuple[List[AnalysisHistory], int]:
        """
        分页查询分析历史记录（带总数）
        
        Args:
            code: 股票代码筛选
            report_type: 报告类型筛选
            start_date: 开始日期（含）
            end_date: 结束日期（含）
            offset: 偏移量（跳过前 N 条）
            limit: 每页数量
            
        Returns:
            Tuple[List[AnalysisHistory], int]: (记录列表, 总数)
        """
        return self._analysis_history_repo.get_analysis_history_paginated(
            code, report_type, start_date, end_date, offset, limit
        )
    
    def get_analysis_history_by_id(self, record_id: int) -> Optional[AnalysisHistory]:
        """
        根据数据库主键 ID 查询单条分析历史记录
        
        由于 query_id 可能重复（批量分析时多条记录共享同一 query_id），
        使用主键 ID 确保精确查询唯一记录。
        
        Args:
            record_id: 分析历史记录的主键 ID
            
        Returns:
            AnalysisHistory 对象，不存在返回 None
        """
        return self._analysis_history_repo.get_analysis_history_by_id(record_id)

    def delete_analysis_history_records(self, record_ids: List[int]) -> int:
        """
        删除指定的分析历史记录。

        同时清理依赖这些历史记录的回测结果和分析来源决策信号，避免
        依赖历史记录的派生数据残留。DecisionSignal 的 source_report_id
        允许弱引用，因此这里只清理 source_type=analysis 的真实历史绑定信号。

        Args:
            record_ids: 要删除的历史记录主键 ID 列表

        Returns:
            实际删除的历史记录数量
        """
        return self._analysis_history_repo.delete_analysis_history_records(record_ids)

    def get_distinct_stocks_from_history(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 200,
        include_market_review: bool = False,
    ) -> List[AnalysisHistory]:
        """
        获取历史记录中的不重复股票列表，每只股票取最新一条记录。

        使用子查询按 code 分组取 MAX(id)，再 JOIN 回查完整记录。
        默认排除大盘复盘，避免混入普通个股栏。

        Args:
            start_date: 开始日期
            end_date: 结束日期
            limit: 最大返回数量
            include_market_review: 是否包含大盘复盘记录

        Returns:
            每条股票最新一条 AnalysisHistory 记录列表
        """
        return self._analysis_history_repo.get_distinct_stocks_from_history(
            start_date, end_date, limit, include_market_review
        )

    def get_latest_analysis_by_query_id(
        self,
        query_id: str,
        *,
        code: Optional[str] = None,
        report_type: Optional[str] = None,
    ) -> Optional[AnalysisHistory]:
        """
        根据 query_id 查询最新一条分析历史记录

        query_id 在批量分析时可能重复，故返回最近创建的一条。

        Args:
            query_id: 分析记录关联的 query_id
            code: 可选股票代码过滤，用于区分同一 query_id 下的 MARKET 与个股记录
            report_type: 可选报告类型过滤

        Returns:
            AnalysisHistory 对象，不存在返回 None
        """
        return self._analysis_history_repo.get_latest_analysis_by_query_id(
            query_id, code=code, report_type=report_type
        )
    
    def get_data_range(
        self, 
        code: str, 
        start_date: date, 
        end_date: date
    ) -> List[StockDaily]:
        """
        获取指定日期范围的数据
        
        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            StockDaily 对象列表
        """
        return self._market_data_repo.get_data_range(code, start_date, end_date)
    
    def save_daily_data(
        self, 
        df: pd.DataFrame, 
        code: str,
        data_source: str = "Unknown"
    ) -> int:
        """
        保存日线数据到数据库
        
        策略：
        - 按 `(code, date)` 做批量 UPSERT，已存在记录会覆盖更新
        - 同一批次内若存在重复日期，以最后一条记录为准
        - SQLite 分支按 chunk 写入以避免绑定参数上限
        
        Args:
            df: 包含日线数据的 DataFrame
            code: 股票代码
            data_source: 数据来源名称
            
        Returns:
            本次实际新增的记录数（不含更新）
        """
        return self._market_data_repo.save_daily_data(df, code, data_source)
    
    def get_analysis_context(
        self, 
        code: str,
        target_date: Optional[date] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取分析所需的上下文数据
        
        返回今日数据 + 昨日数据的对比信息
        
        Args:
            code: 股票代码
            target_date: 目标日期（默认今天）
            
        Returns:
            包含今日数据、昨日对比等信息的字典
        """
        return self._market_data_repo.get_analysis_context(code, target_date)
    
    def analyze_ma_status(self, data: StockDaily) -> str:
        """公开面：均线形态判定（内部实现见 ``_analyze_ma_status``）。

        R3-S15a：pipeline 等上层改用公开名，避免跨对象访问私有成员；
        ``_analyze_ma_status`` 保留以维持既有调用方与测试锚点。
        """
        return self._analyze_ma_status(data)

    def _analyze_ma_status(self, data: StockDaily) -> str:
        """
        分析均线形态
        
        判断条件：
        - 多头排列：close > ma5 > ma10 > ma20
        - 空头排列：close < ma5 < ma10 < ma20
        - 震荡整理：其他情况
        """
        # 注意：这里的均线形态判断基于“close/ma5/ma10/ma20”静态比较，
        # 未考虑均线拐点、斜率、或不同数据源复权口径差异。
        # 该行为目前保留（按需求不改逻辑）。
        close = data.close or 0
        ma5 = data.ma5 or 0
        ma10 = data.ma10 or 0
        ma20 = data.ma20 or 0
        
        if close > ma5 > ma10 > ma20 > 0:
            return "多头排列 📈"
        elif close < ma5 < ma10 < ma20 and ma20 > 0:
            return "空头排列 📉"
        elif close > ma5 and ma5 > ma10:
            return "短期向好 🔼"
        elif close < ma5 and ma5 < ma10:
            return "短期走弱 🔽"
        else:
            return "震荡整理 ↔️"


    @staticmethod
    def _safe_json_dumps(data: Any) -> str:
        """
        安全序列化为 JSON 字符串
        """
        return safe_json_dumps(data)

    @staticmethod
    def _build_raw_result(result: Any) -> Dict[str, Any]:
        """
        生成完整分析结果字典
        """
        return build_raw_result(result)

    @staticmethod
    def _parse_sniper_value(value: Any) -> Optional[float]:
        """解析狙击点数值（委托给 ``src/utils/sniper_points``，保持单一实现）。"""
        return parse_sniper_value(value)

    def _extract_sniper_points(self, result: Any) -> Dict[str, Optional[float]]:
        """Extract normalized sniper point values from an AnalysisResult."""
        return extract_sniper_points(result)


    def save_conversation_message(self, session_id: str, role: str, content: str) -> int:
        """
        保存 Agent 对话消息
        """
        return self._conversation_repo.save_conversation_message(session_id, role, content)

    def get_conversation_history(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取 Agent 对话历史
        """
        return self._conversation_repo.get_conversation_history(session_id, limit)

    def get_visible_conversation_messages(self, session_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return visible user/assistant conversation messages in chronological order."""
        return self._conversation_repo.get_visible_conversation_messages(session_id, limit)

    def get_conversation_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Return the rolling summary for a conversation session, if present."""
        return self._conversation_repo.get_conversation_summary(session_id)

    def save_agent_provider_turn(
        self,
        *,
        session_id: str,
        run_id: str,
        provider: str,
        model: str,
        anchor_user_message_id: int,
        anchor_assistant_message_id: int,
        messages: List[Dict[str, Any]],
        contains_reasoning: bool,
        contains_tool_calls: bool,
        contains_thinking_blocks: bool,
        must_roundtrip: bool,
        estimated_tokens: int,
    ) -> int:
        """Persist one provider protocol trace and enforce per-model retention."""
        return self._conversation_repo.save_agent_provider_turn(
            session_id=session_id,
            run_id=run_id,
            provider=provider,
            model=model,
            anchor_user_message_id=anchor_user_message_id,
            anchor_assistant_message_id=anchor_assistant_message_id,
            messages=messages,
            contains_reasoning=contains_reasoning,
            contains_tool_calls=contains_tool_calls,
            contains_thinking_blocks=contains_thinking_blocks,
            must_roundtrip=must_roundtrip,
            estimated_tokens=estimated_tokens,
        )

    def get_agent_provider_turns(
        self,
        session_id: str,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        must_roundtrip_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Return provider trace turns in chronological order."""
        return self._conversation_repo.get_agent_provider_turns(
            session_id,
            provider=provider,
            model=model,
            must_roundtrip_only=must_roundtrip_only,
        )

    def upsert_conversation_summary(
        self,
        session_id: str,
        summary: str,
        covered_message_id: int,
        source_message_count: int,
        estimated_tokens: int,
    ) -> None:
        """Create or update the rolling summary for a conversation session."""
        return self._conversation_repo.upsert_conversation_summary(
            session_id, summary, covered_message_id, source_message_count, estimated_tokens
        )

    def conversation_session_exists(self, session_id: str) -> bool:
        """Return True when at least one message exists for the given session."""
        return self._conversation_repo.conversation_session_exists(session_id)

    def get_chat_sessions(
        self,
        limit: int = 50,
        session_prefix: Optional[str] = None,
        extra_session_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取聊天会话列表（从 conversation_messages 聚合）

        Args:
            limit: Maximum number of sessions to return.
            session_prefix: If provided, only return sessions whose session_id
                starts with this prefix.  Used for per-user isolation (e.g.
                ``"telegram_12345"``).
            extra_session_ids: Optional exact session ids to include in
                addition to the scoped prefix.

        Returns:
            按最近活跃时间倒序的会话列表，每条包含 session_id, title, message_count, last_active
        """
        return self._conversation_repo.get_chat_sessions(limit, session_prefix, extra_session_ids)

    def get_conversation_messages(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取单个会话的完整消息列表（用于前端恢复历史）
        """
        return self._conversation_repo.get_conversation_messages(session_id, limit)

    def delete_conversation_session(self, session_id: str) -> int:
        """
        删除指定会话的所有消息

        Returns:
            删除的消息数
        """
        return self._conversation_repo.delete_conversation_session(session_id)

    # ------------------------------------------------------------------
    # LLM usage tracking
    # ------------------------------------------------------------------

    def record_llm_usage(
        self,
        call_type: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        stock_code: Optional[str] = None,
        **telemetry: Any,
    ) -> None:
        """Append one LLM call record to llm_usage."""
        return self._llm_usage_repo.record_llm_usage(
            call_type,
            model,
            prompt_tokens,
            completion_tokens,
            total_tokens,
            stock_code=stock_code,
            **telemetry,
        )

    def get_llm_usage_summary(
        self,
        from_dt: datetime,
        to_dt: datetime,
    ) -> Dict[str, Any]:
        """Return aggregated token usage between from_dt and to_dt.

        Returns a dict with keys:
          total_calls, total_prompt_tokens, total_completion_tokens, total_tokens,
          by_call_type: list of {call_type, calls, prompt_tokens,
            completion_tokens, total_tokens},
          by_model: list of {model, calls, prompt_tokens, completion_tokens,
            total_tokens, max_total_tokens}
        """
        return self._llm_usage_repo.get_llm_usage_summary(from_dt, to_dt)

    def get_llm_usage_records(
        self,
        from_dt: datetime,
        to_dt: datetime,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Return recent LLM usage audit rows between from_dt and to_dt.

        Each row contains id, call_type, model, stock_code, prompt_tokens,
        completion_tokens, total_tokens, and called_at. Results are ordered by
        newest call first, and limit is clamped to the public API range.
        """
        return self._llm_usage_repo.get_llm_usage_records(from_dt, to_dt, limit)


# 便捷函数
def get_db() -> DatabaseManager:
    """获取数据库管理器实例的快捷方式"""
    return DatabaseManager.get_instance()


def persist_llm_usage(
    usage: Dict[str, Any],
    model: str,
    call_type: str,
    stock_code: Optional[str] = None,
) -> None:
    """Fire-and-forget: write one LLM call record to llm_usage. Never raises."""
    try:
        if usage is None:
            usage = {}
        prompt_cache_telemetry_disabled = bool(
            getattr(usage, _LLM_PROMPT_CACHE_TELEMETRY_DISABLED_ATTR, False)
        )
        prompt_tokens = _coerce_llm_usage_non_negative_int(usage.get("prompt_tokens")) or 0
        completion_tokens = _coerce_llm_usage_non_negative_int(usage.get("completion_tokens")) or 0
        total_tokens = _coerce_llm_usage_non_negative_int(usage.get("total_tokens")) or 0
        telemetry = {
            column: usage.get(column)
            for column in _LLM_USAGE_TELEMETRY_COLUMN_SQL
        }
        if prompt_cache_telemetry_disabled:
            for column in _LLM_PROMPT_CACHE_TELEMETRY_COLUMNS:
                telemetry[column] = None
        for column in _LLM_USAGE_INTEGER_TELEMETRY_COLUMNS:
            telemetry[column] = _coerce_llm_usage_non_negative_int(telemetry.get(column))
        telemetry["normalized_prompt_tokens"] = (
            telemetry.get("normalized_prompt_tokens")
            if telemetry.get("normalized_prompt_tokens") is not None
            else prompt_tokens
        )
        telemetry["normalized_completion_tokens"] = (
            telemetry.get("normalized_completion_tokens")
            if telemetry.get("normalized_completion_tokens") is not None
            else completion_tokens
        )
        telemetry["normalized_total_tokens"] = (
            telemetry.get("normalized_total_tokens")
            if telemetry.get("normalized_total_tokens") is not None
            else total_tokens
        )
        has_usage_payload = bool(usage.get("provider_usage_json")) or any(
            key in usage
            for key in (
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "normalized_prompt_tokens",
                "normalized_completion_tokens",
                "normalized_total_tokens",
            )
        )
        if not prompt_cache_telemetry_disabled:
            telemetry["cache_capability"] = usage.get("cache_capability") or "unknown"
            telemetry["cache_eligibility"] = usage.get("cache_eligibility") or "unknown"
            telemetry["cache_observation"] = usage.get("cache_observation") or (
                "no_usage" if not has_usage_payload else "unknown"
            )
        db = DatabaseManager.get_instance()
        db.record_llm_usage(
            call_type=call_type,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            stock_code=stock_code,
            **telemetry,
        )
    except Exception as exc:
        logging.getLogger(__name__).warning("[LLM usage] failed to persist usage record: %s", exc)


def _coerce_llm_usage_non_negative_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float):
        if value < 0 or not value.is_integer():
            return None
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text or not text.isdigit():
            return None
        return int(text)
    return None


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)
    
    db = get_db()
    
    print("=== 数据库测试 ===")
    print(f"数据库初始化成功")
    
    # 测试检查今日数据
    has_data = db.has_today_data('600519')
    print(f"茅台今日是否有数据: {has_data}")
    
    # 测试保存数据
    test_df = pd.DataFrame({
        'date': [date.today()],
        'open': [1800.0],
        'high': [1850.0],
        'low': [1780.0],
        'close': [1820.0],
        'volume': [10000000],
        'amount': [18200000000],
        'pct_chg': [1.5],
        'ma5': [1810.0],
        'ma10': [1800.0],
        'ma20': [1790.0],
        'volume_ratio': [1.2],
    })
    
    saved = db.save_daily_data(test_df, '600519', 'TestSource')
    print(f"保存测试数据: {saved} 条")
    
    # 测试获取上下文
    context = db.get_analysis_context('600519')
    print(f"分析上下文: {context}")
