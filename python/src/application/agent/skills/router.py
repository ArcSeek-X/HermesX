# -*- coding: utf-8 -*-
"""
SkillRouter — rule-based skill selection.

Selects which trading skills to apply based on:
1. User-explicit request (highest priority)
2. Market regime detection from technical data in ``AgentContext``
3. Centralised default fallback

SkillRouter —— 基于规则的技能选择。按优先级决定应用哪些交易技能：
① 用户显式请求（最高）；② 由技术数据检测市场状态（regime）；③ 集中式默认回退。
"""

from __future__ import annotations

import logging
from typing import List, Optional

from src.application.agent.protocols import AgentContext
from src.application.agent.skills.defaults import (
    get_default_router_skill_ids,
    get_regime_skill_ids,
)

logger = logging.getLogger(__name__)


class SkillRouter:
    """Select applicable skills for a given analysis context."""

    def select_skills(
        self,
        ctx: AgentContext,
        max_count: int = 3,
    ) -> List[str]:
        """为给定分析上下文选择适用技能：优先用户请求，其次 manual 模式、regime 检测，最后默认回退，结果按 max_count 截断。"""
        requested_skills = ctx.meta.get("skills_requested") or ctx.meta.get("strategies_requested", [])
        if requested_skills:
            logger.info("[SkillRouter] user-requested skills: %s", requested_skills)
            return requested_skills[:max_count]

        routing_mode = self._get_routing_mode()
        if routing_mode == "manual":
            selected = self._get_manual_skills(max_count=max_count)
            logger.info("[SkillRouter] manual mode — using skills: %s", selected)
            return selected

        available_skills = self.get_available_skills()
        skill_catalog = available_skills or None
        available_ids = {skill.name for skill in available_skills}
        regime = self._detect_regime(ctx)
        if regime:
            selected = get_regime_skill_ids(
                regime,
                skill_catalog,
                max_count=max_count,
                available_skill_ids=available_ids or None,
            )
            if selected:
                logger.info("[SkillRouter] regime=%s -> skills: %s", regime, selected)
                return selected

        default_skills = get_default_router_skill_ids(
            skill_catalog,
            max_count=max_count,
            available_skill_ids=available_ids or None,
        )
        logger.info("[SkillRouter] using default skills: %s", default_skills)
        return default_skills

    def select_strategies(
        self,
        ctx: AgentContext,
        max_count: int = 3,
    ) -> List[str]:
        """Compatibility wrapper for legacy strategy-based callers."""
        return self.select_skills(ctx, max_count=max_count)

    def _detect_regime(self, ctx: AgentContext) -> Optional[str]:
        """根据技术面意见（均线对齐、趋势分、量能）与行业热度推断市场状态（trending_up/down/sideways/volatile/sector_hot），无匹配返回 None。"""
        for op in ctx.opinions:
            if op.agent_name != "technical":
                continue
            raw = op.raw_data or {}

            ma_alignment = str(raw.get("ma_alignment", "")).lower()
            try:
                trend_score = float(raw.get("trend_score", 50))
            except (TypeError, ValueError):
                trend_score = 50.0
            volume_status = str(raw.get("volume_status", "")).lower()

            if ma_alignment == "bullish" and trend_score >= 70:
                return "trending_up"
            if ma_alignment == "bearish" and trend_score <= 30:
                return "trending_down"
            if ma_alignment == "neutral" or 35 <= trend_score <= 65:
                return "sideways"
            if volume_status == "heavy" and 30 < trend_score < 70:
                return "volatile"

        if ctx.meta.get("sector_hot"):
            return "sector_hot"
        return None

    @staticmethod
    def _get_routing_mode() -> str:
        """读取配置项 agent_skill_routing（默认 'auto'）；读取失败回退 auto。"""
        try:
            from src.config import get_config

            config = get_config()
            return getattr(config, "agent_skill_routing", "auto")
        except Exception:
            logger.warning("Failed to get routing mode, falling back to auto", exc_info=True)
            return "auto"

    @staticmethod
    def _get_available_ids() -> set:
        """返回当前可用技能的 name 集合。"""
        return {skill.name for skill in SkillRouter.get_available_skills()}

    @staticmethod
    def get_available_skills() -> list:
        """获取可用技能列表：优先用 _SKILL_MANAGER_PROTOTYPE，否则取 get_skill_manager；异常时返回空列表。"""
        try:
            from src.application.agent.factory import _SKILL_MANAGER_PROTOTYPE

            if _SKILL_MANAGER_PROTOTYPE is not None:
                return list(_SKILL_MANAGER_PROTOTYPE.list_skills())

            from src.application.agent.factory import get_skill_manager

            sm = get_skill_manager()
            return list(sm.list_skills())
        except Exception:
            logger.warning("Failed to get available skills", exc_info=True)
            return []

    @classmethod
    def _get_manual_skills(cls, max_count: int) -> List[str]:
        """manual 路由模式：读取配置 agent_skills，过滤出可用项并按 max_count 截断；为空则回退默认技能。"""
        configured: List[str] = []
        try:
            from src.config import get_config

            config = get_config()
            configured = [
                skill_id
                for skill_id in getattr(config, "agent_skills", []) or []
                if isinstance(skill_id, str) and skill_id
            ]
        except Exception:
            logger.warning("Failed to get manual skills config", exc_info=True)
            configured = []

        available_skills = cls.get_available_skills()
        skill_catalog = available_skills or None
        available = {skill.name for skill in available_skills}
        selected = [skill_id for skill_id in configured if skill_id in available][:max_count]
        if selected:
            return selected

        return get_default_router_skill_ids(
            skill_catalog,
            max_count=max_count,
            available_skill_ids=available or None,
        )


StrategyRouter = SkillRouter
_DEFAULT_STRATEGIES = tuple(get_default_router_skill_ids())
_DEFAULT_SKILLS = _DEFAULT_STRATEGIES
