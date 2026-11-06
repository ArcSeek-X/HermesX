"""筹码纯计算归位保留原输入排序、权重归一与分位成本口径。"""

import pandas as pd
import pytest

from src.domain.analysis.chip_rules import compute_cyq_metrics


@pytest.mark.parametrize("weights", [[10, 20, 70], [1, 2, 7]])
def test_cyq_metrics_keep_unsorted_weighted_input_and_price_boundary(weights):
    frame = pd.DataFrame({"price": [12, 8, 10], "percent": weights})
    before = frame.copy(deep=True)
    assert compute_cyq_metrics(frame, 10) == {
        "获利比例": 0.9,
        "平均成本": 9.8,
        "90成本-低": 8,
        "90成本-高": 12,
        "90集中度": 0.2,
        "70成本-低": 8,
        "70成本-高": 10,
        "70集中度": 0.1111,
    }
    pd.testing.assert_frame_equal(frame, before)
