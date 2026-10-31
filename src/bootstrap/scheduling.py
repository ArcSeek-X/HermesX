# -*- coding: utf-8 -*-
"""Translate CLI serve/schedule flags into runtime scheduler environment.

The API process (and the WebUI/Desktop launch mode) owns scheduled analysis.
``main.py`` describes the CLI intent through the ``HRS_RUNTIME_SCHEDULER_*``
environment variables so that the FastAPI lifespan, which runs in the same
process, can pick it up without importing CLI state.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

from src.application.runtime.runtime_scheduler import (
    CLI_SCHEDULER_OWNER_ENV,
    RUNTIME_SCHEDULER_ARGS_ENV,
    RUNTIME_SCHEDULER_FORCE_ENABLED_ENV,
    RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV,
    RUNTIME_SCHEDULER_SUPPRESS_START_ENV,
)

logger = logging.getLogger(__name__)


def configure_runtime_scheduler_env(args: Any, config: Any) -> Dict[str, Any]:
    """Describe the runtime scheduler intent for the in-process API lifespan.

    Returns the schedule argument overrides that were serialized into
    ``HRS_RUNTIME_SCHEDULER_ARGS``. Existing keys are always cleared first so a
    stale value from a previous launch cannot leak into this process.
    """
    os.environ.pop(CLI_SCHEDULER_OWNER_ENV, None)

    if getattr(args, "serve_only", False):
        os.environ[RUNTIME_SCHEDULER_SUPPRESS_START_ENV] = "true"
    else:
        os.environ.pop(RUNTIME_SCHEDULER_SUPPRESS_START_ENV, None)

    runtime_schedule_requested = not getattr(args, "serve_only", False) and (
        getattr(args, "schedule", False) or getattr(config, "schedule_enabled", False)
    )

    if not getattr(args, "serve_only", False) and getattr(args, "schedule", False):
        os.environ[RUNTIME_SCHEDULER_FORCE_ENABLED_ENV] = "true"
    else:
        os.environ.pop(RUNTIME_SCHEDULER_FORCE_ENABLED_ENV, None)

    if runtime_schedule_requested:
        runtime_run_immediately = bool(getattr(config, "schedule_run_immediately", False))
        if getattr(args, "no_run_immediately", False):
            runtime_run_immediately = False
        os.environ[RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV] = (
            "true" if runtime_run_immediately else "false"
        )
    else:
        os.environ.pop(RUNTIME_SCHEDULER_RUN_IMMEDIATELY_ENV, None)

    runtime_scheduler_args: Dict[str, Any] = {
        "no_notify": bool(getattr(args, "no_notify", False)),
        "no_market_review": bool(getattr(args, "no_market_review", False)),
        "dry_run": bool(getattr(args, "dry_run", False)),
        "force_run": bool(getattr(args, "force_run", False)),
        "single_notify": bool(getattr(args, "single_notify", False)),
        "no_context_snapshot": bool(getattr(args, "no_context_snapshot", False)),
        "workers": getattr(args, "workers", None),
    }
    if getattr(args, "portfolio", None):
        runtime_scheduler_args["portfolio"] = args.portfolio
    os.environ[RUNTIME_SCHEDULER_ARGS_ENV] = json.dumps(runtime_scheduler_args)
    return runtime_scheduler_args
