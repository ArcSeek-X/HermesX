"""Explicit roots for Python tests and repository-level tooling."""

from pathlib import Path


def get_python_root() -> Path:
    """Return the directory containing the Python entrypoints and test config."""
    return Path(__file__).resolve().parents[2]


def get_repo_root() -> Path:
    """Return the checkout containing apps, workflows and scripts."""
    return get_python_root().parent
