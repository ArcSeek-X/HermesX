# -*- coding: utf-8 -*-
"""启动期 schema 兼容升级。

``Base.metadata.create_all()`` 只建**缺失**的表；已存在的表不会补列、补索引，
也不会修正历史遗留的约束形态。本模块承载这些「基线之后的增量变更」，全部函数
都是幂等的，启动时按 :func:`apply_startup_migrations` 的顺序执行一次。

设计取舍：

- **不阻断启动**：除个别结构性校验（如 decision_profile 索引形态不一致）会抛错
  外，其余失败只记录告警。老库缺一个可选列不应让整个应用起不来。
- **只做增量**：除 ``intelligence_items`` 的复合唯一约束重建（历史遗留形态所迫）
  外，不做破坏性变更；需要重建表的情况必须在注释里写明为什么。
- **顺序有依赖**：``importance`` 补列必须早于量纲迁移，``create_all`` 必须早于
  全部函数。调整顺序前先看 :func:`apply_startup_migrations` 里的注释。

新增补列 / 补索引时，优先写成 ``IF NOT EXISTS`` 或「先 inspect 再执行」，
不要假设上一次执行成功过。
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import List

from sqlalchemy import MetaData, Table, inspect, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from src.infrastructure.persistence.base import (
    CURRENT_SCHEMA_VERSION,
    LIVE_NEWS_IMPORTANCE_RESCALE_VERSION,
)
from src.infrastructure.persistence.models.agent import (
    LLMUsage,
    _LLM_USAGE_TELEMETRY_COLUMN_SQL,
)
from src.infrastructure.persistence.models.decision import DecisionSignalRecord
from src.infrastructure.persistence.models.intelligence import (
    INTELLIGENCE_ITEM_NULL_SCOPE_VALUE,
    IntelligenceItem,
)
from src.infrastructure.persistence.models.schema import DatabaseSchemaMigration
from src.infrastructure.persistence.session import (
    DatabaseSession,
    is_sqlite_duplicate_column_error,
    is_sqlite_locked_error,
)
from src.domain.decision.profile import extract_legacy_decision_profile

logger = logging.getLogger(__name__)


def ensure_schema_migration_record(db_session: DatabaseSession) -> None:
    """记录基线 schema 版本（幂等）。

    SQLite 走 ``ON CONFLICT DO NOTHING``；其它后端退化为普通插入，
    触发唯一约束冲突时回滚并核对记录是否已存在（并发启动下的正常情况）。
    """
    session = db_session.create_session()
    values = {
        "version": CURRENT_SCHEMA_VERSION,
        "description": "Baseline schema created through SQLAlchemy metadata.create_all",
    }
    try:
        if db_session.is_sqlite:
            statement = sqlite_insert(DatabaseSchemaMigration).values(**values)
            statement = statement.on_conflict_do_nothing(index_elements=["version"])
            session.execute(statement)
        else:
            session.execute(DatabaseSchemaMigration.__table__.insert().values(**values))
        session.commit()
    except IntegrityError:
        session.rollback()
        with db_session.create_session() as verify_session:
            existing = verify_session.get(DatabaseSchemaMigration, CURRENT_SCHEMA_VERSION)
        if existing is None:
            raise
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ensure_decision_signal_profile_schema(db_session: DatabaseSession) -> None:
    """Add and backfill nullable decision_profile for existing SQLite DBs."""

    if not db_session.is_sqlite:
        return
    inspector = inspect(db_session.engine)
    if not inspector.has_table(DecisionSignalRecord.__tablename__):
        return

    try:
        existing = {
            column["name"]
            for column in inspector.get_columns(DecisionSignalRecord.__tablename__)
        }
    except Exception as exc:
        logger.error(
            "[DecisionSignal] failed to inspect decision_profile column; "
            "profile migration cannot continue safely: %s",
            exc,
        )
        raise

    if "decision_profile" not in existing:
        try:
            with db_session.engine.begin() as connection:
                connection.exec_driver_sql(
                    f"ALTER TABLE {DecisionSignalRecord.__tablename__} "
                    "ADD COLUMN decision_profile VARCHAR(16)"
                )
        except OperationalError as exc:
            if not is_sqlite_duplicate_column_error(exc, "decision_profile"):
                raise

    ensure_decision_signal_profile_indexes(db_session)
    backfill_decision_signal_profile_from_metadata(db_session)


def ensure_decision_signal_profile_indexes(db_session: DatabaseSession) -> None:
    """Create profile-aware indexes without dropping legacy indexes."""

    expected_indexes = {
        "ix_decision_signals_decision_profile": ["decision_profile"],
        "ix_decision_signal_market_stock_profile_created": [
            "market", "stock_code", "decision_profile", "created_at",
        ],
        "ix_decision_signal_report_type_market_stock_profile_action_horizon_phase": [
            "source_report_id", "source_type", "market", "stock_code",
            "decision_profile", "action", "horizon", "market_phase",
        ],
        "ix_decision_signal_trace_type_market_stock_profile_action_horizon_phase": [
            "trace_id", "source_type", "market", "stock_code",
            "decision_profile", "action", "horizon", "market_phase",
        ],
    }
    with db_session.engine.begin() as connection:
        for index_name, columns in expected_indexes.items():
            connection.exec_driver_sql(
                f"CREATE INDEX IF NOT EXISTS {index_name} "
                f"ON decision_signals ({', '.join(columns)})"
            )

    actual_indexes = {
        index["name"]: index["column_names"]
        for index in inspect(db_session.engine).get_indexes(
            DecisionSignalRecord.__tablename__
        )
    }
    for index_name, expected_columns in expected_indexes.items():
        if actual_indexes.get(index_name) != expected_columns:
            raise RuntimeError(
                "decision_profile index verification failed: "
                f"index={index_name} expected={expected_columns} "
                f"actual={actual_indexes.get(index_name)}"
            )


def backfill_decision_signal_profile_from_metadata(db_session: DatabaseSession) -> None:
    """把历史 ``decision_signals`` 的决策画像从 metadata JSON 回填到独立列。

    早期版本把画像整体塞进 metadata 的 JSON 里，查询与统计都不方便；
    本函数在启动时把历史行的画像字段提取出来写入专用列。

    回填是**幂等**的：已有画像的行会跳过（计入 ``skipped_existing_profile_count``）。
    各种「跳过 / 无法解析」的情况分别计数，便于在日志中确认回填是否完整。
    """
    stats = {
        "candidate_count": 0,
        "backfilled_count": 0,
        "guard_skipped_count": 0,
        "missing_metadata_count": 0,
        "missing_profile_count": 0,
        "invalid_json_count": 0,
        "non_object_count": 0,
        "invalid_profile_count": 0,
        "skipped_existing_profile_count": 0,
    }
    with db_session.engine.begin() as connection:
        stats["skipped_existing_profile_count"] = connection.execute(
            text(
                "SELECT COUNT(*) FROM decision_signals "
                "WHERE decision_profile IS NOT NULL"
            )
        ).scalar_one()
        candidate_rows = [
            (row["id"], row["metadata_json"])
            for row in connection.execute(
                text(
                    "SELECT id, metadata_json FROM decision_signals "
                    "WHERE decision_profile IS NULL ORDER BY id"
                )
            ).mappings()
        ]
        stats["candidate_count"] = len(candidate_rows)

        for signal_id, metadata_json in candidate_rows:
            if metadata_json is None:
                stats["missing_metadata_count"] += 1
                continue
            try:
                metadata = json.loads(metadata_json)
            except (TypeError, ValueError, RecursionError):
                stats["invalid_json_count"] += 1
                continue
            if not isinstance(metadata, dict):
                stats["non_object_count"] += 1
                continue

            raw_profile = metadata.get("decision_profile")
            if raw_profile is None or (
                isinstance(raw_profile, str) and not raw_profile.strip()
            ):
                stats["missing_profile_count"] += 1
                continue
            profile = extract_legacy_decision_profile(metadata)
            if profile is None:
                stats["invalid_profile_count"] += 1
                continue

            result = connection.execute(
                text(
                    "UPDATE decision_signals "
                    "SET decision_profile = :decision_profile "
                    "WHERE id = :signal_id AND decision_profile IS NULL"
                ),
                {"decision_profile": profile, "signal_id": signal_id},
            )
            if result.rowcount == 1:
                stats["backfilled_count"] += 1
            elif result.rowcount == 0:
                stats["guard_skipped_count"] += 1
            else:
                raise RuntimeError(
                    "decision_profile backfill updated an unexpected number "
                    f"of rows for signal_id={signal_id}: {result.rowcount}"
                )

        classified_count = sum(
            stats[key]
            for key in (
                "backfilled_count",
                "guard_skipped_count",
                "missing_metadata_count",
                "missing_profile_count",
                "invalid_json_count",
                "non_object_count",
                "invalid_profile_count",
            )
        )
        if classified_count != stats["candidate_count"]:
            raise RuntimeError(
                "decision_profile migration stats did not classify every "
                f"candidate: candidates={stats['candidate_count']} "
                f"classified={classified_count}"
            )
    logger.info(
        "[DecisionSignal] decision_profile migration stats: "
        "candidate_count=%s backfilled_count=%s guard_skipped_count=%s "
        "missing_metadata_count=%s missing_profile_count=%s "
        "invalid_json_count=%s non_object_count=%s invalid_profile_count=%s "
        "skipped_existing_profile_count=%s",
        stats["candidate_count"],
        stats["backfilled_count"],
        stats["guard_skipped_count"],
        stats["missing_metadata_count"],
        stats["missing_profile_count"],
        stats["invalid_json_count"],
        stats["non_object_count"],
        stats["invalid_profile_count"],
        stats["skipped_existing_profile_count"],
    )


def ensure_intelligence_items_unique_index(db_session: DatabaseSession) -> None:
    """对齐 ``intelligence_items`` 的唯一约束（启动时幂等执行）。

    历史库上该表只有 ``url`` 单列唯一约束，而通用资讯与实时快讯共用此表后，
    需要改为 ``(source_id, url, scope_type, scope_value, market)`` 复合唯一，
    否则「同一条快讯属于多个频道」会被误判为重复而无法入库。

    迁移分三种情况处理：

    1. 已存在目标复合约束 -> 直接返回；
    2. 存在其它形态的唯一约束 -> 不做破坏性变更，另行补建复合索引（见
       :func:`ensure_intelligence_items_scoped_unique_index_once`）；
    3. 只有旧的 ``url`` 单列约束 -> 重建表（见
       :func:`rebuild_intelligence_items_table`）。

    任何异常都只记录告警不抛出：索引形态不对只会影响去重，不应阻断应用启动。
    """
    if not db_session.is_sqlite:
        return

    if not inspect(db_session.engine).has_table("intelligence_items"):
        return

    try:
        unique_indexes = list_sqlite_unique_indexes(db_session, "intelligence_items")
    except Exception as exc:
        logger.warning(
            "[Intelligence items] failed to inspect unique indexes; "
            "skip migration/repair: %s",
            exc,
        )
        return

    target_columns = ("source_id", "url", "scope_type", "scope_value", "market")
    has_target_index = any(tuple(cols) == target_columns for cols in unique_indexes)
    has_legacy_url_unique = any(tuple(cols) == ("url",) for cols in unique_indexes)

    if has_target_index:
        return
    if unique_indexes and not has_legacy_url_unique:
        # 表上存在其它形态的唯一约束，避免做破坏性变更，直接补建期望的复合唯一索引
        ensure_intelligence_items_scoped_unique_index_once(db_session)
        return

    rebuild_intelligence_items_table(db_session)


def rebuild_intelligence_items_table(db_session: DatabaseSession) -> None:
    """重建 ``intelligence_items`` 表以建立复合唯一约束。

    SQLite 不支持直接修改已有索引，只能「建新表 -> 拷数据 -> 删旧表 -> 改名」。
    步骤：

    1. 按当前 ORM 定义建临时表（表名带纳秒时间戳，避免并发重名）；
    2. 全量拷贝旧表数据；
    3. 删除旧表并把临时表改名为正式表；
    4. 建复合唯一索引。

    ⚠️ 该操作会**删除旧表**，属于破坏性迁移；仅当确认只有旧的单列 url 约束时
    才会被调用（见 :func:`ensure_intelligence_items_unique_index`）。
    拷贝过程中若中断可能丢数据，因此只在启动时执行一次。
    """
    temporary_table = f"intelligence_items_recreate_tmp_{int(time.time() * 1_000_000_000)}"
    columns = [column.name for column in IntelligenceItem.__table__.columns]
    select_clause = ", ".join(f'"{column}"' for column in columns)
    scoped_index_columns = ", ".join(["source_id", "url", "scope_type", "scope_value", "market"])
    scoped_index_name = "uix_intel_item_scope"

    tmp_metadata = MetaData()
    tmp_table = Table(
        temporary_table,
        tmp_metadata,
        *(column.copy() for column in IntelligenceItem.__table__.columns),
    )
    logger.info("Rebuilding intelligence_items table to align composite uniqueness constraints.")
    with db_session.engine.begin() as connection:
        connection.execute(text(f'DROP TABLE IF EXISTS "{temporary_table}"'))
        tmp_table.create(connection)
        connection.execute(
            text(
                f"INSERT INTO \"{temporary_table}\" ({select_clause}) "
                f"SELECT {select_clause} FROM intelligence_items"
            )
        )
        connection.execute(text('DROP TABLE "intelligence_items"'))
        connection.execute(
            text(f'ALTER TABLE "{temporary_table}" RENAME TO intelligence_items')
        )
        connection.execute(
            text(
                f"CREATE UNIQUE INDEX IF NOT EXISTS {scoped_index_name} ON "
                f"intelligence_items ({scoped_index_columns})"
            )
        )


def ensure_intelligence_items_scoped_unique_index_once(db_session: DatabaseSession) -> None:
    """补建复合唯一索引 ``uix_intel_item_scope``（已存在则跳过）。

    用于表上已存在「非旧 url 单列」形态的唯一约束、不适合重建表的场景。

    ⚠️ 若表中已有违反该唯一性的数据（重复行），创建会失败并抛出；
    失败由上层按告警处理，不阻断启动。
    """
    target_index_name = "uix_intel_item_scope"
    with db_session.engine.begin() as connection:
        rows = connection.execute(
            text("PRAGMA index_list(intelligence_items)")
        ).fetchall()
        for row in rows:
            if row[1] == target_index_name:
                return
        index_columns = ", ".join(["source_id", "url", "scope_type", "scope_value", "market"])
        connection.execute(
            text(
                f"CREATE UNIQUE INDEX IF NOT EXISTS {target_index_name} ON "
                f"intelligence_items ({index_columns})"
            )
        )


def list_sqlite_unique_indexes(
    db_session: DatabaseSession, table_name: str
) -> List[List[str]]:
    """列出指定表上所有**唯一**索引的列组合。

    Args:
        db_session: 数据库会话持有者。
        table_name: 表名（调用方需保证为可信常量，避免 SQL 注入）。

    Returns:
        每个元素是一个列名列表，如 ``[['url'], ['source_id', 'url', ...]]``。
    """
    with db_session.engine.connect() as connection:
        rows = connection.execute(
            text(f"PRAGMA index_list({table_name})")
        ).fetchall()
        unique_indexes = []
        for row in rows:
            # row: (seq, name, unique, origin, partial)
            if int(row[2]) != 1:
                continue
            index_name = row[1]
            index_columns = []
            for index_info in connection.execute(
                text(f"PRAGMA index_xinfo({index_name})")
            ).fetchall():
                # index_xinfo: (seqno, cid, name, desc, coll, key, ... )
                column_name = index_info[2]
                if column_name is None:
                    continue
                index_columns.append(column_name)
            unique_indexes.append(index_columns)
        return unique_indexes


def ensure_llm_usage_telemetry_columns(db_session: DatabaseSession) -> None:
    """Add nullable P0a usage telemetry columns to existing SQLite DBs."""
    if not db_session.is_sqlite:
        return
    try:
        existing = {
            column["name"]
            for column in inspect(db_session.engine).get_columns(LLMUsage.__tablename__)
        }
    except Exception as exc:
        logger.warning(
            "[LLM usage] failed to inspect telemetry columns; "
            "skipping best-effort SQLite telemetry column backfill: %s",
            exc,
        )
        return

    max_retries = db_session.sqlite_write_retry_max
    for column, column_type in _LLM_USAGE_TELEMETRY_COLUMN_SQL.items():
        if column in existing:
            continue
        for attempt in range(max_retries + 1):
            try:
                with db_session.engine.begin() as connection:
                    connection.exec_driver_sql(
                        f"ALTER TABLE {LLMUsage.__tablename__} "
                        f"ADD COLUMN {column} {column_type}"
                    )
                existing.add(column)
                break
            except OperationalError as exc:
                if is_sqlite_duplicate_column_error(exc, column):
                    existing.add(column)
                    break
                if is_sqlite_locked_error(exc) and attempt < max_retries:
                    delay = db_session.sqlite_write_retry_base_delay * (2 ** attempt)
                    logger.warning(
                        "[LLM usage] SQLite telemetry column backfill locked, "
                        "retrying: %s (%s/%s, %.2fs)",
                        column,
                        attempt + 1,
                        max_retries,
                        delay,
                    )
                    if delay > 0:
                        time.sleep(delay)
                    continue
                raise


def ensure_intelligence_item_scope_values(db_session: DatabaseSession) -> None:
    """Backfill nullable intelligence item scopes so SQLite unique keys work."""
    if not db_session.is_sqlite:
        return
    try:
        existing = {
            column["name"]
            for column in inspect(db_session.engine).get_columns(IntelligenceItem.__tablename__)
        }
    except Exception as exc:
        logger.warning("资讯池 scope_value 回填检查失败，已跳过: %s", exc)
        return
    if "scope_value" not in existing:
        return
    try:
        with db_session.engine.begin() as connection:
            connection.exec_driver_sql(
                f"UPDATE {IntelligenceItem.__tablename__} "
                "SET scope_value = ? "
                "WHERE scope_value IS NULL OR scope_value = ''",
                (INTELLIGENCE_ITEM_NULL_SCOPE_VALUE,),
            )
    except Exception as exc:
        logger.warning("资讯池 scope_value 回填失败，已跳过: %s", exc)


def ensure_intelligence_item_importance_column(db_session: DatabaseSession) -> None:
    """为存量 ``intelligence_items`` 表补齐 ``importance`` 列与快讯查询索引。

    背景：``importance`` 用于承载华尔街见闻快讯的重要级（score）。新建的表由
    ``create_all`` 直接带上该列，存量库需要在此补齐。

    设计取舍：本函数**不阻断启动**。快讯是新增的可选能力，若补列失败（如数据库
    只读、权限不足、并发启动竞争），只记录告警由上层降级处理，避免拖垮整个应用。
    两种主流后端（SQLite / PostgreSQL）的 ``ALTER TABLE ADD COLUMN`` 与
    ``CREATE INDEX IF NOT EXISTS`` 语法一致，故此处不做引擎分支。
    """
    table_name = IntelligenceItem.__tablename__
    try:
        inspector = inspect(db_session.engine)
        if not inspector.has_table(table_name):
            return
        existing = {column["name"] for column in inspector.get_columns(table_name)}
    except Exception as exc:  # noqa: BLE001 - 结构探测失败不应阻断启动
        logger.warning("[Intelligence] 检查 %s 列信息失败，跳过 importance 补列: %s", table_name, exc)
        return

    if "importance" not in existing:
        try:
            with db_session.engine.begin() as connection:
                connection.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN importance INTEGER")
            logger.info("[Intelligence] 已为 %s 补充 importance 列", table_name)
        except Exception as exc:  # noqa: BLE001 - 并发启动可能已补列，需静默忽略
            if not is_duplicate_column_error(db_session, exc, "importance"):
                logger.warning("[Intelligence] %s 补充 importance 列失败: %s", table_name, exc)

    ensure_intelligence_item_importance_indexes(db_session)


def ensure_intelligence_item_importance_indexes(db_session: DatabaseSession) -> None:
    """创建快讯列表查询所需的复合索引（已存在时幂等跳过）。

    索引面向的查询形态：按频道（scope_value）过滤，可选叠加重要级与时间范围，
    按发布时间倒序分页。
    """
    expected_indexes = {
        # 存量库的 importance 列由 ensure_intelligence_item_importance_column
        # 补齐，而 create_all 不会为已存在的表补建索引，故此处一并兜底，
        # 保证空库与升级库的索引集合一致。
        "ix_intelligence_items_importance": ["importance"],
        "ix_intel_item_channel_importance_time": ["scope_value", "importance", "published_at"],
    }
    table_name = IntelligenceItem.__tablename__
    try:
        with db_session.engine.begin() as connection:
            for index_name, columns in expected_indexes.items():
                connection.exec_driver_sql(
                    f"CREATE INDEX IF NOT EXISTS {index_name} "
                    f"ON {table_name} ({', '.join(columns)})"
                )
    except Exception as exc:  # noqa: BLE001 - 索引缺失只影响性能，不阻断启动
        logger.warning("[Intelligence] 创建快讯查询索引失败，已跳过: %s", exc)


def ensure_live_news_importance_rescaled(db_session: DatabaseSession) -> None:
    """把快讯 ``importance`` 从上游 score 量纲迁移到统一业务量纲（0~4）。

    映射（语义守恒，快讯无「较重要」档）：
        NULL -> 0    上游无重要级字段（如 NewsNow 降级源）
        1 -> 1       普通
        2 -> 3       重要
        3 -> 4       非常重要

    幂等关键：迁移前后取值集合存在交集（前 ``{1,2,3}`` / 后 ``{0,1,3,4}``），
    **无法从单条数据判断它是否已迁移**，重复执行会造成二次映射。
    因此 UPDATE 与迁移标记写入放在**同一事务**内：要么都成功、要么都回滚，
    避免出现「数据已迁移但标记未写入」导致下次启动重复迁移。

    设计取舍：与其它 ``ensure_*`` 一致，**不阻断启动**；迁移失败仅告警，
    此时快讯重要级可能失真（阈值仍按新量纲判定），但不影响其它能力。
    """
    table_name = IntelligenceItem.__tablename__
    try:
        with db_session.engine.begin() as connection:
            marked = connection.exec_driver_sql(
                "SELECT version FROM schema_migrations WHERE version = ?",
                (LIVE_NEWS_IMPORTANCE_RESCALE_VERSION,),
            ).fetchone()
            if marked is not None:
                return
            # 注意：NULL 必须用 IS NULL 判断，写成 CASE importance WHEN NULL 永不匹配
            connection.exec_driver_sql(
                f"UPDATE {table_name} SET importance = CASE "
                "WHEN importance IS NULL THEN 0 "
                "WHEN importance = 1 THEN 1 "
                "WHEN importance = 2 THEN 3 "
                "WHEN importance = 3 THEN 4 "
                "ELSE importance END "
                "WHERE scope_type = 'channel'"
            )
            connection.exec_driver_sql(
                "INSERT INTO schema_migrations (version, description, applied_at) "
                "VALUES (?, ?, ?)",
                (
                    LIVE_NEWS_IMPORTANCE_RESCALE_VERSION,
                    "Rescale live news importance from upstream score to unified 0-4 scale",
                    datetime.now(),
                ),
            )
        logger.info("[Intelligence] 快讯 importance 已迁移至统一业务量纲 0~4")
    except Exception as exc:  # noqa: BLE001 - 迁移失败不阻断启动
        logger.warning("[Intelligence] 快讯 importance 量纲迁移失败，已跳过: %s", exc)


def is_duplicate_column_error(
    db_session: DatabaseSession, exc: Exception, column: str
) -> bool:
    """判断异常是否为「列已存在」，用于幂等补列。

    SQLite 走项目既有的判定逻辑；其余后端（如 PostgreSQL）退化为错误信息包含
    ``duplicate column`` 关键字的粗粒度判断。
    """
    if db_session.is_sqlite:
        return is_sqlite_duplicate_column_error(exc, column)
    return "duplicate column" in str(exc).lower()


def ensure_watchlist_schema(db_session: DatabaseSession) -> None:
    """Ensure watchlist tables/indexes exist (idempotent).

    表与约束主要由 Base.metadata.create_all 创建；此处兜底确保索引存在，
    兼容已有库未触发 create_all 的场景。
    """
    if not db_session.is_sqlite:
        return
    try:
        with db_session.engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE INDEX IF NOT EXISTS idx_watchlist_item_group "
                "ON stock_watchlist_item(group_id)"
            )
    except Exception as exc:  # pragma: no cover - 防御性兜底
        logger.warning("ensure watchlist schema failed: %s", exc)


def apply_startup_migrations(db_session: DatabaseSession) -> None:
    """按固定顺序执行全部启动期 schema 兼容升级。

    顺序约束（改动前必须先看）：

    1. telemetry 补列 / decision_profile / scope_value 都是「先补结构」；
    2. ``ensure_schema_migration_record`` 写基线标记；
    3. ``importance`` 补列必须早于量纲迁移：后者依赖列已存在；
    4. watchlist 索引兜底放最后，不影响其它迁移。

    除结构性校验失败外，各函数内部已做「失败只告警」处理，这里不再包一层
    吞异常——真要吞会把「索引形态不对」这类必须暴露的问题也盖住。
    """
    ensure_llm_usage_telemetry_columns(db_session)
    ensure_decision_signal_profile_schema(db_session)
    ensure_intelligence_item_scope_values(db_session)
    ensure_schema_migration_record(db_session)
    ensure_intelligence_items_unique_index(db_session)
    ensure_intelligence_item_importance_column(db_session)
    # 必须在补列之后执行：依赖 importance 列已存在
    ensure_live_news_importance_rescaled(db_session)
    ensure_watchlist_schema(db_session)
