"""
VaR风险价值计算
提供多种VaR计算方法：参数法、历史模拟法、蒙特卡洛模拟法
"""

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


class VaRCalculator:
    """
    VaR (Value at Risk) 风险价值计算器
    计算给定置信水平下，投资组合在一定持有期内的最大预期损失
    """

    def __init__(self, confidence_level: float = 0.95, holding_days: int = 1):
        """
        初始化VaR计算器

        Args:
            confidence_level: 置信水平，默认95%
            holding_days: 持有期，默认1天
        """
        self._confidence_level = confidence_level
        self._holding_days = holding_days

    def parametric_var(
        self,
        returns: pd.Series,
        portfolio_value: float,
    ) -> Dict[str, Any]:
        """
        参数法（方差-协方差法）计算VaR

        Args:
            returns: 历史收益率序列
            portfolio_value: 当前投资组合价值

        Returns:
            VaR计算结果
        """
        # 计算均值和标准差
        mu = returns.mean()
        sigma = returns.std(ddof=1)

        # 正态分布分位数
        from scipy.stats import norm

        z_score = norm.ppf(1 - self._confidence_level)

        # VaR = -V * (mu*dt + z*sigma*sqrt(dt))
        # z = ppf(1-confidence_level) is negative for confidence_level > 0.5,
        # so result becomes positive for loss
        # returns are daily returns, mu and sigma are already daily
        dt = self._holding_days
        var = -portfolio_value * (mu * dt + z_score * sigma * np.sqrt(dt))

        # 期望损失（ES）
        es = self._calculate_es_parametric(portfolio_value, mu, sigma, z_score, dt)

        return {
            "method": "parametric",
            "confidence_level": self._confidence_level,
            "holding_days": self._holding_days,
            "portfolio_value": portfolio_value,
            "var": max(var, 0),
            "expected_shortfall": es,
            "mu": mu,
            "sigma": sigma,
            "z_score": z_score,
        }

    def historical_simulation(
        self,
        returns: pd.Series,
        portfolio_value: float,
    ) -> Dict[str, Any]:
        """
        历史模拟法计算VaR

        Args:
            returns: 历史收益率序列
            portfolio_value: 当前投资组合价值

        Returns:
            VaR计算结果
        """
        sorted_returns = returns.sort_values(ascending=True)
        percentile = 1 - self._confidence_level
        index = int(len(sorted_returns) * percentile)
        if index >= len(sorted_returns):
            index = len(sorted_returns) - 1

        var_return = sorted_returns.iloc[index]
        # returns are daily returns, scale to holding days
        var = -portfolio_value * var_return * self._holding_days

        # 计算期望损失
        tail_returns = sorted_returns[sorted_returns <= var_return]
        es = -portfolio_value * tail_returns.mean() * self._holding_days if len(tail_returns) > 0 else var

        return {
            "method": "historical",
            "confidence_level": self._confidence_level,
            "holding_days": self._holding_days,
            "portfolio_value": portfolio_value,
            "var": max(var, 0),
            "expected_shortfall": es,
            "percentile_index": index,
            "sample_size": len(returns),
        }

    def monte_carlo_simulation(
        self,
        returns: pd.Series,
        portfolio_value: float,
        simulations: int = 10000,
        seed: int = 42,
    ) -> Dict[str, Any]:
        """
        蒙特卡洛模拟法计算VaR

        Args:
            returns: 历史收益率序列（用于估计参数）
            portfolio_value: 当前投资组合价值
            simulations: 模拟次数
            seed: 随机种子

        Returns:
            VaR计算结果
        """
        np.random.seed(seed)

        # 参数估计
        mu = returns.mean()
        sigma = returns.std(ddof=1)

        # returns are daily returns, mu and sigma already daily
        dt = self._holding_days

        # 生成模拟收益率
        simulated_returns = np.random.normal(loc=mu * dt, scale=sigma * np.sqrt(dt), size=simulations)

        # 排序找分位数
        simulated_returns.sort()
        percentile = int(simulations * (1 - self._confidence_level))
        var_return = simulated_returns[percentile]
        var = -portfolio_value * var_return

        # 计算期望损失
        tail_returns = simulated_returns[simulated_returns <= var_return]
        es = -portfolio_value * tail_returns.mean() if len(tail_returns) > 0 else var

        return {
            "method": "monte_carlo",
            "confidence_level": self._confidence_level,
            "holding_days": self._holding_days,
            "portfolio_value": portfolio_value,
            "simulations": simulations,
            "var": max(var, 0),
            "expected_shortfall": es,
            "mu": mu,
            "sigma": sigma,
        }

    def calculate_portfolio_var(
        self,
        returns_df: pd.DataFrame,
        weights: List[float],
        portfolio_value: float,
        method: str = "parametric",
    ) -> Dict[str, Any]:
        """
        计算投资组合VaR

        Args:
            returns_df: 各资产收益率，columns为资产，index为时间
            weights: 资产权重
            portfolio_value: 投资组合总价值
            method: 计算方法 'parametric'|'historical'|'monte_carlo'

        Returns:
            VaR计算结果
        """
        # 计算投资组合收益率
        weights_arr = np.array(weights)
        portfolio_returns = returns_df.dot(weights_arr)

        if method == "parametric":
            result = self.parametric_var(portfolio_returns, portfolio_value)
        elif method == "historical":
            result = self.historical_simulation(portfolio_returns, portfolio_value)
        elif method == "monte_carlo":
            result = self.monte_carlo_simulation(portfolio_returns, portfolio_value)
        else:
            raise ValueError(f"Unknown method: {method}")

        return result

    def _calculate_es_parametric(
        self,
        portfolio_value: float,
        mu: float,
        sigma: float,
        z_score: float,
        dt: float,
    ) -> float:
        """计算参数法期望损失（Expected Shortfall）"""
        from scipy.stats import norm

        pdf_z = norm.pdf(z_score)
        cdf_z = 1 - self._confidence_level
        es = portfolio_value * (-mu * dt + sigma * np.sqrt(dt) * pdf_z / cdf_z)
        return max(es, 0)

    def set_parameters(self, confidence_level: Optional[float] = None, holding_days: Optional[int] = None) -> None:
        """设置参数"""
        if confidence_level is not None:
            self._confidence_level = confidence_level
        if holding_days is not None:
            self._holding_days = holding_days
