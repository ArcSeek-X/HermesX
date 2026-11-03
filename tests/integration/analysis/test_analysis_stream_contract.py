"""Tests for analysis stream contract."""

from tests.integration.analysis._analysis_api_contract_support import (
    MagicMock,
    _AnalysisApiContractTestCaseFixture,
    asyncio,
    patch,
    unittest,
)


class AnalysisApiContractTestCase(_AnalysisApiContractTestCaseFixture, unittest.TestCase):
    def test_sse_generator_reraises_cancelled_error(self) -> None:
        """CancelledError must propagate (not be swallowed) from the SSE event generator."""
        try:
            from api.v1.endpoints.analysis import task_stream
        except Exception:  # pragma: no cover - optional dependency environments
            self.skipTest("api.v1.endpoints.analysis not importable")

        class _NeverQueue:
            """Queue that never returns from get(), used to exercise cancellation."""
            async def get(self):
                await asyncio.sleep(3600)

        never_queue = _NeverQueue()
        mock_task_queue = MagicMock()
        mock_task_queue.list_pending_tasks.return_value = []

        async def run():
            with patch("api.v1.endpoints.analysis.get_task_queue", return_value=mock_task_queue), \
                 patch("asyncio.Queue", return_value=never_queue):
                response = await task_stream()
                gen = response.body_iterator

                async def consume():
                    async for _ in gen:
                        pass

                task = asyncio.create_task(consume())
                await asyncio.sleep(0)  # let generator start and reach wait_for
                task.cancel()
                await task  # should re-raise CancelledError

        with self.assertRaises(asyncio.CancelledError):
            asyncio.run(run())

        mock_task_queue.unsubscribe.assert_called_once_with(never_queue)
