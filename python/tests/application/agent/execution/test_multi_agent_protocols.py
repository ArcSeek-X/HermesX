"""Tests for multi agent protocols."""

from tests.application.agent._multi_agent_support import (
    AgentContext,
    AgentOpinion,
    AgentRunStats,
    Signal,
    StageResult,
    StageStatus,
    _TestAgentContextFixture,
    _TestAgentOpinionFixture,
    _TestAgentRunStatsFixture,
    unittest,
)


class TestAgentContext(_TestAgentContextFixture, unittest.TestCase):
    def test_add_opinion(self):
        ctx = AgentContext(query="test", stock_code="600519")
        op = AgentOpinion(agent_name="tech", signal="buy", confidence=0.8)
        ctx.add_opinion(op)
        self.assertEqual(len(ctx.opinions), 1)
        self.assertGreater(op.timestamp, 0)

    def test_add_risk_flag(self):
        ctx = AgentContext()
        ctx.add_risk_flag("insider", "major sell-down", severity="high")
        self.assertTrue(ctx.has_risk_flags)
        self.assertEqual(ctx.risk_flags[0]["severity"], "high")

    def test_set_get_data(self):
        ctx = AgentContext()
        ctx.set_data("foo", {"bar": 1})
        self.assertEqual(ctx.get_data("foo"), {"bar": 1})
        self.assertIsNone(ctx.get_data("missing"))
        self.assertEqual(ctx.get_data("missing", "default"), "default")


class TestAgentOpinion(_TestAgentOpinionFixture, unittest.TestCase):
    def test_confidence_clamp_high(self):
        op = AgentOpinion(confidence=1.5)
        self.assertEqual(op.confidence, 1.0)

    def test_confidence_clamp_low(self):
        op = AgentOpinion(confidence=-0.3)
        self.assertEqual(op.confidence, 0.0)

    def test_signal_enum_valid(self):
        op = AgentOpinion(signal="buy")
        self.assertEqual(op.signal_enum, Signal.BUY)

    def test_signal_enum_invalid(self):
        op = AgentOpinion(signal="maybe")
        self.assertIsNone(op.signal_enum)


class TestAgentRunStats(_TestAgentRunStatsFixture, unittest.TestCase):
    def test_record_stage(self):
        stats = AgentRunStats()
        r1 = StageResult(
            stage_name="tech", status=StageStatus.COMPLETED,
            tokens_used=100, tool_calls_count=3, duration_s=1.2,
        )
        r2 = StageResult(
            stage_name="intel", status=StageStatus.FAILED,
            tokens_used=50, tool_calls_count=1, duration_s=0.8,
        )
        stats.record_stage(r1)
        stats.record_stage(r2)

        self.assertEqual(stats.total_stages, 2)
        self.assertEqual(stats.completed_stages, 1)
        self.assertEqual(stats.failed_stages, 1)
        self.assertEqual(stats.total_tokens, 150)
        self.assertEqual(stats.total_tool_calls, 4)

    def test_to_dict(self):
        stats = AgentRunStats()
        d = stats.to_dict()
        self.assertIn("total_stages", d)
        self.assertIn("models_used", d)
