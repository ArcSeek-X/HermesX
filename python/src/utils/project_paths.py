"""Locations shared by the checkout, container and frozen Python backend."""

import os
import sys
from pathlib import Path

PYTHON_ROOT = Path(__file__).resolve().parents[2]
# In an image the Python sources are copied to /app, not nested under python/.
REPOSITORY_ROOT = (
    PYTHON_ROOT.parent
    if PYTHON_ROOT.name == "python" and (PYTHON_ROOT.parent / "apps").is_dir()
    else PYTHON_ROOT
)


def runtime_path(value: str | Path) -> Path:
    """Resolve relative runtime settings outside the relocated source tree."""
    path = Path(value).expanduser()
    root = Path.cwd() if getattr(sys, "frozen", False) else REPOSITORY_ROOT
    return root / path


def env_file_path() -> Path:
    return runtime_path(os.getenv("ENV_FILE") or ".env")


def static_assets_path() -> Path:
    override = os.getenv("HRS_STATIC_DIR")
    return runtime_path(override) if override else REPOSITORY_ROOT / "dist-web"
