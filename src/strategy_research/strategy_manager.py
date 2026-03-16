"""
策略研究统一管理器
作为策略研究子系统的统一入口，整合所有模块提供一站式服务
"""
from typing import Dict, Any, List, Optional, Type
import pandas as pd

from src.strategy_research.base import (
    BaseStrategy,
    BacktestResult,
    StrategyStatus,
)
from src.strategy_research.strategy_management import (
    StrategyManager as MetadataManager,
    StrategyMetadata,
    StrategyVersion,
)
from src.strategy_research.backtest_engine import (
    BacktestEngine,
    BacktestConfig,
)
from src.strategy_research.simulation_trading import (
    SimulationEngine,
    SimulationConfig,
)
from src.strategy_research.strategy_validator import (
    detect_overfit,
    rolling_window_test,
    scan_parameter,
)
from src.strategy_research.report_generator import (
    save_report,
    generate_text_report,
)


class StrategyResearchManager:
    """
    策略研究统一管理器
    - 策略元数据和版本管理
    - 回测执行
    - 策略验证
    - 模拟交易
    - 报告生成
    """

    def __init__(
        self,
        storage_dir: str = "data/strategies",
        strategy_dir: str = "strategies",
    ):
        self._metadata_manager = MetadataManager(storage_dir, strategy_dir)

    def create_strategy(
        self,
        strategy_id: str,
        strategy_name: str,
        class_path: str,
        description: str,
        author: str,
        params: Dict,
        tags: Optional[List[str]] = None,
    ) -> Dict:
        """创建新策略"""
        success, msg, meta = self._metadata_manager.create_strategy(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            strategy_class_path=class_path,
            description=description,
            author=author,
            params=params,
            tags=tags,
        )
        return {
            'success': success,
            'message': msg,
            'metadata': meta,
        }

    def backtest(
        self,
        strategy_id: str,
        data: pd.DataFrame,
        config: Optional[BacktestConfig] = None,
    ) -> BacktestResult:
        """回测策略"""
        strategy = self._metadata_manager.instantiate(strategy_id)
        if strategy is None:
            raise ValueError(f"Cannot instantiate strategy {strategy_id}")

        engine = BacktestEngine(data, config)
        result = engine.run(strategy)
        return result

    def backtest_custom(
        self,
        strategy_class: Type[BaseStrategy],
        params: Dict,
        data: pd.DataFrame,
        config: Optional[BacktestConfig] = None,
    ) -> BacktestResult:
        """回测自定义策略实例"""
        strategy = strategy_class(params=params)
        engine = BacktestEngine(data, config)
        return engine.run(strategy)

    def start_simulation(
        self,
        strategy_id: str,
        config: Optional[SimulationConfig] = None,
    ) -> SimulationEngine:
        """启动模拟交易"""
        strategy = self._metadata_manager.instantiate(strategy_id)
        if strategy is None:
            raise ValueError(f"Cannot instantiate strategy {strategy_id}")

        sim_config = config or SimulationConfig()
        engine = SimulationEngine(strategy, sim_config)
        return engine

    def validate_overfit(self, backtest_result: BacktestResult) -> Dict:
        """过拟合检测"""
        return detect_overfit(backtest_result)

    def parameter_scan(
        self,
        parameter_name: str,
        values: List,
        base_params: Dict,
        strategy_class: Type[BaseStrategy],
        data: pd.DataFrame,
        config: Optional[BacktestConfig] = None,
    ) -> Dict:
        """参数敏感性扫描"""
        engine = BacktestEngine(data, config)
        return scan_parameter(parameter_name, values, base_params, strategy_class, engine)

    def rolling_out_of_sample_test(
        self,
        data: pd.DataFrame,
        strategy_class: Type[BaseStrategy],
        params: Dict,
        train_window_days: int = 252 * 3,
        test_window_days: int = 252,
        config: Optional[BacktestConfig] = None,
    ) -> Dict:
        """滚动样本外测试"""
        from src.strategy_research.strategy_validator import rolling_window_test
        return rolling_window_test(
            data, strategy_class, params, train_window_days, test_window_days, config
        )

    def save_report(
        self,
        result: BacktestResult,
        output_path: str,
        format: str = 'html',
    ) -> Dict:
        """保存回测报告"""
        return save_report(result, output_path, format)

    def get_text_report(self, result: BacktestResult) -> str:
        """获取文本报告"""
        return generate_text_report(result)

    def list_strategies(
        self,
        status: Optional[StrategyStatus] = None,
        tag: Optional[str] = None,
    ) -> List[StrategyMetadata]:
        """列出策略"""
        return self._metadata_manager.list_strategies(status, tag)

    def get_metadata(self, strategy_id: str) -> Optional[StrategyMetadata]:
        """获取策略元数据"""
        return self._metadata_manager.get_metadata(strategy_id)

    def update_status(self, strategy_id: str, status: StrategyStatus) -> bool:
        """更新策略状态"""
        return self._metadata_manager.update_status(strategy_id, status)

    def add_version(
        self,
        strategy_id: str,
        version_code: str,
        params: Dict,
        change_note: str = "",
        created_by: int = 0,
    ) -> bool:
        """添加新版本"""
        success, msg, _ = self._metadata_manager.create_new_version(
            strategy_id, version_code, params, created_by, change_note
        )
        return success

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            'status': 'ok',
            'strategies': self._metadata_manager.count(),
            'metadata_manager': self._metadata_manager.health_check(),
        }
