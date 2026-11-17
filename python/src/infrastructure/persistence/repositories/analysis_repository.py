# -*- coding: utf-8 -*-
"""
===================================
分析历史数据访问层
===================================

职责：
1. 封装分析历史数据的数据库操作
2. 提供 CRUD 接口

同名区分：本仓储（:class:`AnalysisRepository`，P3/P4 持久化收口 PP-2 从
``src/repositories/analysis_repo.py`` 下沉）与同目录的 ``analysis_history_repo.py``
（:class:`AnalysisHistoryRepository`）同操 ``analysis_history`` 表但是不同方法面与消费方：
本类主要作为市场灯塔快照端口 ``MarketLightSnapshotRepositoryPort`` 的实现
（``iter_market_review_snapshot_payloads``）由 ``bootstrap.market`` 装配，不要合并。
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Iterator, List, Optional, Tuple

from sqlalchemy import desc

from src.storage import DatabaseManager
from src.infrastructure.persistence.models.analysis import AnalysisHistory

logger = logging.getLogger(__name__)


MARKET_LIGHT_HISTORY_BATCH_SIZE = 100


class AnalysisRepository:
    """
    分析历史数据访问层
    
    封装 AnalysisHistory 表的数据库操作
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        初始化数据访问层
        
        Args:
            db_manager: 数据库管理器（可选，默认使用单例）
        """
        self.db = db_manager or DatabaseManager.get_instance()
    
    def get_by_query_id(self, query_id: str) -> Optional[AnalysisHistory]:
        """
        根据 query_id 获取分析记录
        
        Args:
            query_id: 查询 ID
            
        Returns:
            AnalysisHistory 对象，不存在返回 None
        """
        try:
            records = self.db.get_analysis_history(query_id=query_id, limit=1)
            return records[0] if records else None
        except Exception as e:
            logger.error(f"查询分析记录失败: {e}")
            return None
    
    def get_list(
        self,
        code: Optional[str] = None,
        days: int = 30,
        limit: int = 50
    ) -> List[AnalysisHistory]:
        """
        获取分析记录列表
        
        Args:
            code: 股票代码筛选
            days: 时间范围（天）
            limit: 返回数量限制
            
        Returns:
            AnalysisHistory 对象列表
        """
        try:
            return self.db.get_analysis_history(
                code=code,
                days=days,
                limit=limit
            )
        except Exception as e:
            logger.error(f"获取分析列表失败: {e}")
            return []
    
    def save(
        self,
        result: Any,
        query_id: str,
        report_type: str,
        news_content: Optional[str] = None,
        context_snapshot: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        保存分析结果
        
        Args:
            result: 分析结果对象
            query_id: 查询 ID
            report_type: 报告类型
            news_content: 新闻内容
            context_snapshot: 上下文快照
            
        Returns:
            新保存的 AnalysisHistory.id；保存失败返回 0。
        """
        try:
            return self.db.save_analysis_history(
                result=result,
                query_id=query_id,
                report_type=report_type,
                news_content=news_content,
                context_snapshot=context_snapshot
            )
        except Exception as e:
            logger.error(f"保存分析结果失败: {e}")
            return 0
    
    def count_by_code(self, code: str, days: int = 30) -> int:
        """
        统计指定股票的分析记录数
        
        Args:
            code: 股票代码
            days: 时间范围（天）
            
        Returns:
            记录数量
        """
        try:
            records = self.db.get_analysis_history(code=code, days=days, limit=1000)
            return len(records)
        except Exception as e:
            logger.error(f"统计分析记录失败: {e}")
            return 0

    def iter_market_review_snapshot_payloads(
        self, *, limit: Optional[int] = None
    ) -> Iterator[Tuple[int, Any]]:
        """惰性遍历大盘复盘历史记录的 `(主键, context_snapshot)` 元组，按时间倒序。

        `market_light.load_previous_snapshot` 需要在大量历史记录里边扫描
        边比较 `trade_date`，逐行取会占内存，这里用 `yield_per` 分批取。把
        `sqlalchemy` 的 `desc` / `session.query` 细节留在仓储层，让服务层不需要
        自己 `import sqlalchemy`；只抛出 `(id, context_snapshot)` 两个普通值（而不
        是 ORM 对象），避免会话关闭后调用方访问已分离的实例。
        """
        # 延迟导入：`src.application.market.market_review` 会拉 NotificationService / analyzer
        # 等重依赖，这里只用它的两个字符串常量，不构成业务依赖。若在模块
        # 顶层导入，会把 repositories 层直接绑上这些重依赖。
        from src.application.market.market_review import (
            MARKET_REVIEW_HISTORY_CODE,
            MARKET_REVIEW_REPORT_TYPE,
        )

        with self.db.get_session() as session:
            query = (
                session.query(AnalysisHistory)
                .filter(
                    AnalysisHistory.code == MARKET_REVIEW_HISTORY_CODE,
                    AnalysisHistory.report_type == MARKET_REVIEW_REPORT_TYPE,
                )
                .order_by(desc(AnalysisHistory.created_at), desc(AnalysisHistory.id))
            )
            if limit is not None:
                query = query.limit(limit)
            for row in query.yield_per(MARKET_LIGHT_HISTORY_BATCH_SIZE):
                yield (row.id, row.context_snapshot)
