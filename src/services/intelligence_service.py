# -*- coding: utf-8 -*-
"""可配置、合规的资讯源（情报源）服务层。

作用
----
本文件是“本地资讯池 / 情报源（Intelligence Source）”的业务服务层，负责把外部公开的
财经资讯源（RSS / Atom / NewsNow JSON API）接入到系统内，并在入库前后完成校验、
清洗与查询封装。上游是 API 层与运行时主流程（调用 ``refresh_auto_sources`` 在分析前
自动补全证据），下游是 ``IntelligenceRepository``（数据访问层）与数据库存储。

核心职责
--------
1. 资讯源管理：创建、列表、按模板创建、批量初始化内置源、启用/停用；
2. 抓取与解析：RSS / Atom / NewsNow 三类源的拉取、重定向处理、体积限制与条目解析；
3. 安全校验（SSRF 防护）：URL 必须为绝对 http(s)、禁止携带凭据、禁止解析到内网/本机
   地址，且在请求过程中通过 DNS guard 复检解析结果，避免 DNS rebinding；
4. 持久化：条目按 URL 去重 upsert，按 ``news_intel_retention_days`` 执行保留期清理，
   并回写资讯源的抓取状态（成功/失败、错误信息、最近抓取时间）；
5. 运行时自动刷新：``refresh_auto_sources`` 提供进程内单例化、带冷却时间（1 小时）、
   fail-open（失败不阻断主流程）的自动抓取能力。

设计约束
--------
- 默认 fail-open：单源抓取失败只记录状态与日志，不拖垮分析主流程；
- 错误信息统一经 ``sanitize_diagnostic_text`` 脱敏后再对外暴露，避免泄漏内部细节；
- 所有出站请求禁用系统代理，并限制单次响应体积与重定向次数。

相关配置（``src/config.py``）：
``news_intel_retention_days``、``news_intel_fetch_timeout_sec``、
``news_intel_max_items_per_source``、``news_intel_auto_fetch_enabled``、``newsnow_base_url``。
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import logging
import re
import socket
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from xml.etree import ElementTree as ET

import requests
from sqlalchemy.exc import IntegrityError

from src.config import Config, get_config
from src.repositories.intelligence_repo import IntelligenceRepository
from src.storage import IntelligenceSource, INTELLIGENCE_ITEM_NULL_SCOPE_VALUE
from src.services.run_diagnostics import sanitize_diagnostic_text

logger = logging.getLogger(__name__)

# 允许的数据源类型：标准 RSS、Atom，以及 NewsNow 的 JSON 接口
_ALLOWED_SOURCE_TYPES = {"rss", "atom", "newsnow"}
# 允许的作用域类型：个股（symbol）、市场（market）、板块（sector）
_ALLOWED_SCOPE_TYPES = {"symbol", "market", "sector"}
# 允许的市场标识
_ALLOWED_MARKETS = {"cn", "hk", "us", "jp", "kr", "tw", "global"}
# 显式禁止的本地主机名（除 IP 层面的内网判断外额外兜底）
_PRIVATE_HOSTNAMES = {"localhost", "localhost.localdomain"}
# 单个 feed 响应体的最大读取字节数（2MB），防止超大响应拖垮进程
_MAX_FEED_BYTES = 2 * 1024 * 1024
# 允许手动跟随的最大重定向次数，超出即视为异常
_MAX_FEED_REDIRECTS = 5
# 上游请求失败时对外的统一文案，避免泄漏内部异常细节
_UPSTREAM_FETCH_FAILURE_MESSAGE = "fetch failed: upstream request failed"
# 需要手动处理的状态码：NewsNow 分支据此拒绝跟随，RSS 分支据此逐跳校验
_REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}
# 出站请求显式禁用系统代理，避免代理绕过 SSRF 校验
_DISABLE_REQUEST_PROXIES = {"http": None, "https": None}
# 保护 socket.getaddrinfo 打桩过程，避免并发请求互相覆盖
_DNS_GUARD_LOCK = threading.Lock()
# 运行时自动抓取的最小间隔（1 小时），防止重复触发打爆上游
_AUTO_FETCH_MIN_INTERVAL_SECONDS = 60 * 60

# 内置资讯源模板（标准 RSS/Atom 类）；NewsNow 源由下方定义动态拼装 URL
_BUILTIN_SOURCE_TEMPLATES = [
    {
        "template_id": "sec-company-news",
        "name": "SEC Latest Filings",
        "source_type": "rss",
        "url": "https://www.sec.gov/news/pressreleases.rss",
        "scope_type": "market",
        "market": "us",
        "description": "SEC official press release RSS feed for US market evidence.",
    },
    {
        "template_id": "hkex-news",
        "name": "HKEX Market News",
        "source_type": "rss",
        "url": "https://www.hkex.com.hk/Services/RSS-Feeds/News-Releases?sc_lang=en",
        "scope_type": "market",
        "market": "hk",
        "description": "HKEX public news entry for Hong Kong market evidence. Test before enabling.",
    },
    {
        "template_id": "global-marketwatch",
        "name": "MarketWatch Top Stories",
        "source_type": "rss",
        "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
        "scope_type": "market",
        "market": "global",
        "description": "Public market news RSS for global market context. Test before enabling.",
    },
]

# NewsNow 内置源定义：只声明 source_id，具体 URL 由 _build_newsnow_url 拼装，
# 这样更换 newsnow_base_url 时无需改动模板本身
_NEWSNOW_DEFAULT_SOURCE_DEFS = [
    {
        "template_id": "newsnow-cls-hot",
        "name": "NewsNow 财联社热门",
        "source_id": "cls-hot",
        "market": "cn",
        "description": "NewsNow 财联社热门财经资讯，适合 A 股大盘和题材热点。",
    },
    {
        "template_id": "newsnow-xueqiu-hotstock",
        "name": "NewsNow 雪球热门股票",
        "source_id": "xueqiu-hotstock",
        "market": "cn",
        "description": "NewsNow 雪球热门股票，适合捕捉 A 股和港美股散户关注度。",
    },
    {
        "template_id": "newsnow-wallstreetcn-quick",
        "name": "NewsNow 华尔街见闻快讯",
        "source_id": "wallstreetcn-quick",
        "market": "cn",
        "description": "NewsNow 华尔街见闻快讯，适合宏观、商品和市场事件上下文。",
    },
    {
        "template_id": "newsnow-jin10",
        "name": "NewsNow 金十数据",
        "source_id": "jin10",
        "market": "global",
        "description": "NewsNow 金十数据实时财经消息，适合全球宏观和外盘事件。",
    },
    {
        "template_id": "newsnow-gelonghui",
        "name": "NewsNow 格隆汇事件",
        "source_id": "gelonghui",
        "market": "hk",
        "description": "NewsNow 格隆汇事件资讯，适合港股和中概股市场上下文。",
    },
]


class IntelligenceServiceError(ValueError):
    """面向调用方的校验/业务错误，其文案会直接透出到 API 响应。"""


@dataclass(frozen=True)
class FeedEntry:
    """解析后的单条资讯条目，与具体数据源类型无关的中间结构。"""

    title: str  # 标题（已清洗、截断）
    summary: str  # 摘要/正文片段（已去除 HTML 标签）
    url: str  # 原文链接；无链接时退化为 no-url:intel:<hash> 形式
    source: str  # 来源的资讯源名称
    published_at: Optional[datetime]  # 发布时间（统一为 UTC naive），解析失败为 None
    raw_payload: Dict[str, Any]  # 预留的原始负载，便于排查与扩展


class IntelligenceService:
    """资讯源服务：抓取、校验、持久化与查询可配置的公开资讯源。

    对外提供资讯源 CRUD、模板创建、连通性测试、单源/全量抓取，以及供运行时调用的
    自动刷新入口。所有网络出口都经过 SSRF 校验，错误统一脱敏。
    """

    # 以下为进程级共享的自动刷新状态，保证同一进程内并发调用只执行一次实际抓取
    _auto_fetch_lock = threading.Lock()
    _auto_fetch_condition = threading.Condition(_auto_fetch_lock)
    _auto_fetch_in_progress = False
    _auto_fetch_last_run_at: Optional[datetime] = None
    _auto_fetch_last_result: Optional[Dict[str, Any]] = None

    def __init__(
        self,
        repository: Optional[IntelligenceRepository] = None,
        config: Optional[Config] = None,
    ):
        self.repo = repository or IntelligenceRepository()
        self.config = config or get_config()

    @classmethod
    def reset_auto_fetch_state(cls) -> None:
        """清空自动刷新的进程内状态，主要用于测试隔离。"""
        with cls._auto_fetch_condition:
            cls._auto_fetch_in_progress = False
            cls._auto_fetch_last_run_at = None
            cls._auto_fetch_last_result = None
            cls._auto_fetch_condition.notify_all()

    def create_source(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """创建资讯源：先归一化与校验字段，再做 SSRF 校验，最后落库。

        名称唯一性由数据库约束保证，此处把 IntegrityError 转成可读的业务错误。
        """
        fields = self._normalize_source_fields(payload)
        self._validate_url(fields["url"])
        try:
            return self._source_to_dict(self.repo.create_source(fields))
        except IntegrityError as exc:
            raise IntelligenceServiceError(f"intelligence source name already exists: {fields['name']}") from exc

    def list_sources(self, **filters: Any) -> Dict[str, Any]:
        """分页查询资讯源；page/page_size 由服务层兜底归一化，避免越界值传入仓库层。"""
        rows, total = self.repo.list_sources(**filters)
        return {
            "items": [self._source_to_dict(row) for row in rows],
            "total": total,
            "page": max(1, int(filters.get("page") or 1)),
            "page_size": max(1, min(int(filters.get("page_size") or 50), 100)),
        }

    def list_source_templates(self, **filters: Any) -> Dict[str, Any]:
        """列出内置资讯源模板，支持按 market / source_type 过滤（空值表示不过滤）。"""
        market = str(filters.get("market") or "").strip().lower()
        source_type = str(filters.get("source_type") or "").strip().lower()
        templates = []
        for template in self._builtin_source_templates():
            if market and template["market"] != market:
                continue
            if source_type and template["source_type"] != source_type:
                continue
            templates.append(dict(template))
        return {"items": templates, "total": len(templates)}

    def create_source_from_template(self, template_id: str, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """基于内置模板创建资讯源，overrides 中非 None 的字段覆盖模板默认值。"""
        selected = next(
            (dict(template) for template in self._builtin_source_templates() if template["template_id"] == template_id),
            None,
        )
        if selected is None:
            raise IntelligenceServiceError(f"Intelligence source template not found: {template_id}")
        payload = {key: value for key, value in selected.items() if key != "template_id"}
        payload.update({key: value for key, value in (overrides or {}).items() if value is not None})
        return self.create_source(payload)

    def create_default_sources(self, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """批量创建全部内置资讯源。

        默认创建后为停用状态（用户需自行确认后再启用），已存在同名源则跳过并返回原记录。
        """
        request_fields = dict(overrides or {})
        request_fields.setdefault("enabled", False)
        created_count = 0
        items = []
        for template in self._builtin_source_templates():
            payload = {key: value for key, value in template.items() if key != "template_id"}
            payload.update({key: value for key, value in request_fields.items() if value is not None})
            existing = self.repo.get_source_by_name(str(payload["name"]))
            if existing is not None:
                items.append({"created": False, "source": self._source_to_dict(existing)})
                continue
            source = self.create_source(payload)
            created_count += 1
            items.append({"created": True, "source": source})
        return {"items": items, "created_count": created_count, "total": len(items)}

    def ensure_default_sources_enabled(self) -> Dict[str, Any]:
        """自动模式引导：补齐缺失的内置源，并把已存在但未启用的内置源打开。

        单个源出错只记录到 errors 中，不影响其余源的处理。
        """
        created_count = 0
        enabled_count = 0
        errors = []
        templates = self._builtin_source_templates()
        for template in templates:
            name = str(template["name"])
            try:
                existing = self.repo.get_source_by_name(name)
                if existing is not None:
                    if not existing.enabled:
                        self.repo.update_source_enabled(existing.id, True)
                        enabled_count += 1
                    continue
                payload = {key: value for key, value in template.items() if key != "template_id"}
                payload["enabled"] = True
                self.create_source(payload)
                created_count += 1
            except Exception as exc:
                errors.append({"source": name, "error": self._sanitize_error(exc)})
        return {
            "created_count": created_count,
            "enabled_count": enabled_count,
            "error_count": len(errors),
            "errors": errors,
            "total": len(templates),
        }

    def list_items(self, **filters: Any) -> Dict[str, Any]:
        """分页查询资讯条目（本地资讯池内容），分页参数同样在此兜底归一化。"""
        rows, total = self.repo.list_items(**filters)
        return {
            "items": [self._item_to_dict(row) for row in rows],
            "total": total,
            "page": max(1, int(filters.get("page") or 1)),
            "page_size": max(1, min(int(filters.get("page_size") or 50), 100)),
        }

    def test_source(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """连通性测试：不落库，只抓取少量（最多 5 条）样本用于人工确认源是否可用。

        返回中的 source 字段经过脱敏，避免回显敏感的自定义请求头或密钥。
        """
        fields = self._normalize_source_fields(payload)
        entries = self._fetch_feed_entries(fields, limit=min(5, self.config.news_intel_max_items_per_source))
        return {
            "ok": True,
            "source": self._redact_source_fields(fields),
            "fetched_count": len(entries),
            "sample_items": [self._feed_entry_to_dict(entry) for entry in entries[:5]],
        }

    def fetch_source(self, source_id: int, *, dry_run: bool = False) -> Dict[str, Any]:
        """抓取单个资讯源并入库（dry_run=True 时只解析不落库）。

        流程：抓取 -> 解析 -> upsert 条目 -> 按保留期清理 -> 回写抓取状态。
        失败时记录 failed 状态与脱敏错误后继续向外抛异常，由调用方决定是否 fail-open。
        """
        source = self.repo.get_source(source_id)
        if source is None:
            raise IntelligenceServiceError(f"Intelligence source not found: {source_id}")
        if not source.enabled:
            raise IntelligenceServiceError(f"Intelligence source is disabled: {source_id}")
        now = datetime.now()
        try:
            entries = self._fetch_feed_entries(self._source_to_fields(source), limit=self.config.news_intel_max_items_per_source)
            item_fields = [self._entry_to_item_fields(entry, source, now) for entry in entries]
            saved = 0 if dry_run else self.repo.upsert_items(item_fields)
            deleted = 0 if dry_run else self.repo.apply_retention(self.config.news_intel_retention_days)
            if not dry_run:
                self.repo.update_source_status(source.id, status="success", error=None, fetched_at=now)
            return {
                "ok": True,
                "source_id": source.id,
                "fetched_count": len(entries),
                "saved_count": saved,
                "retention_deleted": deleted,
                "dry_run": dry_run,
                "sample_items": [self._feed_entry_to_dict(entry) for entry in entries[:5]],
            }
        except Exception as exc:
            error = self._sanitize_error(exc)
            if not dry_run:
                self.repo.update_source_status(source.id, status="failed", error=error)
            logger.warning("Intelligence source fetch failed id=%s name=%s: %s", source.id, source.name, error)
            raise

    def fetch_enabled_sources(self) -> Dict[str, Any]:
        """遍历抓取所有已启用的资讯源（按 100/页分页推进）。

        单源失败不影响其他源，失败结果会以 ok=False 记入 results。
        """
        rows, total = self.repo.list_sources(enabled=True, page=1, page_size=100)
        results = []
        page = 1
        source_count = 0
        while True:
            for row in rows:
                source_count += 1
                try:
                    results.append(self.fetch_source(row.id))
                except Exception as exc:
                    results.append({"ok": False, "source_id": row.id, "error": self._sanitize_error(exc)})
            if source_count >= total:
                break
            page += 1
            rows, _ = self.repo.list_sources(enabled=True, page=page, page_size=100)
            if not rows:
                break
        return {
            "ok": True,
            "source_count": source_count,
            "results": results,
            "saved_count": sum(int(item.get("saved_count") or 0) for item in results),
        }

    def refresh_auto_sources(self, *, force: bool = False) -> Dict[str, Any]:
        """运行时自动刷新入口（fail-open）：开关关闭则直接跳过，失败不影响主流程。

        并发控制：同一进程内若已有刷新在执行，后来者等待其结束并复用其结果；
        非 force 调用在冷却期内（默认 1 小时）直接跳过。
        """
        # 自动抓取为 opt-in 能力，未开启时静默跳过
        if not getattr(self.config, "news_intel_auto_fetch_enabled", False):
            return {"ok": True, "skipped": True, "reason": "disabled"}

        now = datetime.now()
        cls = type(self)
        with cls._auto_fetch_condition:
            waited_for_in_progress = False
            # 已有刷新在执行：等待其完成，避免并发打上游
            while cls._auto_fetch_in_progress:
                waited_for_in_progress = True
                cls._auto_fetch_condition.wait()
            # 等待结束后直接复用已有结果（前提是结果已就绪）
            if waited_for_in_progress and cls._auto_fetch_last_result is not None:
                return dict(cls._auto_fetch_last_result)
            # 冷却期内且未强制刷新时跳过
            if (
                not force
                and cls._auto_fetch_last_run_at is not None
                and (now - cls._auto_fetch_last_run_at).total_seconds() < _AUTO_FETCH_MIN_INTERVAL_SECONDS
            ):
                return {"ok": True, "skipped": True, "reason": "cooldown"}
            cls._auto_fetch_in_progress = True

        result: Dict[str, Any]
        try:
            # 先引导内置源（补齐并启用），再抓取全部启用源
            bootstrap = self.ensure_default_sources_enabled()
            fetch = self.fetch_enabled_sources()
            result = {
                "ok": True,
                "skipped": False,
                "bootstrap": bootstrap,
                "fetch": fetch,
                "saved_count": int(fetch.get("saved_count") or 0),
            }
            logger.info(
                "Intelligence auto fetch completed: sources=%s saved=%s created=%s enabled=%s errors=%s",
                fetch.get("source_count"),
                result["saved_count"],
                bootstrap.get("created_count"),
                bootstrap.get("enabled_count"),
                bootstrap.get("error_count"),
            )
        except Exception as exc:
            # fail-open：自动抓取失败只记录，不向主流程抛出
            error = self._sanitize_error(exc)
            logger.warning("Intelligence auto fetch failed (fail-open): %s", error)
            result = {"ok": False, "skipped": False, "error": error}
        finally:
            # 无论成败都更新时间戳与结果，并唤醒所有等待中的调用
            with cls._auto_fetch_condition:
                cls._auto_fetch_last_run_at = datetime.now()
                cls._auto_fetch_last_result = dict(result)
                cls._auto_fetch_in_progress = False
                cls._auto_fetch_condition.notify_all()
        return result

    def _normalize_source_fields(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """归一化并校验资讯源输入字段，返回可直接落库的字段字典。

        校验点：名称与 URL 必填、source_type/scope_type/market 必须在白名单内、
        scope_type 为 symbol/sector 时必须提供 scope_value，同时统一做长度截断。
        """
        name = str(payload.get("name") or "").strip()
        url = str(payload.get("url") or "").strip()
        source_type = str(payload.get("source_type") or "rss").strip().lower()
        scope_type = str(payload.get("scope_type") or "market").strip().lower()
        scope_value = str(payload.get("scope_value") or "").strip() or None
        market = str(payload.get("market") or "cn").strip().lower()
        enabled = bool(payload.get("enabled", True))
        description = str(payload.get("description") or "").strip() or None
        if not name:
            raise IntelligenceServiceError("source name is required")
        if not url:
            raise IntelligenceServiceError("source url is required")
        if source_type not in _ALLOWED_SOURCE_TYPES:
            raise IntelligenceServiceError(f"unsupported source_type: {source_type}")
        if scope_type not in _ALLOWED_SCOPE_TYPES:
            raise IntelligenceServiceError(f"unsupported scope_type: {scope_type}")
        if scope_type in {"symbol", "sector"} and not scope_value:
            raise IntelligenceServiceError(f"scope_value is required when scope_type={scope_type}")
        if market not in _ALLOWED_MARKETS:
            raise IntelligenceServiceError(f"unsupported market: {market}")
        return {
            "name": name[:100],
            "source_type": source_type,
            "url": url,
            "enabled": enabled,
            "scope_type": scope_type,
            "scope_value": scope_value[:64] if scope_value else None,
            "market": market,
            "description": description,
        }

    def _validate_url(self, raw_url: str, *, allow_no_url: bool = False) -> None:
        """SSRF 前置校验：只允许指向公网地址的绝对 http(s) URL。

        依次检查：no-url 占位符（可选放行）-> scheme 与 host -> 禁止携带凭据 ->
        禁止本地主机名 -> DNS 解析结果不得落在私网/回环/保留地址段。
        allow_no_url 用于放行无链接条目生成的 `no-url:intel:<hash>` 占位 URL。
        """
        if allow_no_url and raw_url.startswith("no-url:intel:"):
            return
        parsed = urlparse(raw_url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            raise IntelligenceServiceError("source url must be an absolute http(s) URL")
        if parsed.username or parsed.password:
            raise IntelligenceServiceError("source url must not contain credentials")
        hostname = (parsed.hostname or "").strip().lower().rstrip(".")
        if not hostname:
            raise IntelligenceServiceError("source url host is required")
        if hostname in _PRIVATE_HOSTNAMES or hostname.endswith(".local"):
            raise IntelligenceServiceError("source url host is not allowed")
        has_public_address = False
        # 直接以 IP 访问时无需 DNS，直接判段
        try:
            ip = ipaddress.ip_address(hostname)
        except ValueError:
            ip = None
        if ip is not None:
            if self._is_blocked_ip(ip):
                raise IntelligenceServiceError("source url must not target private or local network addresses")
            return
        # 域名形式：解析后逐个地址判段，任一地址命中黑名单即拒绝
        try:
            addr_infos = socket.getaddrinfo(hostname, None)
        except OSError as exc:
            raise IntelligenceServiceError(f"source url host DNS resolution failed: {hostname}") from exc
        if not addr_infos:
            raise IntelligenceServiceError(f"source url host DNS resolution failed: {hostname}")
        for info in addr_infos:
            try:
                ip = ipaddress.ip_address(info[4][0])
            except (IndexError, ValueError):
                continue
            if self._is_blocked_ip(ip):
                raise IntelligenceServiceError("source url must not target private or local network addresses")
            has_public_address = True
        if not has_public_address:
            raise IntelligenceServiceError(f"source url host DNS resolution failed: {hostname}")

    @staticmethod
    def _is_blocked_ip(ip: ipaddress._BaseAddress) -> bool:
        """判断 IP 是否属于禁止访问的地址：非全局单播或私网/回环/链路本地/保留/组播。"""
        return (
            not ip.is_global
            or ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        )

    def _fetch_feed_entries(self, fields: Dict[str, Any], *, limit: int) -> List[FeedEntry]:
        """按数据源类型分发抓取逻辑，统一返回解析后的条目列表。

        RSS/Atom 走手动跟随重定向的流式读取；NewsNow 走 JSON 接口。
        所有非业务异常最终都会收敛为统一的“上游请求失败”文案，避免泄漏内部细节。
        """
        if fields["source_type"] == "newsnow":
            return self._fetch_newsnow_entries(fields, limit=limit)

        # 超时限制在 1~30 秒，避免配置异常导致无限等待
        timeout = max(1, min(float(self.config.news_intel_fetch_timeout_sec), 30.0))
        headers = {"User-Agent": "hermesx-intel/1.0"}
        self._validate_url(fields["url"])
        request_url = fields["url"]
        response = None
        try:
            # 手动跟随重定向：每一跳都要重新做 SSRF 校验，防止跳转到内网地址
            for _ in range(_MAX_FEED_REDIRECTS + 1):
                response = self._get_with_validated_dns(
                    request_url,
                    timeout=timeout,
                    headers=headers,
                    allow_redirects=False,
                    stream=True,
                )
                status_code = int(getattr(response, "status_code", 200))
                if status_code in _REDIRECT_STATUS_CODES:
                    location = getattr(response, "headers", {}).get("Location")
                    if not location:
                        raise IntelligenceServiceError("feed redirect missing Location header")
                    response.close()
                    request_url = urljoin(request_url, location)
                    self._validate_url(request_url)
                    continue
                response.raise_for_status()
                break
            else:
                raise IntelligenceServiceError(f"feed redirect chain exceeds {_MAX_FEED_REDIRECTS}")

            # 对最终落地 URL 再校验一次，覆盖库层面可能的额外跳转
            self._validate_url(response.url or request_url)

            # 流式读取并限制总体积，避免超大响应耗尽内存
            if hasattr(response, "iter_content") and callable(response.iter_content):
                chunks = []
                total = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > _MAX_FEED_BYTES:
                        raise IntelligenceServiceError("feed response is too large")
                    chunks.append(chunk)
                content = b"".join(chunks)
            else:
                # 非流式响应（如测试中的替身对象）退化为按字节上限截断
                content = response.content[: _MAX_FEED_BYTES + 1]
                if len(content) > _MAX_FEED_BYTES:
                    raise IntelligenceServiceError("feed response is too large")
            return self._parse_feed(content, source_name=fields["name"], limit=limit)
        except IntelligenceServiceError:
            raise
        except Exception as exc:
            raise IntelligenceServiceError(_UPSTREAM_FETCH_FAILURE_MESSAGE) from exc
        finally:
            if response is not None:
                response.close()

    def _fetch_newsnow_entries(self, fields: Dict[str, Any], *, limit: int) -> List[FeedEntry]:
        """抓取 NewsNow JSON 接口并解析条目。

        与 RSS 分支的差异：使用浏览器 UA 以适配站点反爬；不跟随重定向（直接判失败），
        避免被跳转到未校验的地址。
        """
        timeout = max(1, min(float(self.config.news_intel_fetch_timeout_sec), 30.0))
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 hermesx-intel/1.0"
            ),
            "Accept": "application/json",
        }
        self._validate_url(fields["url"])
        response = None
        try:
            response = self._get_with_validated_dns(
                fields["url"],
                timeout=timeout,
                headers=headers,
                allow_redirects=False,
                stream=True,
            )
            status_code = int(getattr(response, "status_code", 200))
            if status_code in _REDIRECT_STATUS_CODES:
                raise IntelligenceServiceError("NewsNow API redirects are not followed")
            response.raise_for_status()
            self._validate_url(response.url or fields["url"])

            # 与 RSS 分支共用体积限制的读取逻辑
            content = self._read_limited_response(response)
            try:
                payload = json.loads(content.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise IntelligenceServiceError(f"invalid NewsNow JSON response: {exc}") from exc
            return self._parse_newsnow_payload(payload, source_name=fields["name"], limit=limit)
        except IntelligenceServiceError:
            raise
        except Exception as exc:
            raise IntelligenceServiceError(_UPSTREAM_FETCH_FAILURE_MESSAGE) from exc
        finally:
            if response is not None:
                response.close()

    def _read_limited_response(self, response: requests.Response) -> bytes:
        """带体积上限地读取响应体：优先流式读取，否则退化为截断 content。"""
        if hasattr(response, "iter_content") and callable(response.iter_content):
            chunks = []
            total = 0
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                total += len(chunk)
                if total > _MAX_FEED_BYTES:
                    raise IntelligenceServiceError("feed response is too large")
                chunks.append(chunk)
            return b"".join(chunks)
        content = response.content[: _MAX_FEED_BYTES + 1]
        if len(content) > _MAX_FEED_BYTES:
            raise IntelligenceServiceError("feed response is too large")
        return content

    def _get_with_validated_dns(self, raw_url: str, **kwargs: Any) -> requests.Response:
        """发起带 DNS 复检的 GET 请求，防止 DNS rebinding 绕过前置校验。

        做法：临时替换 socket.getaddrinfo，仅对目标主机名重新校验解析结果；
        替换过程由全局锁串行化，并在 finally 中恢复，避免污染其他请求。
        """
        parsed = urlparse(raw_url)
        target_hostname = self._normalize_hostname(parsed.hostname)
        original_getaddrinfo = socket.getaddrinfo

        def guarded_getaddrinfo(host: Any, port: Any, *args: Any, **inner_kwargs: Any) -> Any:
            addrinfos = original_getaddrinfo(host, port, *args, **inner_kwargs)
            # 只校验目标主机，避免影响无关域名（如系统内部解析）
            if self._normalize_hostname(host) == target_hostname:
                self._validate_addrinfos(addrinfos)
            return addrinfos

        with _DNS_GUARD_LOCK:
            socket.getaddrinfo = guarded_getaddrinfo
            try:
                request_kwargs = dict(kwargs)
                # 禁用系统代理，防止代理侧绕过 SSRF 判定
                request_kwargs.setdefault("proxies", _DISABLE_REQUEST_PROXIES)
                return requests.get(raw_url, **request_kwargs)
            finally:
                socket.getaddrinfo = original_getaddrinfo

    @staticmethod
    def _normalize_hostname(hostname: Any) -> str:
        """统一主机名为小写、去尾点、转 IDNA ASCII 的形式，便于一致比较。"""
        if isinstance(hostname, bytes):
            hostname = hostname.decode("ascii", errors="ignore")
        normalized = str(hostname or "").strip().lower().rstrip(".")
        try:
            return normalized.encode("idna").decode("ascii")
        except UnicodeError:
            return normalized

    @staticmethod
    def _validate_addrinfos(addr_infos: Any) -> None:
        """校验一批 getaddrinfo 结果，只要命中黑名单地址即拒绝。"""
        for info in addr_infos or []:
            try:
                ip = ipaddress.ip_address(info[4][0])
            except (IndexError, TypeError, ValueError):
                continue
            if IntelligenceService._is_blocked_ip(ip):
                raise IntelligenceServiceError("source url must not target private or local network addresses")

    def _parse_feed(self, content: bytes, *, source_name: str, limit: int) -> List[FeedEntry]:
        """解析 RSS / Atom XML，按根节点类型分发到对应解析器并截断到 limit 条。"""
        try:
            root = ET.fromstring(content)
        except ET.ParseError as exc:
            raise IntelligenceServiceError(f"invalid RSS/Atom feed: {exc}") from exc
        tag = self._strip_ns(root.tag).lower()
        if tag == "rss":
            nodes = root.findall("./channel/item")
            return [entry for entry in (self._parse_rss_item(node, source_name) for node in nodes[:limit]) if entry]
        if tag == "feed":
            nodes = root.findall("./{*}entry") or root.findall("./entry")
            return [entry for entry in (self._parse_atom_entry(node, source_name) for node in nodes[:limit]) if entry]
        raise IntelligenceServiceError("unsupported feed format; expected RSS or Atom")

    def _parse_newsnow_payload(self, payload: Any, *, source_name: str, limit: int) -> List[FeedEntry]:
        """解析 NewsNow 响应：要求形如 {"items": [{title, url, extra{info/hover/date}, pubDate}]}。"""
        if not isinstance(payload, dict):
            raise IntelligenceServiceError("invalid NewsNow response: expected object")
        items = payload.get("items")
        if not isinstance(items, list):
            raise IntelligenceServiceError("invalid NewsNow response: missing items")
        entries = []
        for item in items[:limit]:
            if not isinstance(item, dict):
                continue
            # 摘要优先取 extra.info，其次 extra.hover；链接优先 url，其次 mobileUrl
            extra = item.get("extra") if isinstance(item.get("extra"), dict) else {}
            published_raw = item.get("pubDate") or extra.get("date")
            entries.append(self._build_entry(
                str(item.get("title") or ""),
                str(extra.get("info") or extra.get("hover") or ""),
                str(item.get("url") or item.get("mobileUrl") or ""),
                source_name,
                self._parse_datetime_or_timestamp(published_raw),
            ))
        return [entry for entry in entries if entry]

    def _parse_rss_item(self, node: ET.Element, source_name: str) -> Optional[FeedEntry]:
        """解析单个 RSS <item>：标题、description、link、pubDate/published。"""
        return self._build_entry(
            self._text(node, "title"),
            self._text(node, "description") or self._text(node, "summary"),
            self._text(node, "link"),
            source_name,
            self._parse_datetime(self._text(node, "pubDate") or self._text(node, "published")),
        )

    def _parse_atom_entry(self, node: ET.Element, source_name: str) -> Optional[FeedEntry]:
        """解析单个 Atom <entry>：链接取 rel=alternate 的 href，时间取 published/updated。"""
        url = ""
        for link in node.findall("./{*}link") or node.findall("./link"):
            if (link.attrib.get("rel") or "alternate").lower() == "alternate" and link.attrib.get("href"):
                url = link.attrib["href"].strip()
                break
        return self._build_entry(
            self._text(node, "title"),
            self._text(node, "summary") or self._text(node, "content"),
            url,
            source_name,
            self._parse_datetime(self._text(node, "published") or self._text(node, "updated")),
        )

    def _build_entry(self, title: str, summary: str, url: str, source_name: str, published_at: Optional[datetime]) -> Optional[FeedEntry]:
        """构造 FeedEntry：清洗文本、截断长度，并为条目生成稳定的去重键。

        有链接时用链接作为去重键（同时校验其合法性，非法直接丢弃该条目）；
        无链接时用 来源+标题+发布时间 的哈希生成 `no-url:intel:<hash>` 占位键，
        保证 upsert 仍能去重。
        """
        title = self._clean_text(title)[:300]
        summary = self._clean_text(summary)[:2000]
        url = url.strip()
        if not title and not url:
            return None
        if url:
            try:
                self._validate_url(url, allow_no_url=True)
            except IntelligenceServiceError:
                return None
            url_key = url
        else:
            digest = hashlib.sha256(f"{source_name}|{title}|{published_at}".encode("utf-8")).hexdigest()[:24]
            url_key = f"no-url:intel:{digest}"
        return FeedEntry(title or url_key, summary, url_key, source_name, published_at, {"source": source_name})

    def _entry_to_item_fields(self, entry: FeedEntry, source: IntelligenceSource, now: datetime) -> Dict[str, Any]:
        """把 FeedEntry 转成待入库字段：作用域与市场信息继承自所属资讯源。"""
        return {
            "source_id": source.id,
            "source_name": source.name,
            "source_type": source.source_type,
            "title": entry.title,
            "summary": entry.summary,
            "url": entry.url,
            "source": entry.source,
            "published_at": entry.published_at,
            "fetched_at": now,
            "scope_type": source.scope_type,
            "scope_value": source.scope_value,
            "market": source.market,
            "raw_payload": json.dumps(entry.raw_payload, ensure_ascii=False),
        }

    @staticmethod
    def _source_to_fields(source: IntelligenceSource) -> Dict[str, Any]:
        """ORM 对象 -> 抓取所需字段（与 _normalize_source_fields 的输出结构一致）。"""
        return {
            "name": source.name,
            "source_type": source.source_type,
            "url": source.url,
            "enabled": source.enabled,
            "scope_type": source.scope_type,
            "scope_value": source.scope_value,
            "market": source.market,
            "description": source.description,
        }

    @staticmethod
    def _source_to_dict(source: IntelligenceSource) -> Dict[str, Any]:
        """ORM 对象 -> API 输出字典（含状态与时间字段，时间统一转 ISO 字符串）。"""
        return {
            "id": source.id,
            "name": source.name,
            "source_type": source.source_type,
            "url": source.url,
            "enabled": bool(source.enabled),
            "scope_type": source.scope_type,
            "scope_value": source.scope_value,
            "market": source.market,
            "description": source.description,
            "last_status": source.last_status,
            "last_error": source.last_error,
            "last_fetched_at": IntelligenceService._iso(source.last_fetched_at),
            "created_at": IntelligenceService._iso(source.created_at),
            "updated_at": IntelligenceService._iso(source.updated_at),
        }

    @staticmethod
    def _item_to_dict(item: Any) -> Dict[str, Any]:
        """资讯条目 ORM -> API 输出字典。

        市场对作用域使用哨兵值入库（便于唯一约束），对外输出时需还原为 None。
        """
        return {
            "id": item.id,
            "source_id": item.source_id,
            "source_name": item.source_name,
            "source_type": item.source_type,
            "title": item.title,
            "summary": item.summary,
            "url": item.url,
            "source": item.source,
            "published_at": IntelligenceService._iso(item.published_at),
            "fetched_at": IntelligenceService._iso(item.fetched_at),
            "scope_type": item.scope_type,
            "scope_value": None if (
                item.scope_type == "market" and item.scope_value == INTELLIGENCE_ITEM_NULL_SCOPE_VALUE
            ) else item.scope_value,
            "market": item.market,
        }

    @staticmethod
    def _feed_entry_to_dict(entry: FeedEntry) -> Dict[str, Any]:
        """FeedEntry -> 测试/预览用的轻量输出字典（不含入库字段）。"""
        return {
            "title": entry.title,
            "summary": entry.summary,
            "url": entry.url,
            "source": entry.source,
            "published_at": IntelligenceService._iso(entry.published_at),
        }

    @staticmethod
    def _redact_source_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
        """剔除敏感字段后再回显资讯源配置（如自定义请求头、令牌、API Key）。"""
        return {k: v for k, v in fields.items() if k not in {"headers", "token", "api_key"}}

    @staticmethod
    def _sanitize_error(exc: Exception) -> str:
        """错误文案脱敏并截断，失败时回退为统一的内部错误提示。"""
        return sanitize_diagnostic_text(str(exc), max_length=500) or "internal intelligence service error"

    @staticmethod
    def _strip_ns(tag: str) -> str:
        """去掉 XML 标签的命名空间前缀，只保留本地标签名。"""
        return tag.rsplit("}", 1)[-1] if "}" in tag else tag

    @classmethod
    def _text(cls, node: ET.Element, name: str) -> str:
        """读取子节点文本：先按任意命名空间匹配，再退回无命名空间匹配。"""
        found = node.find(f"./{{*}}{name}")
        if found is None:
            found = node.find(f"./{name}")
        return "" if found is None or found.text is None else found.text.strip()

    @staticmethod
    def _clean_text(value: str) -> str:
        """清洗文本：先剥离 HTML 标签，再折叠空白字符。"""
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value or "")).strip()

    @staticmethod
    def _parse_datetime(value: str) -> Optional[datetime]:
        """解析时间字符串：优先 RFC 2822（RSS pubDate），其次 ISO 8601；统一转 UTC naive。"""
        raw = (value or "").strip()
        if not raw:
            return None
        try:
            parsed = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            try:
                parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                return None
        if parsed.tzinfo is not None and parsed.utcoffset() is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed

    @classmethod
    def _parse_datetime_or_timestamp(cls, value: Any) -> Optional[datetime]:
        """解析时间：支持秒/毫秒时间戳与常见字符串格式（NewsNow 的 pubDate 两种都有）。"""
        if isinstance(value, (int, float)):
            timestamp = float(value)
            # 超过该阈值视为毫秒时间戳，统一换算成秒
            if timestamp > 10_000_000_000:
                timestamp = timestamp / 1000
            try:
                return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(tzinfo=None)
            except (OSError, OverflowError, ValueError):
                return None
        raw = str(value or "").strip()
        if raw.isdigit():
            return cls._parse_datetime_or_timestamp(float(raw))
        return cls._parse_datetime(raw)

    def _builtin_source_templates(self) -> List[Dict[str, Any]]:
        """返回完整内置模板列表：RSS/Atom 模板 + 由 NewsNow 定义动态生成的模板。"""
        templates = [dict(template) for template in _BUILTIN_SOURCE_TEMPLATES]
        for item in _NEWSNOW_DEFAULT_SOURCE_DEFS:
            templates.append({
                "template_id": item["template_id"],
                "name": item["name"],
                "source_type": "newsnow",
                "url": self._build_newsnow_url(item["source_id"]),
                "scope_type": "market",
                "market": item["market"],
                "description": item["description"],
            })
        return templates

    def _build_newsnow_url(self, source_id: str) -> str:
        """拼装 NewsNow 资讯源 URL：`<newsnow_base_url>/api/s?id=<source_id>`。

        保留 base URL 上已有的查询参数，仅覆盖 id，便于自建实例携带额外参数。
        """
        base_url = (self.config.newsnow_base_url or "https://newsnow.busiyi.world").strip().rstrip("/")
        parsed = urlparse(f"{base_url}/api/s")
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query["id"] = source_id
        return urlunparse(parsed._replace(query=urlencode(query)))

    @staticmethod
    def _iso(value: Optional[datetime]) -> Optional[str]:
        """datetime -> ISO 字符串，None 原样返回。"""
        return value.isoformat() if value else None
