# -*- coding: utf-8 -*-
"""R3-S16 契约测试：``normalize_schedule_times`` 单源化 + ``config`` 反向边。

本片把纯函数从 ``src/scheduler.py`` 抽到 ``src/domain/shared/schedule_times.py``，
再把 ``Scheduler`` 下沉 ``src/application/runtime/scheduler.py``。这里守住三件事：

1. 纯函数行为不变（去空 / 校验 HH:MM / 去重排序 / 非法回退）；
2. 三个调用点解析到**同一个函数对象**，防止有人在搬包后的模块里再抄一份实现；
3. ``src/config/settings.py`` 不再间接拉起 ``src/application``（D-07 的边界本身）。
"""

import subprocess
import sys
import unittest
from pathlib import Path

from src.application.runtime import scheduler as scheduler_module
from src.config.settings import normalize_schedule_times as config_schedule_times
from src.domain.shared.schedule_times import normalize_schedule_times

REPO_ROOT = Path(__file__).resolve().parents[1]


class NormalizeScheduleTimesTests(unittest.TestCase):
    def test_parses_comma_separated_string_and_sorts(self):
        self.assertEqual(normalize_schedule_times("18:00, 09:30 ,18:00"), ["09:30", "18:00"])

    def test_accepts_sequence_and_coerces_items(self):
        self.assertEqual(normalize_schedule_times(["21:05", " 07:00 "]), ["07:00", "21:05"])

    def test_drops_invalid_entries_and_uses_fallback(self):
        self.assertEqual(
            normalize_schedule_times("25:00,abc,", fallback_time="07:30"),
            ["07:30"],
        )

    def test_none_falls_back_to_default_1800(self):
        self.assertEqual(normalize_schedule_times(None), ["18:00"])

    def test_invalid_fallback_degrades_to_1800(self):
        self.assertEqual(normalize_schedule_times("", fallback_time="99:99"), ["18:00"])
        self.assertEqual(normalize_schedule_times(None, fallback_time=""), ["18:00"])


class SingleSourceTests(unittest.TestCase):
    def test_application_module_reuses_domain_function(self):
        self.assertIs(scheduler_module.normalize_schedule_times, normalize_schedule_times)

    def test_config_reuses_domain_function(self):
        self.assertIs(config_schedule_times, normalize_schedule_times)

    def test_importing_config_does_not_load_application_scheduler(self):
        """config → domain; config must not reach into application (D-07 边界)。"""
        code = (
            "import sys\n"
            "import src.config.settings\n"
            "print('src.application.runtime.scheduler' in sys.modules)\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=180,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "False", proc.stderr)


if __name__ == "__main__":
    unittest.main()
