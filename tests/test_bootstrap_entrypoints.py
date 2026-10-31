# -*- coding: utf-8 -*-
"""Entry-point import smoke tests.

Importing an entry point must not start the runtime scheduler, must not run the
FastAPI lifespan and must keep a single lifespan implementation shared by
``server.py``, ``webui.py`` and ``main.py``.

Each case runs in a fresh subprocess because module-level bootstrap runs exactly
once per process and cannot be re-observed in-process.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

_MAIN_WEBUI_SCRIPT = textwrap.dedent(
    """
    import threading

    import main
    import webui

    from src.storage import DatabaseManager

    assert DatabaseManager._instance is None, (
        "importing main/webui must not create the database manager"
    )
    assert main.StockAnalysisPipeline.__name__ == "StockAnalysisPipeline"
    assert callable(webui.main)

    threads = [t.name for t in threading.enumerate() if t is not threading.main_thread()]
    assert not threads, f"entry-point import leaked background threads: {threads}"

    print("OK")
    """
)

_SERVER_SCRIPT = textwrap.dedent(
    """
    import threading

    import api.app
    import server

    from src.bootstrap import api_lifecycle
    from src.storage import DatabaseManager

    assert DatabaseManager._instance is None, (
        "importing api.app/server must not create the database manager"
    )
    assert server.app is api.app.app, "server.app must be the ASGI app object"
    assert server.__all__ == ["app"]
    assert api.app.app_lifespan is api_lifecycle.app_lifespan, (
        "api.app must reuse the bootstrap lifespan instead of defining its own"
    )
    assert getattr(api.app.app.router, "lifespan_context", None) is not None
    assert not hasattr(api.app.app.state, "runtime_scheduler_service"), (
        "the lifespan must not run at import time"
    )

    threads = [t.name for t in threading.enumerate() if t is not threading.main_thread()]
    assert not threads, f"entry-point import leaked background threads: {threads}"

    print("OK")
    """
)

_COMBINED_SCRIPT = textwrap.dedent(
    """
    import api.app
    import main
    import server
    import webui

    from src.storage import DatabaseManager

    assert DatabaseManager._instance is None, (
        "importing an entry point must not create the database manager"
    )
    assert server.app is api.app.app
    assert main.StockAnalysisPipeline is not None
    assert callable(webui.main)

    print("OK")
    """
)


class EntryPointImportTestCase(unittest.TestCase):
    def _run_python(self, script: str) -> str:
        env = dict(os.environ)
        env.setdefault("PYTHONPATH", str(REPO_ROOT))
        env.pop("HRS_PACKAGED_IMPORT_PROBE", None)
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
        )
        self.assertEqual(
            completed.returncode,
            0,
            msg=f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr[-4000:]}",
        )
        self.assertIn("OK", completed.stdout)
        return completed.stdout

    def test_main_and_webui_import_is_side_effect_free(self) -> None:
        self._run_python(_MAIN_WEBUI_SCRIPT)

    def test_server_import_attaches_lifespan_without_starting_it(self) -> None:
        self._run_python(_SERVER_SCRIPT)

    def test_all_entry_points_share_one_asgi_app(self) -> None:
        self._run_python(_COMBINED_SCRIPT)


if __name__ == "__main__":
    unittest.main()
