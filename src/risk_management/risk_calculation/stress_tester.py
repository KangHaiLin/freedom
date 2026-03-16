"""
压力测试器
在极端市场情景下测试投资组合的风险承受能力
"""
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np


class StressScenario:
    """压力测试情景定义"""

    def __init__(
        self,
        scenario_id: str,
        name: str,
        description: str,
        shocks: Dict[str, float],
        baseline_pnl: Optional[float] = None,
    ):
        """
        初始化压力情景

        Args:
            scenario_id: 情景ID
            name: 情景名称
            description: 情景描述
            shocks: 资产冲击字典，ts_code -> 价格变化百分比（负数为下跌）
            baseline_pnl: 基准盈亏
        """
        self.scenario_id = scenario_id
        self.name = name
        self.description = description
        self.shocks = shocks
        self.baseline_pnl = baseline_pnl


class StressTester:
    """
    压力测试器
    支持多种极端市场情景测试，评估投资组合在极端情况下的损失
    """

    def __init__(self):
        self._scenarios: Dict[str, StressScenario] = {}
        self._init_standard_scenarios()

    def _init_standard_scenarios(self) -> None:
        """初始化标准压力测试情景"""
        # 系统性下跌情景
        self.add_scenario(StressScenario(
            scenario_id='systemic_down_10',
            name='系统性下跌10%',
            description='整个市场系统性下跌10%',
            shocks={},  # 空表示所有股票同幅度下跌
        ))
        self.add_scenario(StressScenario(
            scenario_id='systemic_down_20',
            name='系统性下跌20%',
            description='整个市场系统性下跌20%',
            shocks={},
        ))
        # 金融危机情景
        self.add_scenario(StressScenario(
            scenario_id='financial_crisis_2008',
            name='2008金融危机情景',
            description='类似2008金融危机，金融股下跌40%，大盘下跌30%',
            shocks={
                'FINANCE': -0.40,
                'DEFAULT': -0.30,
            },
        ))
        # 流动性危机情景
        self.add_scenario(StressScenario(
            scenario_id='liquidity_crisis',
            name='流动性危机情景',
            description='小盘股跌幅超大盘，流动性枯竭带来额外下跌',
            shocks={
                'LARGE_CAP': -0.15,
                'MID_CAP': -0.25,
                'SMALL_CAP': -0.40,
            },
        ))

    def add_scenario(self, scenario: StressScenario) -> None:
        """添加压力测试情景"""
        self._scenarios[scenario.scenario_id] = scenario

    def remove_scenario(self, scenario_id: str) -> bool:
        """删除压力测试情景"""
        if scenario_id in self._scenarios:
            del self._scenarios[scenario_id]
            return True
        return False

    def get_scenario(self, scenario_id: str) -> Optional[StressScenario]:
        """获取情景"""
        return self._scenarios.get(scenario_id)

    def list_scenarios(self) -> List[Dict[str, str]]:
        """列出所有情景"""
        return [
            {
                'id': s.scenario_id,
                'name': s.name,
                'description': s.description,
            }
            for s in self._scenarios.values()
        ]

    def run_stress_test(
        self,
        scenario_id: str,
        current_positions: Dict[str, Dict[str, Any]],
        custom_shocks: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        执行压力测试

        Args:
            scenario_id: 情景ID
            current_positions: 当前持仓 {ts_code: {'quantity': 数量, 'last_price': 价格, ...}}
            custom_shocks: 自定义冲击，覆盖情景定义

        Returns:
            压力测试结果
        """
        scenario = self._scenarios.get(scenario_id)
        if scenario is None:
            return {
                'success': False,
                'error': f'Scenario not found: {scenario_id}',
            }

        # 合并冲击
        shocks = scenario.shocks.copy()
        if custom_shocks:
            shocks.update(custom_shocks)

        # 计算损失
        total_initial_value = 0.0
        total_final_value = 0.0
        position_results: List[Dict[str, Any]] = []

        for ts_code, position in current_positions.items():
            quantity = position.get('quantity', 0)
            last_price = position.get('last_price', 0.0)
            initial_value = quantity * last_price
            total_initial_value += initial_value

            # 获取该股票的冲击
            shock = self._get_shock(ts_code, shocks, position, scenario_id)
            final_price = last_price * (1 + shock)
            final_value = quantity * final_price
            total_final_value += final_value

            position_results.append({
                'ts_code': ts_code,
                'initial_value': initial_value,
                'final_value': final_value,
                'pnl': final_value - initial_value,
                'pnl_pct': shock * 100,
            })

        # 汇总结果
        total_pnl = total_final_value - total_initial_value
        pnl_pct = (total_pnl / total_initial_value) * 100 if total_initial_value > 0 else 0

        return {
            'success': True,
            'scenario_id': scenario_id,
            'scenario_name': scenario.name,
            'scenario_description': scenario.description,
            'total_initial_value': total_initial_value,
            'total_final_value': total_final_value,
            'total_pnl': total_pnl,
            'total_pnl_pct': pnl_pct,
            'position_results': position_results,
        }

    def run_all_scenarios(
        self,
        current_positions: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        对所有情景执行压力测试

        Args:
            current_positions: 当前持仓

        Returns:
            所有情景测试结果
        """
        results = {}
        worst_loss_pct = 0
        worst_scenario = None

        for scenario_id in self._scenarios:
            result = self.run_stress_test(scenario_id, current_positions)
            results[scenario_id] = result
            if result['success']:
                if result['total_pnl_pct'] < worst_loss_pct:
                    worst_loss_pct = result['total_pnl_pct']
                    worst_scenario = scenario_id

        summary = {
            'total_scenarios': len(results),
            'successful_scenarios': sum(1 for r in results.values() if r['success']),
            'worst_loss_pct': worst_loss_pct,
            'worst_scenario': worst_scenario,
        }

        return {
            'results': results,
            'summary': summary,
        }

    def _get_shock(
        self,
        ts_code: str,
        shocks: Dict[str, float],
        position: Dict[str, Any],
        scenario_id: str = "",
    ) -> float:
        """获取股票对应的冲击"""
        if ts_code in shocks:
            return shocks[ts_code]
        # 按板块
        sector = position.get('sector')
        if sector in shocks:
            return shocks[sector]
        # 按市值分类
        market_cap = position.get('market_cap')
        if 'LARGE_CAP' in shocks and market_cap and market_cap > 500e8:
            return shocks['LARGE_CAP']
        if 'MID_CAP' in shocks and market_cap and market_cap > 100e8:
            return shocks['MID_CAP']
        if 'SMALL_CAP' in shocks:
            return shocks['SMALL_CAP']
        # 默认冲击
        if 'DEFAULT' in shocks:
            return shocks['DEFAULT']
        # 空字典表示全部下跌，从scenario_id判断幅度
        if len(shocks) == 0:
            if '10' in scenario_id:
                return -0.10
            elif '20' in scenario_id:
                return -0.20
        # 默认0，不变化
        return 0.0
