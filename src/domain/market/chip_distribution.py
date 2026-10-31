# -*- coding: utf-8 -*-
"""筹码分布数据模型（domain 层，纯数据结构）。

R3-S15a 从 ``data_provider.realtime_types`` 下沉：pipeline 仅为参数类型注解而
import ``data_provider``，与 application 的分层约束冲突；该数据结构本身无 IO /
框架 / 存储依赖，归属市场领域。``data_provider.realtime_types`` 保留同名
re-export，维持旧导入面与对象身份（``is``）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ChipDistribution:
    """
    筹码分布数据
    
    反映持仓成本分布和获利情况
    """
    code: str
    date: str = ""
    source: str = "akshare"
    
    # 获利情况
    profit_ratio: float = 0.0     # 获利比例(0-1)
    avg_cost: float = 0.0         # 平均成本
    
    # 筹码集中度
    cost_90_low: float = 0.0      # 90%筹码成本下限
    cost_90_high: float = 0.0     # 90%筹码成本上限
    concentration_90: float = 0.0  # 90%筹码集中度（越小越集中）
    
    cost_70_low: float = 0.0      # 70%筹码成本下限
    cost_70_high: float = 0.0     # 70%筹码成本上限
    concentration_70: float = 0.0  # 70%筹码集中度
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'code': self.code,
            'date': self.date,
            'source': self.source,
            'profit_ratio': self.profit_ratio,
            'avg_cost': self.avg_cost,
            'cost_90_low': self.cost_90_low,
            'cost_90_high': self.cost_90_high,
            'concentration_90': self.concentration_90,
            'concentration_70': self.concentration_70,
        }
    
    def get_chip_status(self, current_price: float) -> str:
        """
        获取筹码状态描述
        
        Args:
            current_price: 当前股价
            
        Returns:
            筹码状态描述
        """
        status_parts = []
        
        # 获利比例分析
        if self.profit_ratio >= 0.9:
            status_parts.append("获利盘极高(获利盘>90%)")
        elif self.profit_ratio >= 0.7:
            status_parts.append("获利盘较高(获利盘70-90%)")
        elif self.profit_ratio >= 0.5:
            status_parts.append("获利盘中等(获利盘50-70%)")
        elif self.profit_ratio >= 0.3:
            status_parts.append("套牢盘中等(套牢盘50-70%)")
        elif self.profit_ratio >= 0.1:
            status_parts.append("套牢盘较高(套牢盘70-90%)")
        else:
            status_parts.append("套牢盘极高(套牢盘>90%)")
        
        # 筹码集中度分析 (90%集中度 < 10% 表示集中)
        if self.concentration_90 < 0.08:
            status_parts.append("筹码高度集中")
        elif self.concentration_90 < 0.15:
            status_parts.append("筹码较集中")
        elif self.concentration_90 < 0.25:
            status_parts.append("筹码分散度中等")
        else:
            status_parts.append("筹码较分散")
        
        # 成本与现价关系
        if current_price > 0 and self.avg_cost > 0:
            cost_diff = (current_price - self.avg_cost) / self.avg_cost * 100
            if cost_diff > 20:
                status_parts.append(f"现价高于平均成本{cost_diff:.1f}%")
            elif cost_diff > 5:
                status_parts.append(f"现价略高于成本{cost_diff:.1f}%")
            elif cost_diff > -5:
                status_parts.append("现价接近平均成本")
            else:
                status_parts.append(f"现价低于平均成本{abs(cost_diff):.1f}%")
        
        return "，".join(status_parts)
