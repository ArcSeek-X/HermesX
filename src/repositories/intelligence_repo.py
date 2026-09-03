# -*- coding: utf-8 -*-
"""资讯 / 情报的数据访问层（Repository）。

职责边界：

1. 本模块只负责「资讯源（intelligence_sources）」与「资讯条目（intelligence_items）」
   两张表的持久化与查询；
2. 不负责抓取、字段标准化与业务编排（这些在
   ``src/services/intelligence_service.py`` 与 ``data_provider/`` 中）；
3. 所有会话（session）在本层开闭，返回给上层的 ORM 对象在会话关闭后可能处于
   detached 状态，调用方应在会话内完成所需字段的读取。

两类数据共存在 ``intelligence_items`` 表中，通过 ``scope_type`` / ``scope_value``
区分语义：

- 通用资讯：`scope_type` 取 ``symbol`` / ``market`` / ``sector``，绑定个股或市场；
- 实时快讯：`scope_type` 固定为 ``channel``，`scope_value` 存频道短码（如 ``a-stock``），
  详见 ``list_live_news_items``。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy import and_, delete, desc, func, or_, select
from sqlalchemy.exc import IntegrityError

from src.storage import DatabaseManager, IntelligenceItem, IntelligenceSource, INTELLIGENCE_ITEM_NULL_SCOPE_VALUE


class IntelligenceRepository:
    """资讯源与资讯条目的数据库访问层。

    所有方法均为「一次会话一件事」的短事务，异常由上层（Service / API）统一处理，
    本层不吞异常、不做业务兜底，以便问题能在正确的层级暴露。
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """初始化仓储。

        Args:
            db_manager: 数据库管理器；为空时使用全局单例（常规运行路径）。
                测试或需要隔离存储时传入自定义实例。
        """
        self.db = db_manager or DatabaseManager.get_instance()

    # ------------------------------------------------------------------
    # 资讯源（intelligence_sources）
    # ------------------------------------------------------------------
    def create_source(self, fields: Dict[str, Any]) -> IntelligenceSource:
        """新建资讯源。

        Args:
            fields: 与 ``IntelligenceSource`` 列同名字段；唯一性由 ``name`` 约束保证，
                重名会抛出 ``IntegrityError``，由上层转成校验错误。

        Returns:
            已提交并刷新过的源记录（含自增 id）。
        """
        with self.db.get_session() as session:
            row = IntelligenceSource(**fields)
            session.add(row)
            session.commit()
            session.refresh(row)
            return row

    def get_source(self, source_id: int) -> Optional[IntelligenceSource]:
        """按主键查询资讯源；不存在时返回 None。"""
        with self.db.get_session() as session:
            return session.execute(
                select(IntelligenceSource).where(IntelligenceSource.id == source_id).limit(1)
            ).scalar_one_or_none()

    def get_source_by_name(self, name: str) -> Optional[IntelligenceSource]:
        """按名称查询资讯源；不存在时返回 None。

        名称在表上有唯一约束，因此最多只会命中一条。
        """
        with self.db.get_session() as session:
            return session.execute(
                select(IntelligenceSource).where(IntelligenceSource.name == name).limit(1)
            ).scalar_one_or_none()

    def update_source_enabled(self, source_id: int, enabled: bool) -> None:
        """启停资讯源。

        源不存在时静默返回（避免把「已删除」变成错误，调用方通常只是想确保最终状态）。
        """
        with self.db.get_session() as session:
            row = session.execute(
                select(IntelligenceSource).where(IntelligenceSource.id == source_id).limit(1)
            ).scalar_one_or_none()
            if row is None:
                return
            row.enabled = bool(enabled)
            row.updated_at = datetime.now()
            session.commit()

    def list_sources(
        self,
        *,
        enabled: Optional[bool] = None,
        source_type: Optional[str] = None,
        scope_type: Optional[str] = None,
        market: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[IntelligenceSource], int]:
        """分页查询资讯源。

        所有过滤条件均为可选且按「与」组合；``page_size`` 内部收敛到 1~100，
        避免一次性拉全表。

        Returns:
            ``(当前页记录, 符合条件的总条数)``；按最近更新时间倒序。
        """
        conditions = []
        if enabled is not None:
            conditions.append(IntelligenceSource.enabled.is_(enabled))
        if source_type:
            conditions.append(IntelligenceSource.source_type == source_type)
        if scope_type:
            conditions.append(IntelligenceSource.scope_type == scope_type)
        if market:
            conditions.append(IntelligenceSource.market == market)
        where_clause = and_(*conditions) if conditions else True
        safe_page = max(1, int(page))
        safe_size = max(1, min(int(page_size), 100))
        with self.db.get_session() as session:
            total = session.execute(
                select(func.count(IntelligenceSource.id)).select_from(IntelligenceSource).where(where_clause)
            ).scalar() or 0
            rows = session.execute(
                select(IntelligenceSource)
                .where(where_clause)
                .order_by(desc(IntelligenceSource.updated_at), desc(IntelligenceSource.id))
                .offset((safe_page - 1) * safe_size)
                .limit(safe_size)
            ).scalars().all()
            return list(rows), int(total)

    def update_source_status(
        self,
        source_id: int,
        *,
        status: str,
        error: Optional[str] = None,
        fetched_at: Optional[datetime] = None,
    ) -> None:
        """回写资讯源的最近抓取结果，供前端做健康检查展示。

        Args:
            status: 状态标记（如 ``ok`` / ``error``），由 Service 层定义取值。
            error: 失败原因；**必须已做脱敏处理**（本层不做过滤），避免把
                含 token / 密钥的上游错误原文写库。
            fetched_at: 抓取时间；为空表示不更新该字段（例如仅记录失败原因）。
        """
        with self.db.get_session() as session:
            row = session.execute(
                select(IntelligenceSource).where(IntelligenceSource.id == source_id).limit(1)
            ).scalar_one_or_none()
            if row is None:
                return
            row.last_status = status
            row.last_error = error
            if fetched_at is not None:
                row.last_fetched_at = fetched_at
            row.updated_at = datetime.now()
            session.commit()

    # ------------------------------------------------------------------
    # 资讯条目（intelligence_items）
    # ------------------------------------------------------------------
    def upsert_items(self, items: Iterable[Dict[str, Any]]) -> int:
        """批量写入资讯条目，已存在则按字段补充更新。

        去重键为 ``(source_id 或 source_name, url, source_type, scope_type, scope_value, market)``，
        与表上的唯一约束保持一致：

        - 传入 ``source_id`` 时按源 ID 匹配（常规 RSS / Atom / NewsNow 源）；
        - 未传 ``source_id``（快讯链路，源不注册到 ``intelligence_sources``）时，
          退化为按 ``source_name`` 匹配，保证同一条快讯重复抓取不会堆积。

        已存在记录**只补空值、不覆盖已有值**（``新值 or 旧值``），这样后到的、
        字段更全的响应不会把先前写入的有效内容清掉。

        Args:
            items: 条目字段字典的可迭代对象；缺 url 或 title 的条目会被跳过
                （表上 ``title`` 为 NOT NULL）。

        Returns:
            本次**新增**的条数（已存在被更新的不计入）。
        """
        saved = 0
        with self.db.get_session() as session:
            for fields in items:
                url = (fields.get("url") or "").strip()
                title = (fields.get("title") or "").strip()
                if not url or not title:
                    continue
                item_fields = dict(fields)
                scope_value = self._normalize_scope_value(item_fields.get("scope_value"))
                item_fields["scope_value"] = scope_value
                source_id = item_fields.get("source_id")
                conditions = [
                    IntelligenceItem.url == url,
                    IntelligenceItem.source_type == (item_fields.get("source_type") or "rss"),
                    IntelligenceItem.scope_type == (item_fields.get("scope_type") or "market"),
                    IntelligenceItem.market == (item_fields.get("market") or "cn"),
                ]
                if source_id is None:
                    # 快讯等未注册源的条目：改用 source_name 参与去重
                    conditions.append(IntelligenceItem.source_id.is_(None))
                    conditions.append(IntelligenceItem.source_name == item_fields.get("source_name"))
                else:
                    conditions.append(IntelligenceItem.source_id == source_id)
                conditions.append(IntelligenceItem.scope_value == scope_value)
                existing = session.execute(
                    select(IntelligenceItem).where(and_(*conditions)).limit(1)
                ).scalar_one_or_none()
                if existing is not None:
                    # 只补充、不覆盖：新值为空时保留库中已有内容
                    existing.summary = item_fields.get("summary") or existing.summary
                    existing.source = item_fields.get("source") or existing.source
                    existing.published_at = item_fields.get("published_at") or existing.published_at
                    existing.fetched_at = item_fields.get("fetched_at") or datetime.now()
                    existing.raw_payload = item_fields.get("raw_payload") or existing.raw_payload
                    continue
                try:
                    # 用 SAVEPOINT 包住单条插入：并发写入触发唯一约束冲突时
                    # 只回滚这一条，不影响本批次后续条目
                    with session.begin_nested():
                        session.add(IntelligenceItem(**item_fields))
                        session.flush()
                    saved += 1
                except IntegrityError:
                    continue
            session.commit()
        return saved

    def list_items(
        self,
        *,
        scope_type: Optional[str] = None,
        scope_value: Optional[str] = None,
        market: Optional[str] = None,
        query: Optional[str] = None,
        days: Optional[int] = None,
        published_days: Optional[int] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[IntelligenceItem], int]:
        """通用分页查询资讯条目（面向个股 / 市场 / 板块维度）。

        两个时间过滤参数的语义不同，按需选用：

        - ``days``：按**入库时间** ``fetched_at`` 过滤（我们是什么时候抓到的）；
        - ``published_days``：按**发布时间** ``published_at`` 过滤（资讯本身有多新）。

        Returns:
            ``(当前页记录, 符合条件的总条数)``；发布时间缺失时回退按入库时间排序。
        """
        conditions = []
        if scope_type:
            conditions.append(IntelligenceItem.scope_type == scope_type)
        if scope_value:
            conditions.append(IntelligenceItem.scope_value == self._normalize_scope_value(scope_value))
        if market:
            conditions.append(IntelligenceItem.market == market)
        if query:
            pattern = f"%{query.strip()}%"
            conditions.append(or_(IntelligenceItem.title.like(pattern), IntelligenceItem.summary.like(pattern)))
        if days is not None:
            # 按入库时间过滤
            conditions.append(IntelligenceItem.fetched_at >= datetime.now() - timedelta(days=max(1, int(days))))
        if published_days is not None:
            # 按发布时间过滤；发布时间为空的条目自然被排除
            published_cutoff = datetime.now() - timedelta(days=max(1, int(published_days)))
            conditions.append(IntelligenceItem.published_at >= published_cutoff)
        where_clause = and_(*conditions) if conditions else True
        safe_page = max(1, int(page))
        safe_size = max(1, min(int(page_size), 100))
        with self.db.get_session() as session:
            total = session.execute(
                select(func.count(IntelligenceItem.id)).select_from(IntelligenceItem).where(where_clause)
            ).scalar() or 0
            rows = session.execute(
                select(IntelligenceItem)
                .where(where_clause)
                # 发布时间可能为空（部分源不提供），回退按入库时间排序，
                # 保证排序键永远有值、顺序稳定；id 作为决胜列避免同刻抖动。
                .order_by(desc(func.coalesce(IntelligenceItem.published_at, IntelligenceItem.fetched_at)), desc(IntelligenceItem.id))
                .offset((safe_page - 1) * safe_size)
                .limit(safe_size)
            ).scalars().all()
            return list(rows), int(total)

    # ------------------------------------------------------------------
    # 实时快讯（intelligence_items，scope_type='channel'）
    #
    # 快讯与通用资讯共用一张表，通过 scope_type='channel' + scope_value=频道短码
    # 区分。这样做的好处是不需要新增表、也不必改动既有唯一约束：约束里已包含
    # scope_value，因此「同一条快讯属于多个频道」可以各存一行且天然去重。
    # ------------------------------------------------------------------
    def list_live_news_items(
        self,
        *,
        scope_value: str,
        important_only: bool = False,
        important_threshold: int = 2,
        keyword: Optional[str] = None,
        published_from: Optional[datetime] = None,
        published_to: Optional[datetime] = None,
        cursor: Optional[Tuple[datetime, int]] = None,
        limit: int = 30,
    ) -> Tuple[List[IntelligenceItem], int]:
        """查询快讯条目（面向华尔街见闻快讯页）。

        与通用 ``list_items`` 的差异：
        1. 固定按 ``scope_type='channel'`` + 指定频道短码过滤；
        2. 支持按重要级阈值过滤（``importance >= threshold``）；
        3. 支持按发布时间的闭区间过滤（用于「查询某日快讯」）；
        4. 采用 ``(published_at, id)`` 复合 keyset 游标分页，避免时间相同的条目漏数据或重复。

        Args:
            scope_value: 频道短码，如 ``a-stock``；由调用方保证已归一化。
            important_only: 为 True 时只返回重要级不低于阈值的条目。
            important_threshold: 重要级阈值（对应上游 score）。
            keyword: 关键词，对标题与正文做模糊匹配。
            published_from: 发布时间下界（含）。
            published_to: 发布时间上界（含）。
            cursor: 上一页最后一条的 ``(published_at, id)``；为空表示取第一页。
            limit: 每页条数，内部收敛到 1~100。

        Returns:
            ``(条目列表, 该过滤条件下的总条数)``。
        """
        conditions = [IntelligenceItem.scope_type == "channel"]
        conditions.append(IntelligenceItem.scope_value == self._normalize_scope_value(scope_value))
        if keyword:
            pattern = f"%{keyword.strip()}%"
            conditions.append(or_(IntelligenceItem.title.like(pattern), IntelligenceItem.summary.like(pattern)))
        if published_from is not None:
            conditions.append(IntelligenceItem.published_at >= published_from)
        if published_to is not None:
            conditions.append(IntelligenceItem.published_at <= published_to)
        if important_only:
            # 重要级字段仅快讯源会写入；降级源（NewsNow）该列为 NULL，
            # 此时 important_only 查询结果为空，由前端隐藏该开关。
            conditions.append(IntelligenceItem.importance >= int(important_threshold))
        if cursor is not None:
            # keyset 分页：取「时间更早」或「时间相同但 id 更小」的记录。
            # 只比时间会在同一秒有多条时漏数据或重复，因此必须带上 id 作为决胜列。
            cursor_time, cursor_id = cursor
            conditions.append(
                or_(
                    IntelligenceItem.published_at < cursor_time,
                    and_(
                        IntelligenceItem.published_at == cursor_time,
                        IntelligenceItem.id < cursor_id,
                    ),
                )
            )

        where_clause = and_(*conditions)
        safe_limit = max(1, min(int(limit), 100))
        with self.db.get_session() as session:
            total = session.execute(
                select(func.count(IntelligenceItem.id)).select_from(IntelligenceItem).where(where_clause)
            ).scalar() or 0
            rows = session.execute(
                select(IntelligenceItem)
                .where(where_clause)
                # 时间倒序 + id 倒序，与 keyset 游标方向保持一致
                .order_by(desc(IntelligenceItem.published_at), desc(IntelligenceItem.id))
                .limit(safe_limit)
            ).scalars().all()
            return list(rows), int(total)

    def get_live_news_item_by_id(self, item_id: int) -> Optional[IntelligenceItem]:
        """按快讯原始 ID 查询单条快讯。

        快讯 ID 没有独立列，但会稳定出现在原文链接末尾（``.../livenews/<id>``），
        官方源与 NewsNow 兜底源的链接形态一致，因此用 URL 后缀匹配即可，
        无需依赖 ``raw_payload`` 的 JSON 序列化格式，跨数据源与跨后端都稳定。

        Args:
            item_id: 快讯原始 ID。

        Returns:
            命中的条目；不存在时返回 None。
        """
        suffix = f"/livenews/{int(item_id)}"
        with self.db.get_session() as session:
            return session.execute(
                select(IntelligenceItem)
                .where(and_(
                    IntelligenceItem.scope_type == "channel",
                    IntelligenceItem.url.like(f"%{suffix}"),
                ))
                .order_by(desc(IntelligenceItem.id))
                .limit(1)
            ).scalar_one_or_none()

    def count_live_news_items(self, *, scope_value: str) -> int:
        """统计指定频道已沉淀的快讯条数，用于判断是否需要引导首次抓取。"""
        with self.db.get_session() as session:
            return int(session.execute(
                select(func.count(IntelligenceItem.id))
                .select_from(IntelligenceItem)
                .where(and_(
                    IntelligenceItem.scope_type == "channel",
                    IntelligenceItem.scope_value == self._normalize_scope_value(scope_value),
                ))
            ).scalar() or 0)

    # ------------------------------------------------------------------
    # 消息日历（intelligence_items，scope_type='calendar'）
    #
    # 日历与快讯 / 通用资讯共用一张表，通过 scope_type='calendar' 区分。
    # 一条事件可命中多个分类（宏观 / 财报 / 新股 / 活动），按分类拆多行落库
    # （scope_value 各不相同），由唯一约束天然去重——与快讯「多频道各存一行」一致。
    # 写入复用 ``upsert_items``（其去重键已含 scope_value），查询见本方法。
    # 详见 docs/Live-calendar.md §5。
    # ------------------------------------------------------------------
    def list_calendar_events(
        self,
        *,
        published_from: datetime,
        published_to: datetime,
    ) -> List[IntelligenceItem]:
        """查询指定时间区间（UTC，含端点）内的日历事件行。

        仅按 ``scope_type='calendar'`` + 发布时间闭区间过滤，**不做分类去重**：
        分类聚合（同一事件的多行合并为一条、拼出 tab_keys）由服务层负责。

        Args:
            published_from: 发布时间下界（含，UTC naive）。
            published_to: 发布时间上界（含，UTC naive）。

        Returns:
            按 ``published_at`` 升序、``id`` 升序的事件行列表。
        """
        conditions = [
            IntelligenceItem.scope_type == "calendar",
            IntelligenceItem.published_at >= published_from,
            IntelligenceItem.published_at <= published_to,
        ]
        with self.db.get_session() as session:
            rows = session.execute(
                select(IntelligenceItem)
                .where(and_(*conditions))
                .order_by(IntelligenceItem.published_at, IntelligenceItem.id)
            ).scalars().all()
            return list(rows)

    @staticmethod
    def _normalize_scope_value(value: Any) -> str:
        """归一化作用域取值。

        ``scope_value`` 在表上为 NOT NULL 且有默认值，但显式写入空串会绕过默认值
        并让「按作用域查询」失效；因此这里统一把空值折叠成哨兵常量，
        保证「写入」与「查询」两侧看到完全一致的字符串。

        Args:
            value: 原始取值（可以是任意类型，最终按字符串处理）。

        Returns:
            去空白后的字符串；为空时返回 ``INTELLIGENCE_ITEM_NULL_SCOPE_VALUE``。
        """
        normalized = str(value or "").strip()
        return normalized or INTELLIGENCE_ITEM_NULL_SCOPE_VALUE

    def apply_retention(self, retention_days: int) -> int:
        """按保留期清理过期条目。

        以**入库时间** ``fetched_at`` 而非发布时间为基准：发布时间由上游提供、
        可能缺失或异常，用它做删除基准存在误删与漏删风险。

        Args:
            retention_days: 保留天数，内部至少按 1 天处理。

        Returns:
            实际删除的条数。
        """
        cutoff = datetime.now() - timedelta(days=max(1, int(retention_days)))
        with self.db.get_session() as session:
            result = session.execute(delete(IntelligenceItem).where(IntelligenceItem.fetched_at < cutoff))
            session.commit()
            return int(result.rowcount or 0)
