# -*- coding: utf-8 -*-
"""调度时间字符串的规范化纯规则。

来源：自 ``src/scheduler.py``（原 L27-48）逐字抽出，R3-S16 随 ``Scheduler`` 下沉
``src/application/runtime/`` 一并单源化。抽出的理由不是"看起来更像领域"，而是两条
真实的调用边——``src/config/settings.py``（解析 ``SCHEDULE_TIMES``）与
``src/application/runtime/scheduler.py``（注册 daily job）都需要同一套
"去空、校验 HH:MM、去重排序、非法回退默认值"的语义。函数留在 ``scheduler`` 会让
``config → application`` 形成目标依赖图中不存在的反向边，落 domain 后两条边都变成
"外层指向内层"。

只依赖 stdlib（``re`` / ``typing``），无 IO、无配置读取、无时间获取——给定入参即
确定输出，可直接单测。
"""

import re
from typing import List, Optional, Sequence, Union


def normalize_schedule_times(
    schedule_times: Optional[Union[Sequence[str], str]],
    *,
    fallback_time: str = "18:00",
) -> List[str]:
    """Return sorted unique HH:MM schedule times with SCHEDULE_TIME fallback."""
    if isinstance(schedule_times, str):
        raw_items = [item.strip() for item in schedule_times.split(",")]
    elif schedule_times is None:
        raw_items = []
    else:
        raw_items = [str(item).strip() for item in schedule_times]

    valid = {
        item
        for item in raw_items
        if item and re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", item)
    }
    if not valid:
        fallback = (fallback_time or "18:00").strip() or "18:00"
        valid.add(fallback if re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", fallback) else "18:00")
    return sorted(valid)
