# -*- coding: utf-8 -*-
"""资讯情报域模型：新闻、情报源、情报条目、基本面快照。

本模块只声明 ORM 表结构；全部模型注册在 `src.infrastructure.persistence.base.Base`
这唯一一个 metadata 上。导入本模块即完成注册，不要在别处再建 Base。
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Integer,
    ForeignKey,
    Index,
    UniqueConstraint,
    Text,
)

from src.infrastructure.persistence.base import Base

# intelligence_items.scope_value 的空值哨兵：该列 NOT NULL 且带默认值，但显式写入
# 空串会绕过默认值、让「按作用域查询」失效，因此统一用该常量表示「无作用域」，
# 写入与查询两侧必须一致。单一真源已上收至 ``application/intelligence/ports.py``
# （PP-1：application 服务需按值比较、又不能反向 import infra model，故端口为权威，
# model 与仓储均从此处 import）。
from src.application.intelligence.ports import INTELLIGENCE_ITEM_NULL_SCOPE_VALUE


class NewsIntel(Base):
    """
    新闻情报数据模型

    存储搜索到的新闻情报条目，用于后续分析与查询
    """
    __tablename__ = 'news_intel'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 关联用户查询操作
    query_id = Column(String(64), index=True)

    # 股票信息
    code = Column(String(10), nullable=False, index=True)
    name = Column(String(50))

    # 搜索上下文
    dimension = Column(String(32), index=True)  # latest_news / risk_check / earnings / market_analysis / industry
    query = Column(String(255))
    provider = Column(String(32), index=True)

    # 新闻内容
    title = Column(String(300), nullable=False)
    snippet = Column(Text)
    url = Column(String(1000), nullable=False)
    source = Column(String(100))
    published_date = Column(DateTime, index=True)

    # 入库时间
    fetched_at = Column(DateTime, default=datetime.now, index=True)
    query_source = Column(String(32), index=True)  # bot/web/cli/system
    requester_platform = Column(String(20))
    requester_user_id = Column(String(64))
    requester_user_name = Column(String(64))
    requester_chat_id = Column(String(64))
    requester_message_id = Column(String(64))
    requester_query = Column(String(255))

    __table_args__ = (
        UniqueConstraint('url', name='uix_news_url'),
        Index('ix_news_code_pub', 'code', 'published_date'),
    )

    def __repr__(self) -> str:
        return f"<NewsIntel(code={self.code}, title={self.title[:20]}...)>"


class IntelligenceSource(Base):
    """可配置资讯源（RSS / Atom / NewsNow 等）。

    一张源记录描述「从哪里抓、抓来的内容归属哪个作用域」。
    抓取执行与健康状态回写由 ``IntelligenceService`` 负责，本表只承载配置与状态。

    注意：**实时快讯不使用本表**（见 :class:`IntelligenceItem` 说明），
    因为它需要按 8 个频道分别抓取，一条源记录无法表达，且会被通用抓取链路误抓。
    """

    __tablename__ = 'intelligence_sources'

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 源名称，唯一；创建内置源时靠它做幂等判断
    name = Column(String(100), nullable=False, unique=True, index=True)
    # 协议类型：rss / atom / newsnow（决定用哪个解析器）
    source_type = Column(String(32), nullable=False, default='rss', index=True)
    # 上游地址；抓取前会做 SSRF 校验（禁止内网/私网地址）
    url = Column(String(1000), nullable=False)
    # 是否启用；仅启用的源会被批量拉取
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    # 作用域维度：symbol（个股）/ market（市场）/ sector（板块）
    scope_type = Column(String(32), nullable=False, default='market', index=True)
    # 作用域取值：股票代码 / 板块名等；为空表示不绑定具体对象
    scope_value = Column(String(64), index=True)
    # 市场：cn / hk / us / global
    market = Column(String(32), nullable=False, default='cn', index=True)
    description = Column(Text)
    # 最近一次抓取状态（成功/失败标记），由 Service 定义取值
    last_status = Column(String(32))
    # 最近一次失败原因；必须已脱敏，禁止写入含 token/密钥的上游原文
    last_error = Column(Text)
    last_fetched_at = Column(DateTime, index=True)
    created_at = Column(DateTime, default=datetime.now, index=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, index=True)

    __table_args__ = (
        # 按「作用域 + 市场」查询某只股票/某个市场有哪些源
        Index('ix_intel_source_scope', 'scope_type', 'scope_value', 'market'),
    )


class IntelligenceItem(Base):
    """沉淀后的资讯 / 情报条目。

    **通用资讯与实时快讯共用本表**，靠 ``scope_type`` / ``scope_value`` 区分：

    - 通用资讯：``scope_type`` 取 ``symbol`` / ``market`` / ``sector``，
      一条资讯一行，``source_id`` 指向 :class:`IntelligenceSource`；
    - 实时快讯：``scope_type`` 固定为 ``channel``，``scope_value`` 存频道短码
      （``global`` / ``a-stock`` / ``tech`` 等，见 ``documents/product/行情资讯/live-news.md``）。
      快讯不注册源，``source_id`` 为 NULL，靠 ``source_name`` 标识；
      同一条快讯命中多个频道时**各存一行**，由唯一约束天然去重。

    这样设计的好处是不新增表、不改动既有唯一约束（约束已含 ``scope_value``）。
    """

    __tablename__ = 'intelligence_items'

    id = Column(Integer, primary_key=True, autoincrement=True)
    # 源外键；快讯链路为 NULL（源不注册到 intelligence_sources），删除源时置 NULL
    source_id = Column(Integer, ForeignKey('intelligence_sources.id', ondelete='SET NULL'), nullable=True, index=True)
    # 源名称；source_id 为空时作为去重身份的一部分
    source_name = Column(String(100), index=True)
    # 来源协议：rss / atom / newsnow / wscn_live_news（快讯官方源）
    source_type = Column(String(32), nullable=False, default='rss', index=True)
    title = Column(String(300), nullable=False)
    summary = Column(Text)
    url = Column(String(1000), nullable=False, index=True)
    # 来源展示名（如「华尔街见闻」）
    source = Column(String(100))
    # 上游发布时间（UTC naive）。注意单位差异：华尔街见闻为秒级时间戳、
    # NewsNow 为毫秒级，归一化在 Service 层完成，入库后统一为 datetime
    published_at = Column(DateTime, index=True)
    # 入库时间；保留期清理以该字段为基准（发布时间可能缺失或异常）
    fetched_at = Column(DateTime, default=datetime.now, index=True)
    # 作用域维度：symbol / market / sector / channel（快讯）
    scope_type = Column(String(32), nullable=False, default='market', index=True)
    # 作用域取值；空值统一折叠为 INTELLIGENCE_ITEM_NULL_SCOPE_VALUE
    scope_value = Column(String(64), nullable=False, default=INTELLIGENCE_ITEM_NULL_SCOPE_VALUE, index=True)
    market = Column(String(32), nullable=False, default='cn', index=True)
    # 上游原始条目 JSON，用于排障与后续字段扩展时不丢信息
    raw_payload = Column(Text)
    # 重要级（华尔街见闻快讯的 score：1=普通 / 2=重要 / 3=非常重要）。
    # 仅快讯类数据源（wscn_live_news）会写入；RSS / Atom / NewsNow 因上游无此字段保持 NULL，
    # 前端据此判断「重要级筛选」是否可用。详见 documents/product/行情资讯/live-news.md。
    importance = Column(Integer, nullable=True, index=True)

    __table_args__ = (
        # 去重键：同一来源 + 同一 URL + 同一作用域 + 同一市场只保留一条。
        # scope_value 参与约束，因此「同一条快讯属于多个频道」可以各存一行且互不冲突。
        # 注意：source_id 为 NULL 时 SQLite 的唯一约束不生效（NULL != NULL），
        # 快讯的去重改由仓储层按 source_name 显式匹配后 upsert 保证。
        UniqueConstraint(
            'source_id',
            'url',
            'scope_type',
            'scope_value',
            'market',
            name='uix_intel_item_source_scope_url',
        ),
        # 按「作用域 + 时间」查询某个股票/市场/频道的资讯
        Index('ix_intel_item_scope_time', 'scope_type', 'scope_value', 'market', 'published_at'),
        # 保留期清理按 fetched_at 扫描
        Index('ix_intel_item_fetch_time', 'fetched_at'),
        # 按「频道 + 重要级 + 发布时间」查询快讯列表的复合索引
        Index('ix_intel_item_channel_importance_time', 'scope_value', 'importance', 'published_at'),
    )


class FundamentalSnapshot(Base):
    """
    基本面上下文快照（P0 write-only）。

    仅用于写入，主链路不依赖读取该表，便于后续回测/画像扩展。

    设计意图：分析时用到的基本面上下文若不落库，事后无法解释「当时依据什么
    做出的判断」。本表就是这个留痕，等回测/画像能力成熟后再被消费。
    """
    __tablename__ = 'fundamental_snapshot'

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(String(64), nullable=False, index=True)
    code = Column(String(10), nullable=False, index=True)
    # 基本面数据本体，JSON 字符串
    payload = Column(Text, nullable=False)
    # 取数链路（先查了哪个源、失败后降级到哪个源），用于排障
    source_chain = Column(Text)
    # 字段覆盖情况：哪些字段取到了、哪些缺失
    coverage = Column(Text)
    created_at = Column(DateTime, default=datetime.now, index=True)

    __table_args__ = (
        Index('ix_fundamental_snapshot_query_code', 'query_id', 'code'),
        Index('ix_fundamental_snapshot_created', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<FundamentalSnapshot(query_id={self.query_id}, code={self.code})>"
