"""
情景分析器
分析不同市场情景下的投资组合风险敞口
"""

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


class Scenario:
    """情景定义"""

    def __init__(
        self,
        scenario_id: str,
        name: str,
        description: str,
        factor_changes: Dict[str, float],
    ):
        """
        初始化情景

        Args:
            scenario_id: 情景ID
            name: 情景名称
            description: 情景描述
            factor_changes: 因子变化字典，factor -> change_pct
        """
        self.scenario_id = scenario_id
        self.name = name
        self.description = description
        self.factor_changes = factor_changes


class ScenarioAnalyzer:
    """
    情景分析器
    基于因子模型分析不同市场情景对投资组合的影响
    """

    def __init__(self):
        self._scenarios: Dict[str, Scenario] = {}
        self._init_standard_scenarios()

    def _init_standard_scenarios(self) -> None:
        """初始化标准情景"""
        # 利率上升情景
        # 利率上升100bps -> 固定收益资产价格下跌
        self.add_scenario(
            Scenario(
                scenario_id="rate_up_100bp",
                name="利率上升100基点",
                description="市场利率整体上升100个基点，金融股下跌",
                factor_changes={
                    "interest_rate": -1.0,  # 利率上升 -> 价格下跌，所以负影响
                    "bank_index": -0.10,
                    "insurance_index": -0.08,
                    "real_estate_index": -0.15,
                },
            )
        )
        # 利率下降情景
        self.add_scenario(
            Scenario(
                scenario_id="rate_down_50bp",
                name="利率下降50基点",
                description="市场利率整体下降50个基点",
                factor_changes={
                    "interest_rate": -0.5,
                    "bank_index": 0.05,
                    "insurance_index": 0.04,
                    "real_estate_index": 0.08,
                },
            )
        )
        # 油价上涨情景
        self.add_scenario(
            Scenario(
                scenario_id="oil_up_20pct",
                name="油价上涨20%",
                description="国际油价上涨20%",
                factor_changes={
                    "oil_price": 0.20,
                    "energy_index": 0.15,
                    "transport_index": -0.08,
                },
            )
        )
        # 通胀上升情景
        self.add_scenario(
            Scenario(
                scenario_id="inflation_up",
                name="通胀超预期上升",
                description="CPI通胀超预期上升，央行加息",
                factor_changes={
                    "inflation": 1.0,
                    "interest_rate": 0.5,
                    "market_index": -0.05,
                    "consumer_staples": 0.02,
                },
            )
        )

    def add_scenario(self, scenario: Scenario) -> None:
        """添加情景"""
        self._scenarios[scenario.scenario_id] = scenario

    def remove_scenario(self, scenario_id: str) -> bool:
        """删除情景"""
        if scenario_id in self._scenarios:
            del self._scenarios[scenario_id]
            return True
        return False

    def get_scenario(self, scenario_id: str) -> Optional[Scenario]:
        """获取情景"""
        return self._scenarios.get(scenario_id)

    def list_scenarios(self) -> List[Dict[str, str]]:
        """列出所有情景"""
        return [
            {
                "id": s.scenario_id,
                "name": s.name,
                "description": s.description,
            }
            for s in self._scenarios.values()
        ]

    def analyze(
        self,
        scenario_id: str,
        portfolio_exposures: Dict[str, float],
        current_value: float,
    ) -> Dict[str, Any]:
        """
        执行情景分析

        Args:
            scenario_id: 情景ID
            portfolio_exposures: 投资组合各因子敞口 {factor: exposure}
            current_value: 当前投资组合价值

        Returns:
            分析结果
        """
        scenario = self._scenarios.get(scenario_id)
        if scenario is None:
            return {
                "success": False,
                "error": f"Scenario not found: {scenario_id}",
            }

        # 计算总影响
        total_pnl = 0.0
        factor_results: List[Dict[str, Any]] = []

        for factor, change_pct in scenario.factor_changes.items():
            if factor not in portfolio_exposures:
                continue

            exposure = portfolio_exposures[factor]
            # 对于百分比变化，影响 = 敞口 * 变化百分比
            pnl = exposure * change_pct
            total_pnl += pnl

            factor_results.append(
                {
                    "factor": factor,
                    "change_pct": change_pct * 100,
                    "exposure": exposure,
                    "contribution_pnl": pnl,
                }
            )

        total_pnl_pct = (total_pnl / current_value) * 100 if current_value > 0 else 0

        return {
            "success": True,
            "scenario_id": scenario_id,
            "scenario_name": scenario.name,
            "current_value": current_value,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "factor_results": factor_results,
        }

    def analyze_all(
        self,
        portfolio_exposures: Dict[str, float],
        current_value: float,
    ) -> Dict[str, Any]:
        """分析所有情景"""
        results = {}
        worst_pnl = 0.0
        worst_scenario = None

        for scenario_id in self._scenarios:
            result = self.analyze(scenario_id, portfolio_exposures, current_value)
            results[scenario_id] = result
            if result["success"] and result["total_pnl"] < worst_pnl:
                worst_pnl = result["total_pnl"]
                worst_scenario = scenario_id

        summary = {
            "total_scenarios": len(results),
            "worst_pnl": worst_pnl,
            "worst_pnl_pct": (worst_pnl / current_value) * 100 if current_value > 0 else 0,
            "worst_scenario": worst_scenario,
        }

        return {
            "results": results,
            "summary": summary,
        }

    def calculate_risk_contribution(
        self,
        scenario_id: str,
        portfolio_exposures: Dict[str, float],
        current_value: float,
    ) -> Dict[str, float]:
        """计算各因子对总体风险的贡献百分比"""
        result = self.analyze(scenario_id, portfolio_exposures, current_value)
        if not result["success"]:
            return {}

        total_abs_pnl = sum(abs(r["contribution_pnl"]) for r in result["factor_results"])
        if total_abs_pnl == 0:
            return {}

        contributions = {}
        for r in result["factor_results"]:
            contributions[r["factor"]] = abs(r["contribution_pnl"]) / total_abs_pnl * 100

        return contributions
