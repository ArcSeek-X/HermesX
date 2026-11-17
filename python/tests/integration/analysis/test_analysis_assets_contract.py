"""Tests for analysis assets contract."""

from tests.integration.analysis._analysis_api_contract_support import (
    Path,
    _AnalysisApiContractTestCaseFixture,
    asyncio,
    create_app,
    json,
    tempfile,
    unittest,
)


class AnalysisApiContractTestCase(_AnalysisApiContractTestCaseFixture, unittest.TestCase):
    def test_spa_fallback_returns_json_404_for_bare_api_path(self) -> None:
        if create_app is None:
            self.skipTest("fastapi is not installed in this test environment")

        with tempfile.TemporaryDirectory() as temp_dir:
            static_dir = Path(temp_dir)
            (static_dir / "index.html").write_text("<html>spa</html>", encoding="utf-8")
            app = create_app(static_dir=static_dir)

            serve_spa = next(
                route.endpoint for route in app.routes
                if getattr(route, "path", None) == "/{full_path:path}"
            )

            response = asyncio.run(serve_spa(None, "api"))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            json.loads(response.body),
            {"error": "not_found", "message": "API endpoint /api not found"},
        )

    def test_spa_fallback_blocks_path_traversal(self) -> None:
        """SPA fallback must not serve files outside static_dir.

        Starlette's :path converter does not normalize `..` segments, so
        without an explicit containment check `static_dir / full_path` can
        resolve to arbitrary files on disk (CVE-class path traversal).
        """
        if create_app is None:
            self.skipTest("fastapi is not installed in this test environment")

        from fastapi.responses import FileResponse

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            static_dir = root / "static"
            static_dir.mkdir()
            (static_dir / "index.html").write_text("<html>spa</html>", encoding="utf-8")
            secret = root / "secret.txt"
            secret.write_text("TOPSECRET", encoding="utf-8")

            app = create_app(static_dir=static_dir)
            serve_spa = next(
                route.endpoint for route in app.routes
                if getattr(route, "path", None) == "/{full_path:path}"
            )

            for traversal in ("../secret.txt", "../../secret.txt", "foo/../../secret.txt"):
                with self.subTest(traversal=traversal):
                    response = asyncio.run(serve_spa(None, traversal))
                    self.assertIsInstance(response, FileResponse)
                    self.assertEqual(Path(response.path).resolve(), (static_dir / "index.html").resolve())
