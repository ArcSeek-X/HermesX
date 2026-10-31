# -*- coding: utf-8 -*-
"""AlphaSift 数据目录解析纯规则（env 读取 + Path 组装，无 IO 副作用）。

application 热点缓存与 infrastructure 运行时桥共同复用，保持单一真源。
"""

from __future__ import annotations

import os
from pathlib import Path

from src.domain.analysis.payload_norm import _env_text

HRS_ALPHASIFT_DATA_DIR = Path("data") / "alphasift"


def _resolve_alphasift_data_dir() -> Path:
    configured = _env_text(os.getenv("ALPHASIFT_DATA_DIR"))
    if configured:
        return Path(configured)
    return HRS_ALPHASIFT_DATA_DIR
