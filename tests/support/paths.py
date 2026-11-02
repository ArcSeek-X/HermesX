# -*- coding: utf-8 -*-
"""仓库根路径统一辅助。

以仓库根的稳定标志物（``setup.cfg``、``pyproject.toml``、``main.py`` 同时存在）
自本文件向上回溯定位仓库根，替代各测试里 ``Path(__file__).resolve().parents[N]``
这种与文件深度耦合的硬编码——测试文件被移动到不同层级目录后无需逐点调整 ``parents``
索引，从根本上消除搬迁导致的路径推导漂移。
"""
from __future__ import annotations

from pathlib import Path

# 仓库根三件套：三者同时命中即可唯一确定仓库根，避免误命中上层或下层目录。
_REPO_ROOT_MARKERS = ("setup.cfg", "pyproject.toml", "main.py")


def get_repo_root() -> Path:
    """返回仓库根目录（含 setup.cfg/pyproject.toml/main.py 的最近祖先）。"""
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if all((candidate / marker).exists() for marker in _REPO_ROOT_MARKERS):
            return candidate
    raise RuntimeError(
        f"无法定位仓库根：自 {here} 向上未同时找到 {_REPO_ROOT_MARKERS}"
    )
